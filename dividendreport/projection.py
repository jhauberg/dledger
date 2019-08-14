from datetime import datetime
from dataclasses import dataclass

from dividendreport.ledger import Transaction
from dividendreport.formatutil import format_amount
from dividendreport.dateutil import last_of_month, in_months
from dividendreport.record import by_ticker, within_months, trailing, latest, schedule

from typing import Tuple, Optional, List


@dataclass(frozen=True)
class FutureTransaction(Transaction):
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


def estimate_schedule(records: List[Transaction],
                      *, interval: int) \
        -> List[int]:
    approx_schedule = schedule(records)

    if interval <= 0:
        raise ValueError('interval must be > 0')

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
    next_year = date.year
    next_month_index = months.index(date.month) + 1

    if next_month_index == len(months):
        next_year = next_year + 1
        next_month_index = 0

    future_date = date.replace(year=next_year,
                               month=months[next_month_index],
                               day=1)
    future_date = last_of_month(future_date)

    return future_date


def scheduled_transactions(records: List[Transaction], entries: dict) \
        -> List[FutureTransaction]:
    futures = future_transactions(records, entries)
    estimates = estimated_transactions(records, entries)

    for record in estimates:
        duplicates = [r for r in futures if r.ticker == record.ticker and r.date == record.date]

        if len(duplicates) > 0:
            continue

        futures.append(record)

    exclusion_date = datetime.today().date()
    exclude_tickers = []

    for record in reversed(futures):
        if record.ticker in exclude_tickers:
            continue

        latest_record = latest(by_ticker(records, record.ticker))

        report = entries[latest_record]
        scheduled_months = report['schedule']

        future_date = next_scheduled_date(latest_record.date, scheduled_months)

        if future_date < exclusion_date:
            exclude_tickers.append(record.ticker)

    futures = filter(lambda r: r.ticker not in exclude_tickers, futures)
    futures = filter(lambda r: r.amount > 0, futures)

    return sorted(futures, key=lambda r: (r.date, r.ticker))  # sort by date and ticker


def estimated_transactions(records: List[Transaction], entries: dict) \
        -> List[FutureTransaction]:
    approximate_records = []
    seen_tickers = []
    for record in reversed(records):
        if record.ticker in seen_tickers:
            continue

        seen_tickers.append(record.ticker)
        report = entries[record]
        scheduled_months = report['schedule']
        scheduled_records = []

        future_date = record.date

        # increase number of iterations to extend beyond the next twelve months
        while len(scheduled_records) < len(scheduled_months):
            future_date = next_scheduled_date(future_date, scheduled_months)

            if future_date < datetime.today().date():
                continue

            fictive_record = Transaction(future_date, '', 0, 0)
            reference_records = trailing(by_ticker(records, record.ticker), fictive_record, months=12)
            highest_amount_per_share = report['amount_per_share']
            lowest_amount_per_share = highest_amount_per_share
            for reference_record in reference_records:
                reference_report = entries[reference_record]
                reference_amount_per_share = reference_report['amount_per_share']
                if reference_amount_per_share > highest_amount_per_share:
                    highest_amount_per_share = reference_amount_per_share
                if reference_amount_per_share < lowest_amount_per_share:
                    lowest_amount_per_share = reference_amount_per_share
            mean_amount_per_share = (lowest_amount_per_share + highest_amount_per_share) / 2

            scheduled_records.append(
                FutureTransaction(future_date, record.ticker, record.position,
                                  amount=mean_amount_per_share * record.position,
                                  amount_range=(lowest_amount_per_share * record.position,
                                                highest_amount_per_share * record.position)))

        approximate_records.extend(scheduled_records)

    return sorted(approximate_records, key=lambda r: r.date)


def future_transactions(records: List[Transaction], entries: dict) \
        -> List[FutureTransaction]:
    future_records = []
    for record in records:
        future_date = last_of_month(in_months(record.date, months=12))

        if future_date < datetime.today().date():
            continue

        reference_record = latest(within_months(by_ticker(records, record.ticker), record,
                                                trailing=False,  # don't include this record
                                                preceding=False))  # look ahead

        if reference_record is None:
            continue

        report = entries[record]
        reference_report = entries[reference_record]

        if 'amount_per_share_yoy_change_pct' not in reference_report:
            continue

        comparable_amount_per_share = report['amount_per_share']

        future_position = reference_record.position
        future_amount = comparable_amount_per_share * future_position

        growth_scalar = 1 + (reference_report['amount_per_share_yoy_change_pct'] / 100)

        future_amount = future_amount * (1 + (growth_scalar / 100))
        future_record = FutureTransaction(future_date,
                                          record.ticker,
                                          future_position,
                                          future_amount)

        future_records.append(future_record)

    return sorted(future_records, key=lambda r: r.date)
