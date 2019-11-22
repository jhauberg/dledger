import locale

from typing import List, Optional, Any


def trysetlocale(category: Any, locales: List[str]) -> Optional[str]:
    """ Set first supported locale in a list of locales. """

    for supported_locale in locales:
        try:
            locale.setlocale(category, supported_locale)
            return supported_locale
        except (locale.Error, ValueError):
            continue

    return None
