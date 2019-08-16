from datetime import datetime

from dividendreport.dateutil import months_between, in_months, first_of_month
from dividendreport.ledger import Transaction

from typing import Iterable, Optional, List


def intervals(records: Iterable[Transaction]) \
        -> List[int]:
    """ Return a list of intervals (in normalized months) between a set of records. """

    records = sorted(records, key=lambda r: r.date)

    if len(records) == 0:
        return []

    timespans: List[int] = []

    first_record_date = None
    previous_record_date = None

    for record in records:
        date = first_of_month(record.date)

        if previous_record_date is None:
            first_record_date = date
        else:
            timespans.append(
                months_between(date, previous_record_date, ignore_years=True))

        previous_record_date = date

    next_record_date = first_record_date.replace(year=previous_record_date.year + 1)

    timespans.append(
        months_between(next_record_date, previous_record_date, ignore_years=True))

    return timespans


def tickers(records: Iterable[Transaction]) \
        -> List[str]:
    return list(set([record.ticker for record in records]))


def schedule(records: Iterable[Transaction]) \
        -> List[int]:
    return sorted(set([record.date.month for record in records]))


def trailing(records: Iterable[Transaction], since: datetime.date, *, months: int) \
        -> Iterable[Transaction]:
    begin = in_months(since, months=-months)
    end = since

    return filter(
        lambda r: end >= r.date > begin, records)


def monthly(records: Iterable[Transaction],
            *, year: int, month: int) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated within a given month, on a given year. """

    return filter(
        lambda r: (r.date.year == year and
                   r.date.month == month), records)


def yearly(records: Iterable[Transaction],
           *, year: int, months: int = 12) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated within a given year.

    Optionally only include records up to (and including) a given month.
    For example, if months = 5, only include records daten between January
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
    """ Return total income from a set of records. """

    return sum([record.amount for record in records])


def before(records: Iterable[Transaction], record: Transaction) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated prior to a given record. """

    return filter(
        lambda r: r.date < record.date, records)


def earliest(records: Iterable[Transaction]) \
        -> Optional[Transaction]:
    """ Return the earliest dated record. """

    records = sorted(records, key=lambda r: r.date)

    return records[0] if len(records) > 0 else None


def latest(records: Iterable[Transaction]) \
        -> Optional[Transaction]:
    """ Return the latest dated record. """

    records = sorted(records, key=lambda r: r.date)

    return records[-1] if len(records) > 0 else None


def previous(records: Iterable[Transaction], record: Transaction) \
        -> Optional[Transaction]:
    """ Return the first record dated prior to a given record. """

    return latest(before(records, record))


def previous_comparable(records: Iterable[Transaction], record: Transaction) \
        -> Optional[Transaction]:
    """ Return the first comparable record dated prior to a given record. """

    comparables = filter(
        lambda r: (r.date.month == record.date.month and
                   r.date.year < record.date.year), records)

    return latest(comparables)
