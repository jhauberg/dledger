import locale
import os

from datetime import datetime, date

from dledger.journal import Transaction, Distribution
from dledger.formatutil import format_amount, most_decimal_places
from dledger.printutil import colored, COLOR_NEGATIVE, COLOR_MARKED
from dledger.dateutil import previous_month, last_of_month
from dledger.projection import FutureTransaction, GeneratedDate, symbol_conversion_factors
from dledger.record import (
    income, yearly, monthly, symbols,
    tickers, by_ticker, latest, earliest, before, after
)

from typing import List, Dict, Optional


def print_simple_annual_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).date.year,
                  latest(records).date.year + 1)

    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        for year in years:
            yearly_transactions = list(yearly(matching_transactions, year=year))
            if len(yearly_transactions) == 0:
                continue

            total = income(yearly_transactions)
            amount = format_amount(total, trailing_zero=False)
            amount = latest_transaction.amount.format % amount
            d = f'{year}'
            if any(isinstance(x, FutureTransaction) for x in yearly_transactions):
                if year == years[-1]:
                    d = latest_transaction.date.strftime('%Y/%m')
                    line = f'~ {amount.rjust(18)}  < {d.ljust(11)}'
                else:
                    line = f'~ {amount.rjust(18)}    {d.ljust(11)}'
            else:
                line = f'{amount.rjust(20)}    {d.ljust(11)}'
            if today.year == year:
                print(colored(line, COLOR_MARKED))
            else:
                print(line)
        if commodity != commodities[-1]:
            print()


def print_simple_monthly_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).date.year,
                  latest(records).date.year + 1)

    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        for year in years:
            for month in range(1, 12 + 1):
                monthly_transactions = list(monthly(matching_transactions, year=year, month=month))
                if len(monthly_transactions) == 0:
                    continue

                total = income(monthly_transactions)
                amount = format_amount(total, trailing_zero=False)
                amount = latest_transaction.amount.format % amount
                month_indicator = f'{month}'.zfill(2)
                d = f'{year}/{month_indicator}'
                if any(isinstance(x, FutureTransaction) for x in monthly_transactions):
                    line = f'~ {amount.rjust(18)}    {d.ljust(11)}'
                else:
                    line = f'{amount.rjust(20)}    {d.ljust(11)}'
                if today.year == year and today.month == month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)

        if commodity != commodities[-1]:
            print()


def print_simple_quarterly_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).date.year,
                  latest(records).date.year + 1)

    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        for year in years:
            for quarter in range(1, 4 + 1):
                ending_month = quarter * 3 + 1
                starting_month = ending_month - 3

                quarterly_transactions = []
                for month in range(starting_month, ending_month):
                    monthly_transactions = monthly(matching_transactions, year=year, month=month)
                    quarterly_transactions.extend(monthly_transactions)
                if len(quarterly_transactions) == 0:
                    continue

                total = income(quarterly_transactions)
                amount = format_amount(total, trailing_zero=False)
                amount = latest_transaction.amount.format % amount
                d = f'{year}/Q{quarter}'
                if any(isinstance(x, FutureTransaction) for x in quarterly_transactions):
                    line = f'~ {amount.rjust(18)}    {d.ljust(11)}'
                else:
                    line = f'{amount.rjust(20)}    {d.ljust(11)}'
                if today.year == year and ending_month > today.month >= starting_month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)
        if commodity != commodities[-1]:
            print()


def print_simple_report(records: List[Transaction], *, detailed: bool = False):
    today = datetime.today().date()
    dividend_decimal_places: Dict[str, Optional[int]] = dict()
    if detailed:
        for ticker in tickers(records):
            dividend_decimal_places[ticker] = most_decimal_places(
                (r.dividend.value for r in records if
                 r.ticker == ticker and
                 r.dividend is not None))
    for transaction in records:
        should_colorize_expired_transaction = False

        amount = format_amount(transaction.amount.value, trailing_zero=False)
        amount = transaction.amount.format % amount

        d = transaction.date.strftime('%Y/%m/%d')

        if isinstance(transaction, FutureTransaction):
            if isinstance(transaction.date, GeneratedDate):
                if transaction.date < today:
                    should_colorize_expired_transaction = True
                    # call attention as it may be a payout about to happen, or a closed position
                    line = f'~ {amount.rjust(18)}  ! {d} {transaction.ticker.ljust(8)}'
                else:
                    line = f'~ {amount.rjust(18)}  < {d} {transaction.ticker.ljust(8)}'
            else:
                should_colorize_expired_transaction = True
                # call attention as it is a preliminary record, not completed yet
                line = f'~ {amount.rjust(18)}  ! {d} {transaction.ticker.ljust(8)}'
        else:
            if transaction.kind is Distribution.INTERIM:
                line = f'{amount.rjust(20)}  ^ {d} {transaction.ticker.ljust(8)}'
            elif transaction.kind is Distribution.SPECIAL:
                line = f'{amount.rjust(20)}  * {d} {transaction.ticker.ljust(8)}'
            else:
                line = f'{amount.rjust(20)}    {d} {transaction.ticker.ljust(8)}'

        if transaction.payout_date is not None:
            pd = transaction.payout_date.strftime('%Y/%m/%d')
            line = f'{line} [{pd}]'
        else:
            line = f'{line} ' + (' ' * 12)

        if detailed:
            if transaction.dividend is not None:
                dividend = format_amount(transaction.dividend.value,
                                         trailing_zero=False,
                                         places=dividend_decimal_places[transaction.ticker])
                dividend = transaction.dividend.format % dividend

                line = f'{line} {dividend.rjust(12)}'
            else:
                line = f'{line} ' + (' ' * 12)

            position = f'({transaction.position})'.rjust(8)

            line = f'{line} {position}'

        if should_colorize_expired_transaction:
            line = colored(line, COLOR_NEGATIVE)
        elif transaction.date == today:
            line = colored(line, COLOR_MARKED)

        print(line)


def print_simple_weight_by_ticker(records: List[Transaction]):
    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        total_income = income(matching_transactions)

        weights = []
        for ticker in tickers(records):
            filtered_records = list(by_ticker(records, ticker))
            income_by_ticker = income(filtered_records)

            amount = format_amount(income_by_ticker, trailing_zero=False)
            amount = latest_transaction.amount.format % amount

            weight = income_by_ticker / total_income * 100

            is_estimate = (True if any(isinstance(x, FutureTransaction) for x in filtered_records)
                           else False)
            
            weights.append((ticker, amount, weight, is_estimate))
        weights.sort(key=lambda w: w[2], reverse=True)
        for weight in weights:
            ticker, amount, pct, is_estimate = weight
            pct = f'{format_amount(pct)}%'
            if is_estimate:
                print(f'~ {amount.rjust(18)}    {pct.rjust(7)}    {ticker}')
            else:
                print(f'{amount.rjust(20)}    {pct.rjust(7)}    {ticker}')


def print_simple_sum_report(records: List[Transaction]) -> None:
    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)

        total = income(matching_transactions)
        amount = format_amount(total, trailing_zero=False)
        amount = latest_transaction.amount.format % amount

        if any(isinstance(x, FutureTransaction) for x in matching_transactions):
            print(f'~ {amount.rjust(18)}')
        else:
            print(f'{amount.rjust(20)}')
        if commodity != commodities[-1]:
            print()


def print_stat_row(name: str, text: str) -> None:
    name = name.rjust(10)
    print(f'{name}: {text}')


def print_stats(records: List[Transaction], journal_paths: List[str]):
    for n, journal_path in enumerate(journal_paths):
        print_stat_row(f'Journal {n + 1}', os.path.abspath(journal_path))
    try:
        lc = locale.getlocale(locale.LC_NUMERIC)
        print_stat_row('Locale', f'{lc}')
    except locale.Error:
        print_stat_row('Locale', 'Not configured')
    transactions = list(filter(lambda r: r.amount is not None, records))
    if len(transactions) > 0 and len(transactions) != len(records):
        print_stat_row('Records', f'{len(records)} ({len(transactions)})')
    else:
        print_stat_row('Records', f'{len(records)}')
    if len(records) > 0:
        earliest_datestamp = records[0].date.strftime('%Y/%m/%d')
        latest_datestamp = records[-1].date.strftime('%Y/%m/%d')
        print_stat_row('Earliest', earliest_datestamp)
        print_stat_row('Latest', latest_datestamp)
        print_stat_row('Tickers', f'{len(tickers(records))}')
        currencies = sorted(symbols(records))
        if len(currencies) > 0:
            print_stat_row('Symbols', f'{currencies}')
            conversion_rates = symbol_conversion_factors(records)
            conversion_keys = sorted(conversion_rates, key=lambda c: c[0])
            for from_symbol, to_symbol in conversion_keys:
                conversion_rate = conversion_rates[(from_symbol, to_symbol)]
                conversion_rate_amount = format_amount(conversion_rate)
                print_stat_row(f'{from_symbol}/{to_symbol}', f'{conversion_rate_amount}')


def print_simple_rolling_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).date.year,
                  latest(records).date.year + 1)

    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        for year in years:
            for month in range(1, 12 + 1):
                ending_date = date(year, month, 1)
                if ending_date > today:
                    continue
                starting_date = ending_date.replace(year=ending_date.year - 1)
                ending_date_ex = ending_date
                starting_date_ex = last_of_month(previous_month(starting_date))
                rolling_transactions = list(before(after(
                    matching_transactions, starting_date_ex), ending_date_ex))
                if len(rolling_transactions) == 0:
                    continue
                total = income(rolling_transactions)
                amount = format_amount(total, trailing_zero=False)
                amount = latest_transaction.amount.format % amount
                d = ending_date.strftime('%Y/%m')
                if any(isinstance(x, FutureTransaction) for x in rolling_transactions):
                    line = f'~ {amount.rjust(18)}  < {d.ljust(11)}'
                else:
                    line = f'{amount.rjust(20)}  < {d.ljust(11)}'
                if today.year == year and today.month == month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)

        future_transactions = [r for r in matching_transactions if
                               isinstance(r, FutureTransaction) and r.date >= today]
        if len(future_transactions) > 0:
            total = income(future_transactions)
            amount = format_amount(total, trailing_zero=False)
            amount = latest_transaction.amount.format % amount
            print(f'~ {amount.rjust(18)}    next 12m')

        if commodity != commodities[-1]:
            print()
