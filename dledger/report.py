import locale
import os

from datetime import date

from dledger.journal import Transaction, Distribution, max_decimal_places
from dledger.formatutil import format_amount, decimalplaces
from dledger.printutil import (
    colored,
    COLOR_NEGATIVE,
    COLOR_NEGATIVE_UNDERLINED,
    COLOR_UNDERLINED,
    COLOR_MARKED,
)
from dledger.dateutil import previous_month, last_of_month, months_in_quarter, todayd
from dledger.projection import GeneratedAmount, GeneratedTransaction
from dledger.record import (
    income,
    yearly,
    monthly,
    symbols,
    labels,
    tickers,
    by_ticker,
    latest,
    earliest,
    before,
    after,
    dividends,
    amounts,
)

from typing import List, Dict, Optional, Tuple, Iterable, Callable


def print_simple_annual_report(records: List[Transaction]) -> None:
    today = todayd()
    years = range(
        earliest(records).entry_date.year, latest(records).entry_date.year + 1
    )

    commodities = sorted(symbols(records, excluding_dividends=True))
    amount_decimals, _, _ = decimals_per_component(records)

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        for year in years:
            yearly_transactions = list(yearly(matching_transactions, year=year))
            if len(yearly_transactions) == 0:
                continue

            total = income(yearly_transactions)
            decimals = amount_decimals[commodity]
            if decimals is not None:
                amount = format_amount(total, places=decimals)
            else:
                amount = format_amount(total)
            amount = latest_transaction.amount.fmt % amount
            d = f"{year}"
            if any(isinstance(r.amount, GeneratedAmount) for r in yearly_transactions):
                if year == years[-1]:
                    d = latest_transaction.entry_date.strftime("%Y/%m")
                    line = f"~ {amount.rjust(18)}  < {d.ljust(11)}"
                else:
                    line = f"~ {amount.rjust(18)}    {d.ljust(11)}"
            else:
                line = f"{amount.rjust(20)}    {d.ljust(11)}"
            payers = formatted_prominent_payers(yearly_transactions)
            line = f"{line}{payers}"
            if today.year == year:
                print(colored(line, COLOR_MARKED))
            else:
                print(line)
        if commodity != commodities[-1]:
            print()


def print_simple_monthly_report(records: List[Transaction]) -> None:
    today = todayd()
    years = range(
        earliest(records).entry_date.year, latest(records).entry_date.year + 1
    )

    commodities = sorted(symbols(records, excluding_dividends=True))
    amount_decimals, _, _ = decimals_per_component(records)

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        for year in years:
            for month in range(1, 12 + 1):
                monthly_transactions = list(
                    monthly(matching_transactions, year=year, month=month)
                )
                if len(monthly_transactions) == 0:
                    continue

                total = income(monthly_transactions)
                decimals = amount_decimals[commodity]
                if decimals is not None:
                    amount = format_amount(total, places=decimals)
                else:
                    amount = format_amount(total)
                amount = latest_transaction.amount.fmt % amount
                month_indicator = f"{month}".zfill(2)
                d = f"{year}/{month_indicator}"
                if any(
                    isinstance(r.amount, GeneratedAmount) for r in monthly_transactions
                ):
                    line = f"~ {amount.rjust(18)}    {d.ljust(11)}"
                else:
                    line = f"{amount.rjust(20)}    {d.ljust(11)}"
                payers = formatted_prominent_payers(monthly_transactions)
                line = f"{line}{payers}"
                if today.year == year and today.month == month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)

        if commodity != commodities[-1]:
            print()


def print_simple_quarterly_report(records: List[Transaction]) -> None:
    today = todayd()
    years = range(
        earliest(records).entry_date.year, latest(records).entry_date.year + 1
    )

    commodities = sorted(symbols(records, excluding_dividends=True))
    amount_decimals, _, _ = decimals_per_component(records)

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        for year in years:
            for quarter in range(1, 4 + 1):
                months = months_in_quarter(quarter)
                starting_month = months[0]
                ending_month = months[-1]

                quarterly_transactions = []
                for month in range(starting_month, ending_month + 1):
                    monthly_transactions = monthly(
                        matching_transactions, year=year, month=month
                    )
                    quarterly_transactions.extend(monthly_transactions)
                if len(quarterly_transactions) == 0:
                    continue

                total = income(quarterly_transactions)
                decimals = amount_decimals[commodity]
                if decimals is not None:
                    amount = format_amount(total, places=decimals)
                else:
                    amount = format_amount(total)
                amount = latest_transaction.amount.fmt % amount
                d = f"{year}/Q{quarter}"
                if any(
                    isinstance(r.amount, GeneratedAmount)
                    for r in quarterly_transactions
                ):
                    line = f"~ {amount.rjust(18)}    {d.ljust(11)}"
                else:
                    line = f"{amount.rjust(20)}    {d.ljust(11)}"
                payers = formatted_prominent_payers(quarterly_transactions)
                line = f"{line}{payers}"
                if today.year == year and ending_month > today.month >= starting_month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)
        if commodity != commodities[-1]:
            print()


def print_simple_report(records: List[Transaction], *, detailed: bool = False) -> None:
    today = todayd()

    amount_decimals, dividend_decimals, position_decimals = decimals_per_component(
        records
    )

    underlined_record = next(
        (x for x in reversed(records) if x.entry_date < today), None
    )
    if len(records) > 0 and underlined_record is records[-1]:
        # don't underline the final transaction; there's no transactions below
        underlined_record = None
    for transaction in records:
        should_colorize_expired_transaction = False
        payout = transaction.amount.value
        decimals = amount_decimals[transaction.amount.symbol]
        if decimals is not None:
            amount = format_amount(payout, places=decimals)
        else:
            amount = format_amount(payout)
        amount = transaction.amount.fmt % amount

        d = transaction.entry_date.strftime("%Y/%m/%d")

        if isinstance(transaction.amount, GeneratedAmount):
            line = f"~ {amount.rjust(18)}"
        else:
            line = f"{amount.rjust(20)}"

        if transaction.entry_attr is not None and transaction.entry_attr.is_preliminary:
            should_colorize_expired_transaction = True
            # call attention as it is a preliminary record, not completed yet
            # note that we can't rely on color being supported,
            # so a textual indication must also be applied
            line = f"{line}  ! {d} {transaction.ticker.ljust(8)}"

            if not detailed:
                if transaction.payout_date is not None:
                    pd = transaction.payout_date.strftime("%Y/%m/%d")
                    pd = f"[{pd}]"
                    line = f"{line} {pd.rjust(18)}"
        else:
            if isinstance(transaction, GeneratedTransaction):
                if transaction.entry_date < today:
                    should_colorize_expired_transaction = True
                    # call attention as it may be a payout about to happen, or a closed position
                    line = f"{line}  ~ {d} {transaction.ticker.ljust(8)}"
                else:
                    # indicate that the transaction is expected before, or by, date
                    line = f"{line} <~ {d} {transaction.ticker.ljust(8)}"
            else:
                # todo: we're ignoring these indicators for preliminary records; is that right?
                if transaction.kind is Distribution.INTERIM:
                    line = f"{line}  ^ {d} {transaction.ticker.ljust(8)}"
                elif transaction.kind is Distribution.SPECIAL:
                    line = f"{line}  * {d} {transaction.ticker.ljust(8)}"
                else:
                    line = f"{line}    {d} {transaction.ticker.ljust(8)}"

        if detailed:
            decimals = position_decimals[transaction.ticker]
            if decimals is not None:
                p = format_amount(
                    transaction.position, trailing_zero=False, places=decimals
                )
            else:
                p = format_amount(
                    transaction.position, trailing_zero=False, rounded=False
                )
            position = f"({p})".rjust(18)
            line = f"{line} {position}"

            if transaction.dividend is not None:
                decimals = dividend_decimals[transaction.dividend.symbol]
                if decimals is not None:
                    dividend = format_amount(transaction.dividend.value, places=decimals)
                else:
                    dividend = format_amount(transaction.dividend.value)
                dividend = transaction.dividend.fmt % dividend
                line = f"{line} {dividend.rjust(16)}"

        if should_colorize_expired_transaction:
            if transaction is underlined_record:
                line = colored(line, COLOR_NEGATIVE_UNDERLINED)
            else:
                line = colored(line, COLOR_NEGATIVE)
        elif transaction is underlined_record:
            line = colored(line, COLOR_UNDERLINED)

        print(line)


def print_simple_weight_by_ticker(records: List[Transaction]) -> None:
    commodities = sorted(symbols(records, excluding_dividends=True))

    amount_decimals, _, _ = decimals_per_component(records)

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        total_income = income(matching_transactions)

        weights = []
        for ticker in tickers(matching_transactions):
            filtered_records = list(by_ticker(records, ticker))
            income_by_ticker = income(filtered_records)

            decimals = amount_decimals[commodity]
            if decimals is not None:
                amount = format_amount(income_by_ticker, places=decimals)
            else:
                amount = format_amount(income_by_ticker)
            amount = latest_transaction.amount.fmt % amount

            weight = income_by_ticker / total_income * 100

            is_estimate = any(
                isinstance(r.amount, GeneratedAmount) for r in filtered_records
            )

            weights.append((ticker, amount, weight, is_estimate))
        weights.sort(key=lambda w: w[2], reverse=True)
        for weight in weights:
            ticker, amount, pct, is_estimate = weight
            pct = f"{format_amount(pct, places=2)}%"
            if is_estimate:
                print(f"~ {amount.rjust(18)}    {pct.rjust(7)}    {ticker}")
            else:
                print(f"{amount.rjust(20)}    {pct.rjust(7)}    {ticker}")
        if commodity != commodities[-1]:
            print()


def print_simple_sum_report(records: List[Transaction]) -> None:
    commodities = sorted(symbols(records, excluding_dividends=True))

    amount_decimals, _, _ = decimals_per_component(records)

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)

        total = income(matching_transactions)
        decimals = amount_decimals[commodity]
        if decimals is not None:
            amount = format_amount(total, places=decimals)
        else:
            amount = format_amount(total)
        amount = latest_transaction.amount.fmt % amount

        if any(isinstance(r.amount, GeneratedAmount) for r in matching_transactions):
            line = f"~ {amount.rjust(18)}"
        else:
            line = f"{amount.rjust(20)}"
        payers = formatted_prominent_payers(matching_transactions)
        line = f"{line}               {payers}"
        print(line)
        if commodity != commodities[-1]:
            print()


def print_stat_row(name: str, text: str) -> None:
    name = name.rjust(10)
    print(f"{name}: {text}")


def print_journal_stats(
        records: List[Transaction],
        input_paths: List[str]
) -> None:
    # find all source paths and weed out duplicates
    source_paths = set(record.entry_attr.location[0] for record in records)
    # resolve absolute path for each source path
    source_paths = list(os.path.abspath(path) for path in source_paths)
    # resolve absolute path for each input source path
    input_source_paths = list(os.path.abspath(path) for path in input_paths)
    # find all journals that must have been included from another journal
    included_paths = sorted(path for path in source_paths if path not in input_source_paths)
    # find all journals that must have been specified as an input
    journal_paths = sorted(path for path in source_paths if path in input_source_paths)
    # todo: consider only counting input sources and having included journals in separate section
    for n, path in enumerate(journal_paths + included_paths):
        print_stat_row(
            f"Journal {n + 1}",
            path + (
                " (included)" if path in included_paths else ""
            )
        )


def print_conversion_stats(
        records: List[Transaction],
        rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None
) -> None:
    currencies = sorted(symbols(records))
    if len(currencies) > 0:
        print_stat_row("Currencies", f"{currencies}")
    if rates is not None:
        conversion_keys = sorted(rates, key=lambda c: c[0])
        for from_symbol, to_symbol in conversion_keys:
            conversion_rate = rates[(from_symbol, to_symbol)]
            conversion_rate_amount = format_amount(conversion_rate[1])
            conversion_rate_datestamp = conversion_rate[0].strftime("%Y/%m/%d")
            print_stat_row(
                f"{from_symbol}/{to_symbol}",
                f"{conversion_rate_amount} (as of {conversion_rate_datestamp})"
            )


def print_stats(
    records: List[Transaction],
    input_paths: List[str],
    *,
    rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None,
) -> None:
    print_journal_stats(records, input_paths)
    try:
        lc = locale.getlocale(locale.LC_NUMERIC)
        print_stat_row("Locale", f"{lc}")
    except locale.Error:
        print_stat_row("Locale", "Not configured")
    if len(records) == 0:
        return
    print_stat_row("Records", f"{len(records)}")
    # todo: records last 30/7 days
    earliest_datestamp = records[0].entry_date.strftime("%Y/%m/%d")
    latest_datestamp = records[-1].entry_date.strftime("%Y/%m/%d")
    print_stat_row("Earliest", earliest_datestamp)
    print_stat_row("Latest", latest_datestamp)
    print_stat_row("Tickers", f"{len(tickers(records))}")
    print_conversion_stats(records, rates)
    tags = sorted(labels(records))
    if len(tags) > 0:
        print_stat_row("Tags", f"{tags}")


def print_simple_rolling_report(records: List[Transaction]) -> None:
    # note that this report can be confusing; the "next 12m" row
    # indicates the sum of all forecasted/preliminary records, however
    # having preliminary records that just pass their entry date can
    # incur a drop in the sum, which can look like it just disappeared
    # out of thin air - it will be included when the month passes
    # todo: consider including past preliminary records as still being "in the future"
    today = todayd()
    years = range(
        earliest(records).entry_date.year, latest(records).entry_date.year + 1
    )

    commodities = sorted(symbols(records, excluding_dividends=True))

    amount_decimals, _, _ = decimals_per_component(records)

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
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
                rolling_transactions = list(
                    before(
                        after(matching_transactions, starting_date_ex), ending_date_ex
                    )
                )
                if len(rolling_transactions) == 0:
                    continue
                total = income(rolling_transactions)
                decimals = amount_decimals[commodity]
                if decimals is not None:
                    amount = format_amount(total, places=decimals)
                else:
                    amount = format_amount(total)
                amount = latest_transaction.amount.fmt % amount
                d = ending_date.strftime("%Y/%m")
                if any(
                    isinstance(r.amount, GeneratedAmount) for r in rolling_transactions
                ):
                    line = f"~ {amount.rjust(18)}  < {d.ljust(11)}"
                else:
                    line = f"{amount.rjust(20)}  < {d.ljust(11)}"
                payers = formatted_prominent_payers(rolling_transactions)
                line = f"{line}{payers}"
                if today.year == year and today.month == month:
                    print(colored(line, COLOR_MARKED))
                else:
                    print(line)
                should_breakline = True

        future_transactions = [r for r in matching_transactions if r.entry_date > today]
        if len(future_transactions) > 0:
            total = income(future_transactions)
            decimals = amount_decimals[commodity]
            if decimals is not None:
                amount = format_amount(total, places=decimals)
            else:
                amount = format_amount(total)
            amount = latest_transaction.amount.fmt % amount
            payers = formatted_prominent_payers(future_transactions)
            print(f"~ {amount.rjust(18)}    next 12m   {payers}")
            should_breakline = True

        if commodity != commodities[-1] and should_breakline:
            print()


DRIFT_BY_WEIGHT = 0
DRIFT_BY_AMOUNT = 1
DRIFT_BY_POSITION = 2


def print_balance_report(
    records: List[Transaction], *, deviance: int = DRIFT_BY_WEIGHT
) -> None:
    commodities = sorted(symbols(records, excluding_dividends=True))
    # todo: note that this isn't actually very useful; every record here
    #       is likely to be a generated one; i.e. a forecasted record,
    #       and these typically have no preference on decimal places
    #       so what will happen is format_amount will always fallback
    #       to the default number of decimal places
    amount_decimals, _, _ = decimals_per_component(records)

    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
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
            weight = income_by_ticker / total_income * 100
            weight_drift = target_weight - weight
            amount_drift = target_income - income_by_ticker
            aps = income_by_ticker / position
            position_drift = amount_drift / aps
            drift = (weight_drift, amount_drift, position_drift)
            has_estimate = any(
                isinstance(r.amount, GeneratedAmount) for r in filtered_records
            )
            weights.append(
                (
                    ticker,
                    income_by_ticker,
                    latest_transaction.amount.fmt,
                    weight,
                    position,
                    drift,
                    number_of_payouts,
                    has_estimate,
                )
            )
        weights.sort(key=lambda w: w[1], reverse=True)
        for weight in weights:
            ticker, amount, fmt, pct, p, drift, n, has_estimate = weight
            wdrift, adrift, pdrift = drift
            pct = f"{format_amount(pct, places=2)}%"
            freq = f"{n}"
            decimals = amount_decimals[commodity]
            if decimals is not None:
                amount = format_amount(amount, places=decimals)
            else:
                amount = format_amount(amount)
            amount = fmt % amount
            if has_estimate:
                line = f"~ {amount.rjust(18)}  / {freq.ljust(2)} {pct.rjust(7)} {ticker.ljust(8)}"
            else:
                line = f"{amount.rjust(20)}  / {freq.ljust(2)} {pct.rjust(7)} {ticker.ljust(8)}"
            p_decimals = decimalplaces(p)
            p = format_amount(p, places=p_decimals)
            position = f"({p})".rjust(18)
            if deviance == DRIFT_BY_WEIGHT:
                if wdrift >= 0:
                    drift = f"+ {format_amount(wdrift, places=2)}%".rjust(16)
                else:
                    drift = f"- {format_amount(abs(wdrift), places=2)}%".rjust(16)
            elif deviance == DRIFT_BY_AMOUNT:
                amount_drift = fmt % format_amount(abs(adrift))
                if adrift >= 0:
                    drift = f"+ {amount_drift}".rjust(16)
                else:
                    drift = f"- {amount_drift}".rjust(16)
            elif deviance == DRIFT_BY_POSITION:
                if pdrift >= 0:
                    # increase position (buy)
                    drift = f"+ {format_amount(pdrift, places=p_decimals)}".rjust(16)
                else:
                    # decrease position (sell)
                    drift = f"- {format_amount(abs(pdrift), places=p_decimals)}".rjust(
                        16
                    )
            line = f"{line} {position} {drift}"
            print(line)
        if commodity != commodities[-1]:
            print()


def print_currency_balance_report(records: List[Transaction]) -> None:
    commodities = sorted(symbols(records, excluding_dividends=True))
    # todo: see note in print_balance_report
    amount_decimals, _, _ = decimals_per_component(records)
    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
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
                filter(lambda r: r.dividend.symbol == symbol, matching_transactions)
            )
            income_by_symbol = income(filtered_records)
            weight = income_by_symbol / total_income * 100
            weight_drift = target_weight - weight
            has_estimate = any(
                isinstance(r.amount, GeneratedAmount) for r in filtered_records
            )
            weights.append(
                (
                    symbol,
                    income_by_symbol,
                    latest_transaction.amount.fmt,
                    weight,
                    weight_drift,
                    len(tickers(filtered_records)),
                    has_estimate,
                )
            )
        weights.sort(key=lambda w: w[1], reverse=True)
        for weight in weights:
            symbol, amount, fmt, pct, wdrift, p, has_estimate = weight
            pct = f"{format_amount(pct, places=2)}%"
            decimals = amount_decimals[commodity]
            if decimals is not None:
                amount = format_amount(amount, places=decimals)
            else:
                amount = format_amount(amount)
            amount = fmt % amount
            positions = f"({p})".rjust(18)
            if wdrift >= 0:
                drift = f"+ {format_amount(wdrift, places=2)}%".rjust(16)
            else:
                drift = f"- {format_amount(abs(wdrift), places=2)}%".rjust(16)
            if has_estimate:
                line = f"~ {amount.rjust(18)}"
            else:
                line = f"{amount.rjust(20)}"
            line = f"{line}       {pct.rjust(7)} {symbol.ljust(8)} {positions} {drift}"
            print(line)
        if commodity != commodities[-1]:
            print()


def most_prominent_payers(records: List[Transaction]) -> List[str]:
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
    formatted = ", ".join(top)
    formatted = (formatted[:30] + "…") if len(formatted) > 30 else formatted
    if len(bottom) > 0:
        additionals = f"(+{len(bottom)})"
        formatted = f"{formatted} {additionals}"
    return formatted


def decimals_per_component(
    records: List[Transaction],
) -> Tuple[
    Dict[str, Optional[int]], Dict[str, Optional[int]], Dict[str, Optional[int]]
]:
    amount_decimal_places: Dict[str, Optional[int]] = dict()
    dividend_decimal_places: Dict[str, Optional[int]] = dict()
    position_decimal_places: Dict[str, Optional[int]] = dict()

    for symbol in symbols(records):
        amount_decimal_places[symbol] = max_decimal_places(amounts(records, symbol))
        # todo: note that this is not necessarily what we want; i think preferably
        #       this component had another layer of specificity; i.e. the ticker
        #       the problem is that if there's just _one_ occurrence of a dividend
        #       of e.g. 4 decimals, then _all_ dividends will be set to this precision
        #       right now this is not a problem, because there is no report that includes
        #       the dividend of more than just one ticker anyway
        dividend_decimal_places[symbol] = max_decimal_places(dividends(records, symbol))
        # todo: this would work as a fallback and could be useful
        #       in particular for forecasted records with no preference
        #       toward decimal places; however, it would also lead to
        #       probably unexpected number of decimals... same issue as above
        #       for example, a "$ 0.1925" dividend would cause all payouts to have 4 decimal places
        # if amount_decimal_places[symbol] is None:
        #     amount_decimal_places[symbol] = dividend_decimal_places[symbol]
    for ticker in tickers(records):
        # note ticker key for position component; not symbol
        position_decimal_places[ticker] = max(
            decimalplaces(r.position) for r in records if r.ticker == ticker
        )
    return (amount_decimal_places, dividend_decimal_places, position_decimal_places)
