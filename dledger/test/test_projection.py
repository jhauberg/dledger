from datetime import date

from dledger.journal import Transaction, Amount
from dledger.projection import (
    estimated_monthly_schedule,
    frequency, normalize_interval,
    next_scheduled_date,
    future_transactions,
    estimated_transactions,
    expired_transactions
)


def test_normalize_interval():
    assert normalize_interval(1) == 1

    assert normalize_interval(2) == 3
    assert normalize_interval(3) == 3

    assert normalize_interval(4) == 6
    assert normalize_interval(5) == 6
    assert normalize_interval(6) == 6

    assert normalize_interval(7) == 12
    assert normalize_interval(8) == 12
    assert normalize_interval(9) == 12
    assert normalize_interval(10) == 12
    assert normalize_interval(11) == 12
    assert normalize_interval(12) == 12


def test_annual_frequency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1),
        Transaction(date(2021, 3, 1), 'ABC', 1)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1),
        Transaction(date(2021, 5, 1), 'ABC', 1),
        Transaction(date(2022, 3, 1), 'ABC', 1),
        Transaction(date(2023, 5, 1), 'ABC', 1)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2021, 3, 1), 'ABC', 1)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2018, 5, 4), 'ABC', 1),
        Transaction(date(2018, 5, 4), 'ABC', 1)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2018, 5, 4), 'ABC', 1),
        Transaction(date(2018, 5, 4), 'ABC', 1),
        Transaction(date(2019, 5, 4), 'ABC', 1),
        Transaction(date(2019, 5, 4), 'ABC', 1)
    ]

    assert frequency(records) == 12


def test_biannual_frequency():
    records = [
        Transaction(date(2019, 5, 1), 'ABC', 1),
        Transaction(date(2019, 11, 1), 'ABC', 1)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2020, 4, 1), 'ABC', 1),
        Transaction(date(2020, 6, 1), 'ABC', 1)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 5), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 5, 1), 'ABC', 1)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 8, 1), 'ABC', 1),
        Transaction(date(2019, 8, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    # note that while this result is not a biannual frequency, it is actually correct for the
    # records given- in an actual scenario where this could occur, the same-date record would
    # would have been pruned beforehand, making frequency == 6
    assert frequency(records) == 12


def test_quarterly_frequency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2020, 6, 1), 'ABC', 1),
        Transaction(date(2021, 12, 1), 'ABC', 1),
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 5), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 5), 'ABC', 1)
    ]

    assert frequency(records) == 3


def test_monthly_frequency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 5, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1)
    ]

    assert frequency(records) == 1

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 5, 1), 'ABC', 1)
    ]

    assert frequency(records) == 1


def test_irregular_frequency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 8, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1)
    ]

    # todo: this is a bad case; can this really be considered quarterly?
    assert frequency(records) == 3


def test_estimate_monthly_schedule():
    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1),
        Transaction(date(2019, 2, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    schedule = estimated_monthly_schedule(records, interval=1)

    assert schedule == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        # note the different ticker
        Transaction(date(2019, 9, 1), 'ABCD', 1)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 8, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1)
    ]

    # note that this is an incorrect interval; it is irregular
    schedule = estimated_monthly_schedule(records, interval=3)
    # but it works out anyway; the schedule just isn't padded out, because
    # there's essentially no gaps if this was a quarterly distribution
    assert schedule == [3, 4, 6, 8, 9]


def test_next_scheduled_date():
    d = next_scheduled_date(date(2019, 3, 1), months=[3, 6, 9, 12])

    assert d.year == 2019 and d.month == 6 and d.day == 1

    d = next_scheduled_date(date(2019, 3, 12), months=[3, 6, 9, 12])

    assert d.year == 2019 and d.month == 6 and d.day == 1

    d = next_scheduled_date(date(2019, 12, 1), months=[3, 6, 9, 12])

    assert d.year == 2020 and d.month == 3 and d.day == 1


def test_future_transactions():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    futures = future_transactions(records)

    assert len(futures) == 0

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100))
    ]

    futures = future_transactions(records)

    assert len(futures) == 1
    assert futures[0].date == date(2020, 3, 15)

    records = [
        Transaction(date(2019, 3, 16), 'ABC', 1, Amount(100))
    ]

    futures = future_transactions(records)

    assert len(futures) == 1
    assert futures[0].date == date(2020, 3, 31)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 12, 16), 'ABC', 1, Amount(100))
    ]

    futures = future_transactions(records)

    assert len(futures) == 2
    assert futures[0].date == date(2020, 3, 15)
    assert futures[1].date == date(2021, 12, 31)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100, symbol='$')),
        Transaction(date(2019, 5, 1), 'ABC', 1, Amount(100, symbol='$')),
        Transaction(date(2019, 7, 1), 'ABC', 1, Amount(100, symbol='kr'))
    ]

    futures = future_transactions(records)

    assert len(futures) == 1
    assert futures[0].date == date(2020, 7, 15)


def test_estimated_transactions():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    estimations = estimated_transactions(records)

    assert len(estimations) == 0

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100))
    ]

    estimations = estimated_transactions(records)

    assert len(estimations) == 1
    assert estimations[0].date == date(2020, 3, 15)

    records = [
        Transaction(date(2019, 3, 16), 'ABC', 1, Amount(100))
    ]

    estimations = estimated_transactions(records)

    assert len(estimations) == 1
    assert estimations[0].date == date(2020, 3, 31)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 12, 16), 'ABC', 1, Amount(100))
    ]

    estimations = estimated_transactions(records)

    assert len(estimations) == 2
    assert estimations[0].date == date(2021, 3, 31)
    assert estimations[1].date == date(2021, 12, 31)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100))
    ]

    estimations = estimated_transactions(records)

    assert len(estimations) == 4
    assert estimations[0].date == date(2019, 12, 15)
    assert estimations[0].amount.value == 100
    assert estimations[0].amount_range[0].value == 100
    assert estimations[0].amount_range[1].value == 100
    assert estimations[1].date == date(2020, 3, 15)
    assert estimations[1].amount.value == 100
    assert estimations[2].date == date(2020, 6, 15)
    assert estimations[2].amount.value == 100
    assert estimations[3].date == date(2020, 9, 15)
    assert estimations[3].amount.value == 100

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(30)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(40)),
        Transaction(date(2019, 9, 1), 'ABC', 2, Amount(100))
    ]

    estimations = estimated_transactions(records)

    assert len(estimations) == 4
    assert estimations[0].date == date(2019, 12, 15)
    assert estimations[0].amount_range[0].value == 60   # lowest (adjusted by position)
    assert estimations[0].amount_range[1].value == 100  # highest (adjusted by position)
    assert estimations[0].amount.value == 80            # mean of highest / lowest
    assert estimations[1].date == date(2020, 3, 15)
    assert estimations[1].amount_range[0].value == 80  # lowest (adjusted by position)
    assert estimations[1].amount_range[1].value == 100  # highest (adjusted by position)
    assert estimations[1].amount.value == 90
    assert estimations[2].date == date(2020, 6, 15)
    assert estimations[2].amount.value == 100
    assert estimations[3].date == date(2020, 9, 15)
    assert estimations[3].amount.value == 100

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(40, symbol='$')),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(200, symbol='kr')),
        Transaction(date(2019, 9, 1), 'ABC', 2, Amount(600, symbol='kr'))
    ]

    estimations = estimated_transactions(records)

    assert len(estimations) == 4
    assert estimations[0].amount_range[0].value == 400  # lowest (adjusted by position)
    assert estimations[0].amount_range[1].value == 600  # highest (adjusted by position)
    assert estimations[0].amount.value == 500            # mean of highest aps / lowest aps
    assert estimations[1].date == date(2020, 3, 15)
    assert estimations[1].amount_range[0].value == 400
    assert estimations[1].amount_range[1].value == 600
    assert estimations[1].amount.value == 500
    assert estimations[2].date == date(2020, 6, 15)
    assert estimations[2].amount.value == 600
    assert estimations[3].date == date(2020, 9, 15)
    assert estimations[3].amount.value == 600


def test_expired_transactions():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert len(list(expired_transactions(records, since=date(2019, 3, 1), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 2), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 3), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 4), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 5), grace_period=3))) == 1
