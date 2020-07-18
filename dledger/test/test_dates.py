import locale

from datetime import datetime, date, timedelta

from dledger.localeutil import trysetlocale
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
    assert parse_datestamp('2019/1/01') == date(2019, 1, 1)
    assert parse_datestamp('2019/01/1') == date(2019, 1, 1)
    assert parse_datestamp('2019/1/1') == date(2019, 1, 1)
    assert parse_datestamp('2019/11/01') == date(2019, 11, 1)
    assert parse_datestamp('2019/11/1') == date(2019, 11, 1)
    assert parse_datestamp('2019/11/11') == date(2019, 11, 11)
    assert parse_datestamp('2019/11') == date(2019, 11, 1)
    assert parse_datestamp('2019') == date(2019, 1, 1)

    assert parse_datestamp('2019-1-01') == date(2019, 1, 1)
    assert parse_datestamp('2019-01-1') == date(2019, 1, 1)
    assert parse_datestamp('2019-1-1') == date(2019, 1, 1)
    assert parse_datestamp('2019-11-01') == date(2019, 11, 1)
    assert parse_datestamp('2019-11-1') == date(2019, 11, 1)
    assert parse_datestamp('2019-11-11') == date(2019, 11, 11)
    assert parse_datestamp('2019-11') == date(2019, 11, 1)
    assert parse_datestamp('2019') == date(2019, 1, 1)

    # assert parse_datestamp('') raises ValueError
    # assert parse_datestamp('2019/11-11') raises ValueError
    # assert parse_datestamp('2019 / 11/11') raises ValueError


def test_parse_period():
    assert parse_period('2019/11/11:2020/11/11') == (date(2019, 11, 11),
                                                     date(2020, 11, 11))
    assert parse_period('2019/11:2020/11') == (date(2019, 11, 1),
                                               date(2020, 11, 1))
    assert parse_period('2019:2020') == (date(2019, 1, 1),
                                         date(2020, 1, 1))

    assert parse_period('2019:') == (date(2019, 1, 1), None)
    assert parse_period(':2019') == (None, date(2019, 1, 1))

    assert parse_period('2019') == (date(2019, 1, 1), date(2020, 1, 1))
    assert parse_period('2019/11') == (date(2019, 11, 1), date(2019, 12, 1))
    assert parse_period('2019/11/11') == (date(2019, 11, 11), date(2019, 11, 12))

    assert parse_period('2019/11/11:2020/11') == (date(2019, 11, 11),
                                                  date(2020, 11, 1))

    assert parse_period('2020/11/11:2019/11/11') == (date(2019, 11, 11),
                                                     date(2020, 11, 11))
    assert parse_period('2019/11/11:2019/11/11') == (date(2019, 11, 11),
                                                     date(2019, 11, 11))

    today = datetime.today().date()

    assert parse_period('11') == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period('11:12') == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period('6:1') == (date(today.year, 1, 1), date(today.year, 6, 1))

    tomorrow = today + timedelta(days=1)
    yesterday = today + timedelta(days=-1)

    assert parse_period('today') == (today, tomorrow)
    assert parse_period('tod') == (today, tomorrow)
    assert parse_period('Today') == (today, tomorrow)
    assert parse_period('tomorrow') == (tomorrow, tomorrow + timedelta(days=1))
    assert parse_period('tom') == (tomorrow, tomorrow + timedelta(days=1))
    assert parse_period('yesterday') == (yesterday, today)
    assert parse_period('yest') == (yesterday, today)
    assert parse_period('y') == (yesterday, today)

    assert parse_period('today:tomorrow') == (today, tomorrow)
    assert parse_period('tomorrow:tomorrow') == (tomorrow, tomorrow)
    assert parse_period('yesterday:tomorrow') == (yesterday, tomorrow)
    assert parse_period('y:tom') == (yesterday, tomorrow)

    trysetlocale(locale.LC_TIME, ['en_US', 'en-US', 'en'])

    assert parse_period('november') == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period('November') == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period('nov') == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period('no') == (date(today.year, 11, 1), date(today.year, 12, 1))
    assert parse_period('n') == (date(today.year, 11, 1), date(today.year, 12, 1))

    assert parse_period('nov:dec') == (date(today.year, 11, 1), date(today.year, 12, 1))

    trysetlocale(locale.LC_TIME, ['da_DK', 'da-DK', 'da'])

    assert parse_period('marts') == (date(today.year, 3, 1), date(today.year, 4, 1))
    assert parse_period('feb') == (date(today.year, 2, 1), date(today.year, 3, 1))
    assert parse_period('oct') == (date(today.year, 10, 1), date(today.year, 11, 1))
