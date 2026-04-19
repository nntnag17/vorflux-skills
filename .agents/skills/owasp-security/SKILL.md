---
name: owasp-security
description: This skill should be used when the user asks to run a security audit, check for OWASP vulnerabilities, scan for security issues, perform a penetration test review, check for injection flaws, find authentication weaknesses, detect exposed secrets, audit dependencies for CVEs, or run a security scan before deployment. Trigger phrases include "run a security audit", "check OWASP vulnerabilities", "scan for security issues", "find injection flaws", "check for secrets", "audit dependencies", "security scan", "OWASP check", "check for CVEs", "security review".
version: 1.0.0
license: MIT
allowed-tools:
  - read
  - write
  - bash
metadata:
  version: "1.0"
  tags: [security, owasp, sast, secrets, dependencies, testing]
---

# owasp-security — OWASP Top 10 2021 Security Audit

Perform a comprehensive security audit covering all OWASP Top 10 2021 categories (A01–A10). Runs automated SAST scanners, dependency audits, secret detection, and the project's own test suite. Produces a structured report with severity-graded findings.

**Scope:** Python, Node.js, Go, Rust, Ruby, Java, and container workloads. For general code quality (correctness, performance, maintainability) use the `code-review` skill instead.

> **Example run:** See [`examples/`](./examples/README.md) for a sample scan against a deliberately vulnerable Python file — `summary.json` and `bandit.json` show the skill producing 7 real findings.

## How to use

```
/owasp-security [file, directory, or leave blank for current project]
```

## OWASP Top 10 2021 — Category → Tool Mapping

| ID  | Category                                      | Automated Tools                                          | Key Rules / Checks                              |
|-----|-----------------------------------------------|----------------------------------------------------------|-------------------------------------------------|
| A01 | Broken Access Control                         | semgrep (`p/owasp-top-ten`)                              | Missing authz checks, IDOR patterns             |
| A02 | Cryptographic Failures                        | semgrep, bandit B303/B304/B305/B324                      | Weak ciphers (MD5/SHA1/DES), cleartext storage  |
| A03 | Injection (SQL/OS/LDAP/XSS/template)          | semgrep, bandit B608/B602/B605/B703                      | String-concat queries, `eval`, shell injection  |
| A04 | Insecure Design                               | Manual checklist (A04 section)                           | Threat model gaps, missing rate limiting        |
| A05 | Security Misconfiguration                     | semgrep, trivy config                                    | Debug mode on, default creds, open CORS         |
| A06 | Vulnerable & Outdated Components              | npm audit, pip-audit, govulncheck, bundler-audit, osv-scanner | Known CVEs in direct/transitive deps       |
| A07 | Identification & Authentication Failures      | semgrep, manual checklist                                | Weak passwords, missing MFA, session fixation   |
| A08 | Software & Data Integrity Failures            | osv-scanner, trivy, semgrep                              | Unsigned deps, unsafe deserialization           |
| A09 | Security Logging & Monitoring Failures        | semgrep, manual checklist                                | Sensitive data in logs, missing audit trail     |
| A10 | Server-Side Request Forgery (SSRF)            | semgrep, bandit B310                                     | Unvalidated URL fetch, internal IP access       |

## Severity Mapping (scanner → report)

| Scanner Output                                           | Report Severity |
|----------------------------------------------------------|-----------------|
| semgrep `ERROR`, gitleaks/trufflehog any, trivy `CRITICAL`, npm audit `critical` | 🔴 Critical |
| semgrep `WARNING`, bandit `HIGH`, trivy `HIGH`, npm audit `high` | 🟠 High    |
| bandit `MEDIUM`, npm audit `moderate`, trivy `MEDIUM`    | 🟡 Medium       |
| semgrep `INFO`, bandit `LOW`, npm audit `low`, trivy `LOW` | 🟢 Low        |

## Instructions

> **`${SKILL_DIR}` note:** In the commands below, `${SKILL_DIR}` refers to the absolute path of
> this skill's directory (e.g., `/path/to/vorflux-skills/.agents/skills/owasp-security`).
> Substitute that path when running commands directly, or set the variable first:
> ```bash
> SKILL_DIR=/path/to/vorflux-skills/.agents/skills/owasp-security
> ```

### Step 1 — Determine scope

```bash
TARGET="${ARGUMENTS:-.}"
```

If `$ARGUMENTS` is provided, use it as the scan target. Otherwise default to `.`.

### Step 2 — Run automated security scanners

```bash
bash ${SKILL_DIR}/scripts/owasp_scan.sh "$TARGET"
```

The script writes per-tool output under `./owasp-findings/` and a normalized JSON summary to `./owasp-findings/summary.json`. It never hard-exits on a missing tool — it skips unavailable tools and logs which were skipped.

> **Network requirement:** semgrep fetches rulesets from the Semgrep Registry on first run.
> On air-gapped systems, pre-download rules and pass `--config /path/to/rules.yaml` instead.

Tools run per ecosystem:
- **All stacks:** semgrep (`p/owasp-top-ten` + `p/secrets`), gitleaks/trufflehog/grep fallback
- **Python:** bandit (B303/B304/B305/B324/B608/B602/B605/B310), pip-audit
- **Node.js:** eslint-plugin-security, npm audit
- **Go:** govulncheck
- **Ruby:** bundler-audit
- **Rust:** cargo audit
- **Containers:** trivy config (Dockerfile / docker-compose)
- **Multi-ecosystem:** osv-scanner

### Step 3 — Run the project test suite (MANDATORY — gates the report verdict)

```bash
bash ${SKILL_DIR}/scripts/run_tests.sh "$TARGET"
```

**This step is not optional.** The script exits with a meaningful code:

| Exit code | Meaning | Report verdict |
|-----------|---------|----------------|
| `0` | Tests detected and all passed | Proceed to Step 4 |
| `1` | Tests detected but one or more failed | **BLOCKED** — fix tests first |
| `2` | No test framework detected | **BLOCKED** — add a test suite first |

A passing test suite (`exit 0`) is a prerequisite for a `PASS` or `FINDINGS` verdict. Broken or absent tests indicate untested security-critical paths.

The script auto-detects the test framework:
- `pytest` / `python -m unittest` for Python
- `jest` / `vitest` / `mocha` for Node.js
- `go test ./...` for Go
- `cargo test` for Rust
- `mvn test` / `gradle test` for Java

### Step 4 — Review the manual checklist

Work through `templates/owasp_checklist.md` for the A01, A04, A07, and A09 categories that automated tools cannot fully cover. Mark each item: ✅ Pass | ⚠️ Concern | ❌ Fail | N/A.

### Step 5 — Generate the security report

Fill in `templates/owasp_report.md` with:
- Scanner findings from `./owasp-findings/summary.json` (Step 2)
- Test suite result from Step 3 (sets the top-level Verdict)
- Manual checklist findings from Step 4

Apply the severity mapping table above to translate scanner severities into report severities. Group findings by OWASP category (A01–A10).

### Step 6 — Present findings

Show the report summary. For each Critical or High finding, provide:
1. Exact file and line number
2. A minimal proof-of-concept showing exploitability
3. A concrete fix with before/after code

Offer to auto-fix Low/Medium findings where the fix is mechanical (e.g., replace `MD5` with `SHA-256`, add `httpOnly` cookie flag, pin a dependency version).
