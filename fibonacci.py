"""
fibonacci.py — Fibonacci number computation using dynamic programming.

Provides three DP-based approaches:
  - fibonacci(n)          : bottom-up tabulation, O(n) time, O(n) space
  - fibonacci_optimized(n): bottom-up with O(1) space
  - fibonacci_sequence(n) : returns the full sequence [F(0)..F(n)]
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Upper bound on *n* to prevent runaway memory allocation.  Values close to
# this cap can take noticeable time and memory because Python ints for large
# Fibonacci numbers have thousands of digits.
_MAX_N: int = 10_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_n(n: object) -> int:
    """Validate that *n* is a non-negative integer and return it as ``int``.

    Raises
    ------
    TypeError
        If *n* is not an integer type (``bool`` is a subclass of ``int`` in
        Python but semantically wrong here, so it is explicitly rejected).
    ValueError
        If *n* is negative or exceeds ``_MAX_N``.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(
            f"n must be a non-negative integer, got {type(n).__name__!r}"
        )
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if n > _MAX_N:
        raise ValueError(
            f"n must be <= {_MAX_N} to prevent excessive memory use, got {n}"
        )
    return n


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fibonacci(n: int) -> int:
    """Return the *n*-th Fibonacci number using bottom-up DP (tabulation).

    The sequence is zero-indexed: F(0) = 0, F(1) = 1, F(2) = 1, …

    Parameters
    ----------
    n:
        Index of the desired Fibonacci number.  Must be a non-negative
        integer no greater than ``fibonacci._MAX_N``.

    Returns
    -------
    int
        The *n*-th Fibonacci number.

    Raises
    ------
    TypeError
        If *n* is not an ``int`` (``bool`` values are also rejected).
    ValueError
        If *n* < 0 or *n* > ``_MAX_N``.

    Examples
    --------
    >>> fibonacci(0)
    0
    >>> fibonacci(1)
    1
    >>> fibonacci(10)
    55
    """
    n = _validate_n(n)
    if n < 2:
        return n

    dp: list[int] = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]


def fibonacci_optimized(n: int) -> int:
    """Return the *n*-th Fibonacci number using O(1) space bottom-up DP.

    Identical semantics to :func:`fibonacci` but uses only two variables
    instead of a full table, reducing space complexity from O(n) to O(1).

    Parameters
    ----------
    n:
        Index of the desired Fibonacci number.

    Returns
    -------
    int
        The *n*-th Fibonacci number.

    Raises
    ------
    TypeError
        If *n* is not an ``int`` (``bool`` values are also rejected).
    ValueError
        If *n* < 0 or *n* > ``_MAX_N``.

    Examples
    --------
    >>> fibonacci_optimized(0)
    0
    >>> fibonacci_optimized(7)
    13
    """
    n = _validate_n(n)
    if n < 2:
        return n

    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    return curr


def fibonacci_sequence(n: int) -> list[int]:
    """Return the Fibonacci sequence from F(0) through F(n) inclusive.

    Parameters
    ----------
    n:
        Upper index (inclusive).  Must be a non-negative integer no greater
        than ``_MAX_N``.

    Returns
    -------
    list[int]
        A list of length *n* + 1 where ``result[i] == F(i)``.

    Raises
    ------
    TypeError
        If *n* is not an ``int`` (``bool`` values are also rejected).
    ValueError
        If *n* < 0 or *n* > ``_MAX_N``.

    Examples
    --------
    >>> fibonacci_sequence(0)
    [0]
    >>> fibonacci_sequence(5)
    [0, 1, 1, 2, 3, 5]
    """
    n = _validate_n(n)

    seq: list[int] = [0] * (n + 1)
    if n >= 1:
        seq[1] = 1
    for i in range(2, n + 1):
        seq[i] = seq[i - 1] + seq[i - 2]
    return seq
