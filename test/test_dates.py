import calendar

from datetime import datetime, date, timedelta

from dledger.dateutil import (
    months_between,
    in_months,
    next_month,
    previous_month,
    last_of_month,
    parse_period,
    parse_datestamp,
    parse_month,
    months_in_quarter,
    next_quarter,
    previous_quarter,
)


def test_months_between():
    assert (
        months_between(date(year=2019, month=1, day=1), date(year=2019, month=1, day=1))
        == 0
    )
    assert (
        months_between(date(year=2019, month=1, day=1), date(year=2019, month=2, day=1))
        == 1
    )
    assert (
        months_between(
            date(year=2019, month=3, day=1), date(year=2019, month=12, day=1)
        )
        == 9
    )
    assert (
        months_between(
            date(year=2019, month=12, day=1), date(year=2020, month=3, day=1)
        )
        == 3
    )
    assert (
        months_between(
            date(year=2019, month=1, day=1), date(year=2019, month=12, day=1)
        )
        == 11
    )
    assert (
        months_between(date(year=2019, month=1, day=1), date(year=2020, month=1, day=1))
        == 12
    )
    assert (
        months_between(
            date(year=2019, month=12, day=1), date(year=2020, month=1, day=1)
        )
        == 1
    )
    assert (
        months_between(date(year=2019, month=5, day=1), date(year=2020, month=4, day=1))
        == 11
    )


def test_months_between_normalized():
    assert (
        months_between(
            date(year=2019, month=1, day=1),
            date(year=2019, month=1, day=1),
            ignore_years=True,
        )
        == 12
    )
    assert (
        months_between(
            date(year=2019, month=1, day=1),
            date(year=2020, month=1, day=1),
            ignore_years=True,
        )
        == 12
    )
    assert (
        months_between(
            date(year=2019, month=3, day=1),
            date(year=2019, month=12, day=1),
            ignore_years=True,
        )
        == 9
    )
    assert (
        months_between(
            date(year=2019, month=1, day=1),
            date(year=2019, month=2, day=1),
            ignore_years=True,
        )
        == 1
    )
    assert (
        months_between(
            date(year=2019, month=1, day=1),
            date(year=2019, month=12, day=1),
            ignore_years=True,
        )
        == 11
    )
    assert (
        months_between(
            date(year=2018, month=1, day=1),
            date(year=2020, month=1, day=1),
            ignore_years=True,
        )
        == 12
    )
    assert (
        months_between(
            date(year=2019, month=5, day=1),
            date(year=2020, month=4, day=1),
            ignore_years=True,
        )
        == 11
    )


def test_next_quarter():
    assert next_quarter(1) == 2
    assert next_quarter(2) == 3
    assert next_quarter(3) == 4
    assert next_quarter(4) == 1

    try:
        _ = next_quarter(5)
    except ValueError:
        assert True
    else:
        assert False

    try:
        _ = next_quarter(-1)
    except ValueError:
        assert True
    else:
        assert False


def test_previous_quarter():
    assert previous_quarter(1) == 4
    assert previous_quarter(2) == 1
    assert previous_quarter(3) == 2
    assert previous_quarter(4) == 3

    try:
        _ = previous_quarter(5)
    except ValueError:
        assert True
    else:
        assert False

    try:
        _ = previous_quarter(-1)
    except ValueError:
        assert True
    else:
        assert False


def test_months_in_quarter():
    assert months_in_quarter(1) == [1, 2, 3]
    assert months_in_quarter(2) == [4, 5, 6]
    assert months_in_quarter(3) == [7, 8, 9]
    assert months_in_quarter(4) == [10, 11, 12]

    try:
        _ = months_in_quarter(5)
    except ValueError:
        assert True
    else:
        assert False

    try:
        _ = months_in_quarter(-1)
    except ValueError:
        assert True
    else:
        assert False


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

    d = in_months(date(year=2020, month=6, day=1), months=-12)

    assert d.year == 2019 and d.month == 6 and d.day == 1


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
    assert parse_datestamp("2019/1/01") == date(2019, 1, 1)
    assert parse_datestamp("2019/01/1") == date(2019, 1, 1)
    assert parse_datestamp("2019/1/1") == date(2019, 1, 1)
    assert parse_datestamp("2019/11/01") == date(2019, 11, 1)
    assert parse_datestamp("2019/11/1") == date(2019, 11, 1)
    assert parse_datestamp("2019/11/11") == date(2019, 11, 11)
    assert parse_datestamp("2019/11") == date(2019, 11, 1)
    assert parse_datestamp("2019") == date(2019, 1, 1)

    assert parse_datestamp("2019-1-01") == date(2019, 1, 1)
    assert parse_datestamp("2019-01-1") == date(2019, 1, 1)
    assert parse_datestamp("2019-1-1") == date(2019, 1, 1)
    assert parse_datestamp("2019-11-01") == date(2019, 11, 1)
    assert parse_datestamp("2019-11-1") == date(2019, 11, 1)
    assert parse_datestamp("2019-11-11") == date(2019, 11, 11)
    assert parse_datestamp("2019-11") == date(2019, 11, 1)
    assert parse_datestamp("2019") == date(2019, 1, 1)

    assert parse_datestamp("2019.1.01") == date(2019, 1, 1)
    assert parse_datestamp("2019.01.1") == date(2019, 1, 1)
    assert parse_datestamp("2019.1.1") == date(2019, 1, 1)
    assert parse_datestamp("2019.11.01") == date(2019, 11, 1)
    assert parse_datestamp("2019.11.1") == date(2019, 11, 1)
    assert parse_datestamp("2019.11.11") == date(2019, 11, 11)
    assert parse_datestamp("2019.11") == date(2019, 11, 1)
    assert parse_datestamp("2019") == date(2019, 1, 1)

    assert parse_datestamp("2019/11/11", strict=True) == date(2019, 11, 11)

    try:
        parse_datestamp("2019/11", strict=True)
    except ValueError:
        assert True
    else:
        assert False

    try:
        parse_datestamp("")
    except ValueError:
        assert True
    else:
        assert False

    try:
        parse_datestamp("2019/11/11/11")
    except ValueError:
        assert True
    else:
        assert False

    try:
        parse_datestamp("2019/11-11")
    except ValueError:
        assert True
    else:
        assert False

    try:
        parse_datestamp("2019 / 11/11")
    except ValueError:
        assert True
    else:
        assert False

    try:
        parse_datestamp("200/11/11")
    except ValueError:
        assert True
    else:
        assert False

    assert parse_datestamp("0200/11/11") == date(200, 11, 11)

    try:
        parse_datestamp("2020//11/11")
    except ValueError:
        assert True
    else:
        assert False


def test_parse_period():
    assert parse_period("2019/11/11:2020/11/11") == (
        date(2019, 11, 11),
        date(2020, 11, 11),
    )
    assert parse_period("2019/11:2020/11") == (date(2019, 11, 1), date(2020, 11, 1))
    assert parse_period("2019:2020") == (date(2019, 1, 1), date(2020, 1, 1))

    assert parse_period("2019:") == (date(2019, 1, 1), None)
    assert parse_period(":2019") == (None, date(2019, 1, 1))

    assert parse_period("2019") == (date(2019, 1, 1), date(2020, 1, 1))
    assert parse_period("2019/11") == (date(2019, 11, 1), date(2019, 12, 1))
    assert parse_period("2019/11/11") == (date(2019, 11, 11), date(2019, 11, 12))

    assert parse_period("2019/11/11:2020/11") == (date(2019, 11, 11), date(2020, 11, 1))

    assert parse_period("2020/11/11:2019/11/11") == (
        date(2019, 11, 11),
        date(2020, 11, 11),
    )
    assert parse_period("2019/11/11:2019/11/11") == (
        date(2019, 11, 11),
        date(2019, 11, 11),
    )

    try:
        parse_period("")
    except ValueError:
        assert True
    else:
        assert False

    try:
        parse_period("2019/11/11:2020/11/11:2021/11/11")
    except ValueError:
        assert True
    else:
        assert False

    today = datetime.today().date()

    assert parse_period("11") == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period("11:12") == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period("6:1") == (date(today.year, 1, 1), date(today.year, 6, 1))

    assert parse_period("q1") == (date(today.year, 1, 1), date(today.year, 4, 1))
    assert parse_period("q2") == (date(today.year, 4, 1), date(today.year, 7, 1))
    assert parse_period("q3") == (date(today.year, 7, 1), date(today.year, 10, 1))
    assert parse_period("q4") == (date(today.year, 10, 1), date(today.year + 1, 1, 1))

    assert parse_period("q2:q3") == (date(today.year, 4, 1), date(today.year, 7, 1))
    assert parse_period("q2:q4") == (date(today.year, 4, 1), date(today.year, 10, 1))
    assert parse_period("q4:q1") == (date(today.year, 1, 1), date(today.year, 10, 1))

    tomorrow = today + timedelta(days=1)
    yesterday = today + timedelta(days=-1)

    assert parse_period("today") == (today, tomorrow)
    assert parse_period("tod") == (today, tomorrow)
    assert parse_period("Today") == (today, tomorrow)
    assert parse_period("tomorrow") == (tomorrow, tomorrow + timedelta(days=1))
    assert parse_period("tom") == (tomorrow, tomorrow + timedelta(days=1))
    assert parse_period("yesterday") == (yesterday, today)
    assert parse_period("yest") == (yesterday, today)
    assert parse_period("y") == (yesterday, today)

    assert parse_period("today:tomorrow") == (today, tomorrow)
    assert parse_period("tomorrow:tomorrow") == (tomorrow, tomorrow)
    assert parse_period("yesterday:tomorrow") == (yesterday, tomorrow)
    assert parse_period("y:tom") == (yesterday, tomorrow)

    try:
        parse_period("2019/mar")
    except ValueError:
        assert True
    else:
        assert False

    try:
        parse_period("2019/q2")
    except ValueError:
        assert True
    else:
        assert False


def test_parse_period_months():
    year = datetime.today().date().year

    assert parse_period("november") == (
        date(year, 11, 1),
        date(year, 12, 1),
    )
    assert parse_period("November") == (
        date(year, 11, 1),
        date(year, 12, 1),
    )
    assert parse_period("nov") == (date(year, 11, 1), date(year, 12, 1))
    assert parse_period("no") == (date(year, 11, 1), date(year, 12, 1))
    assert parse_period("n") == (date(year, 11, 1), date(year, 12, 1))

    try:
        parse_period("ju")
    except ValueError:
        assert True
    else:
        assert False

    assert parse_period("nov:dec") == (date(year, 11, 1), date(year, 12, 1))


def test_parse_month():
    for n, name in enumerate(calendar.month_name):
        if n == 0:
            assert parse_month(name) is None
        else:
            assert parse_month(name) == n
