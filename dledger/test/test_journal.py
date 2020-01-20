import locale

from datetime import date

from dledger.journal import Transaction, Amount, read
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
