import importlib.util,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('calculator',Path(__file__).parents[1]/'scripts'/'calculate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def event(id,kind,date='2024-01-01',**extra):
 return {'id':id,'kind':kind,'date':date,'account':'TEST-A','asset':'DEMO','currency':'USD','country':'US','tax_category':'income' if kind in ['dividend','interest'] else 'capital','reviewed':True,'source':{'file':'synthetic','locator':id},**extra}
def doc(events,**extra):
 return {'completeness':{'verified':True,'scope':'synthetic requested scope','basis':'all synthetic evidence covered','gaps':[]},'config':{'year':2024,'fx':{'USD':'1'},'fx_basis':'synthetic test rate; not a real FX quote','capital_netting':'per_disposal','tax_rate':'0.20',**extra},'events':events}
class Calculations(unittest.TestCase):
 def test_fifo(self):
  r=m.calculate(doc([event('a','buy',quantity='2',amount='20',fees='2'),event('b','buy',quantity='1',amount='20',fees='0'),event('s','sell',quantity='2.5',amount='50',fees='1')]))
  self.assertEqual(r['dispositions'][0]['gain'],'17.0');self.assertEqual(r['subset_tax_rmb'],'3.40')
 def test_missing_cost_is_not_zero(self):
  r=m.calculate(doc([event('s','sell',quantity='2',amount='50',fees='0')]))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('dispositions',r)
 def test_short(self):
  r=m.calculate(doc([event('a','short',quantity='10',amount='100',fees='1'),event('b','cover',quantity='4',amount='32',fees='1'),event('c','cover',quantity='6',amount='48',fees='1')]))
  self.assertEqual(sum(m.dec(x['gain']) for x in r['dispositions']),m.dec('17'));self.assertEqual(r['open_positions'],[])
 def test_split(self):
  r=m.calculate(doc([event('b','buy',quantity='2',amount='20',fees='0'),event('sp','split',factor='10'),event('s','sell',quantity='10',amount='30',fees='0')]))
  self.assertEqual(r['dispositions'][0]['gain'],'20');self.assertEqual(r['open_positions'][0]['lots'][0]['amount'],'10')
 def test_transfer_preserves_cost(self):
  r=m.calculate(doc([event('b','buy',quantity='2',amount='20',fees='2'),event('t','transfer',quantity='2',to_account='TEST-B'),event('s','sell',account='TEST-B',quantity='2',amount='40',fees='0')]))
  self.assertEqual(r['dispositions'][0]['gain'],'18')
 def test_next_year_refund(self):
  r=m.calculate(doc([event('d','dividend',amount='100'),event('w','withheld',amount='10',income_id='d',income_year=2024,eligible=True,evidence='synthetic tax certificate'),event('r','refund','2025-02-01',amount='4',withholding_id='w')]))
  self.assertEqual(r['countries'][0]['credit_rmb'],'6.00');self.assertEqual(r['subset_tax_rmb'],'14.00')
 def test_unverified_tax_not_credit(self):
  r=m.calculate(doc([event('d','dividend',amount='100'),event('w','withheld',amount='10',income_id='d',income_year=2024,eligible=False,evidence='')]))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('subset_tax_rmb',r)
 def test_unknown_product_propagates(self):
  r=m.calculate(doc([event('u','exercise',quantity='1'),event('s','sell',quantity='1',amount='100',fees='0')]))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('dispositions',r);self.assertEqual(len(r['review']),2)
 def test_reject_duplicate(self):
  with self.assertRaises(ValueError):m.calculate(doc([event('d','dividend',amount='10'),event('d','dividend',amount='10')]))
 def test_annual_netting_needs_basis(self):
  with self.assertRaises(ValueError):m.calculate(doc([],capital_netting='country_year'))
 def test_float_rejected(self):
  r=m.calculate(doc([event('d','dividend',amount=0.1)]));self.assertEqual(r['status'],'needs_data')
 def test_over_refund_blocks_credit(self):
  r=m.calculate(doc([event('d','dividend',amount='100'),event('w','withheld',amount='10',income_id='d',income_year=2024,eligible=True,evidence='synthetic'),event('r','refund','2025-01-01',amount='12',withholding_id='w')]))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('countries',r)
 def test_transfer_original_fifo(self):
  r=m.calculate(doc([event('a','buy','2024-01-01',quantity='1',amount='10',fees='0'),event('b','buy','2024-02-01',account='TEST-B',quantity='1',amount='100',fees='0'),event('t','transfer','2024-03-01',quantity='1',to_account='TEST-B'),event('s','sell','2024-04-01',account='TEST-B',quantity='1',amount='200',fees='0')]))
  self.assertEqual(r['dispositions'][0]['gain'],'190')
 def test_empty_transfer_account(self):
  r=m.calculate(doc([event('a','buy',quantity='1',amount='10',fees='0'),event('t','transfer',quantity='1',to_account='')]))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('open_positions',r)
 def test_tax_source_file_required(self):
  r=m.calculate(doc([event('d','dividend',amount='100'),event('w','withheld',amount='10',income_id='d',income_year=2024,eligible=True,evidence=True,source={'locator':'1'})]))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('countries',r)
 def test_refund_source_file_required(self):
  r=m.calculate(doc([event('d','dividend',amount='100'),event('w','withheld',amount='10',income_id= 'd',income_year=2024,eligible=True,evidence='synthetic'),event('r','refund','2025-01-01',amount='1',withholding_id='w',source={'locator':'1'})]))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('countries',r)
 def test_missing_completeness_releases_no_numbers(self):
  d=doc([event('d','dividend',amount='100')]);d.pop('completeness')
  r=m.calculate(d);self.assertEqual(r['status'],'needs_data');self.assertNotIn('subset_tax_rmb',r);self.assertNotIn('incomes',r)
 def test_incomplete_scope_releases_no_numbers(self):
  d=doc([event('d','dividend',amount='100')]);d['completeness']['gaps']=[{'reason':'missing another account'}]
  r=m.calculate(d);self.assertEqual(r['status'],'needs_data');self.assertNotIn('countries',r)
 def test_deferred_credit_does_not_block_base_tax(self):
  r=m.calculate(doc([event('d','dividend',amount='100'),event('w','withheld',amount='10',income_id='d',income_year=2024,eligible=False)],credit_mode='deferred'))
  self.assertEqual(r['status'],'base_ready');self.assertEqual(r['subset_tax_rmb'],'20.00');self.assertIn('not final',r['credit_status'])
 def test_core_gap_still_blocks_deferred_result(self):
  r=m.calculate(doc([event('s','sell',quantity='1',amount='100',fees='0')],credit_mode='deferred'))
  self.assertEqual(r['status'],'needs_data');self.assertNotIn('subset_tax_rmb',r)
 def test_broker_year_default_offsets_same_broker(self):
  d=doc([event('a','buy',quantity='1',amount='100',fees='0'),event('b','sell',quantity='1',amount='150',fees='0'),event('c','buy',account='TEST-B',quantity='1',amount='100',fees='0'),event('e','sell',account='TEST-B',quantity='1',amount='80',fees='0')]);d['config'].pop('capital_netting')
  for e in d['events']:e['broker']='ONE'
  r=m.calculate(d);self.assertEqual(r['subset_tax_rmb'],'6.00');self.assertEqual(r['brokers'][0]['annual_gross_sales_rmb'],'230.00');self.assertEqual(r['brokers'][0]['matched_cost_and_fees_rmb'],'200.00')
 def test_broker_year_does_not_offset_other_broker(self):
  d=doc([event('a','buy',quantity='1',amount='100',fees='0'),event('b','sell',quantity='1',amount='150',fees='0'),event('c','buy',account='TEST-B',quantity='1',amount='100',fees='0'),event('e','sell',account='TEST-B',quantity='1',amount='80',fees='0')],capital_netting='broker_year')
  r=m.calculate(d);self.assertEqual(r['subset_tax_rmb'],'10.00')
 def test_short_report_proceeds_cost_reconcile(self):
  r=m.calculate(doc([event('a','short',quantity='10',amount='100',fees='1'),event('b','cover',quantity='10',amount='80',fees='1')],capital_netting='broker_year'))
  b=r['brokers'][0];self.assertEqual(b['realized_matched_proceeds_rmb'],'100.00');self.assertEqual(b['matched_cost_and_fees_rmb'],'82.00');self.assertEqual(b['capital_net_income_rmb'],'18.00')
if __name__=='__main__':unittest.main()
