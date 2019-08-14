import calendar

from datetime import datetime, timedelta


def months_between(a: datetime.date, b: datetime.date,
                   *, normalized: bool = False) -> int:
    """ Return the number of months between two dates, from earliest to latest.

    If normalized is True, keep months within a 12-month range.
    """

    future = max([a, b])
    past = min([a, b])

    months = future.month - past.month + 12 * (future.year - past.year)

    if normalized:
        months = months % 12
        if months == 0:
            months = 12

    return months


def in_months(date: datetime.date, months: int) -> datetime.date:
    month = date.month - 1 + months
    year = date.year + month // 12
    month = month % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return date.replace(year=year, month=month, day=day)


def last_of_month(date: datetime.date) -> datetime.date:
    return previous_month(next_month(date))


def previous_month(date: datetime.date) -> datetime.date:
    """ Return the date of the last day of the previous month for a given date. """

    # set to first day of given month
    date = date.replace(day=1)
    # then backtrack by 1 day to find previous month
    date -= timedelta(days=1)

    return date


def next_month(date: datetime.date) -> datetime.date:
    """ Return the date of the first day of the next month for a given date. """

    # set to first day of month
    date = date.replace(day=1)

    try:
        # try fast-forwarding 1 month
        date = date.replace(month=date.month + 1)
    except ValueError:
        if date.month == 12:
            # fast-forward to next year
            date = date.replace(year=date.year + 1, month=1)

    return date
