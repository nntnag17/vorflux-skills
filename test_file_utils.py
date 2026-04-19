"""Unit tests for file_utils.count_lines."""

import os
import stat
import tempfile

import pytest

from file_utils import count_lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_tmp(content: str) -> str:
    """Write *content* to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestCountLinesHappyPath:
    def test_single_line_no_newline(self):
        path = _write_tmp("hello world")
        try:
            assert count_lines(path) == 1
        finally:
            os.unlink(path)

    def test_single_line_with_trailing_newline(self):
        path = _write_tmp("hello world\n")
        try:
            assert count_lines(path) == 1
        finally:
            os.unlink(path)

    def test_multiple_lines(self):
        path = _write_tmp("line1\nline2\nline3\n")
        try:
            assert count_lines(path) == 3
        finally:
            os.unlink(path)

    def test_multiple_lines_no_trailing_newline(self):
        path = _write_tmp("line1\nline2\nline3")
        try:
            assert count_lines(path) == 3
        finally:
            os.unlink(path)

    def test_empty_file_returns_zero(self):
        path = _write_tmp("")
        try:
            assert count_lines(path) == 0
        finally:
            os.unlink(path)

    def test_blank_lines_are_counted(self):
        # Three blank lines (two newlines produce three "lines" in Python's iterator)
        path = _write_tmp("\n\n\n")
        try:
            assert count_lines(path) == 3
        finally:
            os.unlink(path)

    def test_unicode_content(self):
        path = _write_tmp("こんにちは\n世界\n")
        try:
            assert count_lines(path) == 2
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------

class TestCountLinesErrorHandling:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            count_lines("/nonexistent/path/to/file.txt")

    def test_directory_raises_is_a_directory_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(IsADirectoryError):
                count_lines(tmpdir)

    def test_non_string_filepath_raises_type_error(self):
        with pytest.raises(TypeError):
            count_lines(123)  # type: ignore[arg-type]

    def test_none_filepath_raises_type_error(self):
        with pytest.raises(TypeError):
            count_lines(None)  # type: ignore[arg-type]

    def test_permission_denied(self):
        path = _write_tmp("secret\n")
        try:
            os.chmod(path, 0o000)
            with pytest.raises(PermissionError):
                count_lines(path)
        finally:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            os.unlink(path)
