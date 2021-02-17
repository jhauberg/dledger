from typing import Optional


def fileencoding(path: str) -> Optional[str]:
    supported_encodings = ["utf-8", "utf-16", "cp1252"]

    for encoding in supported_encodings:
        try:
            with open(path, encoding=encoding) as file:
                if file.read():
                    return encoding
        except UnicodeDecodeError:
            continue

    return None
