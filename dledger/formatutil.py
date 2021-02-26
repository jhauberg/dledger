import locale

from decimal import Decimal

from typing import Union


def format_amount(
    amount: float, *, trailing_zero: bool = True, rounded: bool = True, places: int = 2
) -> str:
    """Return a human-readable string for a number.

    Format according to current locale, for example,

      Danish locale:
        1000.6 => '1.000,60',
        1000.0 => '1.000',
        10.6 => '1,60'
        10 => '10'

    Only keep X decimal places for fractional (non-whole) numbers.
    """

    # convert value to str, rounding to N decimal places
    s = f"{amount:.{places}f}" if rounded else f"{amount}"

    # determine if number is fractional (assuming default point notation)
    pad = "0" * places
    if not trailing_zero and s.endswith(f".{pad}"):
        # only keep whole number
        i = 1 + places
        s = s[:-i]

    # convert str to Decimal, respecting the number of decimal places
    d = Decimal(s)

    # finally format using 'n', providing grouping/separators matching current locale
    return f"{d:n}"


def decimalplaces(value: Union[str, float, int]) -> int:
    """Return the number of places after a decimal separator.

    Use 'decimal_point' from current system locale to determine decimal separator.
    """
    if isinstance(value, int):
        return 0
    places = 0
    separator: str = locale.localeconv()["decimal_point"]  # type: ignore
    if isinstance(value, float):
        separator = "."  # assume always period separator for non-string values
        value = str(Decimal(f"{value}"))
    if isinstance(value, str):
        # reverse string and find first index of separator
        # this index corresponds to the number of decimal places
        separator_index = value[::-1].find(separator)
        if separator_index != -1:
            places = separator_index
        if places == 1 and value.endswith("0"):
            return 0
    return places
