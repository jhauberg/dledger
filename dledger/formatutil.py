from decimal import Decimal


def change(a: float, b: float) -> float:
    """ Return the difference from A, to B. """

    return a - b


def pct_change(a: float, b: float) -> float:
    """ Return the %-change from A, to B. """

    if not (b > 0 or b < 0):
        raise TypeError('\'b\' must be a negative or positive value')

    diff = a - b
    pct = (diff / b) * 100

    return pct


def format_pct(pct: float) -> str:
    """ Return a human-readable string for a percentage value. """

    return f'{format_amount(pct, trailing_zero=False)}%'


def format_pct_change(pct: float) -> str:
    """ Return a human-readable string for a percentage value (change).

    Format according to current locale, for example,

      Danish locale:
        1000.6 => '+ 1.000,60%'
        10.6 => '+ 10,60%'

    Always keep 2 decimal places.
    """

    sign = '-' if pct < 0 else '+'
    # convert value to str, rounding to 2 decimal places
    s = f'{abs(pct):.2f}'
    # convert str to Decimal, keeping decimal precision intact
    d = Decimal(s)

    # finally format using 'n', providing grouping/separators matching current locale
    return f'{sign} {d:n}%'


def format_change(amount: float) -> str:
    """ Return a human-readable string for a change in totals. """

    sign = '-' if amount < 0 else '+'

    return f'{sign} {format_amount(abs(amount))}'


def format_amount(amount: float, trailing_zero: bool = True) -> str:
    """ Return a human-readable string for a number.

    Format according to current locale, for example,

      Danish locale:
        1000.6 => '1.000,60',
        1000.0 => '1.000',
        10.6 => '1,60'
        10 => '10'

    Only keep 2 decimal places for fractional (non-whole) numbers.
    """

    # convert value to str, rounding to 2 decimal places
    s = f'{amount:.2f}'

    # determine if number is fractional (assuming default point notation)
    if not trailing_zero and s.endswith('.00'):
        # only keep whole number
        s = s[:-3]

    # convert str to Decimal, respecting the number of decimal places
    d = Decimal(s)

    # finally format using 'n', providing grouping/separators matching current locale
    return f'{d:n}'
