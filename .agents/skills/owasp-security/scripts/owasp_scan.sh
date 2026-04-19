#!/usr/bin/env bash
# owasp_scan.sh — Run all available security scanners against a target.
#
# Writes per-tool output under ./owasp-findings/ and a normalized JSON
# summary to ./owasp-findings/summary.json.
#
# Never hard-exits on a missing tool — skips it and logs the skip.
# FINDINGS counter reflects actual findings, not tool invocations.
#
# Usage: owasp_scan.sh [target_path]
#
# Note: ${SKILL_DIR} in SKILL.md refers to this skill's directory.
# When running directly, invoke as: bash /path/to/owasp-security/scripts/owasp_scan.sh [target]

set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-.}"
OUT_DIR="./owasp-findings"
SUMMARY_FILE="$OUT_DIR/summary.json"
# NDJSON file — one JSON object per line; aggregated at the end via python3
NDJSON_FILE="$OUT_DIR/findings.ndjson"
FINDINGS=0
SKIPPED_TOOLS=()

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

mkdir -p "$OUT_DIR"
# Start fresh
: > "$NDJSON_FILE"

# ── Helpers ───────────────────────────────────────────────────────────────────

banner() {
  echo -e "\n${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}${BOLD}  OWASP Security Scan: $TARGET${NC}"
  echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}\n"
}

section() {
  echo -e "\n${CYAN}── $1 ──${NC}"
}

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

# Append one NDJSON record and increment the global counter.
# All string escaping is handled by python3 — no sed metacharacter risk.
record_finding() {
  local category="$1" tool="$2" severity="$3" count="$4" message="$5"
  FINDINGS=$((FINDINGS + count))
  python3 -c "
import json, sys
rec = {
    'category': sys.argv[1],
    'tool':     sys.argv[2],
    'severity': sys.argv[3],
    'count':    int(sys.argv[4]),
    'message':  sys.argv[5],
}
print(json.dumps(rec))
" "$category" "$tool" "$severity" "$count" "$message" >> "$NDJSON_FILE"
}

# ── A01-A10: SAST — semgrep ───────────────────────────────────────────────────
run_semgrep() {
  section "A01-A10 SAST: semgrep (owasp-top-ten + secrets rulesets)"
  # semgrep requires network access to pull rulesets from the Semgrep Registry.
  # On air-gapped systems, pre-download rules and pass --config /path/to/rules.yaml instead.
  if ! tool_available semgrep; then
    echo -e "${YELLOW}  (skipping semgrep — not installed; install: pip install semgrep)${NC}"
    SKIPPED_TOOLS+=("semgrep")
    return
  fi

  local out_file="$OUT_DIR/semgrep.json"
  semgrep --config "p/owasp-top-ten" --config "p/secrets" \
    --json --quiet "$TARGET" > "$out_file" 2>/dev/null || true

  local result
  result=$(python3 - "$out_file" <<'PYEOF'
import sys, json
path = sys.argv[1]
try:
    with open(path) as f:
        data = json.load(f)
    results = data.get("results", [])
    by_sev = {}
    for r in results:
        sev = r.get("extra", {}).get("severity", "WARNING").upper()
        by_sev[sev] = by_sev.get(sev, 0) + 1
    print(len(results))
    for sev, n in sorted(by_sev.items()):
        print(f"  {sev}: {n}")
    for r in results[:15]:
        sev  = r.get("extra", {}).get("severity", "WARNING")
        msg  = r.get("extra", {}).get("message", "")[:100]
        fp   = r.get("path", "")
        line = r.get("start", {}).get("line", "")
        print(f"  [{sev}] {fp}:{line} — {msg}")
except Exception as e:
    print(f"0\n  (parse error: {e})")
PYEOF
  )

  local total
  total=$(echo "$result" | head -1 | tr -d ' ')
  echo "$result" | tail -n +2

  if [ "${total:-0}" -gt 0 ]; then
    record_finding "A01-A10" "semgrep" "HIGH" "$total" "$total finding(s) from OWASP+secrets ruleset"
    echo -e "${RED}  semgrep: $total finding(s) — see $out_file${NC}"
  else
    echo -e "${GREEN}  semgrep: no findings${NC}"
  fi
}

# ── A02/A03/A10: Python SAST — bandit ────────────────────────────────────────
run_bandit() {
  if ! has_files "$TARGET" "*.py"; then return; fi
  section "A02/A03 Python SAST: bandit"
  if ! tool_available bandit; then
    echo -e "${YELLOW}  (skipping bandit — not installed; install: pip install bandit)${NC}"
    SKIPPED_TOOLS+=("bandit")
    return
  fi

  local out_file="$OUT_DIR/bandit.json"
  # Key rules: B303/B304/B305/B324=weak crypto (A02), B608=SQL injection (A03),
  #            B602/B605=shell injection (A03), B703=template injection (A03)
  bandit -r "$TARGET" -f json -l -q 2>/dev/null > "$out_file" || true

  local result
  result=$(python3 - "$out_file" <<'PYEOF'
import sys, json
path = sys.argv[1]
try:
    with open(path) as f:
        data = json.load(f)
    results = data.get("results", [])
    by_sev = {}
    for r in results:
        sev = r.get("issue_severity", "MEDIUM").upper()
        by_sev[sev] = by_sev.get(sev, 0) + 1
    print(len(results))
    for sev, n in sorted(by_sev.items()):
        print(f"  {sev}: {n}")
    for r in results[:15]:
        sev     = r.get("issue_severity", "")
        test_id = r.get("test_id", "")
        msg     = r.get("issue_text", "")[:100]
        fname   = r.get("filename", "")
        line    = r.get("line_number", "")
        print(f"  [{sev}] {test_id} {fname}:{line} — {msg}")
except Exception as e:
    print(f"0\n  (parse error: {e})")
PYEOF
  )

  local total
  total=$(echo "$result" | head -1 | tr -d ' ')
  echo "$result" | tail -n +2

  if [ "${total:-0}" -gt 0 ]; then
    record_finding "A02/A03" "bandit" "MEDIUM" "$total" "$total Python security issue(s)"
    echo -e "${RED}  bandit: $total issue(s) — see $out_file${NC}"
  else
    echo -e "${GREEN}  bandit: no issues${NC}"
  fi
}

# ── A03: JS/TS SAST — eslint-plugin-security ─────────────────────────────────
run_eslint_security() {
  if ! has_files "$TARGET" "*.js" "*.ts" "*.tsx"; then return; fi
  section "A03 JS/TS SAST: eslint-plugin-security"

  # Require both eslint-plugin-security AND the eslint binary in node_modules
  # to avoid npx auto-install prompts that can hang the scan.
  local plugin_path
  plugin_path=$(find "$TARGET" -maxdepth 4 -path "*/node_modules/eslint-plugin-security" -type d 2>/dev/null | head -1)
  local eslint_bin
  eslint_bin=$(find "$TARGET" -maxdepth 4 -path "*/node_modules/.bin/eslint" -type f 2>/dev/null | head -1)
  if [ -z "$plugin_path" ] || [ -z "$eslint_bin" ]; then
    echo -e "${YELLOW}  (skipping — eslint and/or eslint-plugin-security not found in node_modules; install: npm i -D eslint eslint-plugin-security)${NC}"
    SKIPPED_TOOLS+=("eslint-plugin-security")
    return
  fi

  local out_file="$OUT_DIR/eslint-security.txt"
  "$eslint_bin" \
    --plugin security \
    --rule 'security/detect-eval-with-expression: error' \
    --rule 'security/detect-non-literal-regexp: warn' \
    --rule 'security/detect-object-injection: warn' \
    --rule 'security/detect-possible-timing-attacks: warn' \
    "$TARGET" 2>/dev/null | tee "$out_file" || true

  # grep -c returns 1 (no match) or 0 (match); use || true so pipefail doesn't trigger
  local issue_count
  issue_count=$(grep -cE "error|warning" "$out_file" || true)

  if [ "${issue_count:-0}" -gt 0 ]; then
    record_finding "A03" "eslint-security" "MEDIUM" "$issue_count" "$issue_count JS/TS security lint issue(s)"
    echo -e "${RED}  eslint-security: $issue_count issue(s) — see $out_file${NC}"
  else
    echo -e "${GREEN}  eslint-security: no issues${NC}"
  fi
}

# ── A02/A09: Secret detection ─────────────────────────────────────────────────
run_secret_scan() {
  section "A02/A09 Secret Detection"
  local out_file="$OUT_DIR/secrets.txt"

  if tool_available gitleaks; then
    echo -e "${GREEN}  Running gitleaks...${NC}"
    gitleaks detect --source "$TARGET" --no-git --exit-code 0 > "$out_file" 2>&1 || true
    local leak_count
    leak_count=$(grep -c "^Finding:" "$out_file" || true)
    grep -E "^Finding:|Secret:|File:|Line:" "$out_file" | head -20 || true
    if [ "${leak_count:-0}" -gt 0 ]; then
      record_finding "A02" "gitleaks" "CRITICAL" "$leak_count" "$leak_count secret(s) detected"
      echo -e "${RED}  gitleaks: $leak_count secret(s) — see $out_file${NC}"
    else
      echo -e "${GREEN}  gitleaks: no secrets found${NC}"
    fi

  elif tool_available trufflehog; then
    echo -e "${GREEN}  Running trufflehog...${NC}"
    trufflehog filesystem "$TARGET" 2>&1 | tee "$out_file" | tail -20 || true
    local leak_count
    leak_count=$(grep -ci "found\|detector" "$out_file" || true)
    if [ "${leak_count:-0}" -gt 0 ]; then
      record_finding "A02" "trufflehog" "CRITICAL" "$leak_count" "Potential secret(s) detected"
      echo -e "${RED}  trufflehog: findings present — see $out_file${NC}"
    else
      echo -e "${GREEN}  trufflehog: no secrets found${NC}"
    fi

  else
    echo -e "${YELLOW}  (gitleaks/trufflehog not installed — using grep fallback)${NC}"
    SKIPPED_TOOLS+=("gitleaks" "trufflehog")
    echo "  Scanning for common secret patterns..."
    grep -rn \
      -E "(password|passwd|secret|api_key|apikey|private_key|access_token|auth_token)\s*[=:]\s*['\"][^'\"]{6,}" \
      --include="*.py" --include="*.js" --include="*.ts" --include="*.go" \
      --include="*.rb" --include="*.java" --include="*.env" \
      --include="*.yaml" --include="*.yml" --include="*.json" \
      "$TARGET" 2>/dev/null \
      | grep -v -E "test|spec|mock|example|sample|placeholder|TODO|FIXME" \
      | head -20 > "$out_file" || true

    local grep_count
    grep_count=$(wc -l < "$out_file" | tr -d ' ')
    cat "$out_file"
    if [ "${grep_count:-0}" -gt 0 ]; then
      record_finding "A02" "grep-secrets" "HIGH" "$grep_count" "$grep_count potential hardcoded secret pattern(s)"
      echo -e "${RED}  grep: $grep_count potential pattern(s) — see $out_file${NC}"
    else
      echo -e "${GREEN}  grep: no obvious secret patterns found${NC}"
    fi
  fi
}

# ── A06/A08: Dependency audit — Node.js ──────────────────────────────────────
run_npm_audit() {
  local pkg_dir="$TARGET"
  [ ! -f "$TARGET/package.json" ] && [ -f "package.json" ] && pkg_dir="."
  [ ! -f "$pkg_dir/package.json" ] && return

  section "A06/A08 Node.js Dependencies: npm audit"
  if ! tool_available npm; then
    echo -e "${YELLOW}  (skipping npm audit — npm not installed)${NC}"
    SKIPPED_TOOLS+=("npm-audit")
    return
  fi

  local out_file="$OUT_DIR/npm-audit.json"
  (cd "$pkg_dir" && npm audit --json 2>/dev/null) > "$out_file" || true

  local result
  result=$(python3 - "$out_file" <<'PYEOF'
import sys, json
path = sys.argv[1]
try:
    with open(path) as f:
        data = json.load(f)
    vulns = data.get("metadata", {}).get("vulnerabilities", {})
    total = sum(vulns.values())
    print(total)
    for sev in ["critical", "high", "moderate", "low"]:
        n = vulns.get(sev, 0)
        if n:
            print(f"  {sev}: {n}")
except Exception as e:
    print(f"0\n  (parse error: {e})")
PYEOF
  )

  local total
  total=$(echo "$result" | head -1 | tr -d ' ')
  echo "$result" | tail -n +2

  if [ "${total:-0}" -gt 0 ]; then
    record_finding "A06" "npm-audit" "HIGH" "$total" "$total npm vulnerability/vulnerabilities"
    echo -e "${RED}  npm audit: $total vulnerability/vulnerabilities — see $out_file${NC}"
  else
    echo -e "${GREEN}  npm audit: no vulnerabilities${NC}"
  fi
}

# ── A06/A08: Dependency audit — Python ───────────────────────────────────────
run_pip_audit() {
  if ! has_files "$TARGET" "requirements*.txt" "pyproject.toml" "Pipfile"; then return; fi
  section "A06/A08 Python Dependencies: pip-audit"
  if ! tool_available pip-audit; then
    echo -e "${YELLOW}  (skipping pip-audit — not installed; install: pip install pip-audit)${NC}"
    SKIPPED_TOOLS+=("pip-audit")
    return
  fi

  local out_file="$OUT_DIR/pip-audit.txt"
  pip-audit --format=columns 2>/dev/null | tee "$out_file" || true
  local vuln_count
  vuln_count=$(grep -cE "^[A-Z]" "$out_file" || true)

  if [ "${vuln_count:-0}" -gt 0 ]; then
    record_finding "A06" "pip-audit" "HIGH" "$vuln_count" "$vuln_count Python dependency vulnerability/vulnerabilities"
    echo -e "${RED}  pip-audit: $vuln_count vulnerability/vulnerabilities — see $out_file${NC}"
  else
    echo -e "${GREEN}  pip-audit: no vulnerabilities${NC}"
  fi
}

# ── A06/A08: Dependency audit — Go ───────────────────────────────────────────
run_govulncheck() {
  if ! has_files "$TARGET" "go.mod"; then return; fi
  section "A06/A08 Go Dependencies: govulncheck"
  if ! tool_available govulncheck; then
    echo -e "${YELLOW}  (skipping govulncheck — not installed; install: go install golang.org/x/vuln/cmd/govulncheck@latest)${NC}"
    SKIPPED_TOOLS+=("govulncheck")
    return
  fi

  local out_file="$OUT_DIR/govulncheck.txt"
  (cd "$TARGET" && govulncheck ./... 2>&1) | tee "$out_file" || true
  local vuln_count
  vuln_count=$(grep -c "^Vulnerability #" "$out_file" || true)

  if [ "${vuln_count:-0}" -gt 0 ]; then
    record_finding "A06" "govulncheck" "HIGH" "$vuln_count" "$vuln_count Go vulnerability/vulnerabilities"
    echo -e "${RED}  govulncheck: $vuln_count vulnerability/vulnerabilities — see $out_file${NC}"
  else
    echo -e "${GREEN}  govulncheck: no vulnerabilities${NC}"
  fi
}

# ── A06/A08: Dependency audit — Ruby ─────────────────────────────────────────
run_bundler_audit() {
  if ! has_files "$TARGET" "Gemfile.lock"; then return; fi
  section "A06/A08 Ruby Dependencies: bundler-audit"
  if ! tool_available bundle-audit; then
    echo -e "${YELLOW}  (skipping bundler-audit — not installed; install: gem install bundler-audit)${NC}"
    SKIPPED_TOOLS+=("bundler-audit")
    return
  fi

  local out_file="$OUT_DIR/bundler-audit.txt"
  (cd "$TARGET" && bundle-audit check --update 2>&1) | tee "$out_file" || true
  local vuln_count
  vuln_count=$(grep -c "^Name:" "$out_file" || true)

  if [ "${vuln_count:-0}" -gt 0 ]; then
    record_finding "A06" "bundler-audit" "HIGH" "$vuln_count" "$vuln_count Ruby gem vulnerability/vulnerabilities"
    echo -e "${RED}  bundler-audit: $vuln_count vulnerability/vulnerabilities — see $out_file${NC}"
  else
    echo -e "${GREEN}  bundler-audit: no vulnerabilities${NC}"
  fi
}

# ── A06/A08: Dependency audit — Rust ─────────────────────────────────────────
run_cargo_audit() {
  if ! has_files "$TARGET" "Cargo.lock"; then return; fi
  section "A06/A08 Rust Dependencies: cargo audit"
  if ! tool_available cargo; then
    echo -e "${YELLOW}  (skipping cargo audit — cargo not installed)${NC}"
    SKIPPED_TOOLS+=("cargo-audit")
    return
  fi

  local out_file="$OUT_DIR/cargo-audit.txt"
  (cd "$TARGET" && cargo audit 2>&1) | tee "$out_file" || true
  local vuln_count
  vuln_count=$(grep -c "^error\[" "$out_file" || true)

  if [ "${vuln_count:-0}" -gt 0 ]; then
    record_finding "A06" "cargo-audit" "HIGH" "$vuln_count" "$vuln_count Rust advisory/advisories"
    echo -e "${RED}  cargo audit: $vuln_count advisory/advisories — see $out_file${NC}"
  else
    echo -e "${GREEN}  cargo audit: no advisories${NC}"
  fi
}

# ── A06/A08: Multi-ecosystem — osv-scanner ───────────────────────────────────
run_osv_scanner() {
  section "A06/A08 Multi-ecosystem: osv-scanner"
  if ! tool_available osv-scanner; then
    echo -e "${YELLOW}  (skipping osv-scanner — not installed; install: https://github.com/google/osv-scanner)${NC}"
    SKIPPED_TOOLS+=("osv-scanner")
    return
  fi

  local out_file="$OUT_DIR/osv-scanner.txt"
  osv-scanner --recursive "$TARGET" 2>&1 | tee "$out_file" || true
  local osv_count
  osv_count=$(grep -c "OSV-" "$out_file" || true)

  if [ "${osv_count:-0}" -gt 0 ]; then
    record_finding "A06" "osv-scanner" "HIGH" "$osv_count" "$osv_count OSV advisory/advisories"
    echo -e "${RED}  osv-scanner: $osv_count advisory/advisories — see $out_file${NC}"
  else
    echo -e "${GREEN}  osv-scanner: no advisories${NC}"
  fi
}

# ── A05: Container / IaC misconfiguration — trivy ────────────────────────────
run_trivy() {
  if ! has_files "$TARGET" "Dockerfile" "docker-compose*.yml" "docker-compose*.yaml"; then return; fi
  section "A05 Container/IaC: trivy config"
  if ! tool_available trivy; then
    echo -e "${YELLOW}  (skipping trivy — not installed; install: https://aquasecurity.github.io/trivy)${NC}"
    SKIPPED_TOOLS+=("trivy")
    return
  fi

  local out_file="$OUT_DIR/trivy.txt"
  trivy config "$TARGET" --exit-code 0 --quiet 2>/dev/null | tee "$out_file" || true
  local issue_count
  issue_count=$(grep -cE "^(CRITICAL|HIGH|MEDIUM|LOW)" "$out_file" || true)

  if [ "${issue_count:-0}" -gt 0 ]; then
    record_finding "A05" "trivy" "MEDIUM" "$issue_count" "$issue_count container/IaC misconfiguration(s)"
    echo -e "${RED}  trivy: $issue_count misconfiguration(s) — see $out_file${NC}"
  else
    echo -e "${GREEN}  trivy: no misconfigurations${NC}"
  fi
}

# ── Write normalized JSON summary from NDJSON ─────────────────────────────────
write_summary() {
  python3 - "$NDJSON_FILE" "$SUMMARY_FILE" "$FINDINGS" "${SKIPPED_TOOLS[@]+"${SKIPPED_TOOLS[@]}"}" <<'PYEOF'
import sys, json

ndjson_file  = sys.argv[1]
summary_file = sys.argv[2]
total        = int(sys.argv[3])
skipped      = sys.argv[4:] if len(sys.argv) > 4 else []

records = []
try:
    with open(ndjson_file) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
except FileNotFoundError:
    pass

summary = {
    "total_findings": total,
    "skipped_tools":  skipped,
    "findings":       records,
}

with open(summary_file, "w") as f:
    json.dump(summary, f, indent=2)

print(f"Summary written to {summary_file}")
PYEOF
}

# ── Print summary ─────────────────────────────────────────────────────────────
print_summary() {
  echo -e "\n${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}${BOLD}  Scan Summary${NC}"
  echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"

  if [ "$FINDINGS" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  FINDINGS: 0 — no automated issues detected${NC}"
  else
    echo -e "${RED}${BOLD}  FINDINGS: $FINDINGS total${NC}"
    if [ -f "$NDJSON_FILE" ]; then
      python3 -c "
import sys, json
with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip()
        if line:
            r = json.loads(line)
            print(f\"  [{r['severity']}] {r['category']} ({r['tool']}): {r['message']}\")
" "$NDJSON_FILE" || true
    fi
  fi

  if [ "${#SKIPPED_TOOLS[@]}" -gt 0 ]; then
    echo -e "\n${YELLOW}  Skipped (not installed): ${SKIPPED_TOOLS[*]}${NC}"
    echo -e "${YELLOW}  Install missing tools for broader coverage.${NC}"
  fi

  echo -e "\n  Output directory:   ${BOLD}$OUT_DIR/${NC}"
  echo -e "  Normalized summary: ${BOLD}$SUMMARY_FILE${NC}"
  echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}\n"
}

# ── Main ──────────────────────────────────────────────────────────────────────
banner
run_semgrep
run_bandit
run_eslint_security
run_secret_scan
run_npm_audit
run_pip_audit
run_govulncheck
run_bundler_audit
run_cargo_audit
run_osv_scanner
run_trivy
write_summary
print_summary

exit 0
