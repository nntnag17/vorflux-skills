"""
test_fibonacci.py — Comprehensive pytest suite for fibonacci.py.

Run:
    pytest test_fibonacci.py -v --tb=short
    pytest test_fibonacci.py -v --cov=fibonacci --cov-report=term-missing
"""

from __future__ import annotations

import pytest

from fibonacci import (
    _MAX_N,
    _validate_n,
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
# _validate_n
# ---------------------------------------------------------------------------

class TestValidateN:
    """Unit tests for the internal _validate_n helper."""

    def test_returns_int_for_valid_input(self):
        assert _validate_n(5) == 5

    def test_returns_zero(self):
        assert _validate_n(0) == 0

    def test_returns_max_n(self):
        assert _validate_n(_MAX_N) == _MAX_N

    # --- TypeError cases ---

    @pytest.mark.parametrize("bad_input", [
        None,
        3.0,
        "5",
        [5],
        (5,),
        {},
        3.14,
        complex(1, 2),
    ])
    def test_raises_type_error_for_non_int(self, bad_input):
        with pytest.raises(TypeError, match="non-negative integer"):
            _validate_n(bad_input)

    def test_raises_type_error_for_bool_true(self):
        """bool is a subclass of int; must be explicitly rejected."""
        with pytest.raises(TypeError, match="non-negative integer"):
            _validate_n(True)

    def test_raises_type_error_for_bool_false(self):
        with pytest.raises(TypeError, match="non-negative integer"):
            _validate_n(False)

    # --- ValueError cases ---

    @pytest.mark.parametrize("negative", [-1, -100, -10_000])
    def test_raises_value_error_for_negative(self, negative):
        with pytest.raises(ValueError, match=">= 0"):
            _validate_n(negative)

    def test_raises_value_error_for_exceeding_max(self):
        with pytest.raises(ValueError, match=str(_MAX_N)):
            _validate_n(_MAX_N + 1)

    def test_raises_value_error_for_large_n(self):
        with pytest.raises(ValueError):
            _validate_n(999_999)


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

    # --- Monotonicity ---

    def test_sequence_is_non_decreasing(self):
        values = [fibonacci(i) for i in range(20)]
        for i in range(1, len(values)):
            assert values[i] >= values[i - 1]

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

    def test_raises_for_negative_large(self):
        with pytest.raises(ValueError):
            fibonacci(-1_000_000)


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

    # --- Consistency with tabulation ---

    @pytest.mark.parametrize("n", range(0, 51))
    def test_matches_tabulation(self, n):
        """Both implementations must agree on every value."""
        assert fibonacci_optimized(n) == fibonacci(n)


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
