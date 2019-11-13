from datetime import date

from dledger.dateutil import (
    months_between, in_months,
    next_month, previous_month, last_of_month,
    parse_period, parse_datestamp
)


def test_months_between():
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=1, day=1)) == 0
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=2, day=1)) == 1
    assert months_between(date(year=2019, month=3, day=1),
                          date(year=2019, month=12, day=1)) == 9
    assert months_between(date(year=2019, month=12, day=1),
                          date(year=2020, month=3, day=1)) == 3
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=12, day=1)) == 11
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2020, month=1, day=1)) == 12
    assert months_between(date(year=2019, month=12, day=1),
                          date(year=2020, month=1, day=1)) == 1
    assert months_between(date(year=2019, month=5, day=1),
                          date(year=2020, month=4, day=1)) == 11


def test_months_between_normalized():
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=1, day=1), ignore_years=True) == 12
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2020, month=1, day=1), ignore_years=True) == 12
    assert months_between(date(year=2019, month=3, day=1),
                          date(year=2019, month=12, day=1), ignore_years=True) == 9
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=2, day=1), ignore_years=True) == 1
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=12, day=1), ignore_years=True) == 11
    assert months_between(date(year=2018, month=1, day=1),
                          date(year=2020, month=1, day=1), ignore_years=True) == 12
    assert months_between(date(year=2019, month=5, day=1),
                          date(year=2020, month=4, day=1), ignore_years=True) == 11


def test_in_months():
    d = in_months(date(year=2019, month=1, day=1), months=1)

    assert d.year == 2019 and d.month == 2 and d.day == 1

    d = in_months(date(year=2019, month=1, day=15), months=1)

    assert d.year == 2019 and d.month == 2 and d.day == 15

    d = in_months(date(year=2019, month=1, day=31), months=1)

    assert d.year == 2019 and d.month == 2 and d.day == 28

    d = in_months(date(year=2019, month=1, day=29), months=1)

    assert d.year == 2019 and d.month == 2 and d.day == 28

    d = in_months(date(year=2019, month=1, day=1), months=2)

    assert d.year == 2019 and d.month == 3 and d.day == 1

    d = in_months(date(year=2019, month=1, day=1), months=12)

    assert d.year == 2020 and d.month == 1 and d.day == 1

    d = in_months(date(year=2019, month=1, day=1), months=-1)

    assert d.year == 2018 and d.month == 12 and d.day == 1

    d = in_months(date(year=2019, month=1, day=31), months=-1)

    assert d.year == 2018 and d.month == 12 and d.day == 31


def test_last_of_month():
    d = last_of_month(date(year=2020, month=1, day=1))

    assert d.year == 2020 and d.month == 1 and d.day == 31

    d = last_of_month(date(year=2019, month=6, day=8))

    assert d.year == 2019 and d.month == 6 and d.day == 30


def test_next_month():
    d = next_month(date(year=2019, month=1, day=1))

    assert d.year == 2019 and d.month == 2 and d.day == 1

    d = next_month(date(year=2019, month=1, day=16))

    assert d.year == 2019 and d.month == 2 and d.day == 1

    d = next_month(date(year=2019, month=12, day=1))

    assert d.year == 2020 and d.month == 1 and d.day == 1


def test_previous_next_month():
    d = previous_month(date(year=2019, month=2, day=1))

    assert d.year == 2019 and d.month == 1 and d.day == 31

    d = previous_month(date(year=2019, month=2, day=16))

    assert d.year == 2019 and d.month == 1 and d.day == 31

    d = previous_month(date(year=2020, month=1, day=1))

    assert d.year == 2019 and d.month == 12 and d.day == 31


def test_parse_datestamp():
    assert parse_datestamp('2019/11/11') == date(2019, 11, 11)
    assert parse_datestamp('2019/11') == date(2019, 11, 1)
    assert parse_datestamp('2019') == date(2019, 1, 1)

    assert parse_datestamp('2019-11-11') == date(2019, 11, 11)
    assert parse_datestamp('2019-11') == date(2019, 11, 1)
    assert parse_datestamp('2019') == date(2019, 1, 1)

    assert parse_datestamp('') is None
    assert parse_datestamp('2019/11-11') is None
    assert parse_datestamp('2019 / 11/11') is None


def test_parse_period():
    assert parse_period('2019/11/11;2020/11/11') == [date(2019, 11, 11),
                                                     date(2020, 11, 11)]
    assert parse_period('2019/11;2020/11') == [date(2019, 11, 1),
                                               date(2020, 11, 1)]
    assert parse_period('2019;2020') == [date(2019, 1, 1),
                                         date(2020, 1, 1)]

    assert parse_period('2019/11/11;2020/11') == [date(2019, 11, 11),
                                                  date(2020, 11, 1)]

    assert parse_period('2020/11/11;2019/11/11') == [date(2019, 11, 11),
                                                     date(2020, 11, 11)]
