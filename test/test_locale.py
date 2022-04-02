import locale

from dledger.localeutil import (
    tempconv,
    DECIMAL_POINT_PERIOD,
    DECIMAL_POINT_COMMA,
)


def test_localeconv_override():
    previous_decimal_point = locale.localeconv()["decimal_point"]

    assert previous_decimal_point == "." or previous_decimal_point == ","

    with tempconv(DECIMAL_POINT_PERIOD):
        assert locale.localeconv()["decimal_point"] == "."

    assert locale.localeconv()["decimal_point"] == previous_decimal_point

    with tempconv(DECIMAL_POINT_COMMA):
        assert locale.localeconv()["decimal_point"] == ","

    assert locale.localeconv()["decimal_point"] == previous_decimal_point
