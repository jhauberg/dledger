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
)
from dledger.dateutil import (
    previous_month,
    last_of_month,
    months_in_quarter,
    previous_quarter,
    todayd,
)
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

from typing import List, Dict, Optional, Tuple, Iterable


def print_simple_annual_report(
    records: List[Transaction], *, descending: bool = False
) -> None:
    today = todayd()
    final_year = latest(records).entry_date.year
    years = range(earliest(records).entry_date.year, final_year + 1)

    if descending:
        years = reversed(years)

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
            if contains_estimate_amount(yearly_transactions):
                if year == final_year:
                    d = latest_transaction.entry_date.strftime("%Y/%m")
                    line = f"~ {amount.rjust(18)}  < {d.ljust(11)}"
                else:
                    line = f"~ {amount.rjust(18)}    {d.ljust(11)}"
            else:
                line = f"{amount.rjust(20)}    {d.ljust(11)}"
            payers = formatted_prominent_payers(yearly_transactions)
            line = f"{line}{payers}"
            if year == today.year and not descending:
                # pad to full width to make underline consistent across reports
                line = f"{line: <79}"
                print(colored(line, COLOR_UNDERLINED))
            elif year == today.year + 1 and descending:
                line = f"{line: <79}"
                print(colored(line, COLOR_UNDERLINED))
            # todo: underline might not show when there's years with no income
            else:
                print(line)
        if commodity != commodities[-1]:
            print()


def print_simple_monthly_report(
    records: List[Transaction], *, descending: bool = False
) -> None:
    today = todayd()
    years = range(
        earliest(records).entry_date.year, latest(records).entry_date.year + 1
    )

    if descending:
        years = reversed(years)

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
            months = range(1, 12 + 1)
            if descending:
                months = reversed(months)
            for month in months:
                monthly_transactions = list(
                    monthly(matching_transactions, year=year, month=month)
                )
                if len(monthly_transactions) == 0:
                    continue

                comparable_transactions = list(
                    monthly(matching_transactions, year=year - 1, month=month)
                )
                total = income(monthly_transactions)
                total_comparable = income(comparable_transactions)
                pct_change = None
                if total_comparable > 0:
                    pct_change = (total - total_comparable) / total_comparable
                decimals = amount_decimals[commodity]
                if decimals is not None:
                    amount = format_amount(total, places=decimals)
                else:
                    amount = format_amount(total)
                amount = latest_transaction.amount.fmt % amount
                month_indicator = f"{month}".zfill(2)
                d = f"{year}/{month_indicator}"
                if contains_estimate_amount(monthly_transactions):
                    line = f"~ {amount.rjust(18)}    {d.ljust(11)}"
                else:
                    line = f"{amount.rjust(20)}    {d.ljust(11)}"
                if pct_change is not None and abs(pct_change) >= 0.01:
                    indicator = "+ " if pct_change > 0 else "- "
                    pct_change = f"{indicator}{format_amount(abs(pct_change), places=2)}%"
                else:
                    pct_change = ""
                line = f"{line}{pct_change}"
                if year == today.year and month == today.month and not descending:
                    # pad to full width to make underline consistent across reports
                    line = f"{line: <79}"
                    print(colored(line, COLOR_UNDERLINED))
                elif year == today.year and month == today.month + 1 and descending:
                    line = f"{line: <79}"
                    print(colored(line, COLOR_UNDERLINED))
                # todo: underline might not show when there's months with no income
                else:
                    print(line)

        if commodity != commodities[-1]:
            print()


def print_simple_quarterly_report(
    records: List[Transaction], *, descending: bool = False
) -> None:
    today = todayd()
    years = range(
        earliest(records).entry_date.year, latest(records).entry_date.year + 1
    )

    if descending:
        years = reversed(years)

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
            quarters = range(1, 4 + 1)
            if descending:
                quarters = reversed(quarters)
            for quarter in quarters:
                starting_month, _, ending_month = months_in_quarter(quarter)
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
                if contains_estimate_amount(quarterly_transactions):
                    line = f"~ {amount.rjust(18)}    {d.ljust(11)}"
                else:
                    line = f"{amount.rjust(20)}    {d.ljust(11)}"
                payers = formatted_prominent_payers(quarterly_transactions)
                line = f"{line}{payers}"
                if (
                    year == today.year
                    and today.month in months_in_quarter(quarter)
                    and not descending
                ):
                    # pad to full width to make underline consistent across reports
                    line = f"{line: <79}"
                    print(colored(line, COLOR_UNDERLINED))
                elif (
                    year == today.year
                    and today.month in months_in_quarter(previous_quarter(quarter))
                    and descending
                ):
                    line = f"{line: <79}"
                    print(colored(line, COLOR_UNDERLINED))
                # todo: underline might not show when there's quarters with no income
                else:
                    print(line)
        if commodity != commodities[-1]:
            print()


def previously_seen_on(txn: GeneratedTransaction) -> str:
    # indicate previously seen, at the earliest-latest, on past date
    # i.e. "when can I expect this dividend at the earliest or latest"
    assert txn.earliest_entry_date is not None
    assert txn.latest_entry_date is not None
    if txn.earliest_entry_date.month == txn.latest_entry_date.month:
        earliest_day = txn.earliest_entry_date.day
        month_name = txn.earliest_entry_date.strftime("%b")
        if txn.earliest_entry_date == txn.latest_entry_date:
            return f"{earliest_day} {month_name}"
        else:
            latest_day = txn.latest_entry_date.day
            return f"{earliest_day}-{latest_day} {month_name}"
    else:
        earliest_day = txn.earliest_entry_date.day
        earliest_month_name = txn.earliest_entry_date.strftime("%b")
        latest_day = txn.latest_entry_date.day
        latest_month_name = txn.latest_entry_date.strftime("%b")
        return (
            f"{earliest_day} {earliest_month_name} - "
            f"{latest_day} {latest_month_name}"
        )


def print_simple_report(
    records: List[Transaction], *, detailed: bool = False, descending: bool = False
) -> None:
    today = todayd()

    amount_decimals, dividend_decimals, position_decimals = decimals_per_component(
        records
    )

    if descending:
        records.reverse()
        underlined_record = next(
            (x for x in reversed(records) if x.entry_date > today), None
        )
    else:
        underlined_record = next(
            (x for x in reversed(records) if x.entry_date <= today), None
        )

    if underlined_record is not None:
        if not descending and underlined_record is records[-1]:
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

        if contains_estimate_amount([transaction]):
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
                if transaction.entry_date > today:
                    days_until = (transaction.entry_date - today).days
                    days_until = f"in {days_until} days"
                    line = f"{line} {days_until.rjust(18)}"
        else:
            if isinstance(transaction, GeneratedTransaction):
                if transaction.entry_date < today:
                    should_colorize_expired_transaction = True
                    # call attention as it may be a payout about to happen,
                    # or a closed position
                    line = f"{line}  ~ {d} {transaction.ticker.ljust(8)}"
                else:
                    # indicate that the transaction is expected before, or by, date
                    line = f"{line} <~ {d} {transaction.ticker.ljust(8)}"

                if not detailed:
                    if (
                        transaction.earliest_entry_date is not None
                        and transaction.latest_entry_date is not None
                    ):
                        seen_earlier = f"{previously_seen_on(transaction).rjust(15)}"
                        line = f"{line} {seen_earlier.rjust(18)}"
            else:
                # todo: we're ignoring these indicators for preliminary records;
                #       is that right?
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
                    dividend = format_amount(
                        transaction.dividend.value, places=decimals
                    )
                else:
                    dividend = format_amount(transaction.dividend.value)
                dividend = transaction.dividend.fmt % dividend
                line = f"{line} {dividend.rjust(16)}"

        if transaction is underlined_record:
            # pad to full width to make underline consistent across reports
            line = f"{line: <79}"

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
            filtered_records = list(by_ticker(matching_transactions, ticker))
            income_by_ticker = income(filtered_records)
            decimals = amount_decimals[commodity]
            if decimals is not None:
                amount = format_amount(income_by_ticker, places=decimals)
            else:
                amount = format_amount(income_by_ticker)
            amount = latest_transaction.amount.fmt % amount
            weight = income_by_ticker / total_income * 100
            is_estimate = contains_estimate_amount(filtered_records)
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

        if contains_estimate_amount(matching_transactions):
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


def print_journal_stats(records: List[Transaction], input_paths: List[str]) -> None:
    # find all source paths and weed out duplicates
    source_paths = set(record.entry_attr.location[0] for record in records)
    # resolve absolute path for each source path
    source_paths = list(os.path.abspath(path) for path in source_paths)
    # resolve absolute path for each input source path
    input_source_paths = list(os.path.abspath(path) for path in input_paths)
    # find all journals that must have been included from another journal
    included_paths = sorted(
        path for path in source_paths if path not in input_source_paths
    )
    # find all journals that must have been specified as an input
    journal_paths = sorted(path for path in source_paths if path in input_source_paths)
    # todo: consider only counting input sources and having included journals
    #       in separate section
    for n, path in enumerate(journal_paths + included_paths):
        print_stat_row(
            f"Journal {n + 1}", path + (" (included)" if path in included_paths else "")
        )


def print_conversion_stats(
    records: List[Transaction],
    rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None,
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
                f"{conversion_rate_amount} (as of {conversion_rate_datestamp})",
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
        decimal_point = locale.localeconv()["decimal_point"]
        thousands_separator = locale.localeconv()["thousands_sep"]
        expected_number_format = f"1{thousands_separator}000{decimal_point}00"
        print_stat_row("Locale", f"{lc}, Numbers: \"{expected_number_format}\"")
    except locale.Error:
        print_stat_row("Locale", "Not configured")
    if len(records) == 0:
        return
    print_stat_row("Records", f"{len(records)}")  # todo: X per day?
    # todo: records last 30/7 days
    # todo: X days span from earliest/latest
    earliest_datestamp = records[0].entry_date.strftime("%Y/%m/%d")  # todo: X days ago
    latest_datestamp = records[-1].entry_date.strftime("%Y/%m/%d")  # todo: X days ago
    print_stat_row("Earliest", earliest_datestamp)
    print_stat_row("Latest", latest_datestamp)
    print_stat_row("Tickers", f"{len(tickers(records))}")
    print_conversion_stats(records, rates)
    tags = sorted(labels(records))
    if len(tags) > 0:
        print_stat_row("Tags", f"{tags}")


def print_simple_rolling_report(
    records: List[Transaction], *, descending: bool = False
) -> None:
    today = todayd()
    years = range(
        earliest(records).entry_date.year, latest(records).entry_date.year + 1
    )
    if descending:
        years = reversed(years)
    commodities = sorted(symbols(records, excluding_dividends=True))
    amount_decimals, _, _ = decimals_per_component(records)
    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        decimals = amount_decimals[commodity]
        for year in years:
            months = range(1, 12 + 1)
            if descending:
                months = reversed(months)
            for month in months:
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
                if decimals is not None:
                    amount = format_amount(total, places=decimals)
                else:
                    amount = format_amount(total)
                amount = latest_transaction.amount.fmt % amount
                d = ending_date.strftime("%Y/%m")
                if contains_estimate_amount(rolling_transactions):
                    line = f"~ {amount.rjust(18)}  < {d.ljust(11)}"
                else:
                    line = f"{amount.rjust(20)}  < {d.ljust(11)}"
                payers = formatted_prominent_payers(rolling_transactions)
                line = f"{line}{payers}"
                print(line)
        if commodity != commodities[-1]:
            print()


DRIFT_BY_WEIGHT = 0
DRIFT_BY_AMOUNT = 1
DRIFT_BY_POSITION = 2


def print_balance_report(
    records: List[Transaction],
    *,
    deviance: int = -1,  # i.e. don't show any drift
    descending: bool = False,
) -> None:
    commodities = sorted(symbols(records, excluding_dividends=True))
    # note that this typically results in default decimal places preference,
    # but does have utility in some cases (e.g. if all amounts are trailing zeroes)
    amount_decimals, _, _ = decimals_per_component(records)
    for commodity in commodities:
        matching_transactions = list(
            filter(lambda r: r.amount.symbol == commodity, records)
        )
        if len(matching_transactions) == 0:
            continue
        latest_transaction = latest(matching_transactions)
        total_income = income(matching_transactions)
        total_income_has_estimate = contains_estimate_amount(matching_transactions)
        decimals = amount_decimals[commodity]
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
            has_estimate = contains_estimate_amount(filtered_records)
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
        weights.sort(key=lambda w: w[1], reverse=not descending)
        should_underline_mid_at_index: Optional[int] = None
        if len(weights) > 1 and deviance != -1:
            has_positive = any(True for w in weights if w[5][deviance] > 0)
            has_negative = any(True for w in weights if w[5][deviance] < 0)
            if has_positive and has_negative:
                if descending:
                    first_negative_index = next(
                        i for i, w in enumerate(weights) if w[5][deviance] < 0
                    )
                    last_positive_index = first_negative_index - 1
                    should_underline_mid_at_index = last_positive_index
                else:
                    first_positive_index = next(
                        i for i, w in enumerate(weights) if w[5][deviance] > 0
                    )
                    last_negative_index = first_positive_index - 1
                    should_underline_mid_at_index = last_negative_index
        accumulated_pct = 0
        for i, weight in enumerate(weights):
            ticker, amount, fmt, pct, p, drift, n, has_estimate = weight
            accumulated_pct = accumulated_pct + pct
            pct = f"{format_amount(pct, places=2)}%"
            freq = f"{n}"
            if decimals is not None:
                amount = format_amount(amount, places=decimals)
            else:
                amount = format_amount(amount)
            amount = fmt % amount
            if has_estimate:
                line = (
                    f"~ {amount.rjust(18)}  / {freq.ljust(2)} "
                    f"{pct.rjust(7)} {ticker.ljust(8)}"
                )
            else:
                line = (
                    f"{amount.rjust(20)}  / {freq.ljust(2)} "
                    f"{pct.rjust(7)} {ticker.ljust(8)}"
                )
            p_decimals = decimalplaces(p)
            p = format_amount(p, places=p_decimals)
            position = f"({p})".rjust(18)
            if deviance != -1:
                drift_by = drift[deviance]
                if deviance == DRIFT_BY_WEIGHT:
                    if drift_by >= 0:
                        by = format_amount(drift_by, places=2)
                        drift = f"+ {by}%".rjust(16)
                    else:
                        by = format_amount(abs(drift_by), places=2)
                        drift = f"- {by}%".rjust(16)
                elif deviance == DRIFT_BY_AMOUNT:
                    amount_drift = fmt % format_amount(abs(drift_by))
                    if drift_by >= 0:
                        drift = f"+ {amount_drift}".rjust(16)
                    else:
                        drift = f"- {amount_drift}".rjust(16)
                elif deviance == DRIFT_BY_POSITION:
                    if drift_by >= 0:
                        # increase position (buy)
                        by = format_amount(drift_by, places=p_decimals)
                        drift = f"+ {by}".rjust(16)
                    else:
                        # decrease position (sell)
                        by = format_amount(abs(drift_by), places=p_decimals)
                        drift = f"- {by}".rjust(16)
                line = f"{line} {position} {drift}"
                if i == should_underline_mid_at_index:
                    line = f"{line: <79}"
                    line = colored(line, COLOR_UNDERLINED)
            else:
                line = f"{line} {position}"
            print(line)
        if decimals is not None:
            amount = format_amount(total_income, places=decimals)
        else:
            amount = format_amount(total_income)
        amount = latest_transaction.amount.fmt % amount
        if should_underline_mid_at_index is not None:
            result_separator = "=" * 79  # then pad fully
        else:
            result_separator = "=" * 62  # then pad to position
        print(result_separator)
        if total_income_has_estimate:
            line = f"~ {amount.rjust(18)}"
        else:
            line = f"{amount.rjust(20)}"
        pct = f"{format_amount(accumulated_pct, places=2)}%"
        if deviance != -1:
            positions = f"/ {len(weights)}"
        else:
            positions = f"{len(weights)}"
        line = f"{line.ljust(26)}{pct.rjust(8)}{positions.rjust(28)}"
        if deviance != -1:
            target_pct = f"= {format_amount(target_weight, places=2)}%"
            line = f"{line} {target_pct.rjust(16)}"
        print(line)
        if commodity != commodities[-1]:
            print()


def print_currency_balance_report(
    records: List[Transaction], *, descending: bool = False
) -> None:
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
        total_income_has_estimate = contains_estimate_amount(matching_transactions)
        decimals = amount_decimals[commodity]
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
            has_estimate = contains_estimate_amount(filtered_records)
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
        weights.sort(key=lambda w: w[1], reverse=not descending)
        should_underline_mid_at_index: Optional[int] = None
        if len(weights) > 1:
            has_positive = any(True for w in weights if w[4] > 0)
            has_negative = any(True for w in weights if w[4] < 0)
            if has_positive and has_negative:
                if descending:
                    first_negative_index = next(
                        i for i, w in enumerate(weights) if w[4] < 0
                    )
                    last_positive_index = first_negative_index - 1
                    should_underline_mid_at_index = last_positive_index
                else:
                    first_positive_index = next(
                        i for i, w in enumerate(weights) if w[4] > 0
                    )
                    last_negative_index = first_positive_index - 1
                    should_underline_mid_at_index = last_negative_index
        accumulated_pct = 0
        for i, weight in enumerate(weights):
            symbol, amount, fmt, pct, wdrift, p, has_estimate = weight
            accumulated_pct = accumulated_pct + pct
            pct = f"{format_amount(pct, places=2)}%"
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
            if i == should_underline_mid_at_index:
                line = f"{line: <79}"
                line = colored(line, COLOR_UNDERLINED)
            print(line)
        if decimals is not None:
            amount = format_amount(total_income, places=decimals)
        else:
            amount = format_amount(total_income)
        amount = latest_transaction.amount.fmt % amount
        result_separator = "=" * 79  # padded fully
        print(result_separator)
        if total_income_has_estimate:
            line = f"~ {amount.rjust(18)}"
        else:
            line = f"{amount.rjust(20)}"
        pct = f"{format_amount(accumulated_pct, places=2)}%"
        positions = f"/ {len(weights)}"
        line = f"{line.ljust(26)}{pct.rjust(8)}{positions.rjust(28)}"
        target_pct = f"= {format_amount(target_weight, places=2)}%"
        line = f"{line} {target_pct.rjust(16)}"
        print(line)
        if commodity != commodities[-1]:
            print()


def most_prominent_payers(records: List[Transaction]) -> List[str]:
    combined_income_per_ticker = []
    for ticker in tickers(records):
        filtered_records = by_ticker(records, ticker)
        combined_income_per_ticker.append((ticker, income(filtered_records)))
    combined_income_per_ticker.sort(key=lambda x: x[1], reverse=True)
    return [ticker for ticker, _ in combined_income_per_ticker]


def formatted_prominent_payers(
    records: Iterable[Transaction], *, limit: int = 5
) -> str:
    payers = most_prominent_payers(list(records))
    top = payers[:limit]
    bottom = [payer for payer in payers if payer not in top]
    formatted = ", ".join(top)
    formatted = (formatted[:38] + "…") if len(formatted) > 38 else formatted
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
        dividend_decimal_places[symbol] = max_decimal_places(dividends(records, symbol))
    for ticker in tickers(records):
        # note ticker key for position component; not symbol
        position_decimal_places[ticker] = max(
            decimalplaces(r.position) for r in records if r.ticker == ticker
        )
    return amount_decimal_places, dividend_decimal_places, position_decimal_places


def contains_estimate_amount(records: Iterable[Transaction]) -> bool:
    """Return `True` if any record has an estimated amount component,
    `False` otherwise."""
    return any(isinstance(r.amount, GeneratedAmount) for r in records)
