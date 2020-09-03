import math

from datetime import datetime, date, timedelta
from dataclasses import dataclass, replace

from statistics import multimode, fmean

from dledger.journal import Transaction, Distribution, Amount
from dledger.dateutil import last_of_month, months_between, in_months, next_month
from dledger.formatutil import decimalplaces
from dledger.record import (
    by_ticker, tickers, trailing, latest, before, monthly_schedule, dividends, deltas,
    amount_per_share, amount_conversion_factor, intervals, pruned, symbols, dated
)

from typing import Tuple, Optional, List, Iterable, Dict

EARLY = 0
LATE = 1

EARLY_LATE_THRESHOLD = 15  # early before or at this day of month, late after


class GeneratedDate(date):
    """ Represents a date estimation. """
    def __new__(cls, year: int, month: Optional[int] = None, day: Optional[int] = None):  # type: ignore
        return super(GeneratedDate, cls).__new__(cls, year, month, day)  # type: ignore


@dataclass(frozen=True)
class GeneratedAmount(Amount):
    """ Represents an amount estimation. """
    pass


@dataclass(frozen=True)
class GeneratedTransaction(Transaction):
    """ Represents a projected transaction. """
    pass


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

    # start (exclusive) / end (inclusive)
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
        sample_records = trailing(records, since=last_of_month(latest_record.entry_date), months=12)
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
        -> GeneratedDate:
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

    return GeneratedDate(next_year, month=months[next_month_index], day=1)


def projected_timeframe(d: date) -> int:
    """ Return the timeframe of a given date. """

    return EARLY if d.day <= EARLY_LATE_THRESHOLD else LATE


def projected_date(d: date, *, timeframe: int) -> GeneratedDate:
    """ Return a date where day of month is set according to given timeframe. """

    if timeframe == EARLY:
        return GeneratedDate(d.year, d.month, day=EARLY_LATE_THRESHOLD)
    if timeframe == LATE:
        d = last_of_month(d)
        return GeneratedDate(d.year, d.month, d.day)

    raise ValueError(f'invalid timeframe')


def convert_estimates(records: List[Transaction],
                      rates: Optional[Dict[Tuple[str, str], float]] = None) \
        -> List[Transaction]:
    """ Return a list of transactions, replacing missing amounts with estimates. """
    rates = rates if rates is not None else symbol_conversion_factors(records)
    transactions = list(r for r in records if r.amount is not None)
    estimate_records = (r for r in records if (r.amount is None and
                                               r.dividend is not None))
    for rec in estimate_records:
        conversion_factor = 1.0
        assert rec.dividend is not None
        if rec.entry_attr is not None and rec.entry_attr.preliminary_amount is not None:
            estimate_symbol = rec.entry_attr.preliminary_amount.symbol
            estimate_format = rec.entry_attr.preliminary_amount.fmt
            assert rec.dividend.symbol is not None
            assert estimate_symbol is not None
            conversion_factor = rates[(rec.dividend.symbol, estimate_symbol)]
        else:
            estimate_symbol = rec.dividend.symbol
            estimate_format = rec.dividend.fmt
            latest_transaction = latest(by_ticker(transactions, rec.ticker))
            if latest_transaction is not None:
                assert latest_transaction.amount is not None
                estimate_symbol = latest_transaction.amount.symbol
                estimate_format = latest_transaction.amount.fmt
                if rec.dividend.symbol != latest_transaction.amount.symbol:
                    assert rec.dividend.symbol is not None
                    assert latest_transaction.amount.symbol is not None
                    conversion_factor = rates[(rec.dividend.symbol,
                                               latest_transaction.amount.symbol)]
        estimate_amount = GeneratedAmount(
            value=(rec.position * rec.dividend.value) * conversion_factor,
            symbol=estimate_symbol, fmt=estimate_format)
        estimate = replace(rec, amount=estimate_amount)
        i = records.index(rec)
        records.pop(i)
        records.insert(i, estimate)

    return records


def convert_to_currency(records: List[Transaction], *,
                        symbol: str,
                        rates: Optional[Dict[Tuple[str, str], float]] = None) \
        -> List[Transaction]:
    """ Return a list of transactions, replacing amounts with estimates in given currency. """
    rates = rates if rates is not None else symbol_conversion_factors(records)
    transactions = list(r for r in records if r.amount is not None)
    convertible_records = (r for r in records if (r.amount is not None and
                                                  r.amount.symbol != symbol))
    for rec in convertible_records:
        assert rec.amount is not None
        assert rec.amount.symbol is not None
        try:
            conversion_factor = rates[(rec.amount.symbol, symbol)]
        except KeyError:
            try:
                conversion_factor = rates[(symbol, rec.amount.symbol)]
                conversion_factor = 1.0 / conversion_factor
            except KeyError:
                raise ValueError(f'can\'t exchange between {rec.amount.symbol}/{symbol}')
        estimate_format: Optional[str] = None
        for t in reversed(transactions):
            assert t.amount is not None
            if t.amount.symbol == symbol:
                estimate_format = t.amount.fmt
            elif t.dividend is not None and t.dividend.symbol == symbol:
                estimate_format = t.dividend.fmt
            if estimate_format is not None:
                break
        estimate_amount = GeneratedAmount(
            value=rec.amount.value * conversion_factor,
            symbol=symbol, fmt=estimate_format)
        estimate = replace(rec, amount=estimate_amount)
        i = records.index(rec)
        records.pop(i)
        records.insert(i, estimate)

    return records


def scheduled_transactions(records: List[Transaction], *,
                           since: date = datetime.today().date(),
                           rates: Optional[Dict[Tuple[str, str], float]] = None) \
        -> List[GeneratedTransaction]:
    """ Return a list of forecasted transactions. """
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
        if months_between(latest_record.entry_date, since) > 12:
            # skip projections for this ticker entirely,
            # as latest transaction is dated more than 12 months ago
            continue
        # otherwise, add the trailing 12 months of transactions by this ticker
        sample_records.extend(
            # note using latest_record dating as that potentially adds to the amount of information
            # we'll have available (frequency etc.), and then rely on filtering out older ones later
            trailing(recs, since=latest_record.entry_date, months=12))
    # don't include special dividend transactions
    sample_records = [r for r in sample_records if r.kind is not Distribution.SPECIAL]
    # project sample records 1 year into the future
    futures = future_transactions(sample_records, rates=rates)
    # project sample records by 12-month schedule and frequency
    estimates = estimated_transactions(sample_records, rates=rates)
    # base projections primarily on futures
    scheduled = futures
    # use estimates to fill out gaps in schedule
    for future_record in estimates:
        # determine whether to use estimate to fill out gap by checking
        # if a future already "occupies" this month
        duplicates = [r for r in scheduled
                      if r.ticker == future_record.ticker
                      and r.entry_date.year == future_record.entry_date.year
                      and r.entry_date.month == future_record.entry_date.month]
        if len(duplicates) > 0:
            # it does, so skip this estimate
            continue
        # it does not, so use this estimate to fill out gap
        scheduled.append(future_record)
    # weed out projections in the past or later than 12 months into the future
    # note that we potentially include more than 365 days here;
    #   e.g. remainder of current month + 12 full months
    cutoff_date = next_month(in_months(since, months=12))
    # and with a grace period going back in time, keeping unrealized projections around for a while
    earliest_date = since + timedelta(days=-EARLY_LATE_THRESHOLD)
    # example timespan: since=2020/04/08
    #   [2020/03/23] inclusive, up to
    #   [2021/05/01] exclusive
    scheduled = [r for r in scheduled if cutoff_date > r.entry_date >= earliest_date]
    for sample_record in sample_records:
        if sample_record.amount is None:
            # skip buy/sell transactions; they should not have any effect on this bit of filtering
            continue
        # look for projections dated same month, or less than 15 days between a realized transaction
        discards = [r for r in scheduled if r.ticker == sample_record.ticker and
                    ((r.entry_date.year == sample_record.entry_date.year and
                      r.entry_date.month == sample_record.entry_date.month) or
                     (abs((r.entry_date - sample_record.entry_date).days) <= EARLY_LATE_THRESHOLD))]
        # assuming these projections are incorrect, we discard them
        # note that this method does have false-positive scenarios (see tests),
        # but prefer less projections (pessimistic) over too many projections (optimistic)
        for discarded_record in discards:
            scheduled.remove(discarded_record)
    for ticker in tickers(scheduled):
        # find potential outliers to be weeded out
        recs = list(by_ticker(sample_records, ticker))
        projected_recs = list(by_ticker(scheduled, ticker))
        # determine approximate frequency (in sample period)
        freq = frequency(recs)
        # search for outliers if we have projected more records than expected
        while len(projected_recs) > 12 / freq:
            # base this search on the rule that interval between each projection
            # should match approximated frequency - discard records as needed
            # note that we include latest realized record to determine initial interval
            for n, interval in enumerate(intervals([latest(recs)] + projected_recs)):
                if normalize_interval(interval) != freq:
                    # discard this projection
                    scheduled.remove(projected_recs.pop(n))
                    # start over if there's still more projections than expected
                    break
    # finally sort them by default transaction sorting rules
    return sorted(scheduled)


def estimated_schedule(records: List[Transaction], record: Transaction) \
        -> Schedule:
    """ Return a forecasted dividend schedule. """
    # todo: we should clean this up- don't filter out by period, caller can do that
    sample_records = trailing(by_ticker(records, record.ticker),
                              since=last_of_month(record.entry_date), months=24)

    # exclude closed positions
    sample_records = (r for r in sample_records if r.position > 0)
    # exclude same-date records for more accurate frequency/schedule estimation
    sample_records = pruned(sample_records)
    # determine approximate frequency (annual, biannual, quarterly or monthly)
    approx_frequency = frequency(sample_records)

    months = estimated_monthly_schedule(sample_records, interval=approx_frequency)

    return Schedule(approx_frequency, months)


def estimated_transactions(records: List[Transaction], *,
                           rates: Optional[Dict[Tuple[str, str], float]] = None) \
        -> List[GeneratedTransaction]:
    """ Return a list of forecasted transactions based on a dividend schedule. """

    approximate_records = []

    if rates is None:
        rates = symbol_conversion_factors(records)

    for ticker in tickers(records):
        latest_record = latest(by_ticker(records, ticker), by_exdividend=True)

        assert latest_record is not None

        if not latest_record.position > 0:
            # don't project closed positions
            continue

        # weed out position-only records
        transactions = list(r for r in by_ticker(records, ticker) if r.amount is not None)

        latest_transaction = latest(transactions)

        if latest_transaction is None:
            continue

        assert latest_transaction.amount is not None

        sched = estimated_schedule(transactions, latest_transaction)

        scheduled_months = sched.months
        scheduled_records: List[GeneratedTransaction] = []

        future_date = latest_transaction.entry_date
        future_ex_date = latest_transaction.ex_date
        # estimate timeframe by latest actual record
        future_timeframe = projected_timeframe(future_date)
        future_ex_timeframe = None
        scheduled_months_ex = None
        if future_ex_date is not None:
            future_ex_timeframe = projected_timeframe(future_ex_date)
            latest_transactions_by_exdate = [r if r.ex_date is None else
                                             replace(r, entry_date=r.ex_date, ex_date=None) for
                                             r in transactions]
            latest_transaction_by_exdate = latest(latest_transactions_by_exdate)
            sched_ex = estimated_schedule(latest_transactions_by_exdate, latest_transaction_by_exdate)
            scheduled_months_ex = sched_ex.months

        # increase number of iterations to extend beyond the next twelve months
        while len(scheduled_records) < len(scheduled_months):
            next_date = next_scheduled_date(future_date, scheduled_months)
            future_date = projected_date(next_date, timeframe=future_timeframe)
            # double-check that position is not closed in timeframe leading up to future_date
            if future_ex_date is not None:
                next_ex_date = next_scheduled_date(future_ex_date, scheduled_months_ex)
                future_ex_date = projected_date(next_ex_date, timeframe=future_ex_timeframe)
                future_position = next_position(records, ticker, earlier_than=future_ex_date)
            else:
                future_position = next_position(records, ticker, earlier_than=future_date)

            if not future_position > 0:
                # don't project closed positions
                # but keep going until we've filled the schedule
                continue

            reference_records = trailing(
                by_ticker(transactions, ticker), since=future_date, months=12)
            reference_records = list(r for r in reference_records if
                                     r.amount.symbol == latest_transaction.amount.symbol)

            future_amount = amount_per_share(latest_transaction) * future_position
            future_dividend = next_linear_dividend(reference_records)
            future_dividend_value: Optional[float] = None
            future_dividend_places: Optional[int] = None
            if future_dividend is not None:
                if future_dividend.symbol != latest_transaction.amount.symbol:
                    assert future_dividend.symbol is not None
                    assert latest_transaction.amount.symbol is not None
                    conversion_factor = rates[(future_dividend.symbol,
                                               latest_transaction.amount.symbol)]
                    future_dividend_value = future_dividend.value
                    future_amount = (future_position * future_dividend_value) * conversion_factor
                else:
                    future_amount = future_position * future_dividend.value
            else:
                divs = [r.dividend.value for r in reference_records
                        if (r.dividend is not None and
                            r.dividend.symbol != r.amount.symbol and
                            r.dividend.symbol == latest_transaction.dividend.symbol)]

                aps = [amount_per_share(r) for r in reference_records]

                if len(divs) > 0:
                    assert latest_transaction.amount.symbol is not None
                    assert latest_transaction.dividend.symbol is not None
                    conversion_factor = rates[(latest_transaction.dividend.symbol,
                                               latest_transaction.amount.symbol)]
                    future_dividend_value = fmean(divs)
                    future_dividend_places = max(decimalplaces(div) for div in divs)
                    assert future_dividend_places is not None
                    # truncate/round off to fit longest decimal place count observed
                    # in all of the real transactions
                    s = f'{future_dividend_value:.{future_dividend_places}f}'
                    future_dividend_value = float(s)
                    future_amount = future_dividend_value * future_position
                    future_amount = future_amount * conversion_factor
                elif len(aps) > 0:
                    mean_amount = fmean(aps) * future_position
                    future_amount = mean_amount

            future_record = GeneratedTransaction(future_date, ticker, future_position,
                                                 amount=GeneratedAmount(
                                                     future_amount,
                                                     places=latest_transaction.amount.places,
                                                     symbol=latest_transaction.amount.symbol,
                                                     fmt=latest_transaction.amount.fmt),
                                                 dividend=(GeneratedAmount(
                                                     future_dividend_value,
                                                     places=future_dividend_places,
                                                     symbol=latest_transaction.dividend.symbol,
                                                     fmt=latest_transaction.dividend.fmt)
                                                           if future_dividend_value is not None else
                                                           None))

            scheduled_records.append(future_record)

        approximate_records.extend(scheduled_records)

    return sorted(approximate_records)


def next_linear_dividend(records: List[Transaction], *,
                         kind: Distribution = Distribution.FINAL) \
        -> Optional[GeneratedAmount]:
    """ Return the next linearly projected dividend if any, None otherwise. """

    transactions = list(r for r in records if r.amount is not None)
    latest_transaction = latest(transactions)

    if latest_transaction is None:
        return None

    if latest_transaction.dividend is not None:
        comparable_transactions: List[Transaction] = []
        for comparable_transaction in reversed(transactions):
            if comparable_transaction.kind is not kind:
                # skip if not same kind, as different kinds of distributions
                # might follow different schedules
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
                latest_comparable = latest(comparable_transactions)
                assert latest_comparable is not None
                div = latest_comparable.dividend
                return GeneratedAmount(div.value, places=div.places, symbol=div.symbol, fmt=div.fmt)

    return None


def next_position(records: List[Transaction], ticker: str, *,
                  earlier_than: date = datetime.today().date()) \
        -> float:
    latest_record = latest(before(by_ticker(records, ticker), earlier_than), by_exdividend=True)
    
    assert latest_record is not None
    return latest_record.position


def future_transactions(records: List[Transaction], *,
                        rates: Optional[Dict[Tuple[str, str], float]] = None) \
        -> List[GeneratedTransaction]:
    """ Return a list of forecasted transactions projected 12 months into the future. """
    
    future_records = []

    # weed out position-only records
    transactions = list(r for r in records if r.amount is not None)

    if rates is None:
        rates = symbol_conversion_factors(transactions)

    for transaction in transactions:
        assert transaction.amount is not None

        ticker = transaction.ticker
        matching_transactions = list(by_ticker(transactions, ticker))
        latest_transaction = latest(matching_transactions)

        assert latest_transaction is not None
        assert latest_transaction.amount is not None

        if transaction.amount.symbol != latest_transaction.amount.symbol:
            # don't project transactions that do not match latest recorded currency
            continue

        # offset 12 months into the future by assuming an annual schedule
        next_date = next_scheduled_date(transaction.entry_date, [transaction.entry_date.month])
        future_date = projected_date(next_date, timeframe=projected_timeframe(transaction.entry_date))

        if transaction.ex_date is not None:
            next_ex_date = next_scheduled_date(transaction.ex_date, [transaction.ex_date.month])
            future_ex_date = projected_date(next_ex_date, timeframe=projected_timeframe(transaction.ex_date))
            future_position = next_position(records, ticker, earlier_than=future_ex_date)
        else:
            future_position = next_position(records, ticker, earlier_than=future_date)

        if not future_position > 0:
            # don't project closed positions
            continue

        future_dividend = next_linear_dividend(matching_transactions, kind=transaction.kind)

        if future_dividend is None:
            future_dividend = transaction.dividend

        future_amount = future_position * amount_per_share(transaction)

        if future_dividend is not None:
            if future_dividend.symbol != transaction.amount.symbol:
                assert future_dividend.symbol is not None
                assert transaction.amount.symbol is not None
                conversion_factor = rates[(future_dividend.symbol,
                                           transaction.amount.symbol)]
                future_dividend_value = future_position * future_dividend.value
                future_amount = future_dividend_value * conversion_factor
            else:
                future_amount = future_position * future_dividend.value

        future_record = GeneratedTransaction(future_date, ticker, future_position,
                                             amount=GeneratedAmount(
                                                 future_amount,
                                                 places=transaction.amount.places,
                                                 symbol=latest_transaction.amount.symbol,
                                                 fmt=latest_transaction.amount.fmt),
                                             dividend=future_dividend,
                                             kind=transaction.kind)

        future_records.append(future_record)

    return sorted(future_records)


def symbol_conversion_factors(records: List[Transaction]) \
        -> Dict[Tuple[str, str], float]:
    """ Return a set of currency exchange rates. """

    conversion_factors: Dict[Tuple[str, str], float] = dict()

    transactions = list(r for r in records if r.amount is not None)

    amount_symbols = symbols(records, excluding_dividends=True)
    all_symbols = symbols(records)

    for symbol in amount_symbols:
        for other_symbol in all_symbols:
            if symbol == other_symbol:
                continue

            matching_transactions = list(r for r in transactions if (r.amount.symbol == symbol and
                                                                     r.dividend is not None and
                                                                     r.dividend.symbol == other_symbol))

            latest_transaction = latest(matching_transactions, by_payout=True)
            if latest_transaction is None:
                continue
            # determine the date to reference by; e.g. either payout date or entry date, depending on availability
            latest_transaction_date = (latest_transaction.payout_date if
                                       latest_transaction.payout_date is not None else
                                       latest_transaction.entry_date)
            assert latest_transaction.amount is not None
            assert latest_transaction.amount.symbol is not None

            assert latest_transaction.dividend is not None
            assert latest_transaction.dividend.symbol is not None

            conversion_factor = amount_conversion_factor(latest_transaction)
            conversion_factors[(latest_transaction.dividend.symbol,
                                latest_transaction.amount.symbol)] = conversion_factor

            # bias similar transactions by payout date even if latest is based on entry date
            similar_transactions = list(dated(matching_transactions, latest_transaction_date, by_payout=True))

            if len(similar_transactions) == 1:  # latest_transaction is always included here
                # unless we have more transactions there's no need to proceed further
                continue

            for similar_transaction in similar_transactions:
                similar_conversion_factor = amount_conversion_factor(similar_transaction)
                if not math.isclose(similar_conversion_factor, conversion_factor, abs_tol=0.0001):
                    raise ValueError(f'ambiguous conversion rate ({similar_conversion_factor} or {conversion_factor}?)')

    return conversion_factors
