import locale

from datetime import date

from dledger.journal import (
    Transaction, Amount,
    read, remove_redundant_journal_transactions
)
from dledger.localeutil import trysetlocale


def test_simple_journal():
    records = read('../example/simple.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, '$', '$ %s'),
                                     dividend=Amount(0.73, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))

    records = read('../example/simple-condensed.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, '$', '$ %s'),
                                     dividend=Amount(0.73, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))


def test_ordering():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/ordering.journal', kind='journal')

    assert len(records) == 5
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, '$', '$ %s'),
                                     dividend=Amount(0.73, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 110,
                                     amount=Amount(84.7, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 120,
                                     amount=Amount(92.4, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[4] == Transaction(date(2019, 11, 14), 'AAPL', 0)


def test_positions_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/positions.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, '$', '$ %s'),
                                     dividend=Amount(0.73, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     amount=Amount(92.4, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 140,
                                     amount=Amount(107.8, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))

    records = read('../example/positions-condensed.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, '$', '$ %s'),
                                     dividend=Amount(0.73, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     amount=Amount(92.4, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 140,
                                     amount=Amount(107.8, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))


def test_dividends_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/dividends.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, '$', '$ %s'),
                                     dividend=Amount(0.73, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, '$', '$ %s'),
                                     dividend=Amount(0.77, '$', '$ %s'))


def test_nativedividends_journal():
    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    records = read('../example/nativedividends.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(490.33, 'kr', '%s kr'),
                                     dividend=Amount(0.73, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(517.19, 'kr', '%s kr'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(517.19, 'kr', '%s kr'),
                                     dividend=Amount(0.77, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(517.19, 'kr', '%s kr'),
                                     dividend=Amount(0.77, '$', '$ %s'))


def test_strategic_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/strategic.journal', kind='journal')

    assert len(records) == 6
    assert records[0] == Transaction(date(2019, 1, 20), 'ABC', 10,
                                     amount=Amount(1, '$', '$ %s'),
                                     dividend=Amount(0.1, '$', '$ %s'))
    assert records[1] == Transaction(date(2019, 4, 20), 'ABC', 10,
                                     amount=Amount(2, '$', '$ %s'),
                                     dividend=Amount(0.2, '$', '$ %s'))
    assert records[2] == Transaction(date(2019, 7, 20), 'ABC', 10,
                                     amount=Amount(2, '$', '$ %s'),
                                     dividend=Amount(0.2, '$', '$ %s'))
    assert records[3] == Transaction(date(2019, 10, 20), 'ABC', 10,
                                     amount=Amount(2, '$', '$ %s'),
                                     dividend=Amount(0.2, '$', '$ %s'))
    assert records[4] == Transaction(date(2020, 1, 19), 'ABC', 0)
    assert records[5] == Transaction(date(2020, 2, 1), 'ABC', 10)


def test_remove_redundant_entries():
    records = [
        Transaction(date(2019, 1, 1), 'ABC', 10)
    ]

    records = remove_redundant_journal_transactions(records)

    assert len(records) == 1

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 10),
        Transaction(date(2019, 2, 1), 'ABC', 10, amount=Amount(1))
    ]

    records = remove_redundant_journal_transactions(records)

    assert len(records) == 1

    records = [
        # note that this scenario would not typically happen
        # as a position change record on same date as dividend transaction
        # would occur *after* the dividend transaction
        Transaction(date(2019, 1, 1), 'ABC', 10),
        Transaction(date(2019, 1, 1), 'ABC', 10, amount=Amount(1))
    ]

    records = remove_redundant_journal_transactions(records)

    assert len(records) == 1

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 10, amount=Amount(1)),
        Transaction(date(2019, 1, 1), 'ABC', 10)
    ]

    records = remove_redundant_journal_transactions(records)

    assert len(records) == 1

    records = [
        Transaction(date(2019, 2, 1), 'ABC', 10, amount=Amount(1)),
        Transaction(date(2019, 3, 1), 'ABC', 20, amount=Amount(1)),
        Transaction(date(2019, 4, 1), 'ABC', 30)
    ]

    records = remove_redundant_journal_transactions(records)

    assert len(records) == 3

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 10),
        Transaction(date(2019, 2, 1), 'ABC', 10, amount=Amount(1)),
        Transaction(date(2019, 2, 5), 'ABC', 0),
        Transaction(date(2019, 3, 1), 'DEF', 10, amount=Amount(1))
    ]

    records = remove_redundant_journal_transactions(records)

    assert len(records) == 3
