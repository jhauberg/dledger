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
    has_identical_location,
)
from dledger.projection import (
    GeneratedAmount,
    scheduled_transactions,
)
from dledger.convert import (
    InferenceError,
    inferring_components,
    removing_redundancies,
    with_estimates,
)
from dledger.localeutil import (
    tempconv,
    DECIMAL_POINT_COMMA,
    DECIMAL_POINT_PERIOD,
)
from dledger.formatutil import decimalplaces, format_amount


def test_format_amount():
    assert format_amount(10) == "10.00"
    assert format_amount(10, trailing_zero=False) == "10"
    assert format_amount(10, trailing_zero=False, places=1) == "10"
    assert format_amount(10, trailing_zero=False, places=0) == "10"
    assert format_amount(10, trailing_zero=True, places=1) == "10.0"
    assert format_amount(10, trailing_zero=True, places=0) == "10"


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
    assert parse_amount("$") == Amount(0, places=0, symbol="$", fmt="%s $")
    assert parse_amount("$10") == Amount(10, places=0, symbol="$", fmt="$%s")
    assert parse_amount("$ 10") == Amount(10, places=0, symbol="$", fmt="$ %s")
    assert parse_amount(" $ 10 ") == Amount(10, places=0, symbol="$", fmt="$ %s")
    assert parse_amount("$  10") == Amount(10, places=0, symbol="$", fmt="$ %s")
    assert parse_amount("10 kr") == Amount(10, places=0, symbol="kr", fmt="%s kr")
    assert parse_amount("10   kr") == Amount(10, places=0, symbol="kr", fmt="%s kr")
    assert parse_amount("10 danske kroner") == Amount(
        10, places=0, symbol="danske kroner", fmt="%s danske kroner"
    )
    assert parse_amount("danske kroner 10") == Amount(
        10, places=0, symbol="danske kroner", fmt="danske kroner %s"
    )
    assert parse_amount("10 danske  kroner") == Amount(
        10, places=0, symbol="danske  kroner", fmt="%s danske  kroner"
    )

    with tempconv(DECIMAL_POINT_PERIOD):
        assert parse_amount("$ 0.50") == Amount(0.5, places=2, symbol="$", fmt="$ %s")
        assert parse_amount("0.50 kr") == Amount(
            0.5, places=2, symbol="kr", fmt="%s kr"
        )
        assert parse_amount("0.00 kr") == Amount(0, places=2, symbol="kr", fmt="%s kr")
        assert parse_amount("$ .50") == Amount(0.5, places=2, symbol="$", fmt="$ %s")
        assert parse_amount(".50 kr") == Amount(0.5, places=2, symbol="kr", fmt="%s kr")

    with tempconv(DECIMAL_POINT_COMMA):
        assert parse_amount("$ 0,50") == Amount(0.5, places=2, symbol="$", fmt="$ %s")
        assert parse_amount("0,50 kr") == Amount(
            0.5, places=2, symbol="kr", fmt="%s kr"
        )
        assert parse_amount("0,00 kr") == Amount(0, places=2, symbol="kr", fmt="%s kr")

        assert parse_amount("$ ,50") == Amount(0.5, places=2, symbol="$", fmt="$ %s")
        assert parse_amount(",50 kr") == Amount(0.5, places=2, symbol="kr", fmt="%s kr")

    try:
        parse_amount("10")
    except ValueError as e:
        assert "missing symbol definition" in str(e)
    else:
        assert False

    try:
        parse_amount("$ 10 $")
    except ValueError as e:
        assert "ambiguous symbol definition" in str(e)
    else:
        assert False

    try:
        parse_amount("$10 10")
    except ValueError as e:
        assert "invalid value" in str(e)
    else:
        assert False

    # note that this parses too, but potentially with a confusing result
    assert parse_amount("$ abc") == Amount(0, places=0, symbol="$ abc", fmt="%s $ abc")
    # this, however, does not parse
    try:
        parse_amount("$ .")
    except ValueError as e:
        assert "invalid value" in str(e)
    else:
        assert False


def test_nonexistant_journal():
    path = "subjects/does_not_exist.journal"

    try:
        _ = read(path, kind="journal")
    except ValueError:
        assert True
    else:
        assert False


def test_invalid_journal_type():
    path = "subjects/empty.journal"

    try:
        _ = read(path, kind="other")
    except ValueError:
        assert True
    else:
        assert False


def test_invalid_transaction_unknown_datestamp():
    path = "subjects/invalidtransaction/unknown_datestamp.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 3
        assert "unknown date format" in e.message
    else:
        assert False


def test_invalid_transaction_missing_ticker():
    path = "subjects/invalidtransaction/missing_ticker.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 3
        assert "invalid transaction" in e.message
    else:
        assert False


def test_invalid_transaction_empty_ticker():
    path = "subjects/invalidtransaction/empty_ticker.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 3
        assert "missing ticker" in e.message
    else:
        assert False


def test_invalid_transaction_missing_components():
    path = "subjects/invalidtransaction/missing_components.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 3
        assert "missing components" in e.message
    else:
        assert False


def test_invalid_transaction_unknown_position():
    path = "subjects/invalidtransaction/unknown_position.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 3
        assert "unknown position format" in e.message
    else:
        assert False


def test_recursive_include():
    path = "subjects/include_recursive.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 3
        assert "attempt to recursively include journal" in e.message
    else:
        assert False


def test_include_duplicate():
    path = "subjects/include_duplicate.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 4
        assert "attempt to include same journal twice" in e.message
    else:
        assert False


def test_include_duplicate_recursively():
    path = "subjects/include_duplicate_recursive.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 4
        assert "attempt to include same journal twice" in e.message
    else:
        assert False


def test_ambiguous_symbol():
    path = "subjects/ambiguous_symbol.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 4
        assert "ambiguous symbol definition" in e.message
    else:
        assert False


def test_empty_journal():
    path = "subjects/empty.journal"

    records = read(path, kind="journal")

    assert len(records) == 0


def test_single_journal():
    path = "subjects/single.journal"

    records = inferring_components(read(path, kind="journal"))

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

    records = inferring_components(read(path, kind="journal"))

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

    records = inferring_components(read(path, kind="journal"))

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

    assert records[0].entry_date == date(2019, 11, 14)
    assert records[1].entry_date == date(2019, 11, 14)
    assert records[2].entry_date == date(2019, 8, 15)
    assert records[3].entry_date == date(2019, 8, 15)
    assert records[4].entry_date == date(2019, 5, 16)
    assert records[5].entry_date == date(2019, 5, 16)
    assert records[6].entry_date == date(2019, 2, 14)

    with tempconv(DECIMAL_POINT_PERIOD):
        records = inferring_components(
            sorted(read(path, kind="journal"))
        )

    assert len(records) == 7

    assert records[0].entry_date == date(2019, 2, 14)
    assert records[1].entry_date == date(2019, 5, 16)
    assert records[2].entry_date == date(2019, 5, 16)
    assert records[3].entry_date == date(2019, 8, 15)
    assert records[4].entry_date == date(2019, 8, 15)
    assert records[5].entry_date == date(2019, 11, 14)
    assert records[6].entry_date == date(2019, 11, 14)

    records = removing_redundancies(records, since=date(2019, 12, 1))

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
        records = inferring_components(read(path, kind="journal"))

    assert len(records) == 5

    assert records[2] == Transaction(
        date(2019, 6, 4),
        "AAPL",
        120,
        entry_attr=EntryAttributes(location=(path, 11), positioning=(20, POSITION_ADD)),
    )

    records = removing_redundancies(records, since=date(2019, 12, 1))

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
        records = inferring_components(read(path, kind="journal"))

    assert len(records) == 5

    records = removing_redundancies(records, since=date(2019, 12, 1))

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
        records = inferring_components(read(path, kind="journal"))

    assert len(records) == 6

    records = removing_redundancies(records, since=date(2019, 12, 1))

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
        records = inferring_components(read(path, kind="journal"))

    assert len(records) == 4

    records = removing_redundancies(records, since=date(2019, 12, 1))

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


def test_position_inference_from_missing_dividends_journal():
    path = "subjects/positioninference2.journal"

    if os.name == "nt":
        included_path = "subjects\\positioninference3.journal"
    else:
        included_path = "subjects/positioninference3.journal"

    with tempconv(DECIMAL_POINT_COMMA):
        records = inferring_components(sorted(read(path, kind="journal")))

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 6, 19),
        "BBB",
        15,
        amount=Amount(66.05, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(4.4033, places=4, symbol="kr", fmt="%s kr"),
        payout_date=date(2019, 6, 18),
        ex_date=date(2019, 6, 3),
        entry_attr=EntryAttributes(
            location=(included_path, 5), positioning=(15, POSITION_SET)
        ),
    )

    assert records[1] == Transaction(
        date(2019, 9, 18),
        "BBB",
        15,
        amount=Amount(69.89, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(4.6593, places=4, symbol="kr", fmt="%s kr"),
        payout_date=date(2019, 9, 17),
        ex_date=date(2019, 8, 30),
        entry_attr=EntryAttributes(
            location=(included_path, 9), positioning=(15, POSITION_SET)
        ),
    )

    assert records[2] == Transaction(
        date(2019, 12, 18),
        "BBB",
        15,
        amount=Amount(69.46, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(4.6307, places=4, symbol="kr", fmt="%s kr"),
        payout_date=date(2019, 12, 17),
        ex_date=date(2019, 11, 27),
        entry_attr=EntryAttributes(
            location=(included_path, 13), positioning=(15, POSITION_SET)
        ),
    )

    assert records[3] == Transaction(
        date(2020, 3, 18),
        "BBB",
        15,
        amount=Amount(70.46, places=2, symbol="kr", fmt="%s kr"),
        dividend=Amount(4.6973, places=4, symbol="kr", fmt="%s kr"),
        payout_date=date(2020, 3, 17),
        ex_date=date(2020, 3, 2),
        entry_attr=EntryAttributes(location=(path, 7), positioning=(15, POSITION_SET)),
    )


def test_fractional_positions_journal():
    path = "subjects/fractionalpositions.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = inferring_components(read(path, kind="journal"))

    assert len(records) == 5

    records = removing_redundancies(records, since=date(2019, 12, 1))

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
        records = inferring_components(read(path, kind="journal"))

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
    # note that these records are not ambiguous in terms of the journal;
    # i.e. they can be read without issue
    path = "subjects/positionambiguity.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = inferring_components(read(path, kind="journal"))

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


def test_distribution_followed_by_buy_journal():
    path = "subjects/positionambiguity2.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = inferring_components(sorted(read(path, kind="journal")))

    assert len(records) == 2

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 7), positioning=(100, POSITION_SET)),
    )

    # note that while this record literally occurs _before_,
    # chronologically it should occur _after_
    assert records[1] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        150,
        entry_attr=EntryAttributes(location=(path, 5), positioning=(50, POSITION_ADD)),
    )


def test_nativedividends_journal():
    path = "subjects/nativedividends.journal"

    with tempconv(DECIMAL_POINT_COMMA):
        records = inferring_components(read(path, kind="journal"))

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
        records = inferring_components(read(path, kind="journal"))

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
        records = inferring_components(read(path, kind="journal"))

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
        records = inferring_components(read(path, kind="journal"))

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

    records = inferring_components(read(path, kind="journal"))

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

    records = inferring_components(sorted(read(path, kind="journal")))

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

    records = inferring_components(sorted(read(path, kind="journal")))

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

    records = inferring_components(sorted(read(path, kind="journal")))

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


def test_include_implicit_journal_dependency():
    path = "subjects/include_dependency_second.journal"

    # the three journals show the problem of implicit dependencies;
    # i.e. the second journal can never be read on its own- it has an implicit
    # dependency on the first journal (which reveals the position),
    # and similarly, so does the third journal
    # the third, however, does include both the first and the second journal
    # and thus has access to the information required

    try:
        _ = inferring_components(sorted(read(path, kind="journal")))
    except InferenceError as e:
        assert e.record.entry_attr.location[1] == 3
        assert "position could not be inferred" in e.message
    else:
        assert False

    path = "subjects/include_dependency_third.journal"

    if os.name == "nt":
        included_resolved_path_first = "subjects\\include_dependency_first.journal"
        included_resolved_path_second = "subjects\\include_dependency_second.journal"
    else:
        included_resolved_path_first = "subjects/include_dependency_first.journal"
        included_resolved_path_second = "subjects/include_dependency_second.journal"

    records = inferring_components(sorted(read(path, kind="journal")))

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path_first, 3), positioning=(100, POSITION_SET)
        ),
    )
    assert records[1] == Transaction(
        date(2019, 5, 16),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(included_resolved_path_second, 3),
            positioning=(None, POSITION_SET),
        ),
    )
    assert records[2] == Transaction(
        date(2019, 8, 15),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 6), positioning=(None, POSITION_SET)
        ),
    )
    assert records[3] == Transaction(
        date(2019, 11, 14),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 9), positioning=(None, POSITION_SET)
        ),
    )


def test_implicit_currency():
    path = "subjects/implicitcurrency.journal"

    try:
        _ = read(path, kind="journal")
    except ParseError as e:
        assert e.line_number == 4
        assert "missing symbol definition" in e.message
    else:
        assert False


def test_write():
    existing_path = "../example/simple.journal"
    existing_records = inferring_components(
        read(existing_path, kind="journal")
    )

    import os
    import tempfile

    fd, output_path = tempfile.mkstemp()
    with os.fdopen(fd, "w", newline="") as tmp:
        write(existing_records, file=tmp)
    records = inferring_components(
        read(output_path, kind="journal")
    )
    os.remove(output_path)
    assert len(records) == len(existing_records)
    for n, record in enumerate(records):
        assert record.ticker == existing_records[n].ticker
        assert record.amount == existing_records[n].amount
        assert record.position == existing_records[n].position
        assert record.dividend == existing_records[n].dividend
        assert record.kind == existing_records[n].kind
        assert record.tags == existing_records[n].tags
        assert record.entry_date == existing_records[n].entry_date
        assert record.ex_date == existing_records[n].ex_date
        assert record.payout_date == existing_records[n].payout_date


def test_integrity():
    verify_integrity(
        "subjects/integrity-input.journal", "subjects/integrity-output.journal"
    )
    verify_integrity(
        "subjects/integrity-input.journal",
        "subjects/integrity-output-condensed.journal",
        condense=True,
    )


def verify_integrity(input_path: str, verification_path: str, condense: bool = False):
    # test whether an input journal produces expected output;
    # effectively mimicking the print command
    # it is expected that the output is "lossy"; i.e. that
    # _all_ comments are omitted, and some records _may_ be if deemed redundant
    # similarly, it is expected that output conforms to a consistent style
    # that do not necessarily match that of the input journal
    records = inferring_components(read(input_path, kind="journal"))
    existing_records = removing_redundancies(records, since=date(2019, 12, 10))

    import os
    import tempfile

    fd, output_path = tempfile.mkstemp()
    with os.fdopen(fd, "w", newline="") as tmp:
        with tempconv(DECIMAL_POINT_PERIOD):
            write(existing_records, file=tmp, condensed=condense)
    records = inferring_components(
        read(output_path, kind="journal")
    )
    assert len(records) == 7
    with open(output_path, "r") as f:
        output = f.read()
    with open(verification_path, "r") as f:
        expected_output = f.read()
    assert output == expected_output
    os.remove(output_path)


def test_nordnet_import():
    path = "subjects/nordnet_transactions.csv"

    with tempconv(DECIMAL_POINT_COMMA):
        records = inferring_components(
            sorted(read(path, kind="nordnet"))
        )

    assert len(records) == 3

    assert records[0] == Transaction(
        entry_date=date(2021, 2, 12),
        payout_date=date(2021, 2, 11),
        ex_date=date(2021, 2, 5),
        ticker="AAPL",
        position=10,
        amount=Amount(123.45, places=2, symbol="DKK", fmt="%s DKK"),
        dividend=Amount(0.205, places=3, symbol="USD", fmt="%s USD"),
        entry_attr=EntryAttributes(location=(path, 4), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        entry_date=date(2021, 2, 17),
        payout_date=date(2021, 2, 16),
        ex_date=date(2021, 1, 29),
        ticker="O",
        position=10,
        amount=Amount(123.45, places=2, symbol="DKK", fmt="%s DKK"),
        dividend=Amount(0.2345, places=4, symbol="USD", fmt="%s USD"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[2] == Transaction(
        entry_date=date(2021, 3, 4),
        payout_date=date(2021, 3, 4),
        ex_date=date(2021, 3, 2),
        ticker="ORSTED",
        position=10,
        amount=Amount(115, places=0, symbol="DKK", fmt="%s DKK"),
        dividend=Amount(11.5, places=1, symbol="DKK", fmt="%s DKK"),
        entry_attr=EntryAttributes(location=(path, 2), positioning=(10, POSITION_SET)),
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


def test_nordnet_import_dupes():
    path = "subjects/nordnet_transactions_expect_duplicates.csv"

    try:
        # contains reverted transaction
        with tempconv(DECIMAL_POINT_COMMA):
            _ = read(path, kind="nordnet")
    except ParseError:
        assert True
    else:
        assert False


def test_splits_whole():
    path = "../example/split.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = inferring_components(read(path, kind="journal"))

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
        records = inferring_components(read(path, kind="journal"))

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
        records = inferring_components(read(path, kind="journal"))

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


def test_tags():
    path = "subjects/tags.journal"

    records = inferring_components(read(path, kind="journal"))

    assert len(records) == 6

    assert records[0] == Transaction(
        date(2019, 2, 14),
        "AAPL",
        100,
        amount=Amount(73, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.73, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(100, POSITION_SET)),
        tags=["initial-transaction", "tag", "spring;"],
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
        tags=["summer", ";a"],
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
        tags=["fall;fall2"],  # tags only split by whitespace
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
        tags=[
            "winter",
            "winter",  # duplicates expected to remain
            "hotsprings",
            "everywhere",
        ],  # tags "in the open" still attached to this record
    )
    assert records[4] == Transaction(
        date(2019, 12, 12),
        "BBB",
        1,
        amount=Amount(10, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(10, places=0, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 18), positioning=(1, POSITION_SET)),
        tags=["d", "e", "b", "a", "c"],  # order expected to remain as-is; no sort
    )
    assert records[5] == Transaction(
        date(2019, 12, 13),
        "AAPL",
        100,
        amount=Amount(77, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.77, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(
            location=(path, 21), positioning=(None, POSITION_SET)
        ),
    )


def test_has_identical_location():
    path = "subjects/single.journal"
    records = read(path, kind="journal")
    identical_records = read(path, kind="journal")

    assert len(records) == 1 and len(records) == len(identical_records)
    assert has_identical_location(records[0], identical_records[0])

    path = "../example/simple.journal"
    other_records = inferring_components(read(path, kind="journal"))

    assert len(other_records) == 4
    assert not has_identical_location(records[0], other_records[0])
