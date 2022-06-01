from datetime import date

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
    inferring_components,
    removing_redundancies,
    adjusting_for_splits,
    with_estimates,
    in_currency,
)
from dledger.localeutil import tempconv, DECIMAL_POINT_PERIOD
from dledger.projection import GeneratedAmount


def test_remove_redundant_entries():
    records = [Transaction(date(2019, 1, 1), "ABC", 10)]

    records = removing_redundancies(records, since=date(2019, 2, 2))

    assert len(records) == 0

    records = [
        Transaction(date(2019, 1, 1), "ABC", 10),
        Transaction(date(2019, 2, 1), "ABC", 10, amount=Amount(1)),
    ]

    records = removing_redundancies(records, since=date(2019, 1, 2))

    assert len(records) == 1

    records = [
        # note that this scenario would not typically happen
        # as a position change record on same date as dividend transaction
        # would occur *after* the dividend transaction
        Transaction(date(2019, 1, 1), "ABC", 10),
        Transaction(date(2019, 1, 1), "ABC", 10, amount=Amount(1)),
    ]

    records = removing_redundancies(records, since=date(2019, 1, 2))

    assert len(records) == 1
    # assert that we got rid of the positional record; not the dividend record
    assert records[0].amount == Amount(1)

    records = [
        Transaction(date(2019, 1, 1), "ABC", 10, amount=Amount(1)),
        Transaction(date(2019, 1, 1), "ABC", 10),
    ]

    records = removing_redundancies(records, since=date(2019, 1, 2))

    assert len(records) == 1
    # assert that we got rid of the positional record; not the dividend record
    assert records[0].amount == Amount(1)

    records = [
        Transaction(date(2019, 2, 1), "ABC", 10, amount=Amount(1)),
        Transaction(date(2019, 3, 1), "ABC", 20, amount=Amount(1)),
        Transaction(date(2019, 4, 1), "ABC", 30),
    ]

    records = removing_redundancies(records, since=date(2019, 5, 2))

    assert len(records) == 3

    records = [
        Transaction(date(2019, 2, 1), "ABC", 10, amount=Amount(1)),
        Transaction(date(2019, 3, 1), "ABC", 20, amount=Amount(1)),
        Transaction(date(2019, 4, 1), "ABC", 30),
    ]

    # a year later the positional record is no longer useful
    records = removing_redundancies(records, since=date(2020, 5, 2))

    # assert that we got rid of it
    assert len(records) == 2

    records = [
        Transaction(date(2019, 1, 1), "ABC", 10),
        Transaction(date(2019, 2, 1), "ABC", 10, amount=Amount(1)),
        Transaction(date(2019, 2, 5), "ABC", 0),
        Transaction(date(2019, 3, 1), "DEF", 10, amount=Amount(1)),
    ]

    records = removing_redundancies(records, since=date(2019, 3, 4))

    assert len(records) == 3

    assert records[0].position == 10
    assert records[1].position == 0
    assert records[2].position == 10
    assert records[2].ticker == "DEF"

    # observed issue for T where position was closed same month;
    # a discrepancy in year/month counting between projection and redundancy removal
    # caused a projection to appear unexpectedly
    # i.e. redundancy check was essentially based on 365 days passing, while
    # projection discards records dated more than 13 months back
    records = [
        Transaction(date(2021, 5, 4), "ABC", 10, amount=Amount(1), ex_date=date(2021, 4, 8), payout_date=date(2021, 5, 3)),
        Transaction(date(2021, 5, 18), "ABC", 0),
    ]

    assert len(removing_redundancies(records, since=date(2022, 5, 18))) == 2

    records = removing_redundancies(records, since=date(2022, 5, 19))

    assert len(records) == 2

    # observed issue for LTC where position was closed prior to receiving final
    # payout; ex-date properly recorded and all, but record considered redundant

    records = [
        Transaction(date(2021, 3, 1), "ABC", 10, amount=Amount(1), ex_date=date(2021, 2, 17), payout_date=date(2021, 2, 26)),
        Transaction(date(2021, 4, 1), "ABC", 10, amount=Amount(1), ex_date=date(2021, 3, 22), payout_date=date(2021, 3, 31)),
        Transaction(date(2021, 5, 3), "ABC", 10, amount=Amount(1), ex_date=date(2021, 4, 21), payout_date=date(2021, 4, 30)),
        Transaction(date(2021, 5, 26), "ABC", 0),
        Transaction(date(2021, 6, 1), "ABC", 10, amount=Amount(1), ex_date=date(2021, 5, 19), payout_date=date(2021, 5, 28)),
    ]

    assert len(removing_redundancies(records, since=date(2022, 5, 30))) == 5
    assert len(removing_redundancies(records, since=date(2022, 5, 31))) == 5
    assert len(removing_redundancies(records, since=date(2022, 6, 1))) == 5
    assert len(removing_redundancies(records, since=date(2022, 7, 1))) == 5


def test_adjusting_for_splits_whole():
    path = "../example/split.journal"

    records = adjusting_for_splits(
        inferring_components(
            read(path, kind="journal")
        )
    )

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


def test_adjusting_for_splits_ordering():
    path = "../example/split.journal"

    records = inferring_components(read(path, kind="journal"))

    # ensure that order does not matter for split adjustment
    tmp = records[0]
    records[0] = records[-2]
    records[-2] = tmp

    records = sorted(adjusting_for_splits(records))

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
    path = "subjects/split_fractional.journal"

    with tempconv(DECIMAL_POINT_PERIOD):
        records = inferring_components(read(path, kind="journal"))
    records = adjusting_for_splits(records)

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
    path = "subjects/split_reverse.journal"

    records = adjusting_for_splits(
        inferring_components(
            read(path, kind="journal")
        )
    )

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
