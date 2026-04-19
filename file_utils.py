"""Utility functions for file operations."""

import os
from typing import Union


def count_lines(filepath: Union[str, "os.PathLike[str]"]) -> int:
    """Read a file and return the number of lines it contains.

    Lines are counted by newline characters (``\\n``), matching the behaviour
    of Python's text-mode file iterator.  The function works with any file
    encoding because it reads in binary mode.

    Args:
        filepath: Path to the file to read.  Accepts a ``str`` or any
            ``os.PathLike`` object (e.g. ``pathlib.Path``).

    Returns:
        The number of lines in the file.  An empty file returns 0.

    Raises:
        TypeError: If *filepath* is not a ``str`` or ``os.PathLike``.
        FileNotFoundError: If the file does not exist at the given path.
        IsADirectoryError: If the path points to a directory, not a file.
        PermissionError: If the process lacks read permission for the file.
        OSError: For other OS-level I/O errors.
    """
    if not isinstance(filepath, (str, os.PathLike)):
        raise TypeError(
            f"filepath must be a str or os.PathLike, got {type(filepath).__name__!r}"
        )

    with open(filepath, "rb") as fh:
        return sum(1 for _ in fh)
