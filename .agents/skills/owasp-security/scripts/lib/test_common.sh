#!/usr/bin/env bash
# test_common.sh — Smoke tests for scripts/lib/common.sh helpers.
#
# Run directly: bash scripts/lib/test_common.sh
# Exit code: 0 on success, 1 on any failure.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

FAILED=0
PASSED=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  PASS: $desc"
    PASSED=$((PASSED + 1))
  else
    echo "  FAIL: $desc  expected=$expected  actual=$actual"
    FAILED=$((FAILED + 1))
  fi
}

# Build an isolated temp fixture tree.
FIXTURE="$(mktemp -d)"
trap 'rm -rf "$FIXTURE"' EXIT

mkdir -p "$FIXTURE/nested/sub"
touch "$FIXTURE/nested/sub/test_math.py"
touch "$FIXTURE/top.py"
touch "$FIXTURE/go.mod"
touch "$FIXTURE/some.txt"

echo "── has_files: directory search ──"

# Recursive directory match (the case broken by a bare `-quit`).
if has_files "$FIXTURE" "*.py"; then r=0; else r=1; fi
assert_eq "directory match: *.py matches nested test_math.py" "0" "$r"

if has_files "$FIXTURE" "go.mod"; then r=0; else r=1; fi
assert_eq "directory match: go.mod at top level" "0" "$r"

if has_files "$FIXTURE" "test_*.py"; then r=0; else r=1; fi
assert_eq "directory match: test_*.py matches recursively" "0" "$r"

if has_files "$FIXTURE" "*.rs"; then r=0; else r=1; fi
assert_eq "directory non-match: *.rs returns 1" "1" "$r"

# Multiple globs — any match wins.
if has_files "$FIXTURE" "*.rs" "*.py"; then r=0; else r=1; fi
assert_eq "directory match: any-of globs" "0" "$r"

echo "── has_files: single-file target ──"

if has_files "$FIXTURE/nested/sub/test_math.py" "test_*.py"; then r=0; else r=1; fi
assert_eq "file match: basename glob" "0" "$r"

if has_files "$FIXTURE/nested/sub/test_math.py" "*.py"; then r=0; else r=1; fi
assert_eq "file match: *.py by basename" "0" "$r"

if has_files "$FIXTURE/nested/sub/test_math.py" "*.rs"; then r=0; else r=1; fi
assert_eq "file non-match: *.rs by basename" "1" "$r"

echo "── has_files: nonexistent path ──"

if has_files "$FIXTURE/does-not-exist" "*.py"; then r=0; else r=1; fi
assert_eq "nonexistent path returns 1" "1" "$r"

echo "── tool_available ──"

if tool_available bash; then r=0; else r=1; fi
assert_eq "tool_available bash" "0" "$r"

if tool_available __definitely_not_a_real_tool__; then r=0; else r=1; fi
assert_eq "tool_available rejects missing binary" "1" "$r"

echo ""
echo "── Summary ──"
echo "  passed: $PASSED"
echo "  failed: $FAILED"
[ "$FAILED" -eq 0 ]
