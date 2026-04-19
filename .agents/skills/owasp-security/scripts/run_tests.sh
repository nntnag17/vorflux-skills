#!/usr/bin/env bash
# run_tests.sh — Detect and run the project's test suite.
#
# Exit codes:
#   0 — tests detected and all passed
#   1 — tests detected but one or more failed
#   2 — no test framework detected (report verdict: BLOCKED)
#
# Usage: run_tests.sh [target_path]

set -uo pipefail

TARGET="${1:-.}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "\n${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}  Test Suite Runner: $TARGET${NC}"
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}\n"

tool_available() {
  command -v "$1" &>/dev/null
}

has_files() {
  # Usage: has_files <path> <glob> [glob ...]
  # When <path> is a regular file, matches globs against the file's basename only.
  # When <path> is a directory, searches recursively via find.
  # Note: directory-name globs (e.g. "spec", "test") only work correctly when
  # <path> is a directory — passing a single file will never match them.
  local dir="$1"; shift
  if [ -f "$dir" ]; then
    local fname
    fname="$(basename "$dir")"
    for glob in "$@"; do
      case "$fname" in
        $glob) return 0 ;;
      esac
    done
    return 1
  fi
  for glob in "$@"; do
    if find "$dir" -name "$glob" -quit 2>/dev/null | grep -q .; then
      return 0
    fi
  done
  return 1
}

run_and_report() {
  local framework="$1"; shift
  echo -e "${CYAN}  Detected: $framework${NC}"
  echo -e "${CYAN}  Running: $*${NC}\n"
  if "$@"; then
    echo -e "\n${GREEN}${BOLD}  TEST RESULT: PASSED ($framework)${NC}"
    exit 0
  else
    echo -e "\n${RED}${BOLD}  TEST RESULT: FAILED ($framework)${NC}"
    echo -e "${RED}  Fix failing tests before proceeding with the security audit.${NC}"
    exit 1
  fi
}

# ── Python ────────────────────────────────────────────────────────────────────
if has_files "$TARGET" "*.py"; then
  if has_files "$TARGET" "pytest.ini" "pyproject.toml" "setup.cfg" "conftest.py" "test_*.py" "*_test.py"; then
    if tool_available pytest; then
      run_and_report "pytest" pytest "$TARGET" -v --tb=short
    elif tool_available python3; then
      run_and_report "unittest" python3 -m pytest "$TARGET" -v --tb=short 2>/dev/null \
        || run_and_report "unittest" python3 -m unittest discover -s "$TARGET" -v
    fi
  fi
fi

# ── Node.js ───────────────────────────────────────────────────────────────────
if [ -f "$TARGET/package.json" ] || [ -f "package.json" ]; then
  pkg_json_path="${TARGET}/package.json"
  [ ! -f "$pkg_json_path" ] && pkg_json_path="package.json"
  pkg_dir="$(dirname "$pkg_json_path")"

  # Detect test script from package.json
  test_script=$(python3 -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    scripts = d.get('scripts', {})
    print(scripts.get('test', ''))
except Exception:
    print('')
" "$pkg_json_path" 2>/dev/null || echo "")

  # Skip the npm default placeholder — it always fails with "no test specified"
  case "$test_script" in
    *"no test specified"*|"") : ;;  # skip
    *)
      run_and_report "npm test" sh -c "cd '$pkg_dir' && npm test"
      ;;
  esac

  # Fallback: detect jest/vitest/mocha directly
  if has_files "$TARGET" "jest.config.*" "vitest.config.*" ".mocharc.*"; then
    if tool_available npx; then
      if has_files "$TARGET" "jest.config.*"; then
        run_and_report "jest" sh -c "cd '$pkg_dir' && npx jest --passWithNoTests"
      elif has_files "$TARGET" "vitest.config.*"; then
        run_and_report "vitest" sh -c "cd '$pkg_dir' && npx vitest run"
      elif has_files "$TARGET" ".mocharc.*"; then
        run_and_report "mocha" sh -c "cd '$pkg_dir' && npx mocha"
      fi
    fi
  fi
fi

# ── Go ────────────────────────────────────────────────────────────────────────
if has_files "$TARGET" "go.mod"; then
  if tool_available go; then
    run_and_report "go test" sh -c "cd '$TARGET' && go test ./... -v"
  fi
fi

# ── Rust ──────────────────────────────────────────────────────────────────────
if has_files "$TARGET" "Cargo.toml"; then
  if tool_available cargo; then
    run_and_report "cargo test" sh -c "cd '$TARGET' && cargo test"
  fi
fi

# ── Java (Maven) ──────────────────────────────────────────────────────────────
if has_files "$TARGET" "pom.xml"; then
  if tool_available mvn; then
    run_and_report "maven" sh -c "cd '$TARGET' && mvn test -q"
  fi
fi

# ── Java (Gradle) ─────────────────────────────────────────────────────────────
if has_files "$TARGET" "build.gradle" "build.gradle.kts"; then
  if tool_available gradle; then
    run_and_report "gradle" sh -c "cd '$TARGET' && gradle test"
  elif [ -f "$TARGET/gradlew" ]; then
    run_and_report "gradlew" sh -c "cd '$TARGET' && ./gradlew test"
  fi
fi

# ── Ruby ──────────────────────────────────────────────────────────────────────
if has_files "$TARGET" "Gemfile"; then
  if tool_available bundle && has_files "$TARGET" "spec" "test"; then
    if has_files "$TARGET" "spec"; then
      run_and_report "rspec" sh -c "cd '$TARGET' && bundle exec rspec"
    else
      run_and_report "minitest" sh -c "cd '$TARGET' && bundle exec rake test"
    fi
  fi
fi

# ── No framework detected ─────────────────────────────────────────────────────
# ── No framework detected ─────────────────────────────────────────────────────
# If we reach here, either no framework files were found OR the runner binary
# is not installed. Log which case applies so users know what to install.
if has_files "$TARGET" "test_*.py" "*_test.py" "conftest.py" "pytest.ini" "pyproject.toml"; then
  echo -e "${YELLOW}  (pytest/unittest files found but pytest is not installed; install: pip install pytest)${NC}"
elif has_files "$TARGET" "jest.config.*" "vitest.config.*" ".mocharc.*" "package.json"; then
  echo -e "${YELLOW}  (Node test config found but runner not available; install jest/vitest/mocha)${NC}"
elif has_files "$TARGET" "go.mod"; then
  echo -e "${YELLOW}  (go.mod found but go is not on PATH)${NC}"
elif has_files "$TARGET" "Cargo.toml"; then
  echo -e "${YELLOW}  (Cargo.toml found but cargo is not on PATH)${NC}"
fi

echo -e "${YELLOW}${BOLD}  TEST RESULT: BLOCKED — no test framework detected${NC}"
echo -e "${YELLOW}  The security report verdict will be set to BLOCKED.${NC}"
echo -e "${YELLOW}  Add a test suite before completing the security audit.${NC}\n"
exit 2
