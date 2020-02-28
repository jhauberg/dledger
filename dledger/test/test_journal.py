import locale

from datetime import date

from dledger.journal import (
    Transaction, Amount,
    read, remove_redundant_journal_transactions
)
from dledger.localeutil import trysetlocale
from dledger.formatutil import decimalplaces


def test_decimal_places():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    assert decimalplaces('123') == 0
    assert decimalplaces('123.4') == 1
    assert decimalplaces('123.45') == 2
    assert decimalplaces('123.456') == 3
    assert decimalplaces('12.3456') == 4
    assert decimalplaces('12.34560') == 5
    assert decimalplaces('0.77') == 2

    assert decimalplaces(123) == 0
    assert decimalplaces(123.4) == 1
    assert decimalplaces(123.45) == 2
    assert decimalplaces(123.456) == 3
    assert decimalplaces(12.3456) == 4
    # note that we won't keep the trailing zero here
    assert decimalplaces(12.34560) == 4
    assert decimalplaces(0.77) == 2

    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    assert decimalplaces('123,4') == 1
    assert decimalplaces('123,45') == 2
    assert decimalplaces('123,456') == 3
    assert decimalplaces('12,3456') == 4

    assert decimalplaces(123) == 0
    assert decimalplaces(123.4) == 1
    assert decimalplaces(123.45) == 2
    assert decimalplaces(123.456) == 3
    assert decimalplaces(12.3456) == 4
    # note that we won't keep the trailing zero here
    assert decimalplaces(12.34560) == 4
    assert decimalplaces(0.77) == 2


def test_simple_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/simple.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))

    records = read('../example/simple-condensed.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))


def test_ordering():
    records = [
        Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100)),
        Transaction(date(2019, 2, 1), 'ABC', 10, Amount(200)),
        Transaction(date(2019, 3, 1), 'ABC', 10, Amount(150))
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100))
    assert records[1] == Transaction(date(2019, 2, 1), 'ABC', 10, Amount(200))
    assert records[2] == Transaction(date(2019, 3, 1), 'ABC', 10, Amount(150))

    records = [
        Transaction(date(2019, 3, 1), 'ABC', 10, Amount(150)),
        Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100)),
        Transaction(date(2019, 2, 1), 'ABC', 10, Amount(200)),
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100))
    assert records[1] == Transaction(date(2019, 2, 1), 'ABC', 10, Amount(200))
    assert records[2] == Transaction(date(2019, 3, 1), 'ABC', 10, Amount(150))

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100)),
        Transaction(date(2019, 1, 1), 'ABC', 20),
        Transaction(date(2019, 2, 1), 'ABC', 20, Amount(200)),
        Transaction(date(2019, 3, 1), 'ABC', 20, Amount(150)),
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100))
    assert records[1] == Transaction(date(2019, 1, 1), 'ABC', 20)
    assert records[2] == Transaction(date(2019, 2, 1), 'ABC', 20, Amount(200))
    assert records[3] == Transaction(date(2019, 3, 1), 'ABC', 20, Amount(150))

    records = [
        Transaction(date(2019, 1, 1), 'ABC', 20),
        Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100)),
        Transaction(date(2019, 2, 1), 'ABC', 20, Amount(200)),
        Transaction(date(2019, 3, 1), 'ABC', 20, Amount(150)),
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), 'ABC', 10, Amount(100))
    assert records[1] == Transaction(date(2019, 1, 1), 'ABC', 20)
    assert records[2] == Transaction(date(2019, 2, 1), 'ABC', 20, Amount(200))
    assert records[3] == Transaction(date(2019, 3, 1), 'ABC', 20, Amount(150))


def test_ordering_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/ordering.journal', kind='journal')

    assert len(records) == 5
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 110,
                                     amount=Amount(84.7, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 120,
                                     amount=Amount(92.4, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[4] == Transaction(date(2019, 11, 14), 'AAPL', 0)


def test_positions_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/positions.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     amount=Amount(92.4, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 140,
                                     amount=Amount(107.8, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))

    records = read('../example/positions-condensed.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     amount=Amount(92.4, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 140,
                                     amount=Amount(107.8, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))


def test_position_inference_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/positioninference.journal', kind='journal')

    assert len(records) == 3
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     ex_date=date(2019, 5, 10))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     is_preliminary=True)


def test_fractional_positions_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/fractionalpositions.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 10.6,
                                     amount=Amount(7.738, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 10.6,
                                     amount=Amount(8.162, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 11.3,
                                     amount=Amount(8.701, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 21.3,
                                     amount=Amount(16.401, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))


def test_dividends_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/dividends.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))


def test_nativedividends_journal():
    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    records = read('../example/nativedividends.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(490.33, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(517.19, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(517.19, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(517.19, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'))


def test_strategic_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/strategic.journal', kind='journal')

    assert len(records) == 6
    assert records[0] == Transaction(date(2019, 1, 20), 'ABC', 10,
                                     amount=Amount(1, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.1, places=1, symbol='$', fmt='$ %s'))
    assert records[1] == Transaction(date(2019, 4, 20), 'ABC', 10,
                                     amount=Amount(2, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.2, places=1, symbol='$', fmt='$ %s'))
    assert records[2] == Transaction(date(2019, 7, 20), 'ABC', 10,
                                     amount=Amount(2, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.2, places=1, symbol='$', fmt='$ %s'))
    assert records[3] == Transaction(date(2019, 10, 20), 'ABC', 10,
                                     amount=Amount(2, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.2, places=1, symbol='$', fmt='$ %s'))
    assert records[4] == Transaction(date(2020, 1, 19), 'ABC', 0)
    assert records[5] == Transaction(date(2020, 2, 1), 'ABC', 10)


def test_extended_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    records = read('../example/extendingrecords.journal', kind='journal')

    assert len(records) == 4
    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=date(2019, 2, 14),
                                     ex_date=date(2019, 2, 8))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=None,
                                     ex_date=date(2019, 5, 10))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=date(2019, 8, 15),
                                     ex_date=None)
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=date(2019, 11, 14),
                                     ex_date=date(2019, 11, 7))


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
