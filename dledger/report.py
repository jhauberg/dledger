import locale
import re

from datetime import datetime, date

from dledger.localeutil import trysetlocale
from dledger.journal import Transaction
from dledger.dateutil import previous_month
from dledger.formatutil import (
    change, pct_change, format_amount, format_change
)
from dledger.projection import (
    scheduled_transactions, expired_transactions, estimated_schedule
)
from dledger.record import (
    income, yearly, monthly, amount_per_share, trailing,
    tickers, by_ticker, previous, previous_comparable, latest
)
from dledger.printutil import (
    colored,
    COLOR_BRIGHT_WHITE, COLOR_NEGATIVE, COLOR_POSITIVE
)

from typing import List, Tuple, Optional


def report_by_record(records: List[Transaction]) \
        -> dict:
    reports = dict()

    for record in records:
        report = dict()

        report['amount_per_share'] = amount_per_share(record)

        if record.is_special:
            reports[record] = report

            continue

        comparable_records = list(
            filter(lambda r: not r.is_special, by_ticker(records, record.ticker)))

        schedule = estimated_schedule(comparable_records, record)

        report['frequency'] = schedule.frequency
        report['schedule'] = schedule.months

        previous_record = previous(comparable_records, record)

        if previous_record is None:
            reports[record] = report

            continue

        if record.position != previous_record.position:
            report['position_change'] = change(record.position, previous_record.position)
            report['position_pct_change'] = pct_change(record.position, previous_record.position)

        # linear change; e.g. from previous payout to this payout
        if record.amount.value != previous_record.amount.value:
            # todo: assuming same currency
            report['amount_change'] = change(record.amount.value, previous_record.amount.value)
            report['amount_pct_change'] = pct_change(record.amount.value, previous_record.amount.value)

        previous_report = reports[previous_record]

        if report['amount_per_share'] != previous_report['amount_per_share']:
            # todo: assuming same currency
            report['amount_per_share_change'] = change(report['amount_per_share'], previous_report['amount_per_share'])
            report['amount_per_share_pct_change'] = pct_change(report['amount_per_share'], previous_report['amount_per_share'])

        comparable_record = previous_comparable(comparable_records, record)

        if comparable_record is None:
            reports[record] = report

            continue

        comparable_report = reports[comparable_record]

        # comparable change; e.g. from similar payout in the past to this payout
        if record.amount.value != comparable_record.amount.value:
            # todo: assuming same currency
            report['amount_yoy_change'] = change(record.amount.value, comparable_record.amount.value)
            report['amount_yoy_pct_change'] = pct_change(record.amount.value, comparable_record.amount.value)

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


def report_by_year(records: List[Transaction]) \
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

        report['per_month'] = report_by_month(records, year)
        report['income'] = yearly_income

        report['transaction_count'] = len(list(yearly(records, year=year)))
        report['ticker_count'] = len(list(tickers(yearly(records, year=year))))

        yearly_income_last_year = income(yearly(records, year=year - 1))

        if yearly_income_last_year > 0:
            report['income_change'] = change(yearly_income, yearly_income_last_year)
            report['income_pct_change'] = pct_change(yearly_income, yearly_income_last_year)

        reports[year] = report

    return reports


def report_by_month(records: List[Transaction], year: int) \
        -> dict:
    reports = dict()

    cumulative_income = 0

    for month in range(1, 12 + 1):
        report = dict()

        transactions = list(filter(
            lambda r: r.amount.value > 0, monthly(records, year=year, month=month)))

        if len(transactions) > 0:
            report['transactions'] = transactions

        monthly_income = income(transactions)
        cumulative_income += monthly_income

        report['income'] = monthly_income
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
        filtered_records = list(by_ticker(records, ticker))
        total_income_by_ticker = income(filtered_records)
        report[ticker] = {
            'income': total_income_by_ticker,
            'weight_pct': total_income_by_ticker / total_income * 100,
            'transaction_count': len(filtered_records)
        }
    return report


def print_annual_report(columns: List[Tuple[str, Optional[str], Optional[str]]],
                        left_column_width: int,
                        right_column_width: int) \
        -> None:
    for left, right, additional in columns:
        line = left

        if right is not None:
            should_end_brace = right.startswith('(')

            left = left.ljust(left_column_width + 4)
            right = right.rjust(right_column_width) + (')' if should_end_brace else '')

            line = left + right
        else:
            line = colored(line, COLOR_BRIGHT_WHITE)

        if additional is not None:
            line += f' {additional}'

        def color_repl(m):
            result = m.group(0)
            if result.startswith('+'):
                return colored(result, COLOR_POSITIVE)
            if result.startswith('-'):
                return colored(result, COLOR_NEGATIVE)

        line = re.sub(r'[+-]\s[0-9.,]+', color_repl, line)

        print(line)

    print()


def build_annual_report(year: int, report: dict, transaction_reports: dict) \
        -> List[Tuple[str, Optional[str], Optional[str]]]:
    max_ticker_length = 12

    months = report['per_month']

    columns: List[Tuple[str, Optional[str], Optional[str]]] = list()

    actual_year = datetime.today().date().year
    actual_month = datetime.today().date().month

    latest_month = actual_month

    for month in months:
        latest_month = month
        month_date = date(year=year, month=month, day=1)
        datestamp = month_date.strftime('%Y %B')

        columns.append((f'{datestamp}', None, None))

        monthly_report = months[month]

        transactions = monthly_report.get('transactions', list())

        for transaction in transactions:
            datestamp = transaction.date.strftime('%Y-%m-%d')
            ticker = transaction.ticker[:max_ticker_length].strip()

            transaction_report = transaction_reports[transaction]

            transaction_position_change = transaction_report.get('position_change', 0)
            transaction_amount_change = transaction_report.get('amount_change', 0)

            change_column = None

            if transaction_position_change != 0 or transaction_amount_change != 0:
                change_column = '^' if transaction_position_change > 0 else ' '
                change_column += f' [{format_change(transaction_amount_change)}]' if transaction_amount_change != 0 else ''

            columns.append((f'{datestamp} {ticker}',
                            f'{format_amount(transaction.amount.value)}',
                            change_column))

        income = monthly_report.get('income', 0)
        income_cumulative = monthly_report.get('income_cumulative', 0)

        if income > 0:
            columns.append((f' income', f'({format_amount(income)}', None))

        prev_year = year - 1
        prev_month = previous_month(month_date).month

        if income > 0:
            income_change = monthly_report.get('income_change', 0)
            income_pct_change = monthly_report.get('income_pct_change', 0)
            income_mom_change = monthly_report.get('income_mom_change', 0)
            income_mom_pct_change = monthly_report.get('income_mom_pct_change', 0)

            if income_change != 0:
                prev_datestamp = date(year=year, month=prev_month, day=1).strftime('%b\'%y')
                curr_datestamp = date(year=year, month=month, day=1).strftime('%b\'%y')
                columns.append((f'  {prev_datestamp}/{curr_datestamp}',
                                f'{format_change(income_pct_change)}',
                                f'% [{format_change(income_change)}]'))

            if income_mom_change != 0:
                prev_datestamp = date(year=prev_year, month=month, day=1).strftime('%b\'%y')
                curr_datestamp = date(year=year, month=month, day=1).strftime('%b\'%y')
                columns.append((f'  {prev_datestamp}/{curr_datestamp}',
                                f'{format_change(income_mom_pct_change)}',
                                f'% [{format_change(income_mom_change)}]'))

        columns.append((f' income (YTD)', f'({format_amount(income_cumulative)}', None))

        if income > 0:
            income_yoy_change = monthly_report.get('income_yoy_change', 0)
            income_yoy_pct_change = monthly_report.get('income_yoy_pct_change', 0)

            if income_yoy_change != 0:
                prev_datestamp = date(year=prev_year, month=1, day=1).strftime('%b-')
                prev_datestamp = prev_datestamp + date(year=prev_year, month=month, day=1).strftime('%b\'%y')
                curr_datestamp = date(year=year, month=1, day=1).strftime('%b-')
                curr_datestamp = curr_datestamp + date(year=year, month=month, day=1).strftime('%b\'%y')
                columns.append((f'  {prev_datestamp}/{curr_datestamp}',
                                f'{format_change(income_yoy_pct_change)}',
                                f'% [{format_change(income_yoy_change)}]'))

        if year == actual_year and month == actual_month:
            break

    income = months[latest_month]['income_cumulative']
    income_result = f'{format_amount(income)}'
    columns.append((f'', ''.ljust(len(income_result), '='), None))
    columns.append((f'', f'({income_result}', None))

    return columns


def print_debug_reports(records: List[Transaction]) -> None:
    import pprint
    transactions = list(filter(lambda r: r.amount is not None and r.amount.value > 0, records))
    reports = report_by_record(transactions)
    earliest_record = transactions[0]
    latest_record = transactions[-1]
    print(f'=========== accumulated income ({earliest_record.date.year}-{latest_record.date.year})')
    #transactions = list(filter(lambda r: r.amount is not None and r.amount > 0, records))
    print(f'{format_amount(income(transactions))} ({len(transactions)} transactions)')
    print(f'=========== accumulated income ({earliest_record.date.year}-{latest_record.date.year}, weighted)')
    weights = report_by_weight(transactions)
    weightings = sorted(weights.items(), key=lambda t: t[1]['weight_pct'], reverse=True)
    printer = pprint.PrettyPrinter(indent=2, width=100)
    printer.pprint(weightings)
    print(f'=========== annual income ({earliest_record.date.year}-{latest_record.date.year})')
    printer = pprint.PrettyPrinter(indent=2, width=100)
    printer.pprint(report_by_year(transactions))
    current_year = datetime.today().year
    print(f'=========== annual income ({current_year}) (weighted)')
    weights = report_by_weight(list(yearly(transactions, year=current_year)))
    weightings = sorted(weights.items(), key=lambda t: t[1]['weight_pct'], reverse=True)
    printer.pprint(weightings)
    print('=========== entries')
    printer = pprint.PrettyPrinter(indent=2, width=60)
    for record in transactions:
        printer.pprint(record)
        printer.pprint(reports[record])
    print('=========== historical amount per share')
    printer = pprint.PrettyPrinter(indent=2, width=70)
    timeline = dict()
    for ticker in tickers(transactions):
        timeline[ticker] = [(r.date, reports[r]['amount_per_share'])
                            for r in by_ticker(transactions, ticker)
                            if reports[r]['amount_per_share'] > 0]
    printer.pprint(timeline)
    print('=========== projections')
    printer = pprint.PrettyPrinter(indent=2, width=60)
    futures = scheduled_transactions(records)
    # exclude unrealized projections
    closed = tickers(expired_transactions(futures))
    futures = list(filter(lambda r: r.ticker not in closed, futures))
    printer.pprint(futures)
    print('=========== trailing 12-month income')
    ttm_income = income(trailing(transactions, since=datetime.today().date(), months=12))
    print(f'annual income: {format_amount(ttm_income)}')
    print('=========== forward 12-month income')
    padi = income(futures)
    print(f'annual income: {format_amount(padi)}')
    print(f'change  (TTM): {format_change(change(padi, ttm_income))} / {format_change(pct_change(padi, ttm_income))}%')
    print(f'monthly (avg): {format_amount(padi / 12)}')
    print(f'weekly  (avg): {format_amount(padi / 52)}')
    print(f'daily   (avg): {format_amount(padi / 365)}')
    print(f'hourly  (avg): {format_amount(padi / 8760)}')
    print('=========== impact of latest transaction')
    # todo: i don't think this report is correct - needs a test before being formalized
    latest_record_not_in_future = latest(
        filter(lambda r: r.amount is not None and not r.is_special and r.date <= datetime.today().date(), records))
    records_except_latest = list(records)
    records_except_latest.remove(latest_record_not_in_future)
    reports_except_latest = report_by_record(list(filter(lambda r: r.amount is not None, records_except_latest)))
    futures_except_latest = scheduled_transactions(records_except_latest)
    # exclude unrealized projections (except the latest transaction)
    closed_except_latest = tickers(expired_transactions(futures_except_latest))
    futures_except_latest = list(filter(lambda r: r.ticker == latest_record_not_in_future.ticker or
                                                  r.ticker not in closed_except_latest,
                                        futures_except_latest))
    padi_except_latest = income(futures_except_latest)
    printer.pprint(latest_record_not_in_future)
    print(f'annual income: {format_change(change(padi, padi_except_latest))}')
    print(f'monthly (avg): {format_change(change(padi / 12, padi_except_latest / 12))}')
    print(f'weekly  (avg): {format_change(change(padi / 52, padi_except_latest / 52))}')
    print(f'daily   (avg): {format_change(change(padi / 365, padi_except_latest / 365))}')
    print(f'hourly  (avg): {format_change(change(padi / 8760, padi_except_latest / 8760))}')
    previous_record = latest(
        filter(lambda r: r.amount is not None and not r.is_special,
               by_ticker(records_except_latest, latest_record_not_in_future.ticker)))
    if previous_record is not None:
        now_report = reports[latest_record_not_in_future]
        then_report = reports_except_latest[previous_record]
        then_frequency = then_report['frequency']
        then_schedule = then_report['schedule']
        now_frequency = now_report['frequency']
        now_schedule = now_report['schedule']
        if now_frequency != then_frequency:
            print(f'frequency: {then_frequency} => {now_frequency}')
        if now_schedule != then_schedule:
            print(f'schedule: {then_schedule} => {now_schedule}')
    print('=========== forward annual dividend')
    printer = pprint.PrettyPrinter(indent=2, width=70)
    timeline = dict()
    for ticker in tickers(futures):
        timeline[ticker] = sum([amount_per_share(r) for r in by_ticker(futures, ticker) if r.amount is not None])
    printer.pprint(timeline)
    print('=========== forward 12-month income (weighted)')
    printer = pprint.PrettyPrinter(indent=2, width=100)
    weights = report_by_weight(futures)
    weightings = sorted(weights.items(), key=lambda t: t[1]['weight_pct'], reverse=True)
    printer.pprint(weightings)
    print('=========== annual income (projected)')
    printer = pprint.PrettyPrinter(indent=2, width=100)
    extended_records = records + futures
    extended_transactions = list(filter(lambda r: r.amount is not None and r.amount.value > 0, extended_records))
    annuals = report_by_year(extended_transactions)
    annuals = {year: report for year, report in annuals.items() if year >= datetime.today().year}
    printer.pprint(annuals)


def print_journal_entries(records: List[Transaction]) -> None:
    try:
        # default to system locale, if able
        locale.setlocale(locale.LC_ALL, '')
    except:
        # fallback to US locale
        trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    for record in records:
        special_indicator = '* ' if record.is_special else ''
        datestamp = record.date.strftime('%Y/%m/%d')
        print(f'{datestamp} {special_indicator}{record.ticker} ({record.position})')
        if record.amount is not None:
            amount_display = format_amount(record.amount.value, trailing_zero=False)
            if record.amount.format is not None:
                amount_display = record.amount.format % amount_display
            print(f'  {amount_display}')


def generate(records: List[Transaction], debug: bool = False) -> None:
    # default to use system locale
    # note that this may depend on the current shell/environment and might not
    # give the result that the user expects but is the "correct" approach
    locale.setlocale(locale.LC_ALL, '')
    # except for time/dates where we explicitly want US locale
    trysetlocale(locale.LC_TIME, ['en_US', 'en-US', 'en'])

    if debug:
        print_debug_reports(records)

        return

    reports = report_by_record(records)
    annual_reports = report_by_year(records)

    listings = list()

    for year in annual_reports.keys():
        annual_report = annual_reports[year]
        columns = build_annual_report(year, annual_report, transaction_reports=reports)
        listings.append(columns)

    left_column_width = 0
    right_column_width = 0
    for listing in listings:
        for left, right, additional in listing:
            left_width = len(left)
            if left_column_width < left_width:
                left_column_width = left_width
            if right is not None:
                right_width = len(right)
                if right_column_width < right_width:
                    right_column_width = right_width

    for listing in listings:
        print_annual_report(listing, left_column_width, right_column_width)
