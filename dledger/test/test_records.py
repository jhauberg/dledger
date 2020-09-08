from datetime import date

from dledger.journal import Transaction, Amount
from dledger.record import (
    monthly_schedule, intervals, trailing, pruned, dividends, deltas,
    in_period, symbols, dated
)


def test_trailing():
    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1),
        Transaction(date(2019, 2, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    recs = list(trailing(records, since=records[2].entry_date, months=1))

    assert len(recs) == 1
    assert recs[0] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1),
        Transaction(date(2019, 2, 2), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    recs = list(trailing(records, since=records[2].entry_date, months=1))

    assert len(recs) == 2
    assert recs[0] == records[1] and recs[1] == records[2]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1),
        Transaction(date(2019, 2, 1), 'ABC', 1),
        Transaction(date(2019, 3, 31), 'ABC', 1)
    ]

    recs = list(trailing(records, since=records[2].entry_date, months=1))

    assert len(recs) == 1
    assert recs[0] == records[2]


def test_intervals():
    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 5, 1), 'ABC', 1)
    ]

    assert intervals(records) == [1, 11]

    records = [
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2021, 5, 1), 'ABC', 1)
    ]

    assert intervals(records) == [1, 11]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1)
    ]

    assert intervals(records) == [12]

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 1),
        Transaction(date(2020, 1, 1), 'ABC', 1),
        Transaction(date(2022, 1, 1), 'ABC', 1)
    ]

    assert intervals(records) == [12, 12, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1)
    ]

    assert intervals(records) == [3, 3, 6]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert intervals(records) == [3, 6, 3]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert intervals(records) == [6, 3, 3]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert intervals(records) == [9, 3]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1)
    ]

    assert intervals(records) == [9, 3, 12]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1),
        Transaction(date(2020, 12, 1), 'ABC', 1)
    ]

    assert intervals(records) == [9, 3, 9, 3]

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 4, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 8, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1)
    ]

    assert intervals(records) == [1, 2, 2, 1, 6]

    records = [
        Transaction(date(2018, 5, 4), 'ABC', 1),
        Transaction(date(2018, 5, 4), 'ABC', 1)
    ]

    # note that, though dated identically, these records will be normalized as a year apart
    # this might seem wrong, but what we're interested in here is the pattern of payouts,
    # not the actual number of months between- so in this case, an additional payout on same date
    # just enforces the pattern of an annual payout interval
    assert intervals(records) == [12, 12]

    records = [
        Transaction(date(2018, 5, 4), 'ABC', 1),
        Transaction(date(2018, 5, 14), 'ABC', 1)
    ]

    assert intervals(records) == [12, 12]

    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1)
    ]

    assert intervals(records) == [5, 12, 7]

    records = [
        Transaction(date(2019, 8, 1), 'ABC', 1),
        Transaction(date(2019, 8, 1), 'ABC', 1),
        Transaction(date(2020, 3, 1), 'ABC', 1)
    ]

    assert intervals(records) == [12, 7, 5]

    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    # note that while the results for this case are correct, in the actual scenario where it could
    # occur, the same-date record would have been pruned beforehand, making intervals == [5, 7, 12]
    assert intervals(records) == [5, 12, 7, 12]


def test_schedule():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert monthly_schedule(records) == [3, 6, 9, 12]


def test_pruned():
    records = [
        Transaction(date(2018, 3, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2018, 8, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1)
    ]

    assert len(pruned(records)) == 3


def test_in_period():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 6, 1), 'ABC', 1),
        Transaction(date(2019, 9, 1), 'ABC', 1),
        Transaction(date(2019, 12, 1), 'ABC', 1)
    ]

    assert len(list(in_period(records, (None, None)))) == 4
    assert len(list(in_period(records, (date(2019, 1, 1), None)))) == 4
    assert len(list(in_period(records, (None, date(2020, 1, 1))))) == 4
    assert len(list(in_period(records, (date(2019, 1, 1),
                                        date(2020, 1, 1))))) == 4
    assert len(list(in_period(records, (date(2019, 1, 1),
                                        date(2019, 12, 1))))) == 3
    assert len(list(in_period(records, (date(2019, 3, 1), None)))) == 4
    assert len(list(in_period(records, (date(2019, 3, 2), None)))) == 3
    assert len(list(in_period(records, (None, date(2019, 6, 1))))) == 1


def test_dividends():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, dividend=Amount(1)),
        Transaction(date(2019, 6, 1), 'ABC', 1, dividend=Amount(2))
    ]

    assert dividends(records) == [Amount(1), Amount(2)]


def test_deltas():
    amounts = [
        Amount(1),
        Amount(2)
    ]

    assert deltas(amounts) == [1]
    assert deltas(amounts, normalized=False) == [1]

    amounts = [
        Amount(1),
        Amount(2),
        Amount(2)
    ]

    assert deltas(amounts) == [1, 0]
    assert deltas(amounts, normalized=False) == [1, 0]

    amounts = [
        Amount(1),
        Amount(2.5)
    ]

    assert deltas(amounts) == [1]
    assert deltas(amounts, normalized=False) == [1.5]

    amounts = [
        Amount(1),
        Amount(2.5),
        Amount(1),
        Amount(0.5)
    ]

    assert deltas(amounts) == [1, -1, -1]
    assert deltas(amounts, normalized=False) == [1.5, -1.5, -0.5]

    amounts = [
        Amount(0.12),
        Amount(0.08),
        Amount(0.08)
    ]

    assert deltas(amounts) == [-1, 0]
    # todo: approximate or truncate
    # assert deltas(amounts, normalized=False) == [-0.04, 0]


def test_symbols():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(1, symbol='$')),
        Transaction(date(2019, 6, 1), 'ABC', 1, amount=Amount(2, symbol='kr'))
    ]

    s = symbols(records)

    assert len(s) == 2

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, amount=Amount(1, symbol='kr'), dividend=Amount(1, symbol='$'))
    ]

    s = symbols(records)

    assert len(s) == 2

    s = symbols(records, excluding_dividends=True)

    assert len(s) == 1


def test_dated():
    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1),
        Transaction(date(2019, 3, 1), 'XYZ', 1)
    ]

    hits = list(dated(records, date(2019, 3, 1)))

    assert len(hits) == 2

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, payout_date=date(2019, 2, 28)),
        Transaction(date(2019, 3, 1), 'XYZ', 1)
    ]

    hits = list(dated(records, date(2019, 3, 1), by_payout=True))

    assert len(hits) == 1

    records = [
        Transaction(date(2019, 2, 28), 'XYZ', 1),
        Transaction(date(2019, 3, 1), 'ABC', 1, payout_date=date(2019, 2, 28)),
    ]

    hits = list(dated(records, date(2019, 2, 28), by_payout=True))

    assert len(hits) == 2

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, ex_date=date(2019, 2, 28)),
        Transaction(date(2019, 3, 1), 'XYZ', 1)
    ]

    hits = list(dated(records, date(2019, 3, 1), by_payout=True))

    assert len(hits) == 2

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 1, ex_date=date(2019, 2, 28)),
        Transaction(date(2019, 3, 1), 'XYZ', 1)
    ]

    hits = list(dated(records, date(2019, 3, 1), by_exdividend=True))

    assert len(hits) == 1
