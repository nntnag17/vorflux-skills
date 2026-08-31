#!/usr/bin/env bash
# common.sh — Shared helpers for owasp-security scripts.
# Sourced by owasp_scan.sh and run_tests.sh.
#
# Exposes:
#   Color constants: GREEN YELLOW RED CYAN BOLD NC
#   tool_available <cmd>
#   has_files <path> <glob> [glob ...]

# Guard against double-sourcing
if [ -n "${_OWASP_COMMON_SH_LOADED:-}" ]; then
  return 0 2>/dev/null || exit 0
fi
_OWASP_COMMON_SH_LOADED=1

# ── Color constants ───────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── tool_available ────────────────────────────────────────────────────────────
tool_available() {
  command -v "$1" &>/dev/null
}

# ── has_files ─────────────────────────────────────────────────────────────────
# Usage: has_files <path> <glob> [glob ...]
# When <path> is a regular file, matches globs against the file's basename only.
# When <path> is a directory, searches recursively via find.
# Note: directory-name globs (e.g. "spec", "test") only work correctly when
# <path> is a directory — passing a single file will never match them.
#
# Implementation note: we use `-print -quit` rather than `-quit` alone because
# bare `-quit` suppresses find's implicit `-print`, so nothing is written to
# stdout and `grep -q .` always fails. With `-print -quit`, find emits one
# match and then stops — fast and correct for directory trees of any size.
has_files() {
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
  [ -d "$dir" ] || return 1
  for glob in "$@"; do
    if find "$dir" -name "$glob" -print -quit 2>/dev/null | grep -q .; then
      return 0
    fi
  done
  return 1
}
