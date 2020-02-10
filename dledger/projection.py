from datetime import datetime, date
from dataclasses import dataclass

from statistics import multimode, fmean  # type: ignore

from dledger.journal import Transaction, Distribution, Amount
from dledger.dateutil import last_of_month, months_between
from dledger.formatutil import most_decimal_places
from dledger.record import (
    by_ticker, tickers, trailing, latest, before, monthly_schedule, dividends, deltas,
    amount_per_share, amount_conversion_factor, intervals, pruned, symbols
)

from typing import Tuple, Optional, List, Iterable, Dict

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


def convert_estimates(records: List[Transaction]) -> List[Transaction]:
    conversion_factors = symbol_conversion_factors(records)
    transactions = list(r for r in records if r.amount is not None)
    estimate_records = (r for r in records if (r.amount is None and
                                               r.dividend is not None))
    for rec in estimate_records:
        conversion_factor = 1.0
        estimate_symbol = rec.dividend.symbol
        estimate_format = rec.dividend.format
        latest_transaction = latest(by_ticker(transactions, rec.ticker))
        if latest_transaction is not None:
            estimate_symbol = latest_transaction.amount.symbol
            estimate_format = latest_transaction.amount.format
            if rec.dividend.symbol != latest_transaction.amount.symbol:
                conversion_factor = conversion_factors[(rec.dividend.symbol,
                                                        latest_transaction.amount.symbol)]
        estimate_amount = Amount((rec.position * rec.dividend.value) * conversion_factor,
                                 estimate_symbol, estimate_format)
        estimate = FutureTransaction(rec.date, rec.ticker, rec.position,
                                     estimate_amount, rec.dividend, rec.kind)
        i = records.index(rec)
        records.pop(i)
        records.insert(i, estimate)

    return records


def convert_to_currency(records: List[Transaction], *, symbol: str) -> List[Transaction]:
    conversion_factors = symbol_conversion_factors(records)
    transactions = list(r for r in records if r.amount is not None)
    convertible_records = (r for r in records if (r.amount is not None and
                                                  r.amount.symbol != symbol))
    for rec in convertible_records:
        try:
            conversion_factor = conversion_factors[(rec.amount.symbol, symbol)]
        except KeyError:
            try:
                conversion_factor = conversion_factors[(symbol, rec.amount.symbol)]
                conversion_factor = 1.0 / conversion_factor
            except KeyError:
                continue
        estimate_format: Optional[str] = None
        for t in reversed(transactions):
            if t.amount.symbol == symbol:
                estimate_format = t.amount.format
            elif t.dividend is not None and t.dividend.symbol == symbol:
                estimate_format = t.dividend.format
            if estimate_format is not None:
                break
        estimate_amount = Amount(rec.amount.value * conversion_factor, symbol, estimate_format)
        estimate = FutureTransaction(rec.date, rec.ticker, rec.position,
                                     estimate_amount, rec.dividend, rec.kind)
        i = records.index(rec)
        records.pop(i)
        records.insert(i, estimate)

    return records


def scheduled_transactions(records: List[Transaction],
                           *,
                           since: date = datetime.today().date()) \
        -> List[FutureTransaction]:
    # take a sample set of latest 12 months on a per ticker basis
    sample_records: List[Transaction] = []
    for ticker in tickers(records):
        # note that we sample all records, not just transactions
        # as future_transactions/estimated_transactions require more knowledge
        # todo: we can look into improving that so we do all the filtering in this function instead
        recs = list(by_ticker(records, ticker))
        # find the latest record and base trailing period from its date
        latest_record = latest(recs)
        assert latest_record is not None
        future_position = latest_record.position
        if not future_position > 0:
            # don't project closed positions
            continue
        if months_between(latest_record.date, since) > 12:
            # skip projections for this ticker entirely,
            # as latest transaction is dated more than 12 months ago
            continue
        # otherwise, add the trailing 12 months of transactions by this ticker
        sample_records.extend(
            # todo: 11 months might be correct to avoid some difficult scenarios
            trailing(recs, since=latest_record.date, months=11))
    # don't include special dividend transactions
    sample_records = [r for r in sample_records if r.kind is not Distribution.SPECIAL]
    # project sample records 1 year into the future
    futures = future_transactions(sample_records)
    # project sample records by 12-month schedule and frequency
    estimates = estimated_transactions(sample_records)
    # base projections primarily on futures
    scheduled = futures
    # use estimates to fill out gaps in schedule
    for future_record in estimates:
        # determine whether to use estimate to fill out gap by checking
        # if a future already "occupies" this month
        duplicates = [r for r in scheduled
                      if r.ticker == future_record.ticker
                      and r.date.year == future_record.date.year
                      and r.date.month == future_record.date.month]
        if len(duplicates) > 0:
            # it does, so skip this estimate
            continue
        # it does not, so use this estimate to fill out gap
        scheduled.append(future_record)
    # weed out projections in the past or later than 12 months into the future
    scheduled = [r for r in scheduled if r.date >= since and months_between(r.date, since) <= 12]
    # finally sort them by default transaction sorting rules
    return sorted(scheduled)


def estimated_schedule(records: List[Transaction], record: Transaction) \
        -> Schedule:
    sample_records = trailing(by_ticker(records, record.ticker),
                              since=last_of_month(record.date), months=24)

    # exclude closed positions
    sample_records = (r for r in sample_records if r.position > 0)
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

    conversion_factors = symbol_conversion_factors(records)

    for ticker in tickers(records):
        # weed out position-only records
        transactions = list(r for r in by_ticker(records, ticker) if r.amount is not None)

        latest_transaction = latest(transactions)

        if latest_transaction is None:
            continue

        sched = estimated_schedule(transactions, latest_transaction)

        scheduled_months = sched.months
        scheduled_records: List[FutureTransaction] = []

        future_date = latest_transaction.date
        # estimate timeframe by latest actual record
        future_timeframe = projected_timeframe(future_date)

        can_convert_from_dividend = False
        if (latest_transaction.dividend is not None and
                latest_transaction.dividend.symbol != latest_transaction.amount.symbol):
            can_convert_from_dividend = True

        # increase number of iterations to extend beyond the next twelve months
        while len(scheduled_records) < len(scheduled_months):
            next_date = next_scheduled_date(future_date, scheduled_months)
            future_date = projected_date(next_date, timeframe=future_timeframe)

            # double-check that position is not closed in timeframe leading up to future_date
            latest_record = latest(before(by_ticker(records, ticker), future_date))

            assert latest_record is not None

            future_position = latest_record.position

            if not future_position > 0:
                # don't project closed positions
                continue

            reference_records = trailing(
                by_ticker(transactions, ticker), since=future_date, months=12)
            reference_records = list(r for r in reference_records if
                                     r.amount.symbol == latest_transaction.amount.symbol)

            future_amount = amount_per_share(latest_transaction) * future_position
            future_amount_range = None

            future_dividend = next_linear_dividend(reference_records)

            if future_dividend is not None:
                if can_convert_from_dividend:
                    conversion_factor = conversion_factors[(future_dividend.symbol,
                                                            latest_transaction.amount.symbol)]
                    future_dividend_value = future_position * future_dividend.value
                    future_dividend = future_dividend.value
                    future_amount = future_dividend_value * conversion_factor
                else:
                    future_amount = future_position * future_dividend.value
            else:
                divs = [r.dividend.value for r in reference_records
                        if (r.dividend is not None and
                            r.dividend.symbol != r.amount.symbol and
                            r.dividend.symbol == latest_transaction.dividend.symbol)]

                aps = [amount_per_share(r) for r in reference_records]

                if len(divs) > 0 and can_convert_from_dividend:
                    conversion_factor = conversion_factors[(latest_transaction.dividend.symbol,
                                                            latest_transaction.amount.symbol)]
                    highest_dividend = max(divs) * future_position
                    lowest_dividend = min(divs) * future_position
                    future_dividend = fmean(divs)
                    decimal_places = most_decimal_places(divs)
                    # truncate/round off to fit longest decimal place count observed
                    # in all of the real transactions
                    s = f'{future_dividend:.{decimal_places}f}'
                    future_dividend = float(s)
                    future_amount = future_dividend * future_position
                    future_amount = future_amount * conversion_factor
                    future_amount_range = (Amount(lowest_dividend * conversion_factor,
                                                  symbol=latest_transaction.amount.symbol,
                                                  format=latest_transaction.amount.format),
                                           Amount(highest_dividend * conversion_factor,
                                                  symbol=latest_transaction.amount.symbol,
                                                  format=latest_transaction.amount.format))
                elif len(aps) > 0:
                    highest_amount = max(aps) * future_position
                    lowest_amount = min(aps) * future_position
                    mean_amount = fmean(aps) * future_position
                    future_amount = mean_amount
                    future_amount_range = (Amount(lowest_amount,
                                                  symbol=latest_transaction.amount.symbol,
                                                  format=latest_transaction.amount.format),
                                           Amount(highest_amount,
                                                  symbol=latest_transaction.amount.symbol,
                                                  format=latest_transaction.amount.format))

            future_record = FutureTransaction(future_date, ticker, future_position,
                                              amount=Amount(future_amount,
                                                            symbol=latest_transaction.amount.symbol,
                                                            format=latest_transaction.amount.format),
                                              amount_range=future_amount_range,
                                              dividend=(Amount(future_dividend,
                                                               symbol=latest_transaction.dividend.symbol,
                                                               format=latest_transaction.dividend.format)
                                                        if can_convert_from_dividend else None))

            scheduled_records.append(future_record)

        approximate_records.extend(scheduled_records)

    return sorted(approximate_records)


def next_linear_dividend(records: List[Transaction]) -> Optional[Amount]:
    """ Return the estimated next linearly projected dividend if able, None otherwise. """

    transactions = list(r for r in records if r.amount is not None)
    latest_transaction = latest(transactions)

    if latest_transaction is None:
        return None

    if latest_transaction.dividend is not None:
        comparable_transactions: List[Transaction] = []
        for comparable_transaction in reversed(transactions):
            if comparable_transaction.kind is not Distribution.FINAL:
                # don't include interim/special dividends as they do not necessarily follow
                # the same policy or pattern as final dividends
                continue
            if (comparable_transaction.dividend is None or
                    comparable_transaction.dividend.symbol != latest_transaction.dividend.symbol):
                break
            comparable_transactions.append(comparable_transaction)
        if len(comparable_transactions) > 0:
            comparable_transactions.reverse()
            movements = deltas(dividends(comparable_transactions))
            # consider 'no change' same as going up
            movements = [1 if m == 0 else m for m in movements]
            movements = multimode(movements)
            n = len(multimode(movements))
            # if there's a clear trend, up or down, assume linear pattern
            if n == 0 or n == 1:
                return latest(comparable_transactions).dividend

    return None


def future_transactions(records: List[Transaction]) \
        -> List[FutureTransaction]:
    """ Return a list of transactions, each dated 12 months into the future. """
    
    future_records = []

    # weed out position-only records
    transactions = list(r for r in records if r.amount is not None)

    conversion_factors = symbol_conversion_factors(transactions)

    for transaction in transactions:
        assert transaction.amount is not None

        matching_transactions = list(by_ticker(transactions, transaction.ticker))
        latest_transaction = latest(matching_transactions)

        assert latest_transaction is not None
        assert latest_transaction.amount is not None

        if transaction.amount.symbol != latest_transaction.amount.symbol:
            # don't project transactions that do not match latest recorded currency
            continue

        # offset 12 months into the future by assuming an annual schedule
        next_date = next_scheduled_date(transaction.date, [transaction.date.month])
        future_date = projected_date(next_date, timeframe=projected_timeframe(transaction.date))
        future_payout_date: Optional[date] = None
        if transaction.payout_date is not None:
            next_payout_date = next_scheduled_date(
                transaction.payout_date, [transaction.payout_date.month])
            future_payout_date = projected_date(
                next_payout_date, timeframe=projected_timeframe(transaction.payout_date))

        # we must double-check that the position has not been closed in the timeframe leading
        # up to the projected date; for example, this sequence of transactions should not
        # result in a forecasted transaction:
        #    2019/01/20 ABC (10)  $ 1
        #    2020/01/19 ABC (0)
        #    -- no forecasted transaction here, because position was closed
        #    2020/02/01 ABC (10)
        # note that the final buy transaction has to be dated later than projected_date()
        # (in this case 2020/01/31)
        latest_record = latest(before(by_ticker(records, transaction.ticker), future_date))

        assert latest_record is not None

        future_position = latest_record.position

        if not future_position > 0:
            # don't project closed positions
            continue

        if transaction.kind == Distribution.INTERIM:
            # todo: still ramp, but using past interim dividends
            future_dividend = transaction.dividend
        else:
            future_dividend = next_linear_dividend(matching_transactions)

            if future_dividend is None:
                future_dividend = transaction.dividend

        future_amount = future_position * amount_per_share(transaction)

        if future_dividend is not None:
            if future_dividend.symbol != transaction.amount.symbol:
                conversion_factor = conversion_factors[(future_dividend.symbol,
                                                        transaction.amount.symbol)]
                future_dividend_value = future_position * future_dividend.value
                future_amount = future_dividend_value * conversion_factor
            else:
                future_amount = future_position * future_dividend.value

        future_record = FutureTransaction(future_date, transaction.ticker, future_position,
                                          amount=Amount(future_amount,
                                                        symbol=latest_transaction.amount.symbol,
                                                        format=latest_transaction.amount.format),
                                          dividend=future_dividend,
                                          kind=transaction.kind,
                                          payout_date=future_payout_date)

        future_records.append(future_record)

    return sorted(future_records)


def symbol_conversion_factors(records: List[Transaction]) \
        -> Dict[Tuple[str, str], float]:
    conversion_factors: Dict[Tuple[str, str], float] = dict()

    transactions = list(r for r in records if r.amount is not None)

    amount_symbols = symbols(records, excluding_dividends=True)
    all_symbols = symbols(records)

    for symbol in amount_symbols:
        for other_symbol in all_symbols:
            if symbol == other_symbol:
                continue

            latest_transaction = latest(
                (r for r in transactions if (r.amount.symbol == symbol and
                                             r.dividend is not None and
                                             r.dividend.symbol == other_symbol)), by_payout=True)

            if latest_transaction is None:
                continue

            conversion_factor = amount_conversion_factor(latest_transaction)
            conversion_factors[(latest_transaction.dividend.symbol,
                                latest_transaction.amount.symbol)] = conversion_factor

    return conversion_factors
