"""Deterministic ordinary-rule late-fee scenarios; never decides legal applicability.

python scripts/late_fees.py INPUT.json [--out RESULT.json]
All payments must be principal-only amounts allocated to this one liability.
"""
import argparse
import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path

RATE = Decimal('0.0005')
CENT = Decimal('0.01')
ZERO = Decimal('0')


def money(value):
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def amount(value):
    if not isinstance(value, str):
        raise ValueError('RMB amounts must be decimal strings, never floats')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid RMB amount') from exc
    if not result.is_finite() or result < ZERO:
        raise ValueError('RMB amount must be finite and nonnegative')
    if result > Decimal('999999999999999.99') or result != result.quantize(CENT):
        raise ValueError('RMB amount must be within supported range and whole cents')
    return result


def iso_date(value):
    if not isinstance(value, str):
        raise ValueError('Dates must be YYYY-MM-DD strings')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value or parsed == date.max:
        raise ValueError('Dates must be canonical YYYY-MM-DD before 9999-12-31')
    return parsed


def text_field(document, field):
    value = document.get(field)
    return isinstance(value, str) and bool(value.strip())


def calculate(document):
    """Return no numeric result when applicability/evidence is not established."""
    if not isinstance(document, dict):
        raise ValueError('Input must be an object')
    missing = []
    for field in ('tax_principal_rmb', 'due_date', 'as_of_date'):
        if field not in document:
            missing.append(field)
    for field in ('principal_basis', 'due_date_basis', 'applicability_basis',
                  'payment_history_basis'):
        if not text_field(document, field):
            missing.append(field)
    if document.get('applicability') != 'ordinary':
        missing.append('ordinary-rule applicability (review exemptions separately)')
    if document.get('principal_status') not in ('verified', 'assumed_before_credit'):
        missing.append('principal_status: verified or assumed_before_credit')
    if not isinstance(document.get('payments'), list):
        missing.append('payments: principal payment list, explicitly empty if none')
    if missing:
        return {'status': 'needs_confirmation', 'missing': missing,
                'message': 'No fee released; clarify applicability and evidence first'}

    with localcontext() as context:
        context.prec = 40
        principal = amount(document['tax_principal_rmb'])
        due = iso_date(document['due_date'])
        until = iso_date(document['as_of_date'])
        payments = []
        for row in document['payments']:
            if not isinstance(row, dict) or not text_field(row, 'source'):
                raise ValueError('Each payment needs its evidence source')
            paid_on = iso_date(row['date'])
            paid = amount(row['principal_rmb'])
            if paid <= ZERO:
                raise ValueError('Each principal payment must be positive')
            if paid_on > until:
                raise ValueError('Future payments cannot be treated as already paid')
            payments.append((paid_on, paid))
        payments.sort(key=lambda entry: entry[0])
        outstanding = principal
        cursor = due + timedelta(days=1)
        segments = []
        total = ZERO
        charged_days = 0

        def accrue(end):
            nonlocal cursor, total, charged_days
            if end >= cursor and outstanding > ZERO:
                days = (end - cursor).days + 1
                exact = outstanding * RATE * days
                total += exact
                charged_days += days
                segments.append({'start': cursor.isoformat(), 'end': end.isoformat(),
                                 'days': days, 'principal_rmb': money(outstanding),
                                 'fee_rmb': money(exact), 'fee_exact_rmb': str(exact)})
            if end >= cursor:
                cursor = end + timedelta(days=1)

        for paid_on, paid in payments:
            if paid > outstanding:
                raise ValueError('Payments exceed this liability; check allocation')
            # The actual payment date is charged before reducing principal.
            accrue(paid_on)
            outstanding -= paid
        accrue(until)
        return {
            'status': ('scenario_estimate' if document['principal_status'] ==
                       'assumed_before_credit' else 'estimate'),
            'principal_status': document['principal_status'],
            'principal_basis': document['principal_basis'],
            'due_date': due.isoformat(), 'due_date_basis': document['due_date_basis'],
            'as_of_date': until.isoformat(), 'daily_rate': str(RATE),
            'charged_days': charged_days, 'segments': segments,
            'original_principal_rmb': money(principal),
            'paid_principal_rmb': money(principal - outstanding),
            'outstanding_principal_rmb': money(outstanding),
            'estimated_late_fee_rmb': money(total),
            'fee_exact_rmb': str(total),
            'daily_increase_if_overdue_rmb': str(outstanding * RATE),
            'conditions': {'applicability_basis': document['applicability_basis'],
                           'payment_history_basis': document['payment_history_basis']},
            'notice': 'Arithmetic estimate, not tax-authority assessment. Simple '
                      'interest; payment day included; no guessed due date, payments '
                      'or credit. Daily increase applies only once overdue; '
                      'displayed segment fees may differ from rounded total.'
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('--out')
    args = parser.parse_args()
    try:
        document = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        result = calculate(document)
    except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
        parser.exit(2, 'Input rejected: ' + str(exc) + '\n')
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding='utf-8')
        print(result['status'])
    else:
        print(rendered)


if __name__ == '__main__':
    main()
