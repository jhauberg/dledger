import os

from datetime import date

from dledger.journal import (
    Transaction,
    EntryAttributes,
    Amount,
    Distribution,
    ParseError,
    POSITION_SET,
    POSITION_ADD,
    POSITION_SUB,
    POSITION_SPLIT,
    POSITION_SPLIT_WHOLE,
    read,
    parse_amount,
    write,
)
from dledger.projection import (
    GeneratedAmount,
    scheduled_transactions,
)
from dledger.convert import removing_redundancies, with_estimates
from dledger.localeutil import (
    tempconv,
    DECIMAL_POINT_COMMA,
    DECIMAL_POINT_PERIOD,
)
from dledger.formatutil import decimalplaces


def test_decimal_places():
    with tempconv(DECIMAL_POINT_PERIOD):
        assert decimalplaces("123") == 0
        assert decimalplaces("123.4") == 1
        assert decimalplaces("123.45") == 2
        assert decimalplaces("123.456") == 3
        assert decimalplaces("12.3456") == 4
        assert decimalplaces("12.34560") == 5
        assert decimalplaces("0.77") == 2
        assert decimalplaces("1.0") == 0

        assert decimalplaces(123) == 0
        assert decimalplaces(123.4) == 1
        assert decimalplaces(123.45) == 2
        assert decimalplaces(123.456) == 3
        assert decimalplaces(12.3456) == 4
        # note that we won't keep the trailing zero here
        assert decimalplaces(12.34560) == 4
        assert decimalplaces(0.77) == 2
        assert decimalplaces(1.0) == 0

    with tempconv(DECIMAL_POINT_COMMA):
        assert decimalplaces("123") == 0
        assert decimalplaces("123,4") == 1
        assert decimalplaces("123,45") == 2
        assert decimalplaces("123,456") == 3
        assert decimalplaces("12,3456") == 4
        assert decimalplaces("1,0") == 0

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
    loc = ("", 0)

    assert parse_amount("$", location=loc) == Amount(
        0, places=0, symbol="$", fmt="%s $"
    )
    assert parse_amount("$10", location=loc) == Amount(
        10, places=0, symbol="$", fmt="$%s"
    )
    assert parse_amount("$ 10", location=loc) == Amount(
        10, places=0, symbol="$", fmt="$ %s"
    )
    assert parse_amount(" $ 10 ", location=loc) == Amount(
        10, places=0, symbol="$", fmt="$ %s"
    )
    assert parse_amount("$  10", location=loc) == Amount(
        10, places=0, symbol="$", fmt="$ %s"
    )
    assert parse_amount("10 kr", location=loc) == Amount(
        10, places=0, symbol="kr", fmt="%s kr"
    )
    assert parse_amount("10   kr", location=loc) == Amount(
        10, places=0, symbol="kr", fmt="%s kr"
    )
    assert parse_amount("10 danske kroner", location=loc) == Amount(
        10, places=0, symbol="danske kroner", fmt="%s danske kroner"
    )
    assert parse_amount("10 danske  kroner", location=loc) == Amount(
        10, places=0, symbol="danske  kroner", fmt="%s danske  kroner"
    )

    with tempconv(DECIMAL_POINT_PERIOD):
        assert parse_amount("$ 0.50", location=loc) == Amount(
            0.5, places=2, symbol="$", fmt="$ %s"
        )
        assert parse_amount("0.50 kr", location=loc) == Amount(
            0.5, places=2, symbol="kr", fmt="%s kr"
        )
        assert parse_amount("0.00 kr", location=loc) == Amount(
            0, places=2, symbol="kr", fmt="%s kr"
        )
        assert parse_amount("$ .50", location=loc) == Amount(
            0.5, places=2, symbol="$", fmt="$ %s"
        )
        assert parse_amount(".50 kr", location=loc) == Amount(
            0.5, places=2, symbol="kr", fmt="%s kr"
        )

    with tempconv(DECIMAL_POINT_COMMA):
        assert parse_amount("$ 0,50", location=loc) == Amount(
            0.5, places=2, symbol="$", fmt="$ %s"
        )
        assert parse_amount("0,50 kr", location=loc) == Amount(
            0.5, places=2, symbol="kr", fmt="%s kr"
        )
        assert parse_amount("0,00 kr", location=loc) == Amount(
            0, places=2, symbol="kr", fmt="%s kr"
        )

        assert parse_amount("$ ,50", location=loc) == Amount(
            0.5, places=2, symbol="$", fmt="$ %s"
        )
        assert parse_amount(",50 kr", location=loc) == Amount(
            0.5, places=2, symbol="kr", fmt="%s kr"
        )


def test_empty_journal():
    path = "subjects/empty.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 0


def test_single_journal():
    path = "subjects/single.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 1

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(100, POSITION_SET)),
    )


def test_simple_journal():
    path = "../example/simple.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 6), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 9), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 12), positioning=(None, POSITION_SET)
        ),
    )

    path = "../example/simple-condensed.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 9), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 10), positioning=(None, POSITION_SET)
        ),
    )


def test_ordering():
    records = [
        Transaction(date(2019, 1, 1), "ABC", 10, Amount(100)),
        Transaction(date(2019, 2, 1), "ABC", 10, Amount(200)),
        Transaction(date(2019, 3, 1), "ABC", 10, Amount(150)),
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), "ABC", 10, Amount(100))
    assert records[1] == Transaction(date(2019, 2, 1), "ABC", 10, Amount(200))
    assert records[2] == Transaction(date(2019, 3, 1), "ABC", 10, Amount(150))

    records = [
        Transaction(date(2019, 3, 1), "ABC", 10, Amount(150)),
        Transaction(date(2019, 1, 1), "ABC", 10, Amount(100)),
        Transaction(date(2019, 2, 1), "ABC", 10, Amount(200)),
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), "ABC", 10, Amount(100))
    assert records[1] == Transaction(date(2019, 2, 1), "ABC", 10, Amount(200))
    assert records[2] == Transaction(date(2019, 3, 1), "ABC", 10, Amount(150))

    records = [
        Transaction(date(2019, 1, 1), "ABC", 10, Amount(100)),
        Transaction(date(2019, 1, 1), "ABC", 20),
        Transaction(date(2019, 2, 1), "ABC", 20, Amount(200)),
        Transaction(date(2019, 3, 1), "ABC", 20, Amount(150)),
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), "ABC", 10, Amount(100))
    assert records[1] == Transaction(date(2019, 1, 1), "ABC", 20)
    assert records[2] == Transaction(date(2019, 2, 1), "ABC", 20, Amount(200))
    assert records[3] == Transaction(date(2019, 3, 1), "ABC", 20, Amount(150))

    records = [
        Transaction(date(2019, 1, 1), "ABC", 20),
        Transaction(date(2019, 1, 1), "ABC", 10, Amount(100)),
        Transaction(date(2019, 2, 1), "ABC", 20, Amount(200)),
        Transaction(date(2019, 3, 1), "ABC", 20, Amount(150)),
    ]

    records = sorted(records)

    assert records[0] == Transaction(date(2019, 1, 1), "ABC", 10, Amount(100))
    assert records[1] == Transaction(date(2019, 1, 1), "ABC", 20)
    assert records[2] == Transaction(date(2019, 2, 1), "ABC", 20, Amount(200))
    assert records[3] == Transaction(date(2019, 3, 1), "ABC", 20, Amount(150))


def test_ordering_journal():
    path = "subjects/ordering.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 7

    records = removing_redundancies(records)

    assert len(records) == 5

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 21), positioning=(100, POSITION_SET)
        ),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 16), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        110,
        amount=Amount(84.7, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 13), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        120,
        amount=Amount(92.4, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 5), positioning=(None, POSITION_SET)
        ),
    )
    assert records[4] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        0,
        entry_attr=EntryAttributes(location=(path, 8), positioning=(0, POSITION_SET)),
    )


def test_positions_journal():
    path = "subjects/positions.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 5

    assert records[2] == Transaction(
        date(2019, 6, 4),
        "AAPL",
        120,
        entry_attr=EntryAttributes(location=(path, 11), positioning=(20, POSITION_ADD)),
    )

    records = removing_redundancies(records)

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 5), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        120,
        amount=Amount(92.4, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 13), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        140,
        amount=Amount(107.8, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 16), positioning=(140, POSITION_SET)
        ),
    )

    path = "subjects/positions-condensed.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 5

    records = removing_redundancies(records)

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 5), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 6), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        120,
        amount=Amount(92.4, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        140,
        amount=Amount(107.8, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 9), positioning=(140, POSITION_SET)),
    )


def test_positions_format_journal():
    path = "subjects/positions-oddformat.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 6

    records = removing_redundancies(records)

    assert len(records) == 5

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 5), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 9), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        120,
        amount=Amount(92.4, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 16), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        140,
        amount=Amount(107.8, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 19), positioning=(140, POSITION_SET)
        ),
    )
    assert records[4] == Transaction(
        date(2019, 12, 1),
        "AAPL",
        140,
        kind=Distribution.SPECIAL,
        amount=Amount(107.8, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 25), positioning=(None, POSITION_SET)
        ),
    )


def test_position_inference_journal():
    path = "subjects/positioninference.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    records = removing_redundancies(records)

    assert len(records) == 3

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 5), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        ex_date=date(2019, 5, 10),
        entry_attr=EntryAttributes(
            location=(path, 13), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        120,
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 21), positioning=(None, POSITION_SET), is_preliminary=True
        ),
    )


def test_fractional_positions_journal():
    path = "subjects/fractionalpositions.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 5

    records = removing_redundancies(records)

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        10.6,
        amount=Amount(7.738, places=3, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 5), positioning=(10.6, POSITION_SET)
        ),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        10.6,
        amount=Amount(8.162, places=3, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        11.3,
        amount=Amount(8.701, places=3, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 13), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        21.3,
        amount=Amount(16.401, places=3, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 16), positioning=(21.3, POSITION_SET)
        ),
    )


def test_dividends_journal():
    path = "../example/dividends.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 5), positioning=(None, POSITION_SET)
        ),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 11), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 14), positioning=(None, POSITION_SET)
        ),
    )


def test_ambiguous_position_journal():
    path = "subjects/positionambiguity.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 2

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 5), positioning=(100, POSITION_SET)),
    )

    assert records[1] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        50,
        amount=Amount(36.5, places=1, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 8), positioning=(50, POSITION_SET)),
    )


def test_nativedividends_journal():
    path = "subjects/nativedividends.journal"

    with tempconv(DECIMAL_POINT_COMMA):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(490.33, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 5), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(517.19, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(517.19, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 11), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(517.19, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 14), positioning=(None, POSITION_SET)
        ),
    )


def test_strategic_journal():
    path = "subjects/strategic.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 6

    assert records[0] == Transaction(
        date(2019, 1, 20),
        "ABC",
        10,
        amount=Amount(1, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.1, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 7), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 4, 20),
        "ABC",
        10,
        amount=Amount(2, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.2, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 10), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 7, 20),
        "ABC",
        10,
        amount=Amount(2, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.2, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 13), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 10, 20),
        "ABC",
        10,
        amount=Amount(2, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.2, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 16), positioning=(None, POSITION_SET)
        ),
    )
    assert records[4].ispositional
    assert records[4] == Transaction(
        date(2020, 1, 19),
        "ABC",
        0,
        entry_attr=EntryAttributes(location=(path, 19), positioning=(0, POSITION_SET)),
    )
    assert records[5] == Transaction(
        date(2020, 2, 1),
        "ABC",
        10,
        entry_attr=EntryAttributes(location=(path, 24), positioning=(10, POSITION_SET)),
    )


def test_extended_journal():
    path = "subjects/extendingrecords.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        payout_date=date(2019, 2, 14),
        ex_date=date(2019, 2, 8),
        entry_attr=EntryAttributes(location=(path, 5), positioning=(100, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        payout_date=None,
        ex_date=date(2019, 5, 10),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        payout_date=date(2019, 8, 15),
        ex_date=None,
        entry_attr=EntryAttributes(
            location=(path, 11), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        payout_date=date(2019, 11, 14),
        ex_date=date(2019, 11, 7),
        entry_attr=EntryAttributes(
            location=(path, 14), positioning=(None, POSITION_SET)
        ),
    )


def test_preliminary_expected_currency():
    path = "subjects/preliminaryrecords.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0].entry_attr.is_preliminary is False
    assert records[0].amount is not None
    assert records[1].entry_attr.is_preliminary is True
    assert records[1].amount is None
    assert records[2].entry_attr.is_preliminary is True
    assert records[3].entry_attr.is_preliminary is True

    transactions = with_estimates(records)

    assert transactions[1].amount == GeneratedAmount(
        10, places=None, symbol="$", fmt="$ %s"
    )
    assert transactions[2].amount == GeneratedAmount(
        100, places=None, symbol="DKK", fmt="%s DKK"
    )
    assert transactions[3].amount == GeneratedAmount(
        134.4, places=None, symbol="DKK", fmt="%s DKK"
    )


def test_stable_sort():
    path = "subjects/sorting.journal"

    records = read(path, kind="journal")

    assert len(records) == 8

    for _ in range(5):
        records.sort()

        assert records[0].ticker == "A"
        assert records[1].ticker == "B"
        assert records[2].ticker == "A"
        assert records[3].ticker == "B"
        assert records[4].ticker == "A"
        assert records[5].ticker == "B"
        assert records[6].ticker == "A"
        assert records[7].ticker == "B"

    records.extend(scheduled_transactions(records, since=date(2019, 12, 15)))

    assert len(records) == 16

    for _ in range(5):
        records.sort()

        assert records[0].ticker == "A"
        assert records[1].ticker == "B"
        assert records[2].ticker == "A"
        assert records[3].ticker == "B"
        assert records[4].ticker == "A"
        assert records[5].ticker == "B"
        assert records[6].ticker == "A"
        assert records[7].ticker == "B"

        assert records[8].ticker == "A"
        assert records[9].ticker == "B"
        assert records[10].ticker == "A"
        assert records[11].ticker == "B"
        assert records[12].ticker == "A"
        assert records[13].ticker == "B"
        assert records[14].ticker == "A"
        assert records[15].ticker == "B"


def test_include_journal():
    path = "../example/include.journal"

    if os.name == "nt":
        included_resolved_path = "..\\example\\simple.journal"
    else:
        included_resolved_path = "../example/simple.journal"

    records = read(path, kind="journal")

    assert len(records) == 5

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 3), positioning=(100, POSITION_SET)
        ),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 6), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 9), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 12), positioning=(None, POSITION_SET)
        ),
    )
    assert records[4] == Transaction(
        date(2020, 2, 13),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 5), positioning=(None, POSITION_SET)
        ),
    )


def test_include_journal_quoted():
    path = "subjects/include_quoted_path.journal"

    if os.name == "nt":
        included_resolved_path = "subjects\\..\\..\\example\\simple.journal"
    else:
        included_resolved_path = "subjects/../../example/simple.journal"

    records = read(path, kind="journal")

    assert len(records) == 5

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 3), positioning=(100, POSITION_SET)
        ),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 6), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 9), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 12), positioning=(None, POSITION_SET)
        ),
    )
    assert records[4] == Transaction(
        date(2020, 2, 13),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 5), positioning=(None, POSITION_SET)
        ),
    )


def test_include_journal_out_of_order():
    path = "subjects/include_out_of_order.journal"

    if os.name == "nt":
        included_resolved_path = "subjects\\..\\..\\example\\simple.journal"
    else:
        included_resolved_path = "subjects/../../example/simple.journal"

    records = read(path, kind="journal")

    assert len(records) == 7

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 3), positioning=(100, POSITION_SET)
        ),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 6), positioning=(None, POSITION_SET)
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 9), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path, 12), positioning=(None, POSITION_SET)
        ),
    )
    assert records[4] == Transaction(
        date(2020, 2, 13),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 3), positioning=(None, POSITION_SET)
        ),
    )
    assert records[5] == Transaction(
        date(2020, 5, 15),
        "AAPL",
        100,
        amount=Amount(82, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.82, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(None, POSITION_SET)
        ),
    )
    assert records[6] == Transaction(
        date(2020, 8, 14),
        "AAPL",
        100,
        amount=Amount(82, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.82, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 11), positioning=(None, POSITION_SET)
        ),
    )


def test_implicit_currency():
    path = "subjects/implicitcurrency.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError:
        assert True
    else:
        assert False


def test_write():
    existing_path = "../example/simple.journal"
    existing_records = read(existing_path, kind="journal")

    import os
    import tempfile

    fd, output_path = tempfile.mkstemp()
    with os.fdopen(fd, "w", newline="") as tmp:
        write(existing_records, file=tmp)
    records = read(output_path, kind="journal")
    os.remove(output_path)
    # todo: this simple check won't fly due to entry attributes
    # assert records == existing_records
    assert len(records) == len(existing_records)
    assert records[0].ticker == existing_records[0].ticker
    assert records[0].amount == existing_records[0].amount
    assert records[0].position == existing_records[0].position
    assert records[0].dividend == existing_records[0].dividend
    assert records[0].kind == existing_records[0].kind
    assert records[0].entry_date == existing_records[0].entry_date


def test_integrity():
    # test whether an input journal produces expected output;
    # effectively mimicking the print command
    # it is expected that the output is "lossy"; i.e. that
    # _all_ comments are omitted, and some records _may_ be if deemed redundant
    # similarly, it is expected that output conforms to a consistent style
    # that do not necessarily match that of the input journal
    existing_path = "subjects/integrity-input.journal"
    existing_records = removing_redundancies(
        read(existing_path, kind="journal")
    )

    import os
    import tempfile

    fd, output_path = tempfile.mkstemp()
    with os.fdopen(fd, "w", newline="") as tmp:
        with tempconv(DECIMAL_POINT_PERIOD):
            write(existing_records, file=tmp)
    records = read(output_path, kind="journal")
    assert len(records) == 5
    with open(output_path, "r") as f:
        output = f.read()
    with open("subjects/integrity-output.journal", "r") as f:
        expected_output = f.read()
    assert output == expected_output
    os.remove(output_path)


def test_nordnet_import():
    path = "subjects/nordnet_transactions.csv"

    with tempconv(DECIMAL_POINT_COMMA):
        records = read(path, kind="nordnet")

    assert len(records) == 3

    assert records[0] == Transaction(
        entry_date=date(2021, 3, 4),
        payout_date=date(2021, 3, 4),
        ex_date=date(2021, 3, 2),
        ticker="ORSTED",
        position=10,
        amount=Amount(115, places=0, symbol="DKK", fmt="%s DKK"),
        dividend=Amount(11.5, places=1, symbol="DKK", fmt="%s DKK"),
        entry_attr=EntryAttributes(location=(path, 2), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        entry_date=date(2021, 2, 17),
        payout_date=date(2021, 2, 16),
        ex_date=date(2021, 1, 29),
        ticker="O",
        position=10,
        amount=Amount(14.45, places=2, symbol="DKK", fmt="%s DKK"),
        dividend=Amount(0.2345, places=4, symbol="USD", fmt="%s USD"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[2] == Transaction(
        entry_date=date(2021, 2, 12),
        payout_date=date(2021, 2, 11),
        ex_date=date(2021, 2, 5),
        ticker="AAPL",
        position=10,
        amount=Amount(12.66, places=2, symbol="DKK", fmt="%s DKK"),
        dividend=Amount(0.205, places=3, symbol="USD", fmt="%s USD"),
        entry_attr=EntryAttributes(location=(path, 4), positioning=(10, POSITION_SET)),
    )


def test_nordnet_import_ambiguity():
    path = "subjects/nordnet_transactions_ambiguous_dividend.csv"

    try:
        # record has both "0,234" and "0.2345" dividend component
        with tempconv(DECIMAL_POINT_COMMA):
            _ = read(path, kind="nordnet")
    except ParseError:
        assert True
    else:
        assert False


def test_splits_whole():
    path = "../example/split.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2021, 1, 1),
        "ABC",
        10,
        amount=Amount(1, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.1, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2021, 2, 1),
        "ABC",
        20,
        entry_attr=EntryAttributes(location=(path, 6), positioning=(10, POSITION_ADD)),
    )
    assert records[2] == Transaction(
        date(2021, 2, 10),
        "ABC",
        40,
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(2, POSITION_SPLIT_WHOLE)
        ),
    )
    assert records[3] == Transaction(
        date(2021, 4, 1),
        "ABC",
        40,
        amount=Amount(2, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.05, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 10), positioning=(None, POSITION_SET)
        ),
    )


def test_splits_fractional():
    path = "subjects/split_fractional.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 7

    assert records[0] == Transaction(
        date(2021, 1, 1),
        "ABC",
        10,
        amount=Amount(1, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.1, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2021, 2, 1),
        "ABC",
        20,
        entry_attr=EntryAttributes(location=(path, 6), positioning=(10, POSITION_ADD)),
    )
    assert records[2] == Transaction(
        date(2021, 2, 10),
        "ABC",
        40,
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(2, POSITION_SPLIT_WHOLE)
        ),
    )
    assert records[3] == Transaction(
        date(2021, 2, 11),
        "ABC",
        39,
        entry_attr=EntryAttributes(location=(path, 10), positioning=(1, POSITION_SUB)),
    )
    assert records[4] == Transaction(
        date(2021, 4, 1),
        "ABC",
        39,
        amount=Amount(1.95, places=2, symbol="$", fmt="$ %s"),
        dividend=Amount(0.05, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 12), positioning=(None, POSITION_SET)
        ),
    )
    assert records[5] == Transaction(
        date(2021, 5, 10),
        "ABC",
        58.5,
        entry_attr=EntryAttributes(
            location=(path, 15), positioning=(1.5, POSITION_SPLIT)
        ),
    )
    assert records[6] == Transaction(
        date(2021, 7, 1),
        "ABC",
        58.5,
        amount=Amount(1.95, places=2, symbol="$", fmt="$ %s"),
        dividend=Amount(0.0333, places=4, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 17), positioning=(None, POSITION_SET)
        ),
    )


def test_reverse_split():
    path = "subjects/split_reverse.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = read(path, kind="journal")

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2021, 1, 1),
        "ABC",
        10,
        amount=Amount(1, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.1, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2021, 2, 1),
        "ABC",
        20,
        entry_attr=EntryAttributes(location=(path, 6), positioning=(10, POSITION_ADD)),
    )
    assert records[2] == Transaction(
        date(2021, 2, 10),
        "ABC",
        10,
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(0.5, POSITION_SPLIT_WHOLE)
        ),
    )
    assert records[3] == Transaction(
        date(2021, 4, 1),
        "ABC",
        10,
        amount=Amount(2, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.2, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 10), positioning=(None, POSITION_SET)
        ),
    )
