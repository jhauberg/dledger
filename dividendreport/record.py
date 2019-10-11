from datetime import datetime

from dividendreport.dateutil import months_between, in_months, first_of_month
from dividendreport.ledger import Transaction

from typing import Iterable, Optional, List


def amount_per_share(record: Transaction) \
        -> float:
    """ Return the fractional amount per share. """

    return (record.amount / record.position
            if record.amount > 0 and record.position > 0
            else 0)


def amount_per_share_high(records: Iterable[Transaction]) \
        -> float:
    """ Return the highest amount per share over any period. """

    highest_amount_per_share = -1

    for record in records:
        reference_amount_per_share = amount_per_share(record)
        if highest_amount_per_share == -1 or reference_amount_per_share > highest_amount_per_share:
            highest_amount_per_share = reference_amount_per_share

    if highest_amount_per_share == -1:
        raise TypeError('\'records\' must contain at least one transaction')

    return highest_amount_per_share


def amount_per_share_low(records: Iterable[Transaction]) \
        -> float:
    """ Return the lowest amount per share over any period. """

    lowest_amount_per_share = -1

    for record in records:
        reference_amount_per_share = amount_per_share(record)
        if lowest_amount_per_share == -1 or reference_amount_per_share < lowest_amount_per_share:
            lowest_amount_per_share = reference_amount_per_share

    if lowest_amount_per_share == -1:
        raise TypeError('\'records\' must contain at least one transaction')

    return lowest_amount_per_share


def intervals(records: Iterable[Transaction]) \
        -> List[int]:
    """ Return a list of month intervals between a set of records.

    Does not take years and days into account.
    """

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
    """ Return a list of unique ticker components in a set of records. """

    return list(set([record.ticker for record in records]))


def monthly_schedule(records: Iterable[Transaction]) \
        -> List[int]:
    """ Return a list of unique month components in a set of records. """

    return sorted(set([record.date.month for record in records]))


def trailing(records: Iterable[Transaction], since: datetime.date, *, months: int) \
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

    return sum([record.amount for record in records])


def after(records: Iterable[Transaction], date: datetime.date) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated later than a date. """

    return filter(
        lambda r: r.date > date, records)


def before(records: Iterable[Transaction], date: datetime.date) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated prior to a date. """

    return filter(
        lambda r: r.date < date, records)


def earliest(records: Iterable[Transaction]) \
        -> Optional[Transaction]:
    """ Return the earliest dated record in a set of records. """

    records = sorted(records, key=lambda r: r.date)

    return records[0] if len(records) > 0 else None


def latest(records: Iterable[Transaction]) \
        -> Optional[Transaction]:
    """ Return the latest dated record in a set of records. """

    records = sorted(records, key=lambda r: r.date)

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

    collected_records = []
    for record in records:
        collected = False
        for collected_record in collected_records:
            if record.date == collected_record.date:
                collected = True
                break
        if not collected:
            collected_records.append(record)
    return collected_records
