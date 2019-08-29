from datetime import datetime, timedelta
from dataclasses import dataclass

from statistics import mode, StatisticsError

from dividendreport.ledger import Transaction
from dividendreport.formatutil import format_amount
from dividendreport.dateutil import last_of_month, in_months
from dividendreport.record import by_ticker, tickers, trailing, latest, schedule, intervals, amount_per_share

from typing import Tuple, Optional, List, Iterable


@dataclass(frozen=True)
class FutureTransaction(Transaction):
    """ Represents a transaction that is expected to be realized in the future; a projection. """

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


def estimate_schedule(records: List[Transaction],
                      *, interval: int) \
        -> List[int]:
    if interval <= 0:
        raise ValueError('interval must be > 0')

    approx_schedule = schedule(records)

    payouts_per_year = int(12 / interval)

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
    if date.month not in months:
        raise ValueError('schedule does not match')

    next_month_index = months.index(date.month) + 1
    next_year = date.year

    if next_month_index == len(months):
        next_year = next_year + 1
        next_month_index = 0

    future_date = date.replace(year=next_year,
                               month=months[next_month_index],
                               day=1)
    future_date = last_of_month(future_date)

    return future_date


def scheduled_transactions(records: List[Transaction], entries: dict,
                           *,
                           since: datetime.date = datetime.today().date(),
                           grace_period: int = 2) \
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
                      and r.date == record.date]

        if len(duplicates) > 0:
            continue

        scheduled.append(record)

    # determine tickers with unrealized projections
    # (e.g. if transactions are projected for months [3, 6, 9, 12] but current month is now july
    # and latest actual transaction happened back in march, then june was passed without
    # having the projected transaction be realized)
    exclude_tickers = []

    exclusion_date = since
    # add grace period to account for bank transfer delays
    exclusion_date += timedelta(days=grace_period)

    for record in reversed(scheduled):
        if record.ticker in exclude_tickers:
            continue

        latest_record = latest(by_ticker(records, record.ticker))

        report = entries[latest_record]
        scheduled_months = report['schedule']

        future_date = next_scheduled_date(latest_record.date, scheduled_months)

        if future_date < exclusion_date:
            exclude_tickers.append(record.ticker)

    # exclude unrealized projections
    scheduled = filter(lambda r: r.ticker not in exclude_tickers, scheduled)
    # exclude closed positions
    scheduled = filter(lambda r: r.amount > 0, scheduled)

    return sorted(scheduled, key=lambda r: (r.date, r.ticker))  # sort by date and ticker


def estimated_transactions(records: List[Transaction], entries: dict) \
        -> List[FutureTransaction]:
    approximate_records = []

    for ticker in tickers(records):
        record = latest(by_ticker(records, ticker))

        scheduled_months = entries[record]['schedule']
        scheduled_records = []

        future_date = record.date

        # increase number of iterations to extend beyond the next twelve months
        while len(scheduled_records) < len(scheduled_months):
            future_date = next_scheduled_date(future_date, scheduled_months)

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
    """ Return a list of records dated 12 months into the future.

    Each record has its amount adjusted to match the position of the latest matching record.
    """
    future_records = []

    for record in records:
        future_date = last_of_month(in_months(record.date, months=12))

        latest_record = latest(by_ticker(records, record.ticker))

        future_position = latest_record.position
        future_amount = future_position * amount_per_share(record)

        future_record = FutureTransaction(future_date,
                                          record.ticker,
                                          future_position,
                                          future_amount)

        future_records.append(future_record)

    return sorted(future_records, key=lambda r: r.date)
