from datetime import date

from dividendreport.ledger import Transaction
from dividendreport.record import (
    schedule, intervals, trailing
)


def test_trailing():
    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    recs = list(trailing(records, records[2], months=1))

    assert len(recs) == 1
    assert recs[0] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 2), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    recs = list(trailing(records, records[2], months=1))

    assert len(recs) == 2
    assert recs[0] == records[1] and recs[1] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 31), 'ABC', 1, 100)
    ]

    recs = list(trailing(records, records[2], months=1))

    assert len(recs) == 1
    assert recs[0] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 1), 'ABC', 1, 100)
    ]

    recs = list(trailing(records, records[2], months=1, normalized=True))

    assert len(recs) == 2
    assert recs[0] == records[1] and recs[1] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1, 100),
        Transaction(date(2019, 2, 1), 'ABC', 1, 100),
        Transaction(date(2019, 3, 31), 'ABC', 1, 100)
    ]

    recs = list(trailing(records, records[2], months=1, normalized=True))

    assert len(recs) == 2
    assert recs[0] == records[1] and recs[1] == records[2]


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
        Transaction(date(2022, 1, 1), 'ABC', 1, 100)
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

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 4, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 8, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100)
    ]

    assert intervals(records) == [1, 2, 2, 1, 6]


def test_schedule():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, 100),
        Transaction(date(2019, 6, 1), 'ABC', 1, 100),
        Transaction(date(2019, 9, 1), 'ABC', 1, 100),
        Transaction(date(2019, 12, 1), 'ABC', 1, 100)
    ]

    assert schedule(records) == [3, 6, 9, 12]
