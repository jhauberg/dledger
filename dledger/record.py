from datetime import date

from dledger.dateutil import months_between, in_months, first_of_month
from dledger.journal import Transaction

from typing import Iterable, Optional, List, Set


def amount_per_share(record: Transaction) \
        -> float:
    """ Return the fractional amount per share. """

    assert record.amount is not None

    return (record.amount.value / record.position
            if record.amount.value > 0 and record.position > 0
            else 0)


def intervals(records: Iterable[Transaction]) \
        -> List[int]:
    """ Return a list of month intervals between a set of records.

    Does not take years and days into account.
    """

    records = sorted(records)

    if len(records) == 0:
        return []

    timespans: List[int] = []

    first_record_date: Optional[date] = None
    previous_record_date: Optional[date] = None

    for record in records:
        d = first_of_month(record.date)

        if previous_record_date is None:
            first_record_date = d
        else:
            timespans.append(
                months_between(d, previous_record_date, ignore_years=True))

        previous_record_date = d

    assert first_record_date is not None
    assert previous_record_date is not None

    next_record_date = first_record_date.replace(year=previous_record_date.year + 1)

    timespans.append(
        months_between(next_record_date, previous_record_date, ignore_years=True))

    return timespans


def tickers(records: Iterable[Transaction]) \
        -> List[str]:
    """ Return a list of unique ticker components in a set of records. """

    return list(set([record.ticker for record in records]))


def symbols(records: Iterable[Transaction], *, excluding_dividends: bool = False) \
        -> Set[str]:
    """ Return a set of symbol components in a set of records.

    Optionally excluding symbols attached only to dividends.

    Does not include an entry for records with no symbol attached.
    """

    transactions = filter(lambda r: r.amount is not None, records)

    collected_symbols: List[str] = []

    for record in transactions:
        if record.amount.symbol is not None:
            collected_symbols.append(record.amount.symbol)
        if not excluding_dividends:
            if record.dividend is not None and record.dividend.symbol is not None:
                collected_symbols.append(record.dividend.symbol)

    return set(collected_symbols)


def monthly_schedule(records: Iterable[Transaction]) \
        -> List[int]:
    """ Return a list of unique month components in a set of records. """

    return sorted(set([record.date.month for record in records]))


def trailing(records: Iterable[Transaction], since: date, *, months: int) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated within a number of months prior to a given date.

    Does take days into account.
    """

    begin = in_months(since, months=-months)
    end = since

    return filter(
        lambda r: end >= r.date > begin, records)


def monthly(records: Iterable[Transaction],
            *, year: int, month: int) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated on a given month and year. """

    return filter(
        lambda r: (r.date.year == year and
                   r.date.month == month), records)


def yearly(records: Iterable[Transaction],
           *, year: int, months: int = 12) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated within a given year.

    Optionally only include records up to (and including) a given month.
    For example, if months=5, only include records daten between January
    and May (inclusive).
    """

    return filter(
        lambda r: (r.date.year == year and
                   r.date.month <= months), records)


def by_ticker(records: Iterable[Transaction], symbol: str) \
        -> Iterable[Transaction]:
    """ Return an iterator for records with a given ticker. """

    return filter(
        lambda r: r.ticker == symbol, records)


def income(records: Iterable[Transaction]) \
        -> float:
    """ Return the sum of amount components in a set of records. """

    return sum([record.amount.value for record in records if record.amount is not None])


def after(records: Iterable[Transaction], d: date) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated later than a date. """

    return filter(
        lambda r: r.date > d, records)


def before(records: Iterable[Transaction], d: date) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated prior to a date. """

    return filter(
        lambda r: r.date < d, records)


def earliest(records: Iterable[Transaction]) \
        -> Optional[Transaction]:
    """ Return the earliest dated record in a set of records. """

    records = sorted(records)

    return records[0] if len(records) > 0 else None


def latest(records: Iterable[Transaction]) \
        -> Optional[Transaction]:
    """ Return the latest dated record in a set of records. """

    records = sorted(records)

    return records[-1] if len(records) > 0 else None


def previous(records: Iterable[Transaction], record: Transaction) \
        -> Optional[Transaction]:
    """ Return the latest record dated prior to a given record. """

    return latest(before(records, record.date))


def previous_comparable(records: Iterable[Transaction], record: Transaction) \
        -> Optional[Transaction]:
    """ Return the latest comparable record dated prior to a given record.

    A comparable record is a record dated within same month in an earlier year.
    """

    comparables = filter(
        lambda r: (r.date.month == record.date.month and
                   r.date.year < record.date.year), records)

    return latest(comparables)


def pruned(records: Iterable[Transaction]) \
        -> List[Transaction]:
    """ Return a list of transactions with only the first occurence of a transaction per date. """

    collected_records: List[Transaction] = []
    for record in records:
        collected = False
        for collected_record in collected_records:
            if record.date == collected_record.date:
                collected = True
                break
        if not collected:
            collected_records.append(record)
    return collected_records
