from decimal import Decimal


def format_amount(amount: float, *,
                  trailing_zero: bool = True,
                  rounded: bool = True,
                  places: int = 2) \
        -> str:
    """ Return a human-readable string for a number.

    Format according to current locale, for example,

      Danish locale:
        1000.6 => '1.000,60',
        1000.0 => '1.000',
        10.6 => '1,60'
        10 => '10'

    Only keep X decimal places for fractional (non-whole) numbers.
    """

    # convert value to str, rounding to N decimal places
    s = f'{amount:.{places}f}' if rounded else f'{amount}'

    # determine if number is fractional (assuming default point notation)
    pad = '0' * places
    if not trailing_zero and s.endswith(f'.{pad}'):
        # only keep whole number
        i = 1 + places
        s = s[:-i]

    # convert str to Decimal, respecting the number of decimal places
    d = Decimal(s)

    # finally format using 'n', providing grouping/separators matching current locale
    return f'{d:n}'
