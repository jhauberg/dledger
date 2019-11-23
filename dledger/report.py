from dledger.journal import Transaction
from dledger.formatutil import format_amount
from dledger.projection import FutureTransaction
from dledger.record import (
    income, yearly, monthly, amount_per_share, symbols,
    tickers, by_ticker, latest, earliest
)

from typing import List


def print_simple_annual_report(records: List[Transaction]):
    transactions = list(filter(lambda r: r.amount is not None, records))

    if len(transactions) == 0:
        return

    years = range(earliest(transactions).date.year,
                  latest(transactions).date.year + 1)

    commodities = sorted(symbols(transactions, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, transactions))
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
    transactions = list(filter(lambda r: r.amount is not None, records))

    if len(transactions) == 0:
        return

    years = range(earliest(transactions).date.year,
                  latest(transactions).date.year + 1)

    commodities = sorted(symbols(transactions, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, transactions))
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
    transactions = list(filter(lambda r: r.amount is not None, records))

    if len(transactions) == 0:
        return

    years = range(earliest(transactions).date.year,
                  latest(transactions).date.year + 1)

    commodities = sorted(symbols(transactions, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, transactions))
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
