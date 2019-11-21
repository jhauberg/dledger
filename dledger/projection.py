from datetime import datetime, date, timedelta
from dataclasses import dataclass

from statistics import multimode  # type: ignore

from dledger.journal import Transaction, Amount
from dledger.dateutil import last_of_month
from dledger.record import (
    by_ticker, tickers, trailing, latest, monthly_schedule,
    amount_per_share, amount_per_share_low, amount_per_share_high,
    before, after, intervals, pruned
)

from typing import Tuple, Optional, List, Iterable

EARLY = 0
LATE = 1

EARLY_LATE_THRESHOLD = 15  # early before or at this day of month, late after


@dataclass(frozen=True)
class FutureTransaction(Transaction):
    """ Represents an unrealized transaction; a projection. """

    amount_range: Optional[Tuple[Amount, Amount]] = None


@dataclass(frozen=True)
class Schedule:
    """ Represents a dividend payout schedule. """

    frequency: int  # interval between payouts (in months)
    months: List[int]


def normalize_interval(interval: int) \
        -> int:
    """ Return a normalized interval.

    Normalized intervals:
       1: Monthly   (every month)
       3: Quarterly (every three months)
       6: Biannual  (two times a year)
      12: Annual    (once a year)
    """

    if interval < 1 or interval > 12:
        raise ValueError('interval must be within 1-12-month range')

    normalized_intervals = {
        1: (0, 1),
        3: (1, 3),
        6: (3, 6),
        12: (6, 12)
    }

    for normalized_interval, (start, end) in normalized_intervals.items():
        if start < interval <= end:
            return normalized_interval

    assert False  # we should never reach this point


def frequency(records: Iterable[Transaction]) \
        -> int:
    """ Return the approximated frequency of occurrence (in months) for a set of records. """

    records = list(records)

    if len(records) == 0:
        return 0

    timespans = sorted(intervals(records))

    m = multimode(timespans)

    if len(m) == 1:
        # unambiguous; a clear pattern of common frequency (take a guess)
        return normalize_interval(m[0])
    else:
        # ambiguous; no clear pattern of frequency, fallback to latest 12-month range (don't guess)
        latest_record = latest(records)
        assert latest_record is not None
        sample_records = trailing(records, since=last_of_month(latest_record.date), months=12)
        payouts_per_year = len(list(sample_records))
        average_interval = int(12 / payouts_per_year)
        return normalize_interval(average_interval)


def estimated_monthly_schedule(records: List[Transaction],
                               *, interval: int) \
        -> List[int]:
    """ Return an estimated monthly schedule for a list of records.

    For example, provided with records dated for months (3, 6) at an interval of 3 months,
    the returned schedule would be (3, 6, 9, 12).
    """

    if interval <= 0:
        raise ValueError('interval must be > 0')

    # first determine months that we know for sure is to be scheduled
    # e.g. those months where that actually has a recorded payout
    approx_schedule = monthly_schedule(records)
    # determine approximate number of payouts per year, given approximate interval between payouts
    payouts_per_year = int(12 / interval)
    # then, going by the last recorded month, increment by interval until scheduled months
    # and number of payouts match- looping back as needed
    if len(approx_schedule) < payouts_per_year:
        starting_month = approx_schedule[-1]

        month = starting_month

        while len(approx_schedule) < payouts_per_year:
            month += interval

            if month > 12:
                month = month % 12

            if month in approx_schedule:
                continue

            approx_schedule.append(month)

    return sorted(set(approx_schedule))


def next_scheduled_date(d: date, months: List[int]) \
        -> date:
    """ Return the date that would follow a given date, going by a monthly schedule.

    For example, given a date (2019, 6, 18) and a schedule of (3, 6, 9, 12),
    the next scheduled month would be 9, resulting in date (2019, 9, 1).

    Day is always set to first of month.
    """

    if len(months) > 12:
        raise ValueError('schedule exceeds 12-month range')
    if len(months) != len(set(months)):
        raise ValueError('schedule must not contain duplicate months')
    if d.month not in months:
        raise ValueError('schedule does not match given date')

    next_month_index = months.index(d.month) + 1
    next_year = d.year

    if next_month_index == len(months):
        next_year = next_year + 1
        next_month_index = 0

    future_date = d.replace(year=next_year,
                            month=months[next_month_index],
                            day=1)

    return future_date


def projected_timeframe(d: date) -> int:
    """ Return the timeframe of a given date. """

    return EARLY if d.day <= EARLY_LATE_THRESHOLD else LATE


def projected_date(d: date, *, timeframe: int) -> date:
    """ Return a date where day of month is set according to given timeframe. """

    if timeframe == EARLY:
        return d.replace(day=EARLY_LATE_THRESHOLD)
    if timeframe == LATE:
        return last_of_month(d)
    return d


def expired_transactions(records: Iterable[Transaction],
                         *,
                         since: date = datetime.today().date(),
                         grace_period: int = 3) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated prior to a date.

    Optionally allowing for a grace period of a number of days.
    """

    return before(records, since - timedelta(days=grace_period))


def pending_transactions(records: Iterable[Transaction],
                         *,
                         since: date = datetime.today().date()) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated later than a date. """

    return after(records, since)


def scheduled_transactions(records: List[Transaction],
                           *,
                           since: date = datetime.today().date()) \
        -> List[FutureTransaction]:
    # take a sample set of only latest 12 months
    sample_records = trailing(records, since=since, months=12)
    # don't include special dividends
    sample_records = list(filter(lambda r: not r.is_special, sample_records))

    # project current records by 1 year into the future
    futures = future_transactions(sample_records)
    # project current records by 12-month schedule and frequency
    estimates = estimated_transactions(sample_records)

    scheduled = futures

    # bias toward futures, leaving estimates only to fill out gaps in schedule
    for future_record in estimates:
        duplicates = [r for r in scheduled
                      if r.ticker == future_record.ticker
                      and r.date.year == future_record.date.year
                      and r.date.month == future_record.date.month]

        if len(duplicates) > 0:
            continue

        scheduled.append(future_record)

    pending_records = list(pending_transactions(filter(
        lambda r: not r.is_special, records), since=since))

    # bias toward pending; e.g. keep manually set transactions in the future,
    # discard projections on same date
    for pending_record in pending_records:
        duplicates = [r for r in scheduled
                      if r.ticker == pending_record.ticker
                      and r.date.year == pending_record.date.year
                      and r.date.month == pending_record.date.month]

        if len(duplicates) == 0:
            continue

        for dupe in duplicates:
            scheduled.remove(dupe)

    # exclude unrealized projections
    closed = tickers(expired_transactions(scheduled, since=since))

    return sorted(filter(
        lambda r: r.ticker not in closed, scheduled),
        key=lambda r: (r.date, r.ticker))  # sort by date and ticker


def estimated_schedule(records: List[Transaction], record: Transaction) \
        -> Schedule:
    sample_records = trailing(by_ticker(records, record.ticker),
                              since=last_of_month(record.date), months=24)

    # exclude closed positions
    sample_records = filter(lambda r: r.position > 0, sample_records)
    # exclude same-date records for more accurate frequency/schedule estimation
    sample_records = pruned(sample_records)
    # determine approximate frequency (annual, biannual, quarterly or monthly)
    approx_frequency = frequency(sample_records)

    months = estimated_monthly_schedule(sample_records, interval=approx_frequency)

    return Schedule(approx_frequency, months)


def estimated_transactions(records: List[Transaction]) \
        -> List[FutureTransaction]:
    """ Return a list of transactions dated into the future according to an estimated schedule. """

    approximate_records = []

    for ticker in tickers(records):
        latest_record = latest(by_ticker(records, ticker))

        assert latest_record is not None

        future_position = latest_record.position

        if not future_position > 0:
            # don't project closed positions
            continue

        # weed out position-only records
        transactions = list(filter(
            lambda r: r.amount is not None, by_ticker(records, ticker)))

        if len(transactions) == 0:
            continue

        latest_transaction = latest(transactions)

        assert latest_transaction is not None
        assert latest_transaction.amount is not None

        sched = estimated_schedule(transactions, latest_transaction)

        scheduled_months = sched.months
        scheduled_records: List[FutureTransaction] = []

        future_date = latest_transaction.date
        # estimate timeframe by latest actual record
        future_timeframe = projected_timeframe(future_date)

        # increase number of iterations to extend beyond the next twelve months
        while len(scheduled_records) < len(scheduled_months):
            future_date = projected_date(next_scheduled_date(future_date, scheduled_months),
                                         timeframe=future_timeframe)

            future_amount = amount_per_share(latest_transaction) * future_position
            future_amount_range = None

            reference_records = trailing(
                by_ticker(transactions, ticker), since=future_date, months=12)
            reference_records = list(filter(
                lambda r: r.amount.symbol == latest_transaction.amount.symbol, reference_records))

            if len(reference_records) > 0:
                highest_amount_per_share = amount_per_share_high(reference_records)
                lowest_amount_per_share = amount_per_share_low(reference_records)

                mean_amount_per_share = (lowest_amount_per_share + highest_amount_per_share) / 2

                future_amount = mean_amount_per_share * future_position

                future_amount_range = (Amount(lowest_amount_per_share * future_position,
                                              symbol=latest_transaction.amount.symbol,
                                              format=latest_transaction.amount.format),
                                       Amount(highest_amount_per_share * future_position,
                                              symbol=latest_transaction.amount.symbol,
                                              format=latest_transaction.amount.format))

            future_record = FutureTransaction(future_date, ticker, future_position,
                                              amount=Amount(future_amount,
                                                            symbol=latest_transaction.amount.symbol,
                                                            format=latest_transaction.amount.format),
                                              amount_range=future_amount_range)

            scheduled_records.append(future_record)

        approximate_records.extend(scheduled_records)

    return sorted(approximate_records, key=lambda r: r.date)


def future_transactions(records: List[Transaction]) \
        -> List[FutureTransaction]:
    """ Return a list of transactions dated 12 months into the future.

    Each transaction has its amount adjusted to match the position of the latest matching record.
    """
    
    future_records = []

    # weed out position-only records
    transactions = list(filter(lambda r: r.amount is not None, records))

    for transaction in transactions:
        assert transaction.amount is not None

        latest_record = latest(by_ticker(records, transaction.ticker))

        assert latest_record is not None

        future_position = latest_record.position

        if not future_position > 0:
            # don't project closed positions
            continue

        latest_transaction = latest(by_ticker(transactions, transaction.ticker))

        assert latest_transaction is not None
        assert latest_transaction.amount is not None

        if transaction.amount.symbol != latest_transaction.amount.symbol:
            # don't project transactions that do not match latest recorded currency
            continue

        # offset 12 months into the future by assuming an annual schedule
        next_date = next_scheduled_date(transaction.date, [transaction.date.month])
        future_date = projected_date(next_date, timeframe=projected_timeframe(transaction.date))

        future_amount = future_position * amount_per_share(transaction)
        future_record = FutureTransaction(future_date, transaction.ticker, future_position,
                                          amount=Amount(future_amount,
                                                        symbol=latest_transaction.amount.symbol,
                                                        format=latest_transaction.amount.format))

        future_records.append(future_record)

    return sorted(future_records, key=lambda r: r.date)
