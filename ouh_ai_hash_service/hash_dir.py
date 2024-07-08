import os
import hashlib
import base64
from pathlib import Path
import logging


def hash_dir(directory_path: Path) -> str:
    """
    Iterates through every file, collects the information
    of the file and includes that information in the final
    returned hash string.
    We do not hash the filepaths along. Therefore,
    the method can be used for comparing
    if two directories are identical.
    If identical both directories produce the same
    has.

    :param directory_path: Path that should be hashed
    :type directory_path: Path
    :return: 15 digit long hash
    :rtype: int | bytes
    """
    hash_object = hashlib.md5()
    for root, dirs, files in os.walk(directory_path):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                with open(file_path, 'rb') as file:
                    # Read in 4096-byte sized chunks of the current file
                    # until the sentinel value b"" (i.e. empty byte object)
                    # The choice of 4096 bytes as the chunk size is arbitrary.
                    # But it's small enough that it won't use too much memory,
                    # but large enough that the overhead of looping and function calls won't dominate the time taken.
                    for chunk in iter(lambda: file.read(4096), b""):
                        hash_object.update(chunk)
            except IOError:
                logging.error(f"Could not read file {file_path}. Skipping...")

    # Get the binary digest
    hash: str = hash_object.hexdigest()

    return hash
