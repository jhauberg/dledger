import locale

from contextlib import contextmanager

from typing import Iterator

DECIMAL_POINT_PERIOD = {
    "decimal_point": ".",
    "thousands_sep": ","
}

DECIMAL_POINT_COMMA = {
    "decimal_point": ",",
    "thousands_sep": "."
}


@contextmanager
def tempconv(props: dict) -> Iterator[None]:
    """Override specific properties in currently active locale."""
    impl = locale.localeconv
    conv = locale.localeconv()

    def _localeconv():
        _conv = {k: v for k, v in conv.items()}
        _conv.update(props)
        return _conv

    locale.localeconv = _localeconv
    yield
    locale.localeconv = impl
