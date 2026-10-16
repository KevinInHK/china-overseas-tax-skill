"""Decimal FIFO and conditional tax calculations for reviewed investment events.
No network, broker parsing, identity collection, or embedded FX rates.
"""
import argparse
import json
from collections import defaultdict
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ZERO = Decimal('0')

def dec(value):
    if isinstance(value, (float, bool)) or value is None:
        raise ValueError('Use a decimal string; missing value is not zero')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Non-finite number')
    return result

def positive(value):
    result = dec(value)
    if result <= 0:
        raise ValueError('Expected positive number')
    return result

def money(value):
    return str(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

def calculate(document):
    cfg = document['config']
    year = int(cfg['year'])
    completeness = document.get('completeness', {})
    if completeness.get('verified') is not True or not completeness.get('scope') or not completeness.get('basis') or completeness.get('gaps') != []:
        return {'status':'needs_data','review':completeness.get('gaps') or [{'reason':'Completeness of requested scope not verified'}],'message':'Incomplete data: no calculation result released'}
    mode = cfg.get('capital_netting','broker_year')
    if mode not in ('per_disposal', 'country_year', 'broker_year'):
        raise ValueError('Select an explicit capital_netting scenario')
    if mode == 'country_year' and not cfg.get('netting_basis'):
        raise ValueError('Annual netting requires an explicit basis, not an automatic assumption')
    if not cfg.get('fx_basis'):
        raise ValueError('FX basis must be recorded')
    rates = {k: positive(v) for k, v in cfg['fx'].items()}
    rate = dec(cfg['tax_rate'])
    if not ZERO <= rate <= 1:
        raise ValueError('Invalid tax rate')
    events = deepcopy(document['events'])
    review, dispositions, incomes = [], [], []
    positions = defaultdict(list)
    original_events = {e['id']:e for e in events}
    blocked, seen = set(), set()
    last_date = None
    parsed = []
    for sequence, event in enumerate(events):
        event['_sequence'] = sequence
        try:
            parsed_date = date.fromisoformat(event['date'])
            if last_date and parsed_date < last_date:
                raise ValueError('Events must be chronological; do not silently sort same-day events')
            last_date = parsed_date
        except (KeyError, ValueError) as exc:
            raise ValueError('Invalid chronology at event ' + str(sequence)) from exc
        if not event.get('id') or event['id'] in seen:
            raise ValueError('Missing or duplicate event id; resolve duplicate evidence first')
        seen.add(event['id'])
        event['_year'] = parsed_date.year
        parsed.append(event)

    def issue(e, message, poison=True):
        review.append({'id': e['id'], 'reason': message, 'source': e.get('source')})
        if poison and all(e.get(k) for k in ('account','asset','currency')):
            blocked.add((e['account'],e['asset'],e['currency']))

    def consume(lots, quantity):
        if sum((lot['quantity'] for lot in lots), ZERO) < quantity:
            raise ValueError('Missing historical cost/opening position; market value cannot substitute')
        remainder, amount, matches = quantity, ZERO, []
        while remainder:
            lot = lots[0]
            qty = min(lot['quantity'], remainder)
            part = lot['amount'] if qty == lot['quantity'] else lot['amount'] * qty / lot['quantity']
            amount += part
            matches.append({'opening_id':lot['opening_id'],'quantity':str(qty),'amount':str(part),'source':lot['source']})
            lot['quantity'] -= qty
            lot['amount'] -= part
            remainder -= qty
            if not lot['quantity']:
                lots.pop(0)
        return amount, matches

    for e in parsed:
        kind = e.get('kind')
        if kind in ('withheld','refund'):
            continue
        if e['_year'] > year:
            continue
        key = (e.get('account'),e.get('asset'),e.get('currency'))
        try:
            if not e.get('reviewed') or not e.get('source',{}).get('file') or not e.get('source',{}).get('locator'):
                raise ValueError('Unreviewed fact or missing source locator')
            if not all(key):
                raise ValueError('Missing account, asset or currency')
            if kind not in ('buy','sell','short','cover','split','transfer','dividend','interest'):
                raise ValueError('Event requires product-specific interpretation: ' + str(kind))
            if key in blocked:
                raise ValueError('Earlier unresolved event affects this position')
            if kind in ('dividend','interest'):
                amount = positive(e['amount'])
                if e['_year'] == year:
                    if e.get('tax_category') != 'income' or not e.get('country') or e['country']=='CN':
                        raise ValueError('Income category/source country not reviewed for overseas calculation')
                    incomes.append({'account':e['account'],'broker':e.get('broker',e['account']),'id':e['id'],'country':e['country'],'gross_rmb':amount*rates[e['currency']],'source':e['source']})
                continue
            lots = positions[key]
            if kind == 'split':
                factor = positive(e['factor'])
                for lot in lots:
                    lot['quantity'] *= factor
                continue
            quantity = positive(e['quantity'])
            if kind == 'transfer':
                if not isinstance(e.get('to_account'),str) or not e['to_account'].strip():
                    raise ValueError('Missing destination account')
                dest=(e['to_account'],e['asset'],e['currency'])
                if dest == key or dest in blocked or any(l['side']=='short' for l in lots):
                    raise ValueError('Invalid/uncertain transfer; short transfer requires review')
                if any(l['side']=='short' for l in positions[dest]):
                    raise ValueError('Transfer destination contains short position')
                if sum((l['quantity'] for l in lots),ZERO)<quantity:
                    raise ValueError('Transfer original lots missing')
                remaining=quantity
                while remaining:
                    lot=lots[0];qty=min(lot['quantity'],remaining);part=lot['amount'] if qty==lot['quantity'] else lot['amount']*qty/lot['quantity']
                    positions[dest].append({**lot,'quantity':qty,'amount':part})
                    lot['quantity']-=qty;lot['amount']-=part;remaining-=qty
                    if not lot['quantity']:lots.pop(0)
                positions[dest].sort(key=lambda l:l['opening_sequence'])
                continue
            amount=positive(e['amount']); fees=dec(e['fees'])
            if fees<0:
                raise ValueError('Fees must be nonnegative and not already deducted from amount')
            opening = kind in ('buy','short')
            side = 'long' if kind in ('buy','sell') else 'short'
            if lots and any(l['side']!=side for l in lots):
                raise ValueError('Use explicit close before opposite-side opening')
            if opening:
                carrying=amount+fees if side=='long' else amount-fees
                if carrying<0:raise ValueError('Fees exceed short proceeds')
                lots.append({'quantity':quantity,'amount':carrying,'side':side,'opening_id':e['id'],'opening_sequence':e['_sequence'],'source':e['source']})
                continue
            if e['_year']==year and (e.get('tax_category')!='capital' or not e.get('country') or e['country']=='CN'):
                raise ValueError('Capital category/source country not reviewed for overseas calculation')
            carrying,matches=consume(lots,quantity)
            gain=amount-fees-carrying if side=='long' else carrying-amount-fees
            if e['_year']==year:
                opening_fees=sum((dec(original_events[x['opening_id']]['fees'])*dec(x['quantity'])/positive(original_events[x['opening_id']]['quantity']) for x in matches),ZERO) if side=='short' else ZERO
                gross_proceeds=amount if side=='long' else carrying+opening_fees
                total_cost=carrying+fees if side=='long' else amount+fees+opening_fees
                dispositions.append({'account':e['account'],'broker':e.get('broker',e['account']),'gross_proceeds_rmb':gross_proceeds*rates[e['currency']],'cost_and_fees_rmb':total_cost*rates[e['currency']],'id':e['id'],'country':e['country'],'currency':e['currency'],'gain':gain,'gain_rmb':gain*rates[e['currency']],'matches':matches,'source':e['source']})
        except (KeyError, ValueError, InvalidOperation) as exc:
            issue(e,str(exc))
            if kind=='transfer' and e.get('to_account'):
                blocked.add((e['to_account'],e.get('asset'),e.get('currency')))
    # A later unresolved event can affect position reconciliation but does not erase
    # an already verified disposal. Every result remains a stated subset.
    grouped=defaultdict(lambda:{'capital':ZERO,'income':ZERO,'tax_paid':ZERO})
    taxable_ids={}
    for d in dispositions:
        grouped[d['country']]['capital'] += d['gain_rmb'] if mode=='country_year' else max(d['gain_rmb'],ZERO)
        taxable_ids[d['id']]=d
    for i in incomes:
        grouped[i['country']]['income'] += i['gross_rmb'];taxable_ids[i['id']]=i
    credit_mode=cfg.get('credit_mode','deferred' if mode=='broker_year' else 'verified')
    if mode=='broker_year' and credit_mode=='verified':
        raise ValueError('Broker-year base estimate and source-country credit allocation must be reconciled separately')
    if credit_mode not in ('verified','deferred'):raise ValueError('Invalid credit_mode')
    tax_events=parsed if credit_mode=='verified' else []
    taxes={}
    for e in tax_events:
        if e.get('kind')!='withheld' or e.get('income_year')!=year:
            continue
        try:
            target=taxable_ids[e['income_id']]
            if not e.get('reviewed') or e.get('eligible') is not True or not isinstance(e.get('evidence'),str) or not e['evidence'].strip() or not e.get('source',{}).get('file') or not e.get('source',{}).get('locator'):
                raise ValueError('Foreign tax eligibility/evidence is not verified')
            if e['country']!=target['country']:
                raise ValueError('Tax country differs from income source country')
            taxes[e['id']]={'event':e,'net':positive(e['amount']),'country':e['country'],'currency':e['currency']}
        except (KeyError,ValueError,InvalidOperation) as exc:issue(e,str(exc),False)
    for e in tax_events:
        if e.get('kind')!='refund':continue
        if e.get('withholding_id') not in taxes:
            issue(e,'Refund linked tax not in verified target-year subset',False);continue
        t=taxes[e['withholding_id']]
        try:
            if not e.get('reviewed') or not e.get('source',{}).get('file') or not e.get('source',{}).get('locator') or e['currency']!=t['currency']:
                raise ValueError('Refund currency/source not verified')
            amount=positive(e['amount'])
            if amount>t['net']:raise ValueError('Refund exceeds remaining withholding; credit blocked')
            t['net']-=amount
        except (KeyError,ValueError,InvalidOperation) as exc:
            t['net']=ZERO;issue(e,str(exc),False)
    for t in taxes.values():
        try:grouped[t['country']]['tax_paid']+=t['net']*rates[t['currency']]
        except KeyError:issue(t['event'],'Missing foreign-tax currency FX',False)
    countries=[]
    for country,g in sorted(grouped.items()):
        tax=(max(g['capital'],ZERO)+g['income'])*rate
        credit=min(tax,g['tax_paid'])
        countries.append({'country':country,'capital_base_rmb':money(max(g['capital'],ZERO)),'income_rmb':money(g['income']),'tax_before_credit_rmb':money(tax),'credit_rmb':money(credit),'tax_after_credit_rmb':money(tax-credit),'unapplied_foreign_tax_rmb':money(g['tax_paid']-credit)})
    broker_totals=defaultdict(lambda:{'gross':ZERO,'cost':ZERO,'net':ZERO,'income':ZERO,'annual_sales':ZERO})
    for d in dispositions:
        b=broker_totals[d['broker']];b['gross']+=d['gross_proceeds_rmb'];b['cost']+=d['cost_and_fees_rmb'];b['net']+=d['gain_rmb']
    for i in incomes:broker_totals[i['broker']]['income']+=i['gross_rmb']
    for e in parsed:
        if e['_year']==year and e.get('kind') in ('sell','short'):
            broker_totals[e.get('broker',e['account'])]['annual_sales']+=positive(e['amount'])*rates[e['currency']]
    brokers=[]
    for name,b in sorted(broker_totals.items()):
        base=max(b['net'],ZERO);capital_tax=base*rate;income_tax=b['income']*rate
        brokers.append({'broker':name,'annual_gross_sales_rmb':money(b['annual_sales']),'realized_matched_proceeds_rmb':money(b['gross']),'matched_cost_and_fees_rmb':money(b['cost']),'capital_net_income_rmb':money(b['net']),'capital_tax_rmb':money(capital_tax),'income_rmb':money(b['income']),'income_tax_rmb':money(income_tax),'base_tax_rmb':money(capital_tax+income_tax)})
    if mode=='broker_year':countries=[]
    open_positions=[{'account':k[0],'asset':k[1],'currency':k[2],'lots':lots} for k,lots in positions.items() if lots]
    def serialize(v):
        if isinstance(v,Decimal):return str(v)
        if isinstance(v,list):return [serialize(x) for x in v]
        if isinstance(v,dict):return {k:serialize(x) for k,x in v.items()}
        return v
    if review:
        return serialize({'status':'needs_data','review':review,'message':'Unresolved evidence: no calculation result released'})
    return serialize({'status':'base_ready' if credit_mode=='deferred' else 'ready','credit_status':'pending, not applied; this is before-credit tax, not final tax payable' if credit_mode=='deferred' else 'verified input credit calculation','scope':'reviewed input subset; not all-world tax liability or official credit approval','conditions':cfg,'dispositions':dispositions,'incomes':incomes,'countries':countries,'brokers':brokers,'netting_notice':'Broker-year netting is a disclosed estimation convention, not a universal legal finding; no cross-broker loss offset','sales_notice':'Annual gross sales includes all sell/short openings in the target year; matched proceeds covers realized lots only. Differences require reconciliation, not forced subtraction. Costs include fees once.','subset_tax_rmb':money(sum((dec(b['base_tax_rmb']) for b in brokers),ZERO) if mode=='broker_year' else sum((dec(c['tax_after_credit_rmb']) for c in countries),ZERO)),'review':review,'open_positions':open_positions})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input');parser.add_argument('--out',required=True)
    args=parser.parse_args()
    data=json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    try:result=calculate(data)
    except (ValueError,KeyError,InvalidOperation) as exc:
        parser.exit(2,'Input rejected: '+str(exc)+'\n')
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('needs_data; no calculation result released' if result['status']=='needs_data' else result['status']+'; '+('before-credit tax RMB ' if result['status']=='base_ready' else 'tax RMB ')+result['subset_tax_rmb'])
