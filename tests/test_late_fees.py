import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'late_fees', Path(__file__).parents[1] / 'scripts' / 'late_fees.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def document(**overrides):
    return {'tax_principal_rmb': '10000.00', 'principal_status': 'verified',
            'principal_basis': 'synthetic verified tax liability',
            'due_date': '2025-06-30', 'due_date_basis': 'synthetic deadline',
            'as_of_date': '2025-07-02', 'applicability': 'ordinary',
            'applicability_basis': 'synthetic ordinary overdue case',
            'payment_history_basis': 'synthetic complete principal payments',
            'payments': [], **overrides}


def payment(when, value):
    return {'date': when, 'principal_rmb': value, 'source': 'synthetic receipt'}


class LateFees(unittest.TestCase):
    def test_deadline_and_before_deadline_have_no_fee(self):
        for day in ('2025-06-29', '2025-06-30'):
            result = m.calculate(document(as_of_date=day))
            self.assertEqual(result['estimated_late_fee_rmb'], '0.00')
            self.assertEqual(result['charged_days'], 0)

    def test_first_overdue_day_counts_once(self):
        result = m.calculate(document(as_of_date='2025-07-01'))
        self.assertEqual(result['estimated_late_fee_rmb'], '5.00')
        self.assertEqual(result['charged_days'], 1)

    def test_payment_day_included_then_partial_balance(self):
        result = m.calculate(document(payments=[payment('2025-07-01', '4000')]))
        self.assertEqual(result['estimated_late_fee_rmb'], '8.00')
        self.assertEqual(result['daily_increase_if_overdue_rmb'], '3.000000')
        self.assertEqual(result['outstanding_principal_rmb'], '6000.00')

    def test_full_payment_stops_future_accrual(self):
        result = m.calculate(document(as_of_date='2025-07-20',
                                      payments=[payment('2025-07-02', '10000')]))
        self.assertEqual(result['estimated_late_fee_rmb'], '10.00')
        self.assertEqual(result['charged_days'], 2)

    def test_on_time_payment_no_fee(self):
        result = m.calculate(document(payments=[payment('2025-06-30', '10000')]))
        self.assertEqual(result['estimated_late_fee_rmb'], '0.00')

    def test_same_day_payments_do_not_double_count(self):
        result = m.calculate(document(payments=[payment('2025-07-01', '2000'),
                                                payment('2025-07-01', '3000')]))
        self.assertEqual(result['estimated_late_fee_rmb'], '7.50')
        self.assertEqual(result['charged_days'], 2)

    def test_leap_day_and_year_boundary(self):
        result = m.calculate(document(due_date='2024-02-28', as_of_date='2024-03-01'))
        self.assertEqual(result['charged_days'], 2)
        result = m.calculate(document(due_date='2024-12-31', as_of_date='2025-01-01'))
        self.assertEqual(result['charged_days'], 1)

    def test_scenario_basis_is_not_verified_debt(self):
        result = m.calculate(document(principal_status='assumed_before_credit'))
        self.assertEqual(result['status'], 'scenario_estimate')

    def test_unknown_applicability_or_history_releases_no_fee(self):
        for field, value in [('applicability', 'unresolved'),
                             ('applicability', 'exempt'), ('due_date_basis', ''),
                             ('principal_basis', ''), ('payment_history_basis', ''),
                             ('payments', None)]:
            result = m.calculate(document(**{field: value}))
            self.assertEqual(result['status'], 'needs_confirmation')
            self.assertNotIn('estimated_late_fee_rmb', result)

    def test_invalid_money_rejected(self):
        for value in (1.2, '-1', 'NaN', 'Infinity', '0.001'):
            with self.assertRaises(ValueError):
                m.calculate(document(tax_principal_rmb=value))

    def test_future_payment_and_overpayment_rejected(self):
        for row in (payment('2025-07-03', '100'), payment('2025-07-01', '10001')):
            with self.assertRaises(ValueError):
                m.calculate(document(payments=[row]))

    def test_small_daily_fee_accumulates_before_rounding(self):
        result = m.calculate(document(tax_principal_rmb='1', as_of_date='2025-07-10'))
        self.assertEqual(result['estimated_late_fee_rmb'], '0.01')
        self.assertEqual(result['fee_exact_rmb'], '0.0050')

    def test_long_period_simple_interest_no_automatic_cap(self):
        result = m.calculate(document(due_date='2020-01-01', as_of_date='2026-01-01'))
        self.assertEqual(result['charged_days'], 2192)
        self.assertEqual(result['estimated_late_fee_rmb'], '10960.00')

    def test_zero_principal_has_no_charged_days(self):
        result = m.calculate(document(tax_principal_rmb='0.00'))
        self.assertEqual(result['charged_days'], 0)
        self.assertEqual(result['estimated_late_fee_rmb'], '0.00')

    def test_predeadline_partial_payment_reduces_overdue_principal(self):
        result = m.calculate(document(payments=[payment('2025-06-29', '4000')]))
        self.assertEqual(result['estimated_late_fee_rmb'], '6.00')

    def test_unsorted_payments_and_fractional_total_rounding(self):
        result = m.calculate(document(tax_principal_rmb='10.00',
                                     payments=[payment('2025-07-02', '2.00'),
                                               payment('2025-07-01', '1.00')]))
        self.assertEqual(result['fee_exact_rmb'], '0.009500')
        self.assertEqual(result['estimated_late_fee_rmb'], '0.01')
        self.assertEqual(result['paid_principal_rmb'], '3.00')


if __name__ == '__main__':
    unittest.main()
