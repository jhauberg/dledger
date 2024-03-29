from datetime import date, timedelta

from dledger.dateutil import months_between, in_months, first_of_month
from dledger.journal import Transaction, Amount

from typing import Iterable, Optional, List, Set, Union, Tuple


def amount_per_share(record: Transaction) -> float:
    """Return the amount per share."""

    assert record.amount is not None

    return (
        record.amount.value / record.position
        if record.amount.value > 0 and record.position > 0
        else 0
    )


def amount_conversion_factor(record: Transaction) -> float:
    """Return the conversion factor of dividend to amount.

    Return `1` if no dividend is specified, or dividend is of same symbol as
    amount.
    """

    assert record.amount is not None

    if record.dividend is None:
        return 1
    if record.dividend.symbol == record.amount.symbol:
        return 1

    return amount_per_share(record) / record.dividend.value


def intervals(records: Iterable[Transaction]) -> List[int]:
    """Return a list of month intervals between a set of records.

    Does not take years and days into account.
    """

    records = sorted(records)

    if len(records) == 0:
        return []

    timespans: List[int] = []

    first_record_date: Optional[date] = None
    previous_record_date: Optional[date] = None

    for record in records:
        d = first_of_month(record.entry_date)

        if previous_record_date is None:
            first_record_date = d
        else:
            timespans.append(months_between(d, previous_record_date, ignore_years=True))

        previous_record_date = d

    assert first_record_date is not None
    assert previous_record_date is not None

    next_record_date = first_record_date.replace(year=previous_record_date.year + 1)

    timespans.append(
        months_between(next_record_date, previous_record_date, ignore_years=True)
    )

    return timespans


def amounts(
    records: Iterable[Transaction], symbol: Optional[str] = None
) -> List[Amount]:
    """Return a list of cash components in a set of records.

    Optionally only including those matching a given symbol.
    """

    components = [record.amount for record in records if record.amount is not None]

    if symbol is None:
        return components

    return [component for component in components if component.symbol == symbol]


def dividends(
    records: Iterable[Transaction], symbol: Optional[str] = None
) -> List[Amount]:
    """Return a list of dividend components in a set of records.

    Optionally only including those matching a given symbol.
    """

    components = [record.dividend for record in records if record.dividend is not None]

    if symbol is None:
        return components

    return [component for component in components if component.symbol == symbol]


def deltas(
    amounts: List[Amount], *, normalized: bool = True
) -> List[Union[int, float]]:
    """Return a list of deltas between amounts.

    If `normalized` is `True`, returns deltas in integral numbers (-1, 0, 1)
    indicating direction (down, no difference, up).
    """
    if len(amounts) < 2:
        return []

    if normalized:
        return [
            -1
            if d.value - amounts[i].value < 0
            else (0 if d.value == amounts[i].value else 1)
            for i, d in enumerate(amounts[1:])
        ]

    return [d.value - amounts[i].value for i, d in enumerate(amounts[1:])]


def tickers(records: Iterable[Transaction]) -> List[str]:
    """Return a list of unique ticker components in a set of records.

    Does not guarantee original ordering.
    """

    return list(set([record.ticker for record in records]))


def symbols(
    records: Iterable[Transaction], *, excluding_dividends: bool = False
) -> Set[str]:
    """Return a set of symbol components in a set of records.

    Optionally excluding symbols attached only to dividends.

    Does not include an entry for records with no symbol attached.
    """

    transactions = (r for r in records if r.amount is not None)

    collected_symbols: List[str] = []

    for record in transactions:
        assert record.amount is not None

        if record.amount.symbol is not None:
            collected_symbols.append(record.amount.symbol)
        if not excluding_dividends:
            if record.dividend is not None and record.dividend.symbol is not None:
                collected_symbols.append(record.dividend.symbol)

    return set(collected_symbols)


def labels(records: Iterable[Transaction]) -> Set[str]:
    """Return a set of tags in a set of records."""

    tagged_records = (r for r in records if r.tags is not None)

    tag_lists = [r.tags for r in tagged_records]
    tags = [tag for tag_list in tag_lists for tag in tag_list]

    return set(tags)


def monthly_schedule(records: Iterable[Transaction]) -> List[int]:
    """Return a list of unique month components in a set of records."""

    return sorted(set([record.entry_date.month for record in records]))


def trailing(
    records: Iterable[Transaction], since: date, *, months: int
) -> Iterable[Transaction]:
    """Return an iterator for records dated within months prior to a given
    date (inclusive).

    Does take days into account.
    """

    begin = in_months(since, months=-months)
    end = since

    return (r for r in records if end >= r.entry_date > begin)


def monthly(
    records: Iterable[Transaction], *, year: int, month: int
) -> Iterable[Transaction]:
    """Return an iterator for records dated on a given month and year."""

    return (
        r
        for r in records
        if (r.entry_date.year == year and r.entry_date.month == month)
    )


def yearly(
    records: Iterable[Transaction], *, year: int, months: int = 12
) -> Iterable[Transaction]:
    """Return an iterator for records dated within a given year.

    Optionally only include records up to (and including) a given month.
    For example, if `months` is `5`, only include records daten between January
    and May (inclusive).
    """

    return (
        r
        for r in records
        if (r.entry_date.year == year and r.entry_date.month <= months)
    )


def by_ticker(records: Iterable[Transaction], symbol: str) -> Iterable[Transaction]:
    """Return an iterator for records with a given ticker."""

    return (r for r in records if r.ticker == symbol)


def income(records: Iterable[Transaction]) -> float:
    """Return the sum of amount components in a set of records."""

    return sum([amount.value for amount in amounts(records)])


def after(records: Iterable[Transaction], d: date) -> Iterable[Transaction]:
    """Return an iterator for records dated later than a date."""

    return (r for r in records if r.entry_date > d)


def before(records: Iterable[Transaction], d: date) -> Iterable[Transaction]:
    """Return an iterator for records dated prior to a date."""

    return (r for r in records if r.entry_date < d)


def in_period(
    records: Iterable[Transaction], interval: Tuple[Optional[date], Optional[date]]
) -> Iterable[Transaction]:
    """Return an iterator for records dated within a period.

    Exclusive of end date.
    """

    if interval is None:
        return records

    starting, ending = interval

    if starting is not None:
        # inclusive of starting date
        records = after(records, starting - timedelta(days=1))
    if ending is not None:
        # exclusive of end date
        return before(records, ending)

    return records


def earliest(records: Iterable[Transaction]) -> Optional[Transaction]:
    """Return the earliest dated record in a set of records."""

    records = sorted(records)

    return records[0] if len(records) > 0 else None


def latest(
    records: Iterable[Transaction],
    *,
    by_payout: bool = False,
    by_exdividend: bool = False
) -> Optional[Transaction]:
    """Return the latest dated record in a set of records."""

    assert not (by_payout and by_exdividend)

    if by_payout:
        records = sorted(
            records,
            key=lambda r: (
                r.payout_date if r.payout_date is not None else r.entry_date
            ),
        )
    elif by_exdividend:
        records = sorted(
            records,
            key=lambda r: (r.ex_date if r.ex_date is not None else r.entry_date),
        )
    else:
        records = sorted(records)

    return records[-1] if len(records) > 0 else None


def dated(
    records: Iterable[Transaction],
    d: date,
    *,
    by_payout: bool = False,
    by_exdividend: bool = False
) -> Iterable[Transaction]:
    """Return an iterator for records dated to a specific date."""

    assert not (by_payout and by_exdividend)

    if by_payout:
        return (
            r
            for r in records
            if (r.payout_date == d if r.payout_date is not None else r.entry_date == d)
        )
    elif by_exdividend:
        return (
            r
            for r in records
            if (r.ex_date == d if r.ex_date is not None else r.entry_date == d)
        )
    return (r for r in records if r.entry_date == d)


# todo: not a great name for this function
def pruned(records: Iterable[Transaction]) -> List[Transaction]:
    """Return a list of transactions with only the first occurence of a
    transaction per date."""

    collected_records: List[Transaction] = []
    for record in records:
        collected = False
        for collected_record in collected_records:
            if record.entry_date == collected_record.entry_date:
                collected = True
                break
        if not collected:
            collected_records.append(record)
    return collected_records
