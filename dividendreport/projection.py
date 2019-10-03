from datetime import datetime, timedelta
from dataclasses import dataclass

from statistics import mode, StatisticsError

from dividendreport.ledger import Transaction
from dividendreport.formatutil import format_amount
from dividendreport.dateutil import last_of_month
from dividendreport.record import (
    by_ticker, tickers, trailing, latest, amount_per_share,
    before, after, schedule, intervals
)

from typing import Tuple, Optional, List, Iterable

EARLY = 0
LATE = 1

EARLY_LATE_THRESHOLD = 15  # early before or at this day of month, late after


@dataclass(frozen=True)
class FutureTransaction(Transaction):
    """ Represents an unrealized transaction; a projection. """

    amount_range: Optional[Tuple[float, float]] = None

    def __repr__(self):
        if self.amount_range is None:
            return str((f'{str(self.date)} *',
                        self.ticker,
                        self.position,
                        format_amount(self.amount)))

        return str((f'{str(self.date)} *',
                    self.ticker,
                    self.position,
                    format_amount(self.amount),
                    f'[{format_amount(self.amount_range[0])} -'
                    f' {format_amount(self.amount_range[1])}]'))


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


def frequency(records: Iterable[Transaction]) \
        -> int:
    """ Return the approximated frequency of occurrence (in months) for a set of records. """

    records = list(records)

    if len(records) == 0:
        return 0

    timespans = sorted(intervals(records))

    try:
        # unambiguous; a clear pattern of common frequency (take a guess)
        return normalize_interval(mode(timespans))
    except StatisticsError:
        # ambiguous; no clear pattern of frequency, fallback to latest 12-month range (don't guess)
        latest_record = latest(records)
        sample_records = trailing(records, since=last_of_month(latest_record.date), months=12)
        payouts_per_year = len(list(sample_records))
        average_interval = int(12 / payouts_per_year)
        return normalize_interval(average_interval)


def estimated_schedule(records: List[Transaction],
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
    approx_schedule = schedule(records)
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


def next_scheduled_date(date: datetime.date, months: List[int]) \
        -> datetime.date:
    """ Return the date that would follow a given date, going by a monthly schedule.

    For example, given a date (2019, 6, 18) and a schedule of (3, 6, 9, 12),
    the next scheduled month would be 9, resulting in date (2019, 9, 1).

    Day is always set to first of month.
    """

    if len(months) > 12:
        raise ValueError('schedule exceeds 12-month range')
    if len(months) != len(set(months)):
        raise ValueError('schedule must not contain duplicate months')
    if date.month not in months:
        raise ValueError('schedule does not match to given date')

    next_month_index = months.index(date.month) + 1
    next_year = date.year

    if next_month_index == len(months):
        next_year = next_year + 1
        next_month_index = 0

    future_date = date.replace(year=next_year,
                               month=months[next_month_index],
                               day=1)

    return future_date


def projected_timeframe(date: datetime.date) -> int:
    """ Return the timeframe of a given date. """

    return EARLY if date.day <= EARLY_LATE_THRESHOLD else LATE


def projected_date(date: datetime.date, *, timeframe: int) -> datetime.date:
    """ Return a date where day of month is set according to given timeframe. """

    if timeframe == EARLY:
        return date.replace(day=EARLY_LATE_THRESHOLD)
    if timeframe == LATE:
        return last_of_month(date)
    return date


def expired_transactions(records: Iterable[Transaction],
                         *,
                         since: datetime.date = datetime.today().date(),
                         grace_period: int = 3) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated prior to a date.

    Optionally allowing for a grace period of a number of days.
    """

    return before(records, since - timedelta(days=grace_period))


def pending_transactions(records: List[Transaction],
                         *,
                         since: datetime.date = datetime.today().date()) \
        -> Iterable[Transaction]:
    """ Return an iterator for records dated later than a date. """

    return after(records, since)


def scheduled_transactions(records: List[Transaction], entries: dict,
                           *,
                           since: datetime.date = datetime.today().date()) \
        -> List[FutureTransaction]:
    # take a sample set of only latest 12 months
    sample_records = list(trailing(records, since=since, months=12))

    # project current records by 1 year into the future
    futures = future_transactions(sample_records)
    # project current records by 12-month schedule and frequency
    estimates = estimated_transactions(sample_records, entries)

    scheduled = futures

    # bias toward futures, leaving estimates only to fill out gaps in schedule
    for record in estimates:
        duplicates = [r for r in scheduled
                      if r.ticker == record.ticker
                      and r.date.year == record.date.year
                      and r.date.month == record.date.month]

        if len(duplicates) > 0:
            continue

        scheduled.append(record)

    pending = list(pending_transactions(records, since=since))

    for record in pending:
        duplicates = [r for r in scheduled
                      if r.ticker == record.ticker
                      and r.date.year == record.date.year
                      and r.date.month == record.date.month]

        if len(duplicates) == 0:
            continue

        for dupe in duplicates:
            scheduled.remove(dupe)

    return sorted(scheduled, key=lambda r: (r.date, r.ticker))  # sort by date and ticker


def estimated_transactions(records: List[Transaction], entries: dict) \
        -> List[FutureTransaction]:
    approximate_records = []

    for ticker in tickers(records):
        record = latest(by_ticker(records, ticker))

        if not record.position > 0:
            # don't project closed positions
            continue

        scheduled_months = entries[record]['schedule']
        scheduled_records = []

        future_date = record.date
        # estimate timeframe by latest actual record
        future_timeframe = projected_timeframe(record.date)

        # increase number of iterations to extend beyond the next twelve months
        while len(scheduled_records) < len(scheduled_months):
            future_date = projected_date(next_scheduled_date(future_date, scheduled_months),
                                         timeframe=future_timeframe)

            reference_records = trailing(by_ticker(records, record.ticker),
                                         since=future_date, months=12)

            highest_amount_per_share = amount_per_share(record)
            lowest_amount_per_share = highest_amount_per_share
            reference_points = 0
            for reference_record in reference_records:
                reference_amount_per_share = amount_per_share(reference_record)
                reference_points += 1
                if reference_amount_per_share > highest_amount_per_share:
                    highest_amount_per_share = reference_amount_per_share
                if reference_amount_per_share < lowest_amount_per_share:
                    lowest_amount_per_share = reference_amount_per_share

            mean_amount_per_share = (lowest_amount_per_share + highest_amount_per_share) / 2

            reference_range = (lowest_amount_per_share * record.position,
                               highest_amount_per_share * record.position)

            scheduled_records.append(
                FutureTransaction(future_date, record.ticker, record.position,
                                  amount=mean_amount_per_share * record.position,
                                  amount_range=reference_range if reference_points > 1 else None))

        approximate_records.extend(scheduled_records)

    return sorted(approximate_records, key=lambda r: r.date)


def future_transactions(records: List[Transaction]) \
        -> List[FutureTransaction]:
    """ Return a matching list of records dated 12 months into the future.

    Each record has its amount adjusted to match the position of the latest matching record.
    """
    
    future_records = []

    for record in records:
        # offset 12 months into the future by assuming an annual schedule
        future_date = projected_date(next_scheduled_date(record.date, [record.date.month]),
                                     timeframe=projected_timeframe(record.date))

        latest_record = latest(by_ticker(records, record.ticker))

        future_position = latest_record.position

        if not future_position > 0:
            # don't project closed positions
            continue

        future_amount = future_position * amount_per_share(record)

        future_record = FutureTransaction(future_date,
                                          record.ticker,
                                          future_position,
                                          future_amount)

        future_records.append(future_record)

    return sorted(future_records, key=lambda r: r.date)
