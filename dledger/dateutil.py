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

    If strict is True, a full datestamp is expected (year/month/day).

    Otherwise, a datestamp can be specified in any of the following variations:

        "2019/11/11" => 2019/11/11
        "2019/11"    => 2019/11/01
        "2019"       => 2019/01/01

        or

        "2019-11-11" => 2019/11/11
        "2019-11"    => 2019/11/01
        "2019"       => 2019/01/01

    Components omitted will default to the first of year or month.
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
        -> Tuple[Optional[date], Optional[date]]:
    datestamps = interval.split(':')

    if len(datestamps) > 2 or len(datestamps) == 0:
        raise ValueError('malformed interval')

    starting_datestamp = datestamps[0].strip()
    starting: Optional[date] = None

    if len(starting_datestamp) > 0:
        starting, _ = parse_period_component(starting_datestamp)

    ending_datestamp: Optional[str] = datestamps[1].strip() if len(datestamps) > 1 else None
    ending: Optional[date] = None

    if ending_datestamp is not None and len(ending_datestamp) > 0:
        ending, _ = parse_period_component(ending_datestamp)

    if starting is not None and ending is not None:
        if starting > ending:
            # flip dates such that starting is always earlier
            tmp = starting
            starting = ending
            ending = tmp

    return starting, ending


def parse_period_component(component: str) -> Tuple[date, date]:
    """ Return the date interval that exactly includes the period corresponding to a component.

    A period component can be either a full or partial datestamp, or a pre-defined textual key that
    maps to a specific date.

    For example, if period component is 'today', then the date interval will range from
    today to tomorrow, exactly including only today. Similarly, if component is '2019', then the
    date interval will range from 2019/01/01 to 2020/01/01, including the full year period of 2019.
    """
    today = datetime.today().date()
    component = component.lower()
    try:
        month = int(component)  # if component is a single number, then it might indicate month
        if 0 < month <= 12:  # component assumed to indicate month
            starting = date(today.year, month, 1)
            return starting, next_month(starting)
        else:  # component assumed to indicate year; parsed as normal datestamp later
            pass
    except ValueError:  # component assumed to be typical datestamp or textual key
        pass
    if component == 'today':
        return today, today + timedelta(days=1)
    if component == 'tomorrow':
        return today + timedelta(days=1), today + timedelta(days=2)
    if component == 'yesterday':
        return today + timedelta(days=-1), today
    # check against month names (both abbreviated and full e.g. 'march', 'jun', etc.)
    matching_month_names = [month_name for month_name in calendar.month_name if
                            month_name.lower().startswith(component)]
    # note that a combination of component types is not supported for the time being
    # as it would require parse_datestamp() to include this bit and automatically
    # letting the format loose in journal entries as well; e.g. `2019/mar/14 A  $ 2`
    # might reconsider later
    if len(matching_month_names) == 1:  # ambiguous if more than one match; move on
        for month_index, month_name in enumerate(calendar.month_name):
            print(month_name)
            if month_name == matching_month_names[0]:
                starting = date(today.year, month_index, 1)
                return starting, next_month(starting)
    # assume component is typical datestamp, as no textual keys match
    starting = parse_datestamp(component)
    # determine number of datestamp components
    # (assuming valid datestamp; i.e. only one separator kind, no combination)
    num_separators = max(component.count('/'),
                         component.count('-'))
    if num_separators > 2:  # too many components
        raise ValueError(f'invalid date format (\'{component}\')')
    if num_separators == 0:  # year component
        return starting, starting.replace(year=starting.year + 1)
    if num_separators == 1:  # year and month components
        return starting, next_month(starting)
    # year, month and day components
    return starting, starting + timedelta(days=1)


def parse_period(interval: str) \
        -> Tuple[Optional[date], Optional[date]]:
    interval = interval.strip()
    if ':' in interval:
        return parse_interval(interval)
    return parse_period_component(interval)

