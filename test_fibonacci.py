"""
test_fibonacci.py — Comprehensive pytest suite for fibonacci.py.

Run:
    pytest test_fibonacci.py -v --tb=short
"""

from __future__ import annotations

import pytest

from fibonacci import (
    _MAX_N,
    fibonacci,
    fibonacci_optimized,
    fibonacci_sequence,
)


# ---------------------------------------------------------------------------
# Known Fibonacci values used across multiple test classes
# ---------------------------------------------------------------------------

KNOWN_VALUES: list[tuple[int, int]] = [
    (0, 0),
    (1, 1),
    (2, 1),
    (3, 2),
    (4, 3),
    (5, 5),
    (6, 8),
    (7, 13),
    (8, 21),
    (9, 34),
    (10, 55),
    (15, 610),
    (20, 6765),
    (30, 832040),
    (50, 12586269025),
]


# ---------------------------------------------------------------------------
# fibonacci (tabulation, O(n) space)
# ---------------------------------------------------------------------------

class TestFibonacci:
    """Tests for the bottom-up tabulation implementation."""

    # --- Happy path ---

    @pytest.mark.parametrize("n, expected", KNOWN_VALUES)
    def test_known_values(self, n, expected):
        assert fibonacci(n) == expected

    def test_returns_int(self):
        assert isinstance(fibonacci(10), int)

    def test_large_value_is_correct(self):
        # F(100) is a well-known value
        assert fibonacci(100) == 354224848179261915075

    # --- Boundary / edge cases ---

    def test_n_equals_zero(self):
        assert fibonacci(0) == 0

    def test_n_equals_one(self):
        assert fibonacci(1) == 1

    def test_n_equals_two(self):
        assert fibonacci(2) == 1

    def test_n_equals_max(self):
        result = fibonacci(_MAX_N)
        assert isinstance(result, int)
        assert result > 0

    # --- Recurrence property ---

    @pytest.mark.parametrize("n", range(2, 20))
    def test_recurrence_relation(self, n):
        """F(n) == F(n-1) + F(n-2) for all n >= 2."""
        assert fibonacci(n) == fibonacci(n - 1) + fibonacci(n - 2)

    # --- TypeError ---

    @pytest.mark.parametrize("bad", [None, 3.0, "10", True, False, [1]])
    def test_raises_type_error(self, bad):
        with pytest.raises(TypeError):
            fibonacci(bad)

    # --- ValueError ---

    @pytest.mark.parametrize("bad", [-1, -50, _MAX_N + 1])
    def test_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            fibonacci(bad)


# ---------------------------------------------------------------------------
# fibonacci_optimized (O(1) space)
# ---------------------------------------------------------------------------

class TestFibonacciOptimized:
    """Tests for the space-optimized implementation."""

    @pytest.mark.parametrize("n, expected", KNOWN_VALUES)
    def test_known_values(self, n, expected):
        assert fibonacci_optimized(n) == expected

    def test_returns_int(self):
        assert isinstance(fibonacci_optimized(10), int)

    def test_n_equals_zero(self):
        assert fibonacci_optimized(0) == 0

    def test_n_equals_one(self):
        assert fibonacci_optimized(1) == 1

    def test_n_equals_two(self):
        assert fibonacci_optimized(2) == 1

    def test_large_value_is_correct(self):
        assert fibonacci_optimized(100) == 354224848179261915075

    def test_n_equals_max(self):
        result = fibonacci_optimized(_MAX_N)
        assert isinstance(result, int)
        assert result > 0

    @pytest.mark.parametrize("n", range(2, 20))
    def test_recurrence_relation(self, n):
        assert fibonacci_optimized(n) == fibonacci_optimized(n - 1) + fibonacci_optimized(n - 2)

    @pytest.mark.parametrize("bad", [None, 3.0, "10", True, False])
    def test_raises_type_error(self, bad):
        with pytest.raises(TypeError):
            fibonacci_optimized(bad)

    @pytest.mark.parametrize("bad", [-1, _MAX_N + 1])
    def test_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            fibonacci_optimized(bad)


# ---------------------------------------------------------------------------
# fibonacci_sequence
# ---------------------------------------------------------------------------

class TestFibonacciSequence:
    """Tests for the full-sequence generator."""

    def test_n_zero_returns_single_element(self):
        assert fibonacci_sequence(0) == [0]

    def test_n_one_returns_two_elements(self):
        assert fibonacci_sequence(1) == [0, 1]

    def test_n_five(self):
        assert fibonacci_sequence(5) == [0, 1, 1, 2, 3, 5]

    def test_n_ten(self):
        assert fibonacci_sequence(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]

    def test_returns_list(self):
        assert isinstance(fibonacci_sequence(5), list)

    def test_length_is_n_plus_one(self):
        for n in range(0, 15):
            assert len(fibonacci_sequence(n)) == n + 1

    def test_all_elements_are_int(self):
        for val in fibonacci_sequence(20):
            assert isinstance(val, int)

    def test_first_element_is_zero(self):
        for n in range(0, 10):
            assert fibonacci_sequence(n)[0] == 0

    def test_last_element_matches_fibonacci(self):
        for n in range(0, 20):
            seq = fibonacci_sequence(n)
            assert seq[-1] == fibonacci(n)

    def test_each_element_matches_fibonacci(self):
        seq = fibonacci_sequence(15)
        for i, val in enumerate(seq):
            assert val == fibonacci(i)

    @pytest.mark.parametrize("n", range(2, 20))
    def test_recurrence_holds_within_sequence(self, n):
        seq = fibonacci_sequence(n)
        for i in range(2, len(seq)):
            assert seq[i] == seq[i - 1] + seq[i - 2]

    def test_n_equals_max_returns_correct_length(self):
        seq = fibonacci_sequence(_MAX_N)
        assert len(seq) == _MAX_N + 1

    # --- TypeError ---

    @pytest.mark.parametrize("bad", [None, 3.0, "5", True, False, []])
    def test_raises_type_error(self, bad):
        with pytest.raises(TypeError):
            fibonacci_sequence(bad)

    # --- ValueError ---

    @pytest.mark.parametrize("bad", [-1, -100, _MAX_N + 1])
    def test_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            fibonacci_sequence(bad)


# ---------------------------------------------------------------------------
# Cross-function consistency
# ---------------------------------------------------------------------------

class TestCrossConsistency:
    """Ensure all three public functions agree with each other."""

    @pytest.mark.parametrize("n", [0, 1, 2, 5, 10, 20, 50])
    def test_all_three_agree(self, n):
        tab = fibonacci(n)
        opt = fibonacci_optimized(n)
        seq = fibonacci_sequence(n)[-1]
        assert tab == opt == seq, (
            f"Mismatch at n={n}: tabulation={tab}, optimized={opt}, sequence[-1]={seq}"
        )

    def test_sequence_prefix_matches_individual_calls(self):
        n = 25
        seq = fibonacci_sequence(n)
        for i in range(n + 1):
            assert seq[i] == fibonacci(i), f"Mismatch at index {i}"
