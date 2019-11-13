import sys


def supports_color(stream) -> bool:
    """ Determine whether an output stream (e.g. stdout/stderr) supports displaying colored text.

    A stream that is redirected to a file does not support color.
    """

    return stream.isatty() and hasattr(stream, 'isatty')


def colored(text: str, color: str) -> str:
    if not supports_color(sys.stdout):
        return text

    return f'{color}{text}{COLOR_RESET}'


COLOR_BRIGHT_WHITE = '\x1b[1;37m'
COLOR_POSITIVE = '\x1b[0;32m'
COLOR_NEGATIVE = '\x1b[0;33m'
COLOR_ALTERNATIVE = '\x1b[0;36m'
COLOR_RESET = '\x1b[0m'
