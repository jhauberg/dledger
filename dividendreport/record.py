from statistics import mode, StatisticsError

from dividendreport.dateutil import next_month, previous_month, months_between
from dividendreport.ledger import Transaction

from typing import Iterable, Optional, List


def normalize_timespan(timespan: int) \
        -> int:
    if timespan < 1 or timespan > 12:
        raise ValueError('timespan must be within a 1-12-month range')

    normalized_timespans = {
        1: (0, 1),
        3: (1, 3),
        6: (3, 6),
        12: (6, 12)
    }

    for normalized_timespan, (start, end) in normalized_timespans.items():
        if start < timespan <= end:
            return normalized_timespan


def frequency(records: Iterable[Transaction]) \
        -> int:
    """ Return the approximated frequency of occurrence (in months) for a set of records. """

    records = list(records)

    if len(records) == 0:
        return 0

    timespans = [normalize_timespan(timespan) for timespan in sorted(intervals(records))]

    try:
        # unambiguous; a clear pattern of common frequency (take a guess)
        return mode(timespans)
    except StatisticsError:
        # ambiguous; no clear pattern of frequency, fallback to latest 12-month range (don't guess)
        records = list(within_months(records, latest(records), months=12))
        return int(12 / len(records))


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
        if previous_record_date is None:
            first_record_date = record.date
        else:
            timespans.append(
                months_between(record.date, previous_record_date,
                               normalized=True))

        previous_record_date = record.date

    next_record_date = first_record_date.replace(year=previous_record_date.year + 1)

    timespans.append(
        months_between(next_record_date, previous_record_date,
                       normalized=True))

    return timespans


def tickers(records: Iterable[Transaction]) \
        -> List[str]:
    return list(set([record.ticker for record in records]))


def schedule(records: Iterable[Transaction]) \
        -> List[int]:
    return sorted(set([record.date.month for record in records]))


def within_months(records: Iterable[Transaction], record: Transaction,
                  *, months: int = 12, trailing: bool = False, preceding: bool = True) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated within months of a given record (inclusive).

    If trailing is True, offset to previous month of record date (e.g. exclusive of given record).
    """

    if preceding:
        since = (previous_month(record.date)
                 if trailing else
                 next_month(record.date))
    else:
        since = (next_month(record.date)
                 if trailing else
                 previous_month(record.date))

    return filter(
        lambda r: (r.date <= since if preceding else
                   r.date >= since) and months_between(since, r.date) <= months, records)


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
