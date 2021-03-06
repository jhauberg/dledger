import locale
import os

from datetime import datetime, date

from dledger.journal import Transaction, Distribution, max_decimal_places
from dledger.formatutil import format_amount, decimalplaces
from dledger.printutil import (
    colored,
    COLOR_NEGATIVE, COLOR_NEGATIVE_UNDERLINED,
    COLOR_UNDERLINED,
    COLOR_MARKED
)
from dledger.dateutil import previous_month, last_of_month
from dledger.projection import (
    GeneratedAmount, GeneratedTransaction,
    symbol_conversion_factors
)
from dledger.record import (
    income, yearly, monthly, symbols,
    tickers, by_ticker, latest, earliest, before, after
)

from typing import List, Dict, Optional


def print_simple_annual_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).entry_date.year,
                  latest(records).entry_date.year + 1)

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
            amount = latest_transaction.amount.fmt % amount
            d = f'{year}'
            if any(isinstance(r.amount, GeneratedAmount) for r in yearly_transactions):
                if year == years[-1]:
                    d = latest_transaction.entry_date.strftime('%Y/%m')
                    line = f'~ {amount.rjust(18)}  < {d.ljust(11)}'
                else:
                    line = f'~ {amount.rjust(18)}    {d.ljust(11)}'
            else:
                line = f'{amount.rjust(20)}    {d.ljust(11)}'
            payers = formatted_prominent_payers(yearly_transactions)
            line = f'{line}{payers}'
            if today.year == year:
                print(colored(line, COLOR_MARKED))
            else:
                print(line)
        if commodity != commodities[-1]:
            print()


def print_simple_monthly_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).entry_date.year,
                  latest(records).entry_date.year + 1)

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
                amount = latest_transaction.amount.fmt % amount
                month_indicator = f'{month}'.zfill(2)
                d = f'{year}/{month_indicator}'
                if any(isinstance(r.amount, GeneratedAmount) for r in monthly_transactions):
                    line = f'~ {amount.rjust(18)}    {d.ljust(11)}'
                else:
                    line = f'{amount.rjust(20)}    {d.ljust(11)}'
                payers = formatted_prominent_payers(monthly_transactions)
                line = f'{line}{payers}'
                if today.year == year and today.month == month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)

        if commodity != commodities[-1]:
            print()


def print_simple_quarterly_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).entry_date.year,
                  latest(records).entry_date.year + 1)

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
                amount = latest_transaction.amount.fmt % amount
                d = f'{year}/Q{quarter}'
                if any(isinstance(r.amount, GeneratedAmount) for r in quarterly_transactions):
                    line = f'~ {amount.rjust(18)}    {d.ljust(11)}'
                else:
                    line = f'{amount.rjust(20)}    {d.ljust(11)}'
                payers = formatted_prominent_payers(quarterly_transactions)
                line = f'{line}{payers}'
                if today.year == year and ending_month > today.month >= starting_month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)
        if commodity != commodities[-1]:
            print()


def print_simple_report(records: List[Transaction], *, detailed: bool = False):
    today = datetime.today().date()
    payout_decimal_places: Dict[str, Optional[int]] = dict()
    dividend_decimal_places: Dict[str, Optional[int]] = dict()
    position_decimal_places: Dict[str, Optional[int]] = dict()
    for ticker in tickers(records):
        payout_decimal_places[ticker] = max_decimal_places(
            (r.amount for r in records if r.ticker == ticker)
        )
    if detailed:
        for ticker in tickers(records):
            dividend_decimal_places[ticker] = max_decimal_places(
                (r.dividend for r in records if r.ticker == ticker)
            )
            position_decimal_places[ticker] = max(
                decimalplaces(r.position) for r in records if r.ticker == ticker
            )
    underlined_record = next((x for x in reversed(records) if x.entry_date < today), None)
    if len(records) > 0 and underlined_record is records[-1]:
        # don't underline the final transaction; there's no transactions below
        underlined_record = None
    for transaction in records:
        should_colorize_expired_transaction = False
        payout = transaction.amount.value
        amount_decimal_places = payout_decimal_places[transaction.ticker]
        if amount_decimal_places is not None:
            amount = format_amount(payout, places=amount_decimal_places)
        else:
            amount = format_amount(payout)
        amount = transaction.amount.fmt % amount

        d = transaction.entry_date.strftime('%Y/%m/%d')

        if isinstance(transaction.amount, GeneratedAmount):
            line = f'~ {amount.rjust(18)}'
        else:
            line = f'{amount.rjust(20)}'

        if transaction.entry_attr is not None and transaction.entry_attr.is_preliminary:
            should_colorize_expired_transaction = True
            # call attention as it is a preliminary record, not completed yet
            # note that we can't rely on color being supported,
            # so a textual indication must also be applied
            line = f'{line}  ! {d} {transaction.ticker.ljust(8)}'

            if not detailed:
                if transaction.payout_date is not None:
                    pd = transaction.payout_date.strftime('%Y/%m/%d')
                    pd = f'[{pd}]'
                    line = f'{line} {pd.rjust(18)}'
        else:
            if isinstance(transaction, GeneratedTransaction):
                if transaction.entry_date < today:
                    should_colorize_expired_transaction = True
                    # call attention as it may be a payout about to happen, or a closed position
                    line = f'{line}  ~ {d} {transaction.ticker.ljust(8)}'
                else:
                    # indicate that the transaction is expected before, or by, date
                    line = f'{line} <~ {d} {transaction.ticker.ljust(8)}'
            else:
                # todo: we're ignoring these indicators for preliminary records; is that right?
                if transaction.kind is Distribution.INTERIM:
                    line = f'{line}  ^ {d} {transaction.ticker.ljust(8)}'
                elif transaction.kind is Distribution.SPECIAL:
                    line = f'{line}  * {d} {transaction.ticker.ljust(8)}'
                else:
                    line = f'{line}    {d} {transaction.ticker.ljust(8)}'

        if detailed:
            p_decimal_places = position_decimal_places[transaction.ticker]
            if p_decimal_places is not None:
                p = format_amount(transaction.position, trailing_zero=False,
                                  places=p_decimal_places)
            else:
                p = format_amount(transaction.position, trailing_zero=False, rounded=False)
            position = f'({p})'.rjust(18)
            line = f'{line} {position}'

            assert transaction.dividend is not None

            div_decimal_places = dividend_decimal_places[transaction.ticker]
            if div_decimal_places is not None:
                dividend = format_amount(transaction.dividend.value,
                                         places=div_decimal_places)
            else:
                dividend = format_amount(transaction.dividend.value)
            dividend = transaction.dividend.fmt % dividend
            line = f'{line} {dividend.rjust(16)}'

        if should_colorize_expired_transaction:
            if transaction is underlined_record:
                line = colored(line, COLOR_NEGATIVE_UNDERLINED)
            else:
                line = colored(line, COLOR_NEGATIVE)
        elif transaction is underlined_record:
            line = colored(line, COLOR_UNDERLINED)

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
        for ticker in tickers(matching_transactions):
            filtered_records = list(by_ticker(records, ticker))
            income_by_ticker = income(filtered_records)

            amount = format_amount(income_by_ticker, trailing_zero=False)
            amount = latest_transaction.amount.fmt % amount

            weight = income_by_ticker / total_income * 100

            is_estimate = any(isinstance(r.amount, GeneratedAmount) for r in filtered_records)
            
            weights.append((ticker, amount, weight, is_estimate))
        weights.sort(key=lambda w: w[2], reverse=True)
        for weight in weights:
            ticker, amount, pct, is_estimate = weight
            pct = f'{format_amount(pct)}%'
            if is_estimate:
                print(f'~ {amount.rjust(18)}    {pct.rjust(7)}    {ticker}')
            else:
                print(f'{amount.rjust(20)}    {pct.rjust(7)}    {ticker}')
        if commodity != commodities[-1]:
            print()


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
        amount = latest_transaction.amount.fmt % amount

        if any(isinstance(r.amount, GeneratedAmount) for r in matching_transactions):
            line = f'~ {amount.rjust(18)}'
        else:
            line = f'{amount.rjust(20)}'
        payers = formatted_prominent_payers(matching_transactions)
        line = f'{line}               {payers}'
        print(line)
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
        earliest_datestamp = records[0].entry_date.strftime('%Y/%m/%d')
        latest_datestamp = records[-1].entry_date.strftime('%Y/%m/%d')
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


def most_prominent_payers(records: List[Transaction]) \
        -> List[str]:
    combined_income_per_ticker = []
    for ticker in tickers(records):
        filtered_records = list(by_ticker(records, ticker))
        combined_income_per_ticker.append((ticker, income(filtered_records)))
    combined_income_per_ticker.sort(key=lambda x: x[1], reverse=True)
    return [ticker for ticker, _ in combined_income_per_ticker]


def formatted_prominent_payers(records: List[Transaction], *, limit: int = 3) -> str:
    payers = most_prominent_payers(records)
    top = payers[:limit]
    bottom = [payer for payer in payers if payer not in top]
    formatted = ', '.join(top)
    formatted = (formatted[:30] + '…') if len(formatted) > 30 else formatted
    if len(bottom) > 0:
        additionals = f'(+{len(bottom)})'
        formatted = f'{formatted} {additionals}'
    return formatted


def print_simple_rolling_report(records: List[Transaction]):
    today = datetime.today().date()
    years = range(earliest(records).entry_date.year,
                  latest(records).entry_date.year + 1)

    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        should_breakline = False
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
                amount = latest_transaction.amount.fmt % amount
                d = ending_date.strftime('%Y/%m')
                if any(isinstance(r.amount, GeneratedAmount) for r in rolling_transactions):
                    line = f'~ {amount.rjust(18)}  < {d.ljust(11)}'
                else:
                    line = f'{amount.rjust(20)}  < {d.ljust(11)}'
                payers = formatted_prominent_payers(rolling_transactions)
                line = f'{line}{payers}'
                if today.year == year and today.month == month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)
                should_breakline = True

        future_transactions = [r for r in matching_transactions if r.entry_date > today]
        if len(future_transactions) > 0:
            total = income(future_transactions)
            amount = format_amount(total, trailing_zero=False)
            amount = latest_transaction.amount.fmt % amount
            payers = formatted_prominent_payers(future_transactions)
            print(f'~ {amount.rjust(18)}    next 12m   {payers}')
            should_breakline = True

        if commodity != commodities[-1] and should_breakline:
            print()


DRIFT_BY_WEIGHT = 0
DRIFT_BY_AMOUNT = 1
DRIFT_BY_POSITION = 2


def print_balance_report(records: List[Transaction], *, deviance: int = DRIFT_BY_WEIGHT):
    commodities = sorted(symbols(records, excluding_dividends=True))

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        total_income = income(matching_transactions)
        ticks = tickers(matching_transactions)
        target_weight = 100 / len(ticks)
        target_income = total_income * target_weight / 100
        weights = []
        for ticker in ticks:
            filtered_records = list(by_ticker(records, ticker))
            latest_transaction_by_ticker = latest(filtered_records)
            assert latest_transaction_by_ticker is not None
            position = latest_transaction_by_ticker.position
            income_by_ticker = income(filtered_records)
            number_of_payouts = len(filtered_records)
            # amount = format_amount(income_by_ticker, trailing_zero=False)
            # amount = latest_transaction.amount.fmt % amount
            weight = income_by_ticker / total_income * 100
            weight_drift = target_weight - weight
            amount_drift = target_income - income_by_ticker
            # amount_drift = format_amount(amount_drift, trailing_zero=False)
            # amount_drift = latest_transaction.amount.fmt % amount_drift
            aps = income_by_ticker / position
            position_drift = amount_drift / aps
            drift = (weight_drift, amount_drift, position_drift)
            has_estimate = any(isinstance(r.amount, GeneratedAmount) for r in filtered_records)
            weights.append((ticker, income_by_ticker, latest_transaction.amount.fmt, weight,
                            position, drift, number_of_payouts, has_estimate))
        weights.sort(key=lambda w: w[1], reverse=True)
        for weight in weights:
            ticker, amount, fmt, pct, p, drift, n, has_estimate = weight
            wdrift, adrift, pdrift = drift
            pct = f'{format_amount(pct)}%'
            freq = f'{n}'
            amount = fmt % format_amount(amount, trailing_zero=False)
            if has_estimate:
                line = f'~ {amount.rjust(18)}  / {freq.ljust(2)} {pct.rjust(7)} {ticker.ljust(8)}'
            else:
                line = f'{amount.rjust(20)}  / {freq.ljust(2)} {pct.rjust(7)} {ticker.ljust(8)}'
            p_decimals = decimalplaces(p)
            p = format_amount(p, places=p_decimals)
            position = f'({p})'.rjust(18)
            if deviance == DRIFT_BY_WEIGHT:
                if wdrift >= 0:
                    drift = f'+ {format_amount(wdrift)}%'.rjust(16)
                else:
                    drift = f'- {format_amount(abs(wdrift))}%'.rjust(16)
            elif deviance == DRIFT_BY_AMOUNT:
                amount_drift = fmt % format_amount(abs(adrift), trailing_zero=False)
                if adrift >= 0:
                    drift = f'+ {amount_drift}'.rjust(16)
                else:
                    drift = f'- {amount_drift}'.rjust(16)
            elif deviance == DRIFT_BY_POSITION:
                if pdrift >= 0:
                    # increase position (buy)
                    drift = f'+ {format_amount(pdrift, places=p_decimals)}'.rjust(16)
                else:
                    # decrease position (sell)
                    drift = f'- {format_amount(abs(pdrift), places=p_decimals)}'.rjust(16)
            line = f'{line} {position} {drift}'
            print(line)
        if commodity != commodities[-1]:
            print()


def print_currency_balance_report(records: List[Transaction]):
    commodities = sorted(symbols(records, excluding_dividends=True))
    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records))
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        total_income = income(matching_transactions)
        weights = []
        dividend_symbols = []
        for transaction in matching_transactions:
            assert transaction.dividend is not None
            if transaction.dividend.symbol not in dividend_symbols:
                dividend_symbols.append(transaction.dividend.symbol)
        target_weight = 100 / len(dividend_symbols)
        for symbol in dividend_symbols:
            filtered_records = list(
                filter(lambda r: r.dividend.symbol == symbol, matching_transactions))
            income_by_symbol = income(filtered_records)
            weight = income_by_symbol / total_income * 100
            weight_drift = target_weight - weight
            has_estimate = any(isinstance(r.amount, GeneratedAmount) for r in filtered_records)
            weights.append((symbol, income_by_symbol, latest_transaction.amount.fmt, weight,
                            weight_drift, len(tickers(filtered_records)), has_estimate))
        weights.sort(key=lambda w: w[1], reverse=True)
        for weight in weights:
            symbol, amount, fmt, pct, wdrift, p, has_estimate = weight
            pct = f'{format_amount(pct)}%'
            amount = fmt % format_amount(amount, trailing_zero=False)
            positions = f'({p})'.rjust(18)
            if wdrift >= 0:
                drift = f'+ {format_amount(wdrift)}%'.rjust(16)
            else:
                drift = f'- {format_amount(abs(wdrift))}%'.rjust(16)
            if has_estimate:
                line = f'~ {amount.rjust(18)}'
            else:
                line = f'{amount.rjust(20)}'
            line = f'{line}       {pct.rjust(7)} {symbol.ljust(8)} {positions} {drift}'
            print(line)
        if commodity != commodities[-1]:
            print()
