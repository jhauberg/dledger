import locale
import os

from datetime import datetime, date

from dledger.journal import Transaction
from dledger.formatutil import format_amount
from dledger.dateutil import next_month, previous_month, last_of_month
from dledger.projection import FutureTransaction, symbol_conversion_factors
from dledger.record import (
    income, yearly, monthly, amount_per_share, symbols,
    tickers, by_ticker, latest, earliest, before, after
)

from typing import List


def print_simple_annual_report(records: List[Transaction]):
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
                    print(f'~ {amount.rjust(18)}  < {d.ljust(11)}')
                else:
                    print(f'~ {amount.rjust(18)}    {d.ljust(11)}')
            else:
                print(f'{amount.rjust(20)}    {d.ljust(11)}')
        if commodity != commodities[-1]:
            print()


def print_simple_monthly_report(records: List[Transaction]):
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
                    print(f'~ {amount.rjust(18)}    {d.ljust(11)}')
                else:
                    print(f'{amount.rjust(20)}    {d.ljust(11)}')

        if commodity != commodities[-1]:
            print()


def print_simple_quarterly_report(records: List[Transaction]):
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
                    print(f'~ {amount.rjust(18)}    {d.ljust(11)}')
                else:
                    print(f'{amount.rjust(20)}    {d.ljust(11)}')
        if commodity != commodities[-1]:
            print()


def print_simple_report(records: List[Transaction]):
    for transaction in records:
        amount = format_amount(transaction.amount.value, trailing_zero=False)
        amount = transaction.amount.format % amount

        d = transaction.date.strftime('%Y/%m/%d')

        if isinstance(transaction, FutureTransaction):
            print(f'~ {amount.rjust(18)}  < {d} {transaction.ticker}')
        else:
            if transaction.is_special:
                print(f'{amount.rjust(20)}  * {d} {transaction.ticker}')
            else:
                print(f'{amount.rjust(20)}    {d} {transaction.ticker}')


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

            weights.append((ticker, amount, weight))
        weights.sort(key=lambda w: w[2], reverse=True)
        for weight in weights:
            ticker, amount, pct = weight
            pct = f'{format_amount(pct)}%'
            print(f'{amount.rjust(20)}    {pct.rjust(7)}    {ticker}')


def print_simple_chart(records: List[Transaction]):
    for transaction in records:
        amount = format_amount(transaction.amount.value, trailing_zero=False)
        amount = transaction.amount.format % amount

        d = transaction.date.strftime('%Y/%m/%d')

        if isinstance(transaction, FutureTransaction):
            line = f'~ {amount.rjust(18)}  < {d}'
        else:
            if transaction.is_special:
                line = f'{amount.rjust(20)}  * {d}'
            else:
                line = f'{amount.rjust(20)}    {d}'

        if transaction.dividend is not None:
            dividend = format_amount(transaction.dividend.value, trailing_zero=False)
            dividend = transaction.dividend.format % dividend

            line = f'{line} {dividend.rjust(12)}'
        else:
            dividend = format_amount(amount_per_share(transaction), trailing_zero=False)
            dividend = transaction.amount.format % dividend

            line = f'{line} {dividend.rjust(12)}'

        line = f'{line} / {transaction.position}'

        print(line)


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
        print_stat_row('Earliest', f'{records[0].date}')
        print_stat_row('Latest', f'{records[-1].date}')
        print_stat_row('Tickers', f'{len(tickers(records))}')
        currencies = sorted(symbols(records))
        if len(currencies) > 0:
            print_stat_row('Symbols', f'{currencies}')
            conversion_rates = symbol_conversion_factors(records)
            conversion_keys = sorted(symbol_conversion_factors(records), key=lambda c: c[0])
            for from_symbol, to_symbol in conversion_keys:
                conversion_rate = conversion_rates[(from_symbol, to_symbol)]
                conversion_rate_amount = format_amount(conversion_rate)
                print_stat_row(f'{from_symbol}/{to_symbol}', f'{conversion_rate_amount}')


def print_simple_rolling_report(records: List[Transaction]):
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
                if ending_date > datetime.today().date():
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
                    print(f'~ {amount.rjust(18)}  < {d}')
                else:
                    print(f'{amount.rjust(20)}  < {d}')

        if commodity != commodities[-1]:
            print()
