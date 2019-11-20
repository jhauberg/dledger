import calendar

from datetime import datetime, timedelta, date

from typing import Tuple, Optional


def months_between(a: date, b: date,
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


def in_months(d: date, months: int) -> date:
    """ Return the date in a number of months. """

    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])

    return d.replace(year=year, month=month, day=day)


def last_of_month(d: date) -> date:
    """ Return the date at the last day of the month. """

    return previous_month(next_month(d))


def first_of_month(d: date) -> date:
    """ Return the date at the first day of the month. """

    return d.replace(day=1)


def previous_month(d: date) -> date:
    """ Return the date at the last day of the previous month. """

    d = first_of_month(d)
    # then backtrack by 1 day to find previous month
    d -= timedelta(days=1)

    return d


def next_month(d: date) -> date:
    """ Return the date at the first day of the following month. """

    d = first_of_month(d)

    try:
        # try fast-forwarding 1 month
        d = d.replace(month=d.month + 1)
    except ValueError:
        if d.month == 12:
            # fast-forward to next year
            d = d.replace(year=d.year + 1, month=1)

    return d


def parse_datestamp(datestamp: str, *, strict: bool = False) \
        -> date:
    """ Return the date that maps to datestamp.

    A datestamp can be specified in any of the following variations:

        "2019/11/11" => 2019/11/11
        "2019/11"    => 2019/11/01
        "2019"       => 2019/01/01

        or

        "2019-11-11" => 2019/11/11
        "2019-11"    => 2019/11/01
        "2019"       => 2019/01/01

    Components left out will default to the first of year or month.
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
            raise ValueError(f'invalid date format (\'{datestamp}\')')


def parse_interval(interval: str) \
        -> Tuple[Optional[date],
                 Optional[date]]:
    datestamps = interval.split(':')

    if len(datestamps) > 2 or len(datestamps) == 0:
        raise ValueError('malformed interval')

    starting_datestamp = datestamps[0].strip()
    starting: Optional[date] = None

    if len(starting_datestamp) > 0:
        starting = parse_datestamp(starting_datestamp)

    ending_datestamp: Optional[str] = datestamps[1].strip() if len(datestamps) > 1 else None
    ending: Optional[date] = None

    if ending_datestamp is not None and len(ending_datestamp) > 0:
        ending = parse_datestamp(ending_datestamp)

    if starting is not None and ending is not None:
        if starting > ending:
            tmp = starting
            starting = ending
            ending = tmp

    return starting, ending


def parse_period(interval: str) \
        -> Tuple[Optional[date],
                 Optional[date]]:
    if ':' in interval:
        return parse_interval(interval)

    n = max(interval.count('/'), interval.count('-'))

    starting = parse_datestamp(interval)
    ending = None

    if n == 0:
        ending = starting.replace(year=starting.year + 1)
    if n == 1:
        ending = next_month(starting)
    if n == 2:
        ending = starting + timedelta(days=1)

    return starting, ending

