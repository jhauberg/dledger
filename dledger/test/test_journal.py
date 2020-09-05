import locale

from datetime import date

from dledger.journal import (
    Transaction, EntryAttributes, Amount, Distribution,
    POSITION_SET, POSITION_ADD, POSITION_SUB,
    read, remove_redundant_journal_transactions, parse_amount
)
from dledger.projection import GeneratedAmount, scheduled_transactions, convert_estimates
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
    assert decimalplaces('1.0') == 0

    assert decimalplaces(123) == 0
    assert decimalplaces(123.4) == 1
    assert decimalplaces(123.45) == 2
    assert decimalplaces(123.456) == 3
    assert decimalplaces(12.3456) == 4
    # note that we won't keep the trailing zero here
    assert decimalplaces(12.34560) == 4
    assert decimalplaces(0.77) == 2
    assert decimalplaces(1.0) == 0

    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    assert decimalplaces('123,4') == 1
    assert decimalplaces('123,45') == 2
    assert decimalplaces('123,456') == 3
    assert decimalplaces('12,3456') == 4
    assert decimalplaces('1,0') == 0

    assert decimalplaces(123) == 0
    assert decimalplaces(123.4) == 1
    assert decimalplaces(123.45) == 2
    assert decimalplaces(123.456) == 3
    assert decimalplaces(12.3456) == 4
    # note that we won't keep the trailing zero here
    assert decimalplaces(12.34560) == 4
    assert decimalplaces(0.77) == 2
    assert decimalplaces(1.0) == 0


def test_parse_amount():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    loc = ('', 0)

    assert parse_amount('$', location=loc) == Amount(0, places=0, symbol='$', fmt='%s $')

    assert parse_amount('$10', location=loc) == Amount(10, places=0, symbol='$', fmt='$%s')
    assert parse_amount('$ 10', location=loc) == Amount(10, places=0, symbol='$', fmt='$ %s')
    assert parse_amount(' $ 10 ', location=loc) == Amount(10, places=0, symbol='$', fmt='$ %s')
    assert parse_amount('$  10', location=loc) == Amount(10, places=0, symbol='$', fmt='$ %s')
    assert parse_amount('10 kr', location=loc) == Amount(10, places=0, symbol='kr', fmt='%s kr')
    assert parse_amount('10   kr', location=loc) == Amount(10, places=0, symbol='kr', fmt='%s kr')

    assert parse_amount('$ 0.50', location=loc) == Amount(0.5, places=2, symbol='$', fmt='$ %s')
    assert parse_amount('0.50 kr', location=loc) == Amount(0.5, places=2, symbol='kr', fmt='%s kr')
    assert parse_amount('0.00 kr', location=loc) == Amount(0, places=2, symbol='kr', fmt='%s kr')

    assert parse_amount('$ .50', location=loc) == Amount(0.5, places=2, symbol='$', fmt='$ %s')
    assert parse_amount('.50 kr', location=loc) == Amount(0.5, places=2, symbol='kr', fmt='%s kr')

    assert parse_amount('10 danske kroner', location=loc) == Amount(10, places=0,
                                                                    symbol='danske kroner',
                                                                    fmt='%s danske kroner')
    assert parse_amount('10 danske  kroner', location=loc) == Amount(10, places=0,
                                                                     symbol='danske  kroner',
                                                                     fmt='%s danske  kroner')

    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    assert parse_amount('$ 0,50', location=loc) == Amount(0.5, places=2, symbol='$', fmt='$ %s')
    assert parse_amount('0,50 kr', location=loc) == Amount(0.5, places=2, symbol='kr', fmt='%s kr')
    assert parse_amount('0,00 kr', location=loc) == Amount(0, places=2, symbol='kr', fmt='%s kr')

    assert parse_amount('$ ,50', location=loc) == Amount(0.5, places=2, symbol='$', fmt='$ %s')
    assert parse_amount(',50 kr', location=loc) == Amount(0.5, places=2, symbol='kr', fmt='%s kr')


def test_empty_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/empty.journal'

    records = read(path, kind='journal')

    assert len(records) == 0


def test_single_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/single.journal'

    records = read(path, kind='journal')

    assert len(records) == 1

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 3),
                                                                positioning=(100, POSITION_SET)))


def test_simple_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/simple.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 3),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 6),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 9),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 12),
                                                                positioning=(None, POSITION_SET)))

    path = '../example/simple-condensed.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 3),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 9),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 10),
                                                                positioning=(None, POSITION_SET)))


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

    path = '../example/ordering.journal'

    records = read(path, kind='journal')

    assert len(records) == 5

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 21),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 16),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 110,
                                     amount=Amount(84.7, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 13),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 120,
                                     amount=Amount(92.4, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(None, POSITION_SET)))
    assert records[4] == Transaction(date(2019, 11, 14), 'AAPL', 0,
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(0, POSITION_SET)))


def test_positions_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/positions.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     amount=Amount(92.4, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 13),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 140,
                                     amount=Amount(107.8, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 16),
                                                                positioning=(140, POSITION_SET)))

    path = '../example/positions-condensed.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 6),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     amount=Amount(92.4, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 140,
                                     amount=Amount(107.8, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 9),
                                                                positioning=(140, POSITION_SET)))


def test_positions_format_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/positions-oddformat.journal'

    records = read(path, kind='journal')

    assert len(records) == 5

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 9),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     amount=Amount(92.4, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 16),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 140,
                                     amount=Amount(107.8, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 19),
                                                                positioning=(140, POSITION_SET)))
    assert records[4] == Transaction(date(2019, 12, 1), 'AAPL', 140,
                                     kind=Distribution.SPECIAL,
                                     amount=Amount(107.8, places=1, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 25),
                                                                positioning=(None, POSITION_SET)))


def test_position_inference_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/positioninference.journal'

    records = read(path, kind='journal')

    assert len(records) == 3

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     ex_date=date(2019, 5, 10),
                                     entry_attr=EntryAttributes(location=(path, 13),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 120,
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 21),
                                                                positioning=(None, POSITION_SET),
                                                                is_preliminary=True))


def test_fractional_positions_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/fractionalpositions.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 10.6,
                                     amount=Amount(7.738, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(10.6, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 10.6,
                                     amount=Amount(8.162, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 11.3,
                                     amount=Amount(8.701, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 13),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 21.3,
                                     amount=Amount(16.401, places=3, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 16),
                                                                positioning=(21.3, POSITION_SET)))


def test_dividends_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/dividends.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(None, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 11),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 14),
                                                                positioning=(None, POSITION_SET)))


def test_nativedividends_journal():
    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    path = '../example/nativedividends.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(490.33, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(517.19, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(517.19, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 11),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(517.19, places=2, symbol='kr', fmt='%s kr'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 14),
                                                                positioning=(None, POSITION_SET)))


def test_strategic_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/strategic.journal'

    records = read(path, kind='journal')

    assert len(records) == 6

    assert records[0] == Transaction(date(2019, 1, 20), 'ABC', 10,
                                     amount=Amount(1, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.1, places=1, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 7),
                                                                positioning=(10, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 4, 20), 'ABC', 10,
                                     amount=Amount(2, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.2, places=1, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 10),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 7, 20), 'ABC', 10,
                                     amount=Amount(2, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.2, places=1, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 13),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 10, 20), 'ABC', 10,
                                     amount=Amount(2, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.2, places=1, symbol='$', fmt='$ %s'),
                                     entry_attr=EntryAttributes(location=(path, 16),
                                                                positioning=(None, POSITION_SET)))
    assert records[4].ispositional
    assert records[4] == Transaction(date(2020, 1, 19), 'ABC', 0,
                                     entry_attr=EntryAttributes(location=(path, 19),
                                                                positioning=(0, POSITION_SET)))
    assert records[5] == Transaction(date(2020, 2, 1), 'ABC', 10,
                                     entry_attr=EntryAttributes(location=(path, 28),
                                                                positioning=(10, POSITION_SET)))


def test_extended_journal():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/extendingrecords.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0] == Transaction(date(2019, 2, 14), 'AAPL', 100,
                                     amount=Amount(73, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.73, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=date(2019, 2, 14),
                                     ex_date=date(2019, 2, 8),
                                     entry_attr=EntryAttributes(location=(path, 5),
                                                                positioning=(100, POSITION_SET)))
    assert records[1] == Transaction(date(2019, 5, 16), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=None,
                                     ex_date=date(2019, 5, 10),
                                     entry_attr=EntryAttributes(location=(path, 8),
                                                                positioning=(None, POSITION_SET)))
    assert records[2] == Transaction(date(2019, 8, 15), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=date(2019, 8, 15),
                                     ex_date=None,
                                     entry_attr=EntryAttributes(location=(path, 11),
                                                                positioning=(None, POSITION_SET)))
    assert records[3] == Transaction(date(2019, 11, 14), 'AAPL', 100,
                                     amount=Amount(77, places=0, symbol='$', fmt='$ %s'),
                                     dividend=Amount(0.77, places=2, symbol='$', fmt='$ %s'),
                                     payout_date=date(2019, 11, 14),
                                     ex_date=date(2019, 11, 7),
                                     entry_attr=EntryAttributes(location=(path, 14),
                                                                positioning=(None, POSITION_SET)))


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


def test_preliminary_expected_currency():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/preliminaryrecords.journal'

    records = read(path, kind='journal')

    assert len(records) == 4

    assert records[0].entry_attr.is_preliminary is False
    assert records[0].amount is not None
    assert records[1].entry_attr.is_preliminary is True
    assert records[1].amount is None
    assert records[2].entry_attr.is_preliminary is True
    assert records[3].entry_attr.is_preliminary is True

    transactions = convert_estimates(records)

    assert transactions[1].amount == GeneratedAmount(10, places=None, symbol='$', fmt='$ %s')
    assert transactions[2].amount == GeneratedAmount(100, places=None, symbol='DKK', fmt='%s DKK')
    assert transactions[3].amount == GeneratedAmount(134.4, places=None, symbol='DKK', fmt='%s DKK')


def test_stable_sort():
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    path = '../example/sorting.journal'

    records = read(path, kind='journal')

    assert len(records) == 8

    for _ in range(5):
        records.sort()

        assert records[0].ticker == 'A'
        assert records[1].ticker == 'B'
        assert records[2].ticker == 'A'
        assert records[3].ticker == 'B'
        assert records[4].ticker == 'A'
        assert records[5].ticker == 'B'
        assert records[6].ticker == 'A'
        assert records[7].ticker == 'B'

    records.extend(scheduled_transactions(records, since=date(2019, 12, 15)))

    assert len(records) == 16

    for _ in range(5):
        records.sort()

        assert records[0].ticker == 'A'
        assert records[1].ticker == 'B'
        assert records[2].ticker == 'A'
        assert records[3].ticker == 'B'
        assert records[4].ticker == 'A'
        assert records[5].ticker == 'B'
        assert records[6].ticker == 'A'
        assert records[7].ticker == 'B'

        assert records[8].ticker == 'A'
        assert records[9].ticker == 'B'
        assert records[10].ticker == 'A'
        assert records[11].ticker == 'B'
        assert records[12].ticker == 'A'
        assert records[13].ticker == 'B'
        assert records[14].ticker == 'A'
        assert records[15].ticker == 'B'
