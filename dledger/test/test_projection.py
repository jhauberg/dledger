from datetime import date

from dledger.journal import Transaction, Amount, Distribution
from dledger.projection import (
    FutureTransaction,
    estimated_monthly_schedule,
    frequency, normalize_interval,
    next_scheduled_date,
    next_linear_dividend,
    future_transactions,
    estimated_transactions,
    symbol_conversion_factors,
    scheduled_transactions,
    convert_estimates,
    convert_to_currency
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

    records = [
        Transaction(date(2019, 8, 29), 'ABC', 1),
        Transaction(date(2019, 10, 31), 'ABC', 1),
        Transaction(date(2020, 2, 6), 'ABC', 1)
    ]

    #assert frequency(records) == 3
    # todo: note that this is a false-positive, we expect quarterly here
    #       requires an additional transaction; see next
    assert frequency(records) == 6

    records = [
        Transaction(date(2019, 5, 9), 'ABC', 1),  # additional
        Transaction(date(2019, 8, 29), 'ABC', 1),
        Transaction(date(2019, 10, 31), 'ABC', 1),
        Transaction(date(2020, 2, 6), 'ABC', 1)
    ]

    assert frequency(records) == 3

    records = [
        Transaction(date(2019, 2, 7), 'ABC', 1),
        Transaction(date(2019, 5, 9), 'ABC', 1),
        Transaction(date(2019, 8, 29), 'ABC', 1),
        Transaction(date(2019, 10, 31), 'ABC', 1),
        Transaction(date(2020, 2, 6), 'ABC', 1)
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


def test_next_linear_dividend():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(1))
    ]

    dividend = next_linear_dividend(records)

    assert dividend == Amount(1)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(1)),
        Transaction(date(2019, 6, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(2)),
    ]

    dividend = next_linear_dividend(records)

    assert dividend == Amount(2)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(1)),
        Transaction(date(2019, 6, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(2)),
        Transaction(date(2019, 9, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(2)),
    ]

    dividend = next_linear_dividend(records)

    assert dividend == Amount(2)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(2)),
        Transaction(date(2019, 6, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(1)),
    ]

    dividend = next_linear_dividend(records)

    assert dividend == Amount(1)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(1)),
        Transaction(date(2019, 6, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(2)),
        Transaction(date(2019, 9, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(1.5)),
    ]

    dividend = next_linear_dividend(records)

    assert dividend is None

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(1)),
        Transaction(date(2019, 6, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(2)),
        Transaction(date(2019, 6, 15), 'ABC', 1, amount=Amount(100), dividend=Amount(1.5),
                    kind=Distribution.SPECIAL),
        Transaction(date(2019, 9, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(3)),
    ]

    dividend = next_linear_dividend(records)

    assert dividend == Amount(3)

    records = [
        Transaction(date(2019, 6, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(2)),
        Transaction(date(2019, 6, 15), 'ABC', 1, amount=Amount(100), dividend=Amount(1.5),
                    kind=Distribution.INTERIM),
        Transaction(date(2020, 6, 1), 'ABC', 1, amount=Amount(100), dividend=Amount(3)),
    ]

    dividend = next_linear_dividend(records)

    assert dividend == Amount(3)


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

    # only transactions that match in currency will be projected
    # because of that we only expect 1 in this case
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
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100, symbol='$')),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100, symbol='$')),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100, symbol='kr'))
    ]

    estimations = estimated_transactions(records)

    # varying currencies should not have an effect on the resulting number of projections
    # (e.g. it's not limiting like future_transactions())
    # it does affect the estimated amount, however, as that will only ever be based upon
    # the latest transaction (and all previous transactions of matching symbols)
    assert len(estimations) == 4
    assert estimations[0].date == date(2019, 12, 15)
    assert estimations[1].date == date(2020, 3, 15)
    assert estimations[2].date == date(2020, 6, 15)
    assert estimations[3].date == date(2020, 9, 15)

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


def test_scheduled_transactions():
    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 9, 1), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2019, 10, 1))

    assert len(scheduled) == 0

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 8, 1))

    assert len(scheduled) == 1

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 9, 1))

    assert len(scheduled) == 1

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 2), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 9, 1))

    assert len(scheduled) == 1

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),  # dated in future
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),  # dated in future
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100))  # dated in future
    ]

    # here, the trailing date range will be from 2018/09/01-2019/09/01
    # which should result in only 1 forecast within the forward 12month
    # range from the `since` date at 2019/01/01
    scheduled = scheduled_transactions(records, since=date(2019, 1, 1))

    assert len(scheduled) == 1
    assert scheduled[0].date == date(2019, 12, 15)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100))
    ]

    # the PEP case where payouts are [3, 6, 9, 1], but until a january transaction
    # has been recorded, january will be forecasted as a december payout
    scheduled = scheduled_transactions(records, since=date(2019, 10, 1))

    assert len(scheduled) == 4
    assert scheduled[0].date == date(2019, 12, 15)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        # but once a january transaction is recorded, forecasts should be on track
        Transaction(date(2020, 1, 1), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 1, 15))

    assert len(scheduled) == 4
    assert scheduled[0].date == date(2020, 3, 15)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 1), 'ABC', 1, Amount(100))  # dated in the future
    ]

    scheduled = scheduled_transactions(records, since=date(2019, 10, 1))

    assert len(scheduled) == 3
    assert scheduled[0].date == date(2020, 3, 15)  # because we have one prelim record for dec
    assert scheduled[1].date == date(2020, 6, 15)
    assert scheduled[2].date == date(2020, 9, 15)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 1), 'ABC', 1, Amount(100)),  # dated in the future
        Transaction(date(2020, 3, 1), 'ABC', 1, Amount(100)),  # dated in the future
    ]

    scheduled = scheduled_transactions(records, since=date(2019, 10, 1))

    assert len(scheduled) == 2
    assert scheduled[0].date == date(2020, 6, 15)
    assert scheduled[1].date == date(2020, 9, 15)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 11, 1), 'ABC', 1, Amount(100))  # dated in the future
    ]

    scheduled = scheduled_transactions(records, since=date(2019, 10, 1))

    assert len(scheduled) == 3
    assert scheduled[0].date == date(2020, 3, 15)
    assert scheduled[1].date == date(2020, 6, 15)
    assert scheduled[2].date == date(2020, 9, 15)


def test_scheduled_transactions_closed_position():
    records = [
        Transaction(date(2019, 1, 20), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 1, 19), 'ABC', 0)
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 1, 20))

    assert len(scheduled) == 0

    records = [
        Transaction(date(2019, 1, 20), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 1, 19), 'ABC', 0),
        Transaction(date(2020, 2, 1), 'ABC', 1)
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 1, 20))

    assert len(scheduled) == 0


def test_scheduled_transactions_sampling():
    records = [
        Transaction(date(2019, 3, 10), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 1), 'ABC', 1, Amount(100)),
        # note 5 days earlier than in the past; this leads to an additional projection
        # since there's not more than 12m between; e.g. records sampled will range from:
        #  2019/03/05 (exclusive) - 2020/03/05 (inclusive)
        Transaction(date(2020, 3, 5), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 3, 12))

    assert len(scheduled) == 3
    assert scheduled[0].date == date(2020, 6, 15)

    records = [
        Transaction(date(2019, 3, 5), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 1), 'ABC', 1, Amount(100)),
        # if it was 5 days later, however, then it would be more than 12m and prove no issue
        # e.g. records sampled will range from:
        #  2019/03/10 (exclusive) - 2020/03/10 (inclusive)
        Transaction(date(2020, 3, 10), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 3, 15))

    assert len(scheduled) == 4
    assert scheduled[0].date == date(2020, 6, 15)

    records = [
        Transaction(date(2019, 3, 10), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 3, 5), 'ABC', 1, Amount(100)),
    ]

    # no issue whether earliest record was dated later,
    # because the earliest record is now out of the 12m period entirely
    scheduled = scheduled_transactions(records, since=date(2020, 4, 1))

    assert len(scheduled) == 4
    assert scheduled[0].date == date(2020, 6, 15)

    records = [
        Transaction(date(2019, 3, 10), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 1), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 3, 12))

    assert len(scheduled) == 4
    assert scheduled[0].date == date(2020, 3, 15)

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 1), 'ABC', 1, Amount(100)),
        # note february instead of march; i.e. less than 12m between
        Transaction(date(2020, 2, 28), 'ABC', 1, Amount(100)),  # dated today
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 2, 28))
    # assert len(scheduled) == 4
    # assert scheduled[0].date == date(2020, 6, 15)
    # todo: note that this is a false-positive due to leap year; i.e. if we get a projection:
    #         2020/03/15
    #       and then have realized transaction:
    #         2020/02/28
    #       then there's 16 days between, crossing the 15 days threshold for filtering
    assert len(scheduled) == 5
    assert scheduled[0].date == date(2020, 3, 15)

    records = [
        Transaction(date(2018, 1, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 2, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 4, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 5, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 7, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 8, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 10, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 11, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 12, 1), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2019, 1, 1))

    assert len(scheduled) == 12
    assert scheduled[0].date == date(2019, 1, 15)
    assert scheduled[0].amount_range is None  # to verify that this is not projected by estimate
    assert scheduled[1].date == date(2019, 2, 15)
    assert scheduled[1].amount_range is None
    assert scheduled[2].date == date(2019, 3, 15)
    # ...
    assert scheduled[11].date == date(2019, 12, 15)

    records = [
        Transaction(date(2018, 1, 31), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 2, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 4, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 5, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 6, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 7, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 8, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 9, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 10, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 11, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2018, 12, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 1, 1), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2019, 1, 3))

    assert len(scheduled) == 11
    assert scheduled[0].date == date(2019, 2, 15)

    records = [
        Transaction(date(2019, 4, 30), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 5, 31), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 6, 28), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 7, 31), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 8, 30), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 9, 30), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 10, 31), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 11, 28), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 12, 31), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 1, 31), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 2, 11))

    assert len(scheduled) == 12
    assert scheduled[0].date == date(2020, 2, 29)


def test_scheduled_transactions_in_leap_year():
    records = [
        Transaction(date(2019, 2, 28), 'ABC', 1, Amount(100))
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 1, 1))

    assert len(scheduled) == 1
    assert scheduled[0].date == date(2020, 2, 29)

    records = [
        Transaction(date(2019, 2, 28), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 3, 25), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 1, 1))

    assert len(scheduled) == 2
    assert scheduled[0].date == date(2020, 2, 29)
    assert scheduled[1].date == date(2020, 3, 31)

    records = [
        Transaction(date(2019, 2, 28), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 2, 29), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 3, 1))

    # assert len(scheduled) == 2
    # assert scheduled[0].date == date(2020, 3, 15)
    # assert scheduled[1].date == date(2021, 2, 28)
    # todo: note that this should be considered a false-positive, as we may not expect
    #       2020/03/15 to be discarded, but in other cases, we do!
    assert len(scheduled) == 1
    assert scheduled[0].date == date(2021, 2, 28)

    records = [
        Transaction(date(2019, 2, 28), 'ABC', 1, Amount(100)),
        Transaction(date(2019, 3, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 2, 15), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 3, 1))

    assert len(scheduled) == 2
    assert scheduled[0].date == date(2020, 3, 15)
    assert scheduled[1].date == date(2021, 2, 15)

    records = [
        Transaction(date(2019, 2, 28), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 2, 1), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 2, 15))

    assert len(scheduled) == 1
    assert scheduled[0].date == date(2021, 2, 15)

    records = [
        Transaction(date(2019, 2, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2020, 2, 29), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2020, 3, 1))

    assert len(scheduled) == 1
    assert scheduled[0].date == date(2021, 2, 28)

    records = [
        Transaction(date(2020, 2, 29), 'ABC', 1, Amount(100)),
        Transaction(date(2021, 2, 1), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2021, 2, 15))

    assert len(scheduled) == 1
    assert scheduled[0].date == date(2022, 2, 15)

    records = [
        Transaction(date(2020, 2, 1), 'ABC', 1, Amount(100)),
        Transaction(date(2021, 2, 28), 'ABC', 1, Amount(100)),
    ]

    scheduled = scheduled_transactions(records, since=date(2021, 3, 1))

    assert len(scheduled) == 1
    assert scheduled[0].date == date(2022, 2, 28)


def test_conversion_factors():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(100, symbol='kr'), dividend=Amount(1, symbol='$'))
    ]

    factors = symbol_conversion_factors(records)

    assert len(factors) == 1
    assert factors[('$', 'kr')] == 1

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(675, symbol='kr'), dividend=Amount(1, symbol='$'))
    ]

    factors = symbol_conversion_factors(records)

    assert len(factors) == 1
    assert factors[('$', 'kr')] == 6.75

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(10, symbol='kr'), dividend=Amount(1, symbol='$'))
    ]

    factors = symbol_conversion_factors(records)

    assert len(factors) == 1
    assert factors[('$', 'kr')] == 0.1

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(1, symbol='kr'), dividend=Amount(10, symbol='$'))
    ]

    factors = symbol_conversion_factors(records)

    assert len(factors) == 1
    assert factors[('$', 'kr')] == 0.001

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(100, symbol='kr'), dividend=Amount(1, symbol='$')),
        Transaction(date(2019, 6, 1), 'ABC', 100, amount=Amount(110, symbol='kr'), dividend=Amount(1, symbol='$')),
        Transaction(date(2019, 9, 1), 'ABC', 100, amount=Amount(105, symbol='kr'), dividend=Amount(1, symbol='$'))
    ]

    factors = symbol_conversion_factors(records)

    assert len(factors) == 1
    assert factors[('$', 'kr')] == 1.05


def test_convert_estimates():
    records = [
        Transaction(date(2019, 6, 1), 'ABC', 100, dividend=Amount(1, symbol='$'))
    ]

    records = convert_estimates(records)

    assert isinstance(records[0], FutureTransaction)
    assert records[0].amount.symbol == '$'
    assert records[0].amount.value == 100

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(150, symbol='kr'), dividend=Amount(1.5, symbol='$')),
        Transaction(date(2019, 6, 1), 'ABC', 100, dividend=Amount(1.5, symbol='$'))
    ]

    records = convert_estimates(records)

    assert isinstance(records[1], FutureTransaction)
    assert records[1].amount.symbol == 'kr'
    assert records[1].amount.value == 150


def test_convert_to_currency():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(150, symbol='kr'), dividend=Amount(1, symbol='$'))
    ]

    records = convert_to_currency(records, symbol='$')

    assert isinstance(records[0], FutureTransaction)
    assert records[0].amount.symbol == '$'
    assert records[0].amount.value == 100

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 100, amount=Amount(150, symbol='kr'), dividend=Amount(1, symbol='$')),
        Transaction(date(2019, 3, 2), 'DEF', 100, amount=Amount(50, symbol='kr'), dividend=Amount(0.5, symbol='kr'))
    ]

    records = convert_to_currency(records, symbol='$')

    assert records[0].amount.symbol == '$'
    assert records[0].amount.value == 100
    assert records[1].amount.symbol == '$'
    import math
    assert math.floor(records[1].amount.value) == 33  # floor to ignore decimals
