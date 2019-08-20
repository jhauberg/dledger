from datetime import datetime, date

from dividendreport.dateutil import previous_month, last_of_month
from dividendreport.formatutil import change, pct_change, format_amount, format_change
from dividendreport.ledger import Transaction
from dividendreport.projection import frequency, scheduled_transactions, estimate_schedule
from dividendreport.record import (
    income, yearly, monthly, trailing, amount_per_share,
    tickers, by_ticker, previous, previous_comparable
)

from typing import List


def report_per_record(records: List[Transaction]) \
        -> dict:
    reports = dict()

    for record in records:
        report = dict()

        sample_records = list(trailing(by_ticker(records, record.ticker),
                                       since=last_of_month(record.date), months=24))

        approx_frequency = frequency(sample_records)
        approx_schedule = estimate_schedule(sample_records, interval=approx_frequency)

        report['schedule'] = approx_schedule
        report['frequency'] = approx_frequency

        report['amount_per_share'] = amount_per_share(record)

        previous_record = previous(by_ticker(records, record.ticker), record)

        if previous_record is None:
            reports[record] = report

            continue

        if record.position != previous_record.position:
            report['position_change'] = change(record.position, previous_record.position)
            report['position_pct_change'] = pct_change(record.position, previous_record.position)

        # linear change; e.g. from previous payout to this payout
        if record.amount != previous_record.amount:
            report['amount_change'] = change(record.amount, previous_record.amount)
            report['amount_pct_change'] = pct_change(record.amount, previous_record.amount)

        previous_report = reports[previous_record]

        if report['amount_per_share'] != previous_report['amount_per_share']:
            report['amount_per_share_change'] = change(report['amount_per_share'], previous_report['amount_per_share'])
            report['amount_per_share_pct_change'] = pct_change(report['amount_per_share'], previous_report['amount_per_share'])

        comparable_record = previous_comparable(by_ticker(records, record.ticker), record)

        if comparable_record is None:
            reports[record] = report

            continue

        comparable_report = reports[comparable_record]

        # comparable change; e.g. from similar payout in the past to this payout
        if record.amount != comparable_record.amount:
            report['amount_yoy_change'] = change(record.amount, comparable_record.amount)
            report['amount_yoy_pct_change'] = pct_change(record.amount, comparable_record.amount)

        # note that this includes both dividend change, but also exchange rate discrepancies;
        # e.g. a weaker currency in the past compared to stronger of present would contribute to
        # a growth in amount per share and vice versa; dividend could have been raised while
        # currency has weakened, such that growth levels out or even go negative
        report['amount_per_share_yoy_change'] = \
            change(report['amount_per_share'], comparable_report['amount_per_share'])
        report['amount_per_share_yoy_change_pct'] = \
            pct_change(report['amount_per_share'], comparable_report['amount_per_share'])

        reports[record] = report

    return reports


def report_per_year(records: List[Transaction]) \
        -> dict:
    reports = dict()

    if len(records) == 0:
        return reports

    earliest_year = records[0].date.year
    latest_year = records[-1].date.year

    for year in range(earliest_year, latest_year + 1):
        yearly_income = income(yearly(records, year=year))

        if yearly_income == 0:
            continue

        report = dict()

        report['per_month'] = report_per_month(records, year)
        report['income'] = yearly_income

        yearly_income_last_year = income(yearly(records, year=year - 1))

        if yearly_income_last_year > 0:
            report['income_change'] = change(yearly_income, yearly_income_last_year)
            report['income_pct_change'] = pct_change(yearly_income,
                                                     yearly_income_last_year)

        reports[year] = report

    return reports


def report_per_month(records: List[Transaction], year: int) \
        -> dict:
    reports = dict()

    cumulative_income = 0

    for month in range(1, 12 + 1):
        report = dict()

        transactions = list(filter(
            lambda r: r.amount > 0, monthly(records, year=year, month=month)))

        if len(transactions) > 0:
            report['transactions'] = transactions

        monthly_income = income(transactions)
        cumulative_income += monthly_income

        if monthly_income > 0:
            report['income'] = monthly_income

        if cumulative_income > 0:
            report['income_cumulative'] = cumulative_income

        current_date = date(year=year, month=month, day=1)
        previous_date = previous_month(current_date)

        previous_monthly_income = income(
            monthly(records, year=previous_date.year, month=previous_date.month))

        if previous_monthly_income > 0:
            report['income_change'] = change(monthly_income, previous_monthly_income)
            report['income_pct_change'] = pct_change(monthly_income,
                                                     previous_monthly_income)

        monthly_income_last_year = income(monthly(records, year=year - 1, month=month))

        if monthly_income_last_year > 0:
            report['income_mom_change'] = change(monthly_income, monthly_income_last_year)
            report['income_mom_pct_change'] = pct_change(monthly_income,
                                                         monthly_income_last_year)

        cumulative_income_last_year = income(yearly(records, year=year - 1, months=month))

        if cumulative_income_last_year > 0:
            report['income_yoy_change'] = change(cumulative_income, cumulative_income_last_year)
            report['income_yoy_pct_change'] = pct_change(cumulative_income,
                                                         cumulative_income_last_year)

        reports[month] = report

    return reports


def report_by_weight(records: List[Transaction]) \
        -> dict:
    report = dict()
    total_income = income(records)
    for ticker in tickers(records):
        total_income_by_ticker = income(by_ticker(records, ticker))
        report[ticker] = {
            'income': total_income_by_ticker,
            'weight_pct': total_income_by_ticker / total_income * 100
        }
    return report


def generate(records: List[Transaction]) -> None:
    reports = report_per_record(records)
    import pprint
    earliest_record = records[0]
    latest_record = records[-1]
    print(f'=========== accumulated income ({earliest_record.date.year}-{latest_record.date.year})')
    print(f'{format_amount(income(records))} ({len(records)} transactions)')
    print(f'=========== annual income ({earliest_record.date.year}-{latest_record.date.year})')
    printer = pprint.PrettyPrinter(indent=2, width=100)
    printer.pprint(report_per_year(records))
    current_year = datetime.today().year
    print(f'=========== annual income ({current_year}) (weighted)')
    weights = report_by_weight(list(yearly(records, year=current_year)))
    weightings = sorted(weights.items(), key=lambda t: t[1]['weight_pct'], reverse=True)
    printer.pprint(weightings)
    print('=========== entries')
    printer = pprint.PrettyPrinter(indent=2, width=60)
    for record in records:
        printer.pprint(record)
        printer.pprint(reports[record])
    print('=========== historical amount per share')
    printer = pprint.PrettyPrinter(indent=2, width=70)
    timeline = dict()
    for ticker in tickers(records):
        timeline[ticker] = [(r.date, reports[r]['amount_per_share'])
                            for r in by_ticker(records, ticker)]
    printer.pprint(timeline)
    print('=========== projections')
    printer = pprint.PrettyPrinter(indent=2, width=60)
    futures = scheduled_transactions(records, reports)
    printer.pprint(futures)
    print('=========== forward 12-month income')
    padi = income(futures)
    print(f'annual income: {format_amount(padi)}')
    print(f'monthly (avg): {format_amount(padi / 12)}')
    print(f'weekly  (avg): {format_amount(padi / 52)}')
    print(f'daily   (avg): {format_amount(padi / 365)}')
    print(f'hourly  (avg): {format_amount(padi / 8760)}')
    print('=========== impact of latest transaction')
    records_except_latest = records[:-1]
    reports_except_latest = report_per_record(records_except_latest)
    futures_except_latest = scheduled_transactions(records_except_latest, reports_except_latest)
    padi_except_latest = income(futures_except_latest)
    printer.pprint(latest_record)
    print(f'annual income: {format_change(change(padi, padi_except_latest))}')
    print(f'monthly (avg): {format_change(change(padi / 12, padi_except_latest / 12))}')
    print(f'weekly  (avg): {format_change(change(padi / 52, padi_except_latest / 52))}')
    print(f'daily   (avg): {format_change(change(padi / 365, padi_except_latest / 365))}')
    print(f'hourly  (avg): {format_change(change(padi / 8760, padi_except_latest / 8760))}')
    print('=========== forward 12-month income (weighted)')
    printer = pprint.PrettyPrinter(indent=2, width=100)
    weights = report_by_weight(futures)
    weightings = sorted(weights.items(), key=lambda t: t[1]['weight_pct'], reverse=True)
    printer.pprint(weightings)
    print('=========== annual income (projected)')
    printer = pprint.PrettyPrinter(indent=2, width=100)
    extended_records = records + futures
    annuals = report_per_year(extended_records)
    annuals = {year: report for year, report in annuals.items() if year >= datetime.today().year}
    printer.pprint(annuals)
