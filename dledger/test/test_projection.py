from datetime import date

from dledger.journal import Transaction
from dledger.projection import (
    estimated_monthly_schedule,
    frequency, normalize_interval,
    next_scheduled_date,
    future_transactions,
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
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2020, 3, 1), 'ABC', 1, 100),
        Transaction(date(2021, 3, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2020, 3, 1), 'ABC', 1, 100),
        Transaction(date(2021, 5, 1), 'ABC', 1, 100),
        Transaction(date(2022, 3, 1), 'ABC', 1, 100),
        Transaction(date(2023, 5, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2021, 3, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2018, 5, 4), 'ABC', 1, 100),
        Transaction(date(2018, 5, 4), 'ABC', 1, 100)
    ]

    assert frequency(records) == 12

    records = [
        Transaction(date(2018, 5, 4), 'ABC', 1, 100),
        Transaction(date(2018, 5, 4), 'ABC', 1, 100),
        Transaction(date(2019, 5, 4), 'ABC', 1, 100),
        Transaction(date(2019, 5, 4), 'ABC', 1, 100)
    ]

    assert frequency(records) == 12


def test_biannual_frequency():
    records = [
        Transaction(date(2019, 5, 1), 'ABC', 1, 100),
        Transaction(date(2019, 11, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2020, 4, 1), 'ABC', 1, 100),
        Transaction(date(2020, 6, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100),
        Transaction(date(2020, 3, 1), 'ABC', 1, 100)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 3, 5), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100),
        Transaction(date(2020, 3, 1), 'ABC', 1, 100)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 5, 1), 'ABC', 1, 100)
    ]

    # ambiguous; fallback as biannual
    assert frequency(records) == 6

    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1, 100),
        Transaction(date(2018, 8, 1), 'ABC', 1, 100),
        Transaction(date(2018, 8, 1), 'ABC', 1, 200)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 8, 1), 'ABC', 1, 100),
        Transaction(date(2019, 8, 1), 'ABC', 1, 200),
        Transaction(date(2020, 3, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 6

    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1, 100),
        Transaction(date(2018, 8, 1), 'ABC', 1, 100),
        Transaction(date(2018, 8, 1), 'ABC', 1, 200),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    # note that while this result is not a biannual frequency, it is actually correct for the
    # records given- in an actual scenario where this could occur, the same-date record would
    # would have been pruned beforehand, making frequency == 6
    assert frequency(records) == 12


def test_quarterly_frequency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2020, 6, 1), 'ABC', 1, 100),
        Transaction(date(2021, 12, 1), 'ABC', 1, 100),
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 5), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 5), 'ABC', 1, 100)
    ]

    assert frequency(records) == 3


def test_monthly_frequency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 5, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 1

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 5, 1), 'ABC', 1, 100)
    ]

    assert frequency(records) == 1


def test_irregular_frequency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 8, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100)
    ]

    # todo: this is a bad case; can this really be considered quarterly?
    assert frequency(records) == 3


def test_estimate_monthly_schedule():
    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    schedule = estimated_monthly_schedule(records, interval=1)

    assert schedule == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        # note the different ticker
        Transaction(date(2019, 9, 1), 'ABCD', 1, 100)
    ]

    schedule = estimated_monthly_schedule(records, interval=3)

    assert schedule == [3, 6, 9, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 8, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100)
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
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    futures = future_transactions(records)

    assert len(futures) == 1
    assert futures[0].date == date(2020, 3, 15)

    records = [
        Transaction(date(2019, 3, 16), 'ABC', 1, 100)
    ]

    futures = future_transactions(records)

    assert len(futures) == 1
    assert futures[0].date == date(2020, 3, 31)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2020, 12, 16), 'ABC', 1, 100)
    ]

    futures = future_transactions(records)

    assert len(futures) == 2
    assert futures[0].date == date(2020, 3, 15)
    assert futures[1].date == date(2021, 12, 31)


def test_expired_transactions():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert len(list(expired_transactions(records, since=date(2019, 3, 1), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 2), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 3), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 4), grace_period=3))) == 0
    assert len(list(expired_transactions(records, since=date(2019, 3, 5), grace_period=3))) == 1
