"""Unit tests for file_utils.count_lines."""

import os
import stat
import tempfile
from pathlib import Path

import pytest

from file_utils import count_lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_tmp(content: bytes) -> str:
    """Write *content* (bytes) to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "wb") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestCountLinesHappyPath:
    def test_single_line_no_newline(self):
        path = _write_tmp(b"hello world")
        try:
            assert count_lines(path) == 1
        finally:
            os.unlink(path)

    def test_single_line_with_trailing_newline(self):
        path = _write_tmp(b"hello world\n")
        try:
            assert count_lines(path) == 1
        finally:
            os.unlink(path)

    def test_multiple_lines(self):
        path = _write_tmp(b"line1\nline2\nline3\n")
        try:
            assert count_lines(path) == 3
        finally:
            os.unlink(path)

    def test_multiple_lines_no_trailing_newline(self):
        path = _write_tmp(b"line1\nline2\nline3")
        try:
            assert count_lines(path) == 3
        finally:
            os.unlink(path)

    def test_empty_file_returns_zero(self):
        path = _write_tmp(b"")
        try:
            assert count_lines(path) == 0
        finally:
            os.unlink(path)

    def test_blank_lines_are_counted(self):
        path = _write_tmp(b"\n\n\n")
        try:
            assert count_lines(path) == 3
        finally:
            os.unlink(path)

    def test_utf8_content(self):
        path = _write_tmp("こんにちは\n世界\n".encode("utf-8"))
        try:
            assert count_lines(path) == 2
        finally:
            os.unlink(path)

    def test_latin1_content(self):
        """Non-UTF-8 files must not raise UnicodeDecodeError."""
        path = _write_tmp("café\nnaïve\n".encode("latin-1"))
        try:
            assert count_lines(path) == 2
        finally:
            os.unlink(path)

    def test_utf16_content(self):
        """UTF-16 encoded files should be counted without error."""
        path = _write_tmp("hello\nworld\n".encode("utf-16"))
        try:
            # Binary mode: the BOM + encoded bytes may produce extra "lines"
            # depending on content, but the call must not raise.
            result = count_lines(path)
            assert isinstance(result, int)
            assert result >= 0
        finally:
            os.unlink(path)

    def test_accepts_pathlib_path(self):
        """pathlib.Path objects must be accepted without TypeError."""
        path = _write_tmp(b"a\nb\nc\n")
        try:
            assert count_lines(Path(path)) == 3
        finally:
            os.unlink(path)

    def test_accepts_str_path(self):
        path = _write_tmp(b"x\n")
        try:
            assert count_lines(path) == 1
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

    def test_non_string_non_pathlike_raises_type_error(self):
        with pytest.raises(TypeError):
            count_lines(123)  # type: ignore[arg-type]

    def test_none_filepath_raises_type_error(self):
        with pytest.raises(TypeError):
            count_lines(None)  # type: ignore[arg-type]

    def test_permission_denied(self):
        path = _write_tmp(b"secret\n")
        try:
            os.chmod(path, 0o000)
            with pytest.raises(PermissionError):
                count_lines(path)
        finally:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            os.unlink(path)
