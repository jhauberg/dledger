import locale

from datetime import date

from dledger.localeutil import trysetlocale
from dledger.journal import (
    EntryAttributes,
    Transaction,
    Amount,
    read,
    POSITION_SET,
    POSITION_ADD,
    POSITION_SUB,
    POSITION_SPLIT,
    POSITION_SPLIT_WHOLE,
)

from dledger.convert import (
    removing_redundancies,
    adjusting_for_splits,
    with_estimates,
    in_currency,
)

from dledger.projection import GeneratedAmount


def test_remove_redundant_entries():
    records = [Transaction(date(2019, 1, 1), "ABC", 10)]

    records = removing_redundancies(records)

    assert len(records) == 1

    records = [
        Transaction(date(2019, 1, 1), "ABC", 10),
        Transaction(date(2019, 2, 1), "ABC", 10, amount=Amount(1)),
    ]

    records = removing_redundancies(records)

    assert len(records) == 1

    records = [
        # note that this scenario would not typically happen
        # as a position change record on same date as dividend transaction
        # would occur *after* the dividend transaction
        Transaction(date(2019, 1, 1), "ABC", 10),
        Transaction(date(2019, 1, 1), "ABC", 10, amount=Amount(1)),
    ]

    records = removing_redundancies(records)

    assert len(records) == 1

    records = [
        Transaction(date(2019, 1, 1), "ABC", 10, amount=Amount(1)),
        Transaction(date(2019, 1, 1), "ABC", 10),
    ]

    records = removing_redundancies(records)

    assert len(records) == 1

    records = [
        Transaction(date(2019, 2, 1), "ABC", 10, amount=Amount(1)),
        Transaction(date(2019, 3, 1), "ABC", 20, amount=Amount(1)),
        Transaction(date(2019, 4, 1), "ABC", 30),
    ]

    records = removing_redundancies(records)

    assert len(records) == 3

    records = [
        Transaction(date(2019, 1, 1), "ABC", 10),
        Transaction(date(2019, 2, 1), "ABC", 10, amount=Amount(1)),
        Transaction(date(2019, 2, 5), "ABC", 0),
        Transaction(date(2019, 3, 1), "DEF", 10, amount=Amount(1)),
    ]

    records = removing_redundancies(records)

    assert len(records) == 3


def test_adjusting_for_splits_whole():
    trysetlocale(locale.LC_NUMERIC, ["en_US", "en-US", "en"])

    path = "../example/split.journal"

    records = adjusting_for_splits(read(path, kind="journal"))

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2021, 1, 1),
        "ABC",
        20,
        amount=Amount(1, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.05, places=2, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2021, 2, 1),
        "ABC",
        40,
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


def test_adjusting_for_splits_fractional():
    trysetlocale(locale.LC_NUMERIC, ["en_US", "en-US", "en"])

    path = "subjects/split_fractional.journal"

    records = adjusting_for_splits(read(path, kind="journal"))

    assert len(records) == 7

    assert records[0] == Transaction(
        date(2021, 1, 1),
        "ABC",
        30,
        amount=Amount(1, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.0333, places=4, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2021, 2, 1),
        "ABC",
        60,
        entry_attr=EntryAttributes(location=(path, 6), positioning=(10, POSITION_ADD)),
    )
    assert records[2] == Transaction(
        date(2021, 2, 10),
        "ABC",
        60,
        entry_attr=EntryAttributes(
            location=(path, 8), positioning=(2, POSITION_SPLIT_WHOLE)
        ),
    )
    assert records[3] == Transaction(
        date(2021, 2, 11),
        "ABC",
        58.5,
        entry_attr=EntryAttributes(location=(path, 10), positioning=(1, POSITION_SUB)),
    )
    assert records[4] == Transaction(
        date(2021, 4, 1),
        "ABC",
        58.5,
        amount=Amount(1.95, places=2, symbol="$", fmt="$ %s"),
        dividend=Amount(0.0333, places=4, symbol="$", fmt="$ %s"),
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


def test_adjusting_for_splits_reverse():
    trysetlocale(locale.LC_NUMERIC, ["en_US", "en-US", "en"])

    path = "subjects/split_reverse.journal"

    records = adjusting_for_splits(read(path, kind="journal"))

    assert len(records) == 4

    assert records[0] == Transaction(
        date(2021, 1, 1),
        "ABC",
        5,
        amount=Amount(1, places=0, symbol="$", fmt="$ %s"),
        dividend=Amount(0.2, places=1, symbol="$", fmt="$ %s"),
        entry_attr=EntryAttributes(location=(path, 3), positioning=(10, POSITION_SET)),
    )
    assert records[1] == Transaction(
        date(2021, 2, 1),
        "ABC",
        10,
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


def test_convert_estimates():
    records = [
        Transaction(date(2019, 6, 1), "ABC", 100, dividend=Amount(1, symbol="$"))
    ]

    records = with_estimates(records)

    assert records[0].amount == GeneratedAmount(100, symbol="$")

    records = [
        Transaction(
            date(2019, 3, 1),
            "ABC",
            100,
            amount=Amount(150, symbol="kr"),
            dividend=Amount(1.5, symbol="$"),
        ),
        Transaction(date(2019, 6, 1), "ABC", 100, dividend=Amount(1.5, symbol="$")),
    ]

    records = with_estimates(records)

    assert records[1].amount == GeneratedAmount(150, symbol="kr")


def test_convert_to_currency():
    records = [
        Transaction(
            date(2019, 3, 1),
            "ABC",
            100,
            amount=Amount(150, symbol="kr"),
            dividend=Amount(1, symbol="$"),
        )
    ]

    records = in_currency(records, symbol="$")

    assert records[0].amount == GeneratedAmount(100, symbol="$")

    records = [
        Transaction(
            date(2019, 3, 1),
            "ABC",
            100,
            amount=Amount(150, symbol="kr"),
            dividend=Amount(1, symbol="$"),
        ),
        Transaction(
            date(2019, 3, 2),
            "DEF",
            100,
            amount=Amount(50, symbol="kr"),
            dividend=Amount(0.5, symbol="kr"),
        ),
    ]

    records = in_currency(records, symbol="$")

    assert records[0].amount == GeneratedAmount(100, symbol="$")
    assert isinstance(records[1].amount, GeneratedAmount)
    import math

    assert math.floor(records[1].amount.value) == 33  # floor to ignore decimals


# todo: test convert_to_native_currency
