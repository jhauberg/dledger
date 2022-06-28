import math

from datetime import date, timedelta
from dataclasses import dataclass, replace

from statistics import multimode, fmean

from dledger.journal import (
    Transaction,
    Distribution,
    Amount,
    ParseError,
)
from dledger.dateutil import (
    last_of_month,
    months_between,
    days_between,
    in_months,
    next_month,
    previous_month,
    todayd,
    is_within_period,
    is_weekend,
    next_weekday,
    closest_weekday,
    previous_friday,
)
from dledger.record import (
    by_ticker,
    tickers,
    trailing,
    latest,
    before,
    monthly_schedule,
    dividends,
    deltas,
    amount_per_share,
    amount_conversion_factor,
    intervals,
    pruned,
    symbols,
    dated,
)

from typing import Tuple, Optional, List, Iterable, Dict

EARLY = 0
LATE = 1

EARLY_LATE_THRESHOLD = 15  # early before or at this day of month, late after


class GeneratedDate(date):
    """Represents a date estimation."""

    def __new__(
        cls, year: int, month: Optional[int] = None, day: Optional[int] = None
    ):  # type: ignore
        return super(GeneratedDate, cls).__new__(cls, year, month, day)  # type: ignore


@dataclass(frozen=True)
class GeneratedAmount(Amount):
    """Represents an amount estimation."""

    pass


@dataclass(frozen=True)
class GeneratedTransaction(Transaction):
    """Represents a projected transaction."""

    # todo: could keep a set like this for each date (entry, ex, payout)
    #       but only if we have something useful to do with them
    # note that, if applicable, both dates will be set (i.e. if only one comparable
    # transaction is found, that date will act as both the earliest and the latest)
    earliest_entry_date: Optional[date] = None
    latest_entry_date: Optional[date] = None

    def __lt__(self, other: Transaction):  # type: ignore
        return (
            self.entry_date,
            self.earliest_entry_date,
            self.latest_entry_date,
            self.ticker,
        ) < (
            other.entry_date,
            other.earliest_entry_date if isinstance(other, GeneratedTransaction) else None,
            other.latest_entry_date if isinstance(other, GeneratedTransaction) else None,
            other.ticker,
        )


@dataclass(frozen=True)
class Schedule:
    """Represents a dividend payout schedule."""

    frequency: int  # interval between payouts (in months)
    months: List[int]


def normalize_interval(interval: int) -> int:
    """Return a normalized interval.

    Normalized intervals:
       1: Monthly   (every month)
       3: Quarterly (every three months)
       6: Biannual  (two times a year)
      12: Annual    (once a year)
    """

    if interval < 1 or interval > 12:
        raise ValueError("interval must be within 1-12-month range")

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


def frequency(records: Iterable[Transaction]) -> int:
    """Return the approximated frequency of occurrence (in months) for a set of
    records."""

    records = list(records)

    if len(records) == 0:
        return 0

    timespans = sorted(intervals(records))

    m = multimode(timespans)

    if len(m) == 1:
        # unambiguous; a clear pattern of common frequency (take a guess)
        return normalize_interval(m[0])
    else:
        # ambiguous; no clear pattern of frequency,
        # fallback to latest 12-month range (don't guess)
        latest_record = latest(records)
        assert latest_record is not None
        sample_records = trailing(
            records, since=last_of_month(latest_record.entry_date), months=12
        )
        payouts_per_year = len(list(sample_records))
        average_interval = int(12 / payouts_per_year)
        return normalize_interval(average_interval)


def estimated_monthly_schedule(
    records: List[Transaction], *, interval: int
) -> List[int]:
    """Return an estimated monthly schedule for a list of records.

    For example, provided with records dated for months (3, 6) at an interval
    of 3 months, the returned schedule would be (3, 6, 9, 12).
    """

    if interval <= 0:
        raise ValueError("interval must be > 0")

    # first determine months that we know for sure is to be scheduled
    # e.g. those months where that actually has a recorded payout
    approx_schedule = monthly_schedule(records)
    # determine approximate number of payouts per year,
    # given approximate interval between payouts
    payouts_per_year = int(12 / interval)
    # then, going by the last recorded month, increment by interval until
    # scheduled months and number of payouts match- looping back as needed
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


def next_scheduled_date(d: date, months: List[int]) -> GeneratedDate:
    """Return the date that would follow a given date, going by a monthly
    schedule.

    For example, given a date (2019, 6, 18) and a schedule of (3, 6, 9, 12),
    the next scheduled month would be 9, resulting in date (2019, 9, 1).

    Day is always set to first of month.
    """

    if len(months) > 12:
        raise ValueError("schedule exceeds 12-month range")
    if len(months) != len(set(months)):
        raise ValueError("schedule must not contain duplicate months")
    if d.month not in months:
        raise ValueError("schedule does not match given date")

    next_month_index = months.index(d.month) + 1
    next_year = d.year

    if next_month_index == len(months):
        next_year = next_year + 1
        next_month_index = 0

    return GeneratedDate(next_year, month=months[next_month_index], day=1)


def projected_timeframe(d: date) -> int:
    """Return the timeframe of a given date."""

    return EARLY if d.day <= EARLY_LATE_THRESHOLD else LATE


def projected_date(d: date, *, timeframe: int) -> GeneratedDate:
    """Return a date where day of month is set according to given timeframe."""

    next_date: GeneratedDate
    if timeframe == EARLY:
        next_date = GeneratedDate(d.year, d.month, day=EARLY_LATE_THRESHOLD)
    elif timeframe == LATE:
        d = last_of_month(d)
        next_date = GeneratedDate(d.year, d.month, d.day)
    else:
        raise ValueError(f"invalid timeframe")
    if is_weekend(next_date):
        d = previous_friday(next_date)
        # always go backwards in time to prevent jumping months
        next_date = GeneratedDate(d.year, d.month, d.day)
    return next_date


def sample_ttm(
    records: List[Transaction], *, since: date = todayd()
) -> List[Transaction]:
    """Return a list of records dated in the latest trailing 12 months.

    Only includes records from tickers with open positions and activity within
    12 months of a given date.
    """
    # take a sample set of latest 12 months on a per ticker basis
    sample_records: List[Transaction] = []
    for ticker in tickers(records):
        # note that we sample all records, not just transactions,
        # as future_transactions/estimated_transactions require more knowledge
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
        # note using latest_record dating as that potentially adds to the amount
        # of information we'll have available (frequency etc.),
        # and then rely on filtering out older ones later
        recs_in_period = list(trailing(recs, since=latest_record.entry_date, months=12))
        # assert that we don't have identically dated records
        # this is a core requirement for unambiguously projecting transactions
        for i, record in enumerate(recs_in_period):
            for j, other_record in enumerate(recs_in_period):
                if i == j:
                    # don't compare to self
                    continue
                if record.entry_date != other_record.entry_date:
                    # not dated identically
                    continue
                if record.ispositional or other_record.ispositional:
                    # either is positional
                    continue
                if record.position == other_record.position:
                    # position is not ambiguous
                    # the entries may still be incorrect, though, but
                    # the journal parser should catch this
                    continue
                # records dated identically (based on entry date)
                # todo: note that there might be some intricacies with ex-date here
                #       (i.e. in some cases ex-date is the date to compare against),
                #       but for now just base this logic on primary date
                if (
                    record.kind == Distribution.SPECIAL
                    or other_record.kind == Distribution.SPECIAL
                ):
                    # allow identically dated records if one or the other is a
                    # special dividend, but check for ambiguous position
                    # see journal.py:232 for tolerance
                    if not math.isclose(
                        record.position, other_record.position, abs_tol=0.000001
                    ):
                        if other_record.entry_attr is not None:
                            raise ParseError(
                                f"ambiguous position "
                                f"({record.position} or {other_record.position}?)",
                                location=other_record.entry_attr.location,
                            )
                        raise ValueError(
                            f"ambiguous position: {other_record.entry_date} {ticker} "
                            f"({record.position} or {other_record.position}?)"
                        )
                else:
                    # otherwise, don't allow records dated identically
                    if other_record.entry_attr is not None:
                        raise ParseError(
                            f"ambiguous record entry (similar entry dated identically)",
                            location=other_record.entry_attr.location,
                        )
                    raise ValueError(
                        f"ambiguous record entry: {other_record.entry_date} {ticker}"
                    )
        # don't include special dividend transactions
        sample_records.extend(
            r for r in recs_in_period if r.kind is not Distribution.SPECIAL
        )
    return sample_records


def forecast_period(
    starting: date, *, adding_grace_period: bool = False
) -> Tuple[date, date]:
    # weed out projections in the past or later than 12 months into the future
    # note that we potentially include more than 365 days here;
    #   e.g. remainder of current month + 12 full months
    cutoff_date = next_month(in_months(starting, months=12))
    if not adding_grace_period:
        return starting, cutoff_date
    # and with a grace period going back in time,
    # keeping unrealized projections around for a while
    earliest_date = starting + timedelta(days=-EARLY_LATE_THRESHOLD)
    return earliest_date, cutoff_date


def scheduled_transactions(
    records: List[Transaction],
    *,
    since: date = todayd(),
    rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None,
) -> List[GeneratedTransaction]:
    """Return a list of forecasted transactions."""
    sample_records = sample_ttm(records, since=since)
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
        duplicates = [
            r
            for r in scheduled
            if r.ticker == future_record.ticker
            and r.entry_date.year == future_record.entry_date.year
            and r.entry_date.month == future_record.entry_date.month
        ]
        if len(duplicates) > 0:
            # it does, so skip this estimate
            continue
        # it does not, so use this estimate to fill out gap
        scheduled.append(future_record)
    earliest_date, cutoff_date = forecast_period(
        starting=since, adding_grace_period=True
    )
    # example timespan: since=2020/04/08
    #   [2020/03/23] inclusive, up to
    #   [2021/05/01] exclusive
    scheduled = [
        r
        for r in scheduled
        if is_within_period(r.entry_date, earliest_date, cutoff_date)
    ]

    def is_too_closely_dated(txn: GeneratedTransaction, d: date) -> bool:
        # if a transaction is dated same month and same year
        # then consider this forecast a false-positive
        if txn.entry_date.year == d.year and txn.entry_date.month == d.month:
            return True
        # look back far enough to cover earlier-than-expected
        # transactions, but not so far to hit _other_ forecasts
        # if there's a hit, consider this forecast a false-positive
        if days_between(txn.entry_date, d) <= 26:
            return True
        return False

    for sample_record in sample_records:
        if sample_record.amount is None:
            # skip buy/sell transactions;
            # they should not have any effect on this bit of filtering
            continue
        # look for potential false-positive forecasts
        # todo: why not just filter instead of individual removal?
        discards = [
            r
            for r in scheduled
            if r.ticker == sample_record.ticker
            and is_too_closely_dated(r, sample_record.entry_date)
        ]
        for discarded_record in discards:
            scheduled.remove(discarded_record)
    for ticker in tickers(scheduled):
        # find potential outliers to be weeded out
        recs = list(by_ticker(sample_records, ticker))
        projected_recs = list(by_ticker(scheduled, ticker))
        # determine approximate frequency (in sample period)
        freq = frequency(recs)
        expected_projection_count = 12 / freq
        excess_projections = len(projected_recs) - expected_projection_count
        # search for outliers if we have projected more records than expected
        while excess_projections > 0:
            # base this search on the rule that interval between each projection
            # should match approximated frequency - discard records as needed
            # note that we include latest realized record to determine initial interval
            latest_record = latest(recs)
            combined_recs = (
                [latest_record] + projected_recs
                if latest_record is not None
                else projected_recs
            )
            for n, interval in enumerate(intervals(combined_recs)):
                if normalize_interval(interval) != freq:
                    # discard this projection
                    scheduled.remove(projected_recs.pop(n))
                    # start over if there's still more projections than expected
                    break
            next_excess_projections = len(projected_recs) - expected_projection_count
            if next_excess_projections < 0:
                # we removed more than expected
                raise AssertionError
            if next_excess_projections == excess_projections:
                # no change; this leads to an infinite recursion
                raise RecursionError
            excess_projections = next_excess_projections
    for i, txn in enumerate(scheduled):
        comparables = list(comparable_transactions(by_ticker(records, txn.ticker), txn))
        if len(comparables) == 0:
            continue

        def compare_by_day(other: Transaction):
            # we might have transactions dated either 1 month earlier or later
            # so we can't just compare by day; i.e. a transaction dated
            # dec 12 2020 should be considered lower than e.g. jan 2 2021
            # todo: note that this has potentially odd effect for monthly dividends
            if months_between(other.entry_date, txn.entry_date, ignore_years=True) == 1:
                if next_month(txn.entry_date).month == other.entry_date.month:
                    return 1, other.entry_date.day
                if previous_month(txn.entry_date).month == other.entry_date.month:
                    return -1, other.entry_date.day
            return 0, other.entry_date.day

        earliest_comparable_transaction = min(comparables, key=compare_by_day)
        latest_comparable_transaction = max(comparables, key=compare_by_day)

        def next_valid_day(year: int, month: int, day: int) -> date:
            try:
                return date(year, month, day)
            except ValueError:
                return next_valid_day(year, month, day - 1)

        earliest_entry_date = earliest_comparable_transaction.entry_date
        if earliest_entry_date.month == 12 and txn.entry_date.month == 1:
            earliest_entry_date = next_valid_day(
                txn.entry_date.year - 1,
                earliest_entry_date.month,
                earliest_entry_date.day,
            )
        else:
            earliest_entry_date = next_valid_day(
                txn.entry_date.year, earliest_entry_date.month, earliest_entry_date.day
            )
        latest_entry_date = latest_comparable_transaction.entry_date
        if latest_entry_date.month == 1 and txn.entry_date.month == 12:
            latest_entry_date = next_valid_day(
                txn.entry_date.year + 1, latest_entry_date.month, latest_entry_date.day
            )
        else:
            latest_entry_date = next_valid_day(
                txn.entry_date.year, latest_entry_date.month, latest_entry_date.day
            )

        if is_weekend(earliest_entry_date):
            # earliest can go both back and forward in time
            earliest_entry_date = closest_weekday(earliest_entry_date)
        if is_weekend(latest_entry_date):
            # latest can only go forward in time
            latest_entry_date = next_weekday(latest_entry_date)

        txn = replace(
            txn,
            earliest_entry_date=earliest_entry_date,
            latest_entry_date=latest_entry_date,
        )
        scheduled[i] = txn

    # finally, sort them by default transaction sorting rules
    return sorted(scheduled)


def estimated_schedule(records: Iterable[Transaction], record: Transaction) -> Schedule:
    """Return a forecasted dividend schedule based on a given record."""
    sample_records = trailing(
        by_ticker(records, record.ticker),
        since=last_of_month(record.entry_date),
        months=24,
    )

    # exclude closed positions
    sample_records = (r for r in sample_records if r.position > 0)
    # exclude same-date records for more accurate frequency/schedule estimation
    sample_records = pruned(sample_records)
    # determine approximate frequency (annual, biannual, quarterly or monthly)
    approx_frequency = frequency(sample_records)

    months = estimated_monthly_schedule(sample_records, interval=approx_frequency)

    return Schedule(approx_frequency, months)


def estimated_transactions(
    records: List[Transaction],
    *,
    rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None,
) -> List[GeneratedTransaction]:
    """Return a list of forecasted transactions based on a dividend schedule."""

    approximate_records = []

    rates = rates if rates is not None else latest_exchange_rates(records)

    for ticker in tickers(records):
        latest_record = latest(by_ticker(records, ticker), by_exdividend=True)

        assert latest_record is not None

        if not latest_record.position > 0:
            # don't project closed positions
            continue

        # weed out position-only records
        transactions = list(
            r for r in by_ticker(records, ticker) if r.amount is not None
        )

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
            latest_transactions_by_exdate = [
                replace(record, entry_date=record.ex_date, ex_date=None)
                if record.ex_date is not None
                else record
                for record in transactions
            ]
            latest_transaction_by_exdate = latest(latest_transactions_by_exdate)
            assert latest_transaction_by_exdate is not None
            sched_ex = estimated_schedule(
                latest_transactions_by_exdate, latest_transaction_by_exdate
            )
            scheduled_months_ex = sched_ex.months

        # increase number of iterations to extend beyond the next twelve months
        while len(scheduled_records) < len(scheduled_months):
            next_date = next_scheduled_date(future_date, scheduled_months)
            future_date = projected_date(next_date, timeframe=future_timeframe)
            # double-check that position is not closed in the timeframe
            # leading up to future date
            if future_ex_date is not None:
                next_ex_date = next_scheduled_date(future_ex_date, scheduled_months_ex)
                assert future_ex_timeframe is not None
                future_ex_date = projected_date(
                    next_ex_date, timeframe=future_ex_timeframe
                )
                future_position = next_position(
                    records, ticker, earlier_than=future_ex_date
                )
            else:
                future_position = next_position(
                    records, ticker, earlier_than=future_date
                )

            if not future_position > 0:
                # don't project closed positions
                # but keep going until we've filled the schedule
                continue

            reference_records = trailing(
                by_ticker(transactions, ticker), since=future_date, months=12
            )
            reference_records = list(
                r
                for r in reference_records
                if r.amount.symbol == latest_transaction.amount.symbol
            )

            future_amount = amount_per_share(latest_transaction) * future_position
            future_dividend = next_linear_dividend(reference_records)
            future_dividend_value: Optional[float] = None
            if future_dividend is not None:
                future_dividend_value = future_dividend.value
                if future_dividend.symbol != latest_transaction.amount.symbol:
                    assert future_dividend.symbol is not None
                    assert latest_transaction.amount.symbol is not None
                    rate = rates[
                        (future_dividend.symbol, latest_transaction.amount.symbol)
                    ]
                    conversion_factor = rate[1]
                    future_amount = (
                        future_position * future_dividend_value
                    ) * conversion_factor
                else:
                    future_amount = future_position * future_dividend_value
            else:
                divs = [
                    r.dividend.value
                    for r in reference_records
                    if (
                        r.dividend is not None
                        and r.dividend.symbol != r.amount.symbol
                        and r.dividend.symbol == latest_transaction.dividend.symbol
                    )
                ]

                aps = [amount_per_share(r) for r in reference_records]

                if len(divs) > 0:
                    assert latest_transaction.amount.symbol is not None
                    assert latest_transaction.dividend.symbol is not None
                    rate = rates[
                        (
                            latest_transaction.dividend.symbol,
                            latest_transaction.amount.symbol,
                        )
                    ]
                    conversion_factor = rate[1]
                    future_dividend_value = fmean(divs)
                    future_amount = future_dividend_value * future_position
                    future_amount = future_amount * conversion_factor
                elif len(aps) > 0:
                    mean_amount = fmean(aps) * future_position
                    future_amount = mean_amount

            future_record = GeneratedTransaction(
                future_date,
                ticker,
                future_position,
                amount=GeneratedAmount(
                    future_amount,
                    symbol=latest_transaction.amount.symbol,
                    fmt=latest_transaction.amount.fmt,
                ),
                dividend=(
                    GeneratedAmount(
                        future_dividend_value,
                        symbol=latest_transaction.dividend.symbol,
                        fmt=latest_transaction.dividend.fmt,
                    )
                    if future_dividend_value is not None
                    else None
                ),
            )

            scheduled_records.append(future_record)

        approximate_records.extend(scheduled_records)

    return sorted(approximate_records)


def next_linear_dividend(
    records: List[Transaction], *, kind: Distribution = Distribution.FINAL
) -> Optional[GeneratedAmount]:
    """Return the next linearly projected dividend if any, None otherwise."""

    transactions = list(r for r in records if r.amount is not None)
    latest_transaction = latest(transactions)

    if latest_transaction is None or latest_transaction.dividend is None:
        return None

    past_transactions: List[Transaction] = []
    for transaction in transactions:
        if transaction.kind is not kind:
            # skip if not same kind, as different kinds of distributions
            # might follow different schedules
            continue
        if (
            transaction.dividend is None
            or transaction.dividend.symbol != latest_transaction.dividend.symbol
        ):
            break
        past_transactions.append(transaction)

    if len(past_transactions) == 0:
        return None

    movements = deltas(dividends(past_transactions))
    # consider 'no change' same as going up
    movements = [1 if m == 0 else m for m in movements]
    assert all(e == 1 or e == -1 for e in movements)  # only contains 1 or -1 movements
    movements = multimode(movements)
    # if there's a clear trend, up or down (i.e. not an equal amount of ups
    # and downs), then we consider the dividend to follow a linear pattern
    has_linear_pattern = len(multimode(movements)) != 2
    if has_linear_pattern:
        latest_comparable = latest(past_transactions)
        assert latest_comparable is not None
        div = latest_comparable.dividend
        return GeneratedAmount(div.value, symbol=div.symbol, fmt=div.fmt)

    return None


def next_position(
    records: List[Transaction],
    ticker: str,
    *,
    earlier_than: date = todayd(),
) -> float:
    """Return the position of a ticker prior to a date.

    The date is compared against the ex-dividend date.
    """
    latest_record = latest(
        before(by_ticker(records, ticker), earlier_than), by_exdividend=True
    )

    assert latest_record is not None
    return latest_record.position


def comparable_transactions(
    records: Iterable[Transaction], transaction: Transaction
) -> Iterable[Transaction]:
    def is_comparable_date(a: date, b: date) -> bool:
        if a.month == b.month:
            return True
        # dates late/early in neighboring months should also be considered comparable
        if months_between(a, b, ignore_years=True) == 1:
            # todo: prefer something like days_between
            return a.day > 25 or a.day < 5

    return filter(
        lambda txn: is_comparable_date(txn.entry_date, transaction.entry_date)
        and txn.kind is transaction.kind,
        records,
    )


def future_transactions(
    records: List[Transaction],
    *,
    rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None,
) -> List[GeneratedTransaction]:
    """Return a list of forecasted transactions projected 12 months into the
    future."""

    future_records = []

    # weed out position-only records
    transactions = list(r for r in records if r.amount is not None)

    rates = rates if rates is not None else latest_exchange_rates(transactions)

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
        next_date = next_scheduled_date(
            transaction.entry_date, [transaction.entry_date.month]
        )
        future_date = projected_date(
            next_date, timeframe=projected_timeframe(transaction.entry_date)
        )

        if transaction.ex_date is not None:
            next_ex_date = next_scheduled_date(
                transaction.ex_date, [transaction.ex_date.month]
            )
            future_ex_date = projected_date(
                next_ex_date, timeframe=projected_timeframe(transaction.ex_date)
            )
            future_position = next_position(
                records, ticker, earlier_than=future_ex_date
            )
        else:
            future_position = next_position(records, ticker, earlier_than=future_date)

        if not future_position > 0:
            # don't project closed positions
            continue

        future_dividend = next_linear_dividend(
            matching_transactions, kind=transaction.kind
        )

        if future_dividend is None:
            future_dividend = transaction.dividend

        future_amount = future_position * amount_per_share(transaction)

        if future_dividend is not None:
            if future_dividend.symbol != transaction.amount.symbol:
                assert future_dividend.symbol is not None
                assert transaction.amount.symbol is not None
                rate = rates[(future_dividend.symbol, transaction.amount.symbol)]
                conversion_factor = rate[1]
                future_dividend_value = future_position * future_dividend.value
                future_amount = future_dividend_value * conversion_factor
            else:
                future_amount = future_position * future_dividend.value

        future_record = GeneratedTransaction(
            future_date,
            ticker,
            future_position,
            amount=GeneratedAmount(
                future_amount,
                symbol=latest_transaction.amount.symbol,
                fmt=latest_transaction.amount.fmt,
            ),
            dividend=future_dividend,
            kind=transaction.kind,
        )

        future_records.append(future_record)

    return sorted(future_records)


def conversion_factors(
    records: List[Transaction],
) -> Dict[Tuple[str, str], List[Tuple[date, float]]]:
    """Return a set of currency exchange rates."""

    factors: Dict[Tuple[str, str], List[Tuple[date, float]]] = dict()

    transactions = list(r for r in records if r.amount is not None)

    amount_symbols = symbols(records, excluding_dividends=True)
    all_symbols = symbols(records)

    for symbol in amount_symbols:
        for other_symbol in all_symbols:
            if symbol == other_symbol:
                continue

            matching_transactions = list(
                record
                for record in transactions
                if (
                    record.amount.symbol == symbol
                    and record.dividend is not None
                    and record.dividend.symbol == other_symbol
                )
            )

            latest_transaction = latest(matching_transactions, by_payout=True)
            if latest_transaction is None:
                continue
            # determine the date to reference by;
            # e.g. either payout date or entry date, depending on availability
            latest_transaction_date = (
                latest_transaction.payout_date
                if latest_transaction.payout_date is not None
                else latest_transaction.entry_date
            )
            assert latest_transaction.amount is not None
            assert latest_transaction.amount.symbol is not None

            assert latest_transaction.dividend is not None
            assert latest_transaction.dividend.symbol is not None

            conversion_factor = (
                latest_transaction_date,
                amount_conversion_factor(latest_transaction),
            )
            conversion_key = (
                latest_transaction.dividend.symbol,
                latest_transaction.amount.symbol,
            )
            factors[conversion_key] = []

            # bias similar transactions by payout even if latest is based on entry date
            # note that this list will always include latest_transaction as well
            similar_transactions = list(
                dated(matching_transactions, latest_transaction_date, by_payout=True)
            )

            for similar_transaction in similar_transactions:
                similar_conversion_factor = (
                    latest_transaction_date,
                    amount_conversion_factor(similar_transaction),
                )

                def is_ambiguous_rate(
                    a: Tuple[date, float], b: Tuple[date, float]
                ) -> bool:
                    return a[0] == b[0] and not math.isclose(a[1], b[1], abs_tol=0.0001)

                if is_ambiguous_rate(similar_conversion_factor, conversion_factor):
                    is_probably_duplicate = False
                    for previous_ambiguous_rate in factors[conversion_key]:
                        if not is_ambiguous_rate(
                            previous_ambiguous_rate, similar_conversion_factor
                        ):
                            # weed out "duplicate" rates
                            is_probably_duplicate = True
                            break
                    if not is_probably_duplicate:
                        factors[conversion_key].append(similar_conversion_factor)
            # note that we set the applicable rate as last factor,
            # as this seems more intuitive
            # (i.e. the last/latest is the rate being applied to conversions)
            factors[conversion_key].append(conversion_factor)
    # todo: consider including all rates and then sort by date
    return factors


def latest_exchange_rates(
    records: List[Transaction],
) -> Dict[Tuple[str, str], Tuple[date, float]]:
    """Return a set of currency exchange rates."""

    # note that this assumes that, given a bunch of ambiguous rates,
    # the factor to be applied is the last of the bunch
    return {k: v[-1] for k, v in conversion_factors(records).items()}
