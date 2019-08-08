from datetime import date

from dividendreport.dateutil import (
    months_between,
    next_month, previous_month
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
                          date(year=2019, month=1, day=1), normalized=True) == 12
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2020, month=1, day=1), normalized=True) == 12
    assert months_between(date(year=2019, month=3, day=1),
                          date(year=2019, month=12, day=1), normalized=True) == 9
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=2, day=1), normalized=True) == 1
    assert months_between(date(year=2019, month=1, day=1),
                          date(year=2019, month=12, day=1), normalized=True) == 11
    assert months_between(date(year=2018, month=1, day=1),
                          date(year=2020, month=1, day=1), normalized=True) == 12
    assert months_between(date(year=2019, month=5, day=1),
                          date(year=2020, month=4, day=1), normalized=True) == 11


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
