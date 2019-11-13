import os
import errno
import shutil
import filecmp


from typing import Tuple, Optional


def fileencoding(path: str) -> Optional[str]:
    supported_encodings = [
        'utf-8',
        'utf-16',
        'cp1252'
    ]

    for encoding in supported_encodings:
        try:
            with open(path, encoding=encoding) as file:
                if file.read():
                    return encoding
        except UnicodeDecodeError:
            continue

    return None


def make_dirs(path: str) -> bool:
    try:
        os.makedirs(path)

        return True
    except OSError as error:
        if error.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

    return False


def copy_to(source_path: str, destination_path: str) -> Tuple[bool, bool]:
    file_already_exists = os.path.exists(destination_path)

    if not file_already_exists or not filecmp.cmp(source_path, destination_path):
        # the file doesn't already exist, or it does exist, but is different
        try:
            shutil.copyfile(source_path, destination_path)

            return True, file_already_exists
        except IOError:
            pass

    return False, file_already_exists
