"""Utility functions for file operations."""

import os


def count_lines(filepath: str) -> int:
    """Read a file and return the number of lines it contains.

    Args:
        filepath: Path to the file to read.

    Returns:
        The number of lines in the file. An empty file returns 0.

    Raises:
        TypeError: If filepath is not a string.
        FileNotFoundError: If the file does not exist at the given path.
        IsADirectoryError: If the path points to a directory, not a file.
        PermissionError: If the process lacks read permission for the file.
        OSError: For other OS-level I/O errors.
    """
    if not isinstance(filepath, str):
        raise TypeError(f"filepath must be a str, got {type(filepath).__name__!r}")

    with open(filepath, "r", encoding="utf-8") as fh:
        return sum(1 for _ in fh)
