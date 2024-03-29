import calendar

from datetime import datetime, timedelta, date

from typing import Tuple, Optional, List


def todayd() -> date:
    """Return today's date.
    This function should always be used to determine today's date.
    For debugging purposes, the function may return any other date.
    """
    return datetime.today().date()


def is_weekend(d: date) -> bool:
    return d.weekday() in [5, 6]


def closest_weekday(d: date) -> date:
    weekday = d.weekday()
    if weekday in [0, 1, 2, 3, 4]:
        return d
    if weekday == 5:
        return d - timedelta(days=1)
    if weekday == 6:
        return d + timedelta(days=1)


def next_weekday(d: date) -> date:
    d = d + timedelta(days=1)
    weekday = d.weekday()
    if weekday not in [5, 6]:
        return d
    days_to_weekday = 6 - weekday + 1
    return d + timedelta(days=days_to_weekday)


def previous_friday(d: date) -> date:
    weekday = d.weekday()
    if weekday in [5, 6]:
        return d - timedelta(days=weekday - 4)
    return d - timedelta(weeks=1) + timedelta(days=4 - weekday)


def is_within_period(a: date, starting: date, ending: date) -> bool:
    """Determine whether a date is within a period.

    Start is inclusive; end is exclusive.
    """
    return ending > a >= starting


def days_between(a: date, b: date) -> int:
    """Return the number of days between two dates.

    The result is an unsigned number of days;
    i.e. whether `a` is earlier or later than `b` makes no difference.
    """

    return abs((a - b).days)


def months_between(a: date, b: date, *, ignore_years: bool = False) -> int:
    """Return the number of months between two dates.

    The result is an unsigned number of months;
    i.e. whether `a` is earlier or later than `b` makes no difference.

    Does not take days into account.

    For example, 2019-05-20 - 2019-06-20 is exactly 1 month apart, but so is
    2019-05-20 - 2019-06-29 or 2019-06-01.

    If `ignore_years` is `True`, do not take years into account.

    For example, 2019-05-20 - 2020-07-20 is exactly 14 months apart,
    but only 2 months apart if `ignore_years` is `True`.
    """

    future = max([a, b])
    past = min([a, b])

    months = future.month - past.month + 12 * (future.year - past.year)

    if ignore_years:
        months = months % 12
        if months == 0:
            months = 12

    return months


def months_in_quarter(quarter: int) -> List[int]:
    """Return the months in a given quarter.

    There are always 3 months in a valid quarter (1-4).

    Months are ordered such that January is `1` and December is `12`.
    """

    if quarter < 1 or quarter > 4:
        raise ValueError("quarter must be within 1-4 range")

    number_of_months = 3
    starting_month = ((quarter - 1) * number_of_months) + 1

    return [month for month in range(starting_month, starting_month + number_of_months)]


def next_quarter(quarter: int) -> int:
    if quarter < 1 or quarter > 4:
        raise ValueError("quarter must be within 1-4 range")
    return (quarter + 1 - 1) % 4 + 1


def previous_quarter(quarter: int) -> int:
    if quarter < 1 or quarter > 4:
        raise ValueError("quarter must be within 1-4 range")
    return (quarter - 1 + 4 - 1) % 4 + 1


def in_months(d: date, months: int) -> date:
    """Return the date in a number of months."""

    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])

    return d.replace(year=year, month=month, day=day)


def last_of_month(d: date) -> date:
    """Return the date at the last day of the month."""

    return previous_month(next_month(d))


def first_of_month(d: date) -> date:
    """Return the date at the first day of the month."""

    return d.replace(day=1)


def previous_month(d: date) -> date:
    """Return the date at the last day of the previous month."""

    d = first_of_month(d)
    # then backtrack by 1 day to find previous month
    d -= timedelta(days=1)

    return d


def next_month(d: date) -> date:
    """Return the date at the first day of the following month."""

    d = first_of_month(d)

    try:
        # try fast-forwarding 1 month
        d = d.replace(month=d.month + 1)
    except ValueError:
        if d.month == 12:
            # fast-forward to next year
            d = d.replace(year=d.year + 1, month=1)

    return d


def parse_month(name: str) -> Optional[int]:
    """Return the month that unambiguously matches name partially or fully.

    Return `None` if more than one month matches.

    Month names that are matched against are localized according to the
    currently active system locale.
    """
    comparable_name = name.lower()
    months = [
        n
        for n, m in enumerate(calendar.month_name)
        if n > 0 and m.lower().startswith(comparable_name)
    ]
    # ambiguous if more than one match; return None
    return months[0] if len(months) == 1 else None


def parse_datestamp(datestamp: str, *, strict: bool = False) -> date:
    """Return the date that maps to datestamp.

    If `strict` is `True`, a full datestamp is expected (year/month/day):

        "2019/11/11" => 2019/11/11

    Otherwise, a datestamp can be specified in any of the following variations:

        "2019/11"    => 2019/11/01
        "2019"       => 2019/01/01

    Components omitted will default to the first of year or month.
    """

    strict_formats = ["%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"]
    month_formats = ["%Y/%m", "%Y-%m", "%Y.%m"]
    year_formats = ["%Y"]

    def tryparse(string: str, formats: List[str]) -> Optional[date]:
        for fmt in formats:
            try:
                return datetime.strptime(string, fmt).date()
            except ValueError:
                continue
        return None

    d = tryparse(datestamp, formats=strict_formats)

    if d is None:
        if strict:
            raise ValueError(
                f"invalid date format ('{datestamp}'; expected strict format)"
            )
        other_formats = month_formats + year_formats
        d = tryparse(datestamp, formats=other_formats)
        if d is None:
            raise ValueError(f"invalid date format ('{datestamp}')")
    return d


def parse_interval(interval: str) -> Tuple[Optional[date], Optional[date]]:
    datestamps = interval.split(":")

    if len(datestamps) > 2 or len(datestamps) == 0:
        raise ValueError("malformed interval")

    starting_datestamp = datestamps[0].strip()
    starting: Optional[date] = None

    if len(starting_datestamp) > 0:
        starting, _ = parse_period_component(starting_datestamp)

    ending_datestamp: Optional[str] = (
        datestamps[1].strip() if len(datestamps) > 1 else None
    )
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
    """Return the date interval that exactly includes the period corresponding
    to a component.

    A period component can be either a full or partial datestamp, or a
    pre-defined textual key that maps to a specific date.

    For example, if period component is 'today', then the date interval will
    range from today to tomorrow, exactly including only today.
    Similarly, if component is '2019', then the date interval will range from
    2019/01/01 to 2020/01/01, including the full year period of 2019.
    """
    today = todayd()
    component = component.lower()
    month: Optional[int]
    try:
        month = int(component)  # a single number typically indicates month
        if 0 < month <= 12:  # component assumed to indicate month
            starting = date(today.year, month, 1)
            return starting, next_month(starting)
        else:  # component assumed to indicate year; parsed as normal datestamp later
            pass
    except ValueError:  # component assumed to be typical datestamp or textual key
        pass
    default_month_keys = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]
    textual_keys = [
        "today", "tomorrow", "yesterday",
        "q1", "q2", "q3", "q4",
    ]
    # note that we include english named months here as the default option
    # this allows us to not have to trigger any change in system locale
    # (otherwise this would require two changes;
    # first to en_US, then another back to what it was initially)
    textual_keys.extend(default_month_keys)
    matching_keys = [k for k in textual_keys if k.startswith(component)]
    if len(matching_keys) == 1:
        component = matching_keys[0]
    if component == "today":
        return today, today + timedelta(days=1)
    if component == "tomorrow":
        return today + timedelta(days=1), today + timedelta(days=2)
    if component == "yesterday":
        return today + timedelta(days=-1), today
    if component == "q1" or component == "q2" or component == "q3" or component == "q4":
        starting_month, _, ending_month = months_in_quarter(int(component[-1]))
        return date(today.year, starting_month, 1), next_month(
            date(today.year, ending_month, 1)
        )
    if component in default_month_keys:
        starting = date(today.year, default_month_keys.index(component) + 1, 1)
        return starting, next_month(starting)
    # check against localized month names
    # (both full and abbreviated e.g. 'march', 'jun', etc.)
    month = parse_month(component)
    if month is not None:
        # todo: it's not easy to reach this point for a test;
        #       requires atypical language locale
        starting = date(today.year, month, 1)
        return starting, next_month(starting)
    # assume component is typical datestamp, as no textual keys match
    # note that a combination of component types is not supported for the time being
    # as it would require parse_datestamp() to include this bit and automatically
    # letting the format loose in journal entries as well; e.g. `2019/mar/14 A  $ 2`
    # might reconsider later
    starting = parse_datestamp(component)
    # determine number of datestamp components
    # (assuming valid datestamp; i.e. only one separator kind, no combination)
    num_separators = max(
        component.count("/"),
        component.count("-"),
        component.count(".")
    )
    assert num_separators < 3
    if num_separators == 0:  # year component
        return starting, starting.replace(year=starting.year + 1)
    if num_separators == 1:  # year and month components
        return starting, next_month(starting)
    # year, month and day components
    return starting, starting + timedelta(days=1)


def parse_period(interval: str) -> Tuple[Optional[date], Optional[date]]:
    interval = interval.strip()
    if ":" in interval:
        return parse_interval(interval)
    return parse_period_component(interval)
