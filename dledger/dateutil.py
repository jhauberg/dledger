import calendar

from datetime import datetime, timedelta


def months_between(a: datetime.date, b: datetime.date,
                   *, ignore_years: bool = False) -> int:
    """ Return the number of months between two dates, from earliest to latest.

    Does not take days into account.

    For example,
      2019-05-20 - 2019-06-20 is exactly 1 month apart, but so is
      2019-05-20 - 2019-06-29 or 2019-06-01

    If ignore_years is True, do not take years into account.

    For example,
      2019-05-20 - 2020-07-20 is exactly 14 months apart, but only 2 if ignore_years is True.
    """

    future = max([a, b])
    past = min([a, b])

    months = future.month - past.month + 12 * (future.year - past.year)

    if ignore_years:
        months = months % 12
        if months == 0:
            months = 12

    return months


def in_months(date: datetime.date, months: int) -> datetime.date:
    """ Return the date in a number of months. """

    month = date.month - 1 + months
    year = date.year + month // 12
    month = month % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])

    return date.replace(year=year, month=month, day=day)


def last_of_month(date: datetime.date) -> datetime.date:
    """ Return the date at the last day of the month. """

    return previous_month(next_month(date))


def first_of_month(date: datetime.date) -> datetime.date:
    """ Return the date at the first day of the month. """

    return date.replace(day=1)


def previous_month(date: datetime.date) -> datetime.date:
    """ Return the date at the last day of the previous month. """

    date = first_of_month(date)
    # then backtrack by 1 day to find previous month
    date -= timedelta(days=1)

    return date


def next_month(date: datetime.date) -> datetime.date:
    """ Return the date at the first day of the following month. """

    date = first_of_month(date)

    try:
        # try fast-forwarding 1 month
        date = date.replace(month=date.month + 1)
    except ValueError:
        if date.month == 12:
            # fast-forward to next year
            date = date.replace(year=date.year + 1, month=1)

    return date


def parse_datestamp(datestamp: str, *, strict: bool = False) -> datetime.date:
    """ Return the date that maps to datestamp.

    A datestamp can be specified in any of the following variations:

        "2019/11/11" => 2019/11/11
        "2019/11"    => 2019/11/01
        "2019"       => 2019/01/01

        or

        "2019-11-11" => 2019/11/11
        "2019-11"    => 2019/11/01
        "2019"       => 2019/01/01

    Components left out will always default to the first of year or month.
    """

    try:
        return datetime.strptime(datestamp, '%Y/%m/%d').date()
    except ValueError:
        try:
            return datetime.strptime(datestamp, '%Y-%m-%d').date()
        except ValueError:
            if strict:
                raise

    try:
        return datetime.strptime(datestamp, '%Y/%m').date()
    except ValueError:
        try:
            return datetime.strptime(datestamp, '%Y-%m').date()
        except ValueError:
            pass

    try:
        return datetime.strptime(datestamp, '%Y').date()
    except ValueError:
        try:
            return datetime.strptime(datestamp, '%Y').date()
        except ValueError:
            pass

    return None


def parse_period(interval: str):
    datestamps = interval.split(';')

    if len(datestamps) != 2:
        raise ValueError('malformed period')

    return sorted([parse_datestamp(datestamp.strip()) for datestamp in datestamps])
