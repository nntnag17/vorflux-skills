# owasp-security skill — Examples

This directory contains a deliberately vulnerable Python file and the real scan output
produced by running `owasp_scan.sh` against it. These files exist to demonstrate that
the skill produces findings on vulnerable code and degrades gracefully when optional
tools are not installed.

## Files

| File | Purpose |
|------|---------|
| `vulnerable_sample.py` | Intentionally insecure Python file covering A02 (weak crypto, hardcoded credentials), A03 (SQL injection, shell injection, eval), A09 (password in logs), and A10 (SSRF). **Do not use any of these patterns in production.** |
| `summary.json` | Normalized JSON output from `owasp_scan.sh` — 7 bandit findings, skipped tools listed. |
| `bandit.json` | Raw bandit output (full detail per finding). |

## How the scan was run

```bash
export PATH="$HOME/.local/bin:$PATH"   # bandit installed via pip
SKILL_DIR=/path/to/.agents/skills/owasp-security

cd /tmp/scan-output
bash "$SKILL_DIR/scripts/owasp_scan.sh" \
  /path/to/.agents/skills/owasp-security/examples/vulnerable_sample.py
```

Tools available during this run: **bandit** (installed).
Tools skipped (not installed): semgrep, gitleaks, trufflehog, osv-scanner.

The `summary.json` shows `total_findings: 7` — all from bandit — demonstrating that
the skill correctly surfaces A02/A03 issues even with only one scanner available.

## Secret-scanner allowlist

`vulnerable_sample.py` contains intentional credential-like strings for demo purposes.
A `.gitleaks.toml` at the repo root allowlists this directory so `gitleaks detect`
does not flag these as real secrets.
