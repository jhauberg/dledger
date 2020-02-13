import os
import sys

# color escape sequences
COLOR_NEGATIVE = '\x1b[0;33m'
COLOR_MARKED = '\x1b[0;30;47m'
COLOR_RESET = '\x1b[0m'

# windows specific handles
STD_OUTPUT_HANDLE = -11
# windows specific flags
ENABLE_PROCESSED_OUTPUT = 0x0001
ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004


def supports_color(stream) -> bool:  # type: ignore
    """ Determine whether an output stream (e.g. stdout/stderr) supports displaying colored text.

    A stream that is redirected to a file does not support color.
    """

    return stream.isatty() and hasattr(stream, 'isatty')


def colored(text: str, color: str) -> str:
    if not supports_color(sys.stdout):
        return text

    return f'{color}{text}{COLOR_RESET}'


def is_windows_environment() -> bool:
    """ Return True if on a Windows platform, False otherwise. """

    return os.name == 'nt'


def enable_color_escapes() -> None:
    """ Enable terminal color support. """

    if not is_windows_environment():
        return

    # enable color escape processing on Windows
    # see https://stackoverflow.com/a/36760881/144433
    import ctypes

    kernel32 = ctypes.windll.kernel32  # type: ignore
    handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

    mode = (ENABLE_PROCESSED_OUTPUT |
            ENABLE_WRAP_AT_EOL_OUTPUT |
            ENABLE_VIRTUAL_TERMINAL_PROCESSING)

    kernel32.SetConsoleMode(handle, mode)
