from datetime import date

from dividendreport.ledger import Transaction
from dividendreport.record import (
    schedule, frequency, intervals,
    normalize_timespan,
    trailing
)


def test_trailing():
    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
    ]

    recs = list(trailing(records, records[2], months=1))

    assert len(recs) == 1
    assert recs[0] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 2), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
    ]

    recs = list(trailing(records, records[2], months=1))

    assert len(recs) == 2
    assert recs[0] == records[1] and recs[1] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 31), 'ABC', 1, 100),
    ]

    recs = list(trailing(records, records[2], months=1))

    assert len(recs) == 1
    assert recs[0] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
    ]

    recs = list(trailing(records, records[2], months=1, normalized=True))

    assert len(recs) == 2
    assert recs[0] == records[1] and recs[1] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 31), 'ABC', 1, 100),
    ]

    recs = list(trailing(records, records[2], months=1, normalized=True))

    assert len(recs) == 2
    assert recs[0] == records[1] and recs[1] == records[2]


def test_normalize_timespan():
    assert normalize_timespan(1) == 1

    assert normalize_timespan(2) == 3
    assert normalize_timespan(3) == 3

    assert normalize_timespan(4) == 6
    assert normalize_timespan(5) == 6
    assert normalize_timespan(6) == 6

    assert normalize_timespan(7) == 12
    assert normalize_timespan(8) == 12
    assert normalize_timespan(9) == 12
    assert normalize_timespan(10) == 12
    assert normalize_timespan(11) == 12
    assert normalize_timespan(12) == 12


def test_intervals():
    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 5, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [1, 11]

    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2021, 5, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [1, 11]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [12]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2020, 1, 1), 'ABC', 1, 100),
        Transaction(date(2022, 1, 1), 'ABC', 1, 100),
    ]

    assert intervals(records) == [12, 12, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [3, 3, 6]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [3, 6, 3]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [6, 3, 3]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [9, 3]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100),
        Transaction(date(2020, 3, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [9, 3, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100),
        Transaction(date(2020, 3, 1), 'ABC', 1, 100),
        Transaction(date(2020, 12, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [9, 3, 9, 3]


def test_schedule():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert schedule(records) == [3, 6, 9, 12]


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
