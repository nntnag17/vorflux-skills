# OWASP Top 10 2021 — Security Audit Report

**Project:** {{PROJECT_NAME}}
**Auditor:** AI Security Audit (owasp-security skill)
**Date:** {{DATE}}
**Scope:** {{SCOPE_DESCRIPTION}}
**Commit / Branch:** {{GIT_REF}}

---

## Verdict

> **{{VERDICT}}**
>
> Allowed values:
> - `PASS` — no Critical/High findings; test suite passed; all manual checks clear
> - `FINDINGS` — issues found; test suite passed; review required before merge
> - `BLOCKED` — test suite failed or not detected; audit cannot be completed until tests pass

---

## Test Suite Result

| Status | Framework | Command | Duration |
|--------|-----------|---------|----------|
| {{TEST_STATUS}} | {{TEST_FRAMEWORK}} | {{TEST_COMMAND}} | {{TEST_DURATION}} |

> If status is FAILED or NOT DETECTED, set Verdict to **BLOCKED** and stop here.

---

## Automated Scanner Summary

| Tool | Category | Findings | Severity |
|------|----------|----------|----------|
| semgrep | A01–A10 | {{SEMGREP_COUNT}} | {{SEMGREP_SEV}} |
| bandit | A02/A03/A10 | {{BANDIT_COUNT}} | {{BANDIT_SEV}} |
| gitleaks/trufflehog | A02/A09 | {{SECRETS_COUNT}} | {{SECRETS_SEV}} |
| npm audit | A06/A08 | {{NPM_COUNT}} | {{NPM_SEV}} |
| pip-audit | A06/A08 | {{PIP_COUNT}} | {{PIP_SEV}} |
| govulncheck | A06/A08 | {{GO_COUNT}} | {{GO_SEV}} |
| bundler-audit | A06/A08 | {{RUBY_COUNT}} | {{RUBY_SEV}} |
| cargo audit | A06/A08 | {{RUST_COUNT}} | {{RUST_SEV}} |
| osv-scanner | A06/A08 | {{OSV_COUNT}} | {{OSV_SEV}} |
| trivy | A05 | {{TRIVY_COUNT}} | {{TRIVY_SEV}} |

**Skipped tools (not installed):** {{SKIPPED_TOOLS}}

Full per-tool output: `./owasp-findings/`
Normalized summary: `./owasp-findings/summary.json`

---

## 🔴 Critical Findings (exploitable with no preconditions)

<!-- Hardcoded secrets, unauthenticated RCE, gitleaks/trufflehog hits -->

### C1: {{TITLE}}
**OWASP Category:** {{A0X — Category Name}}
**Tool:** {{tool}} | **File:** `{{path}}:{{line}}`
**Problem:** {{clear description of the vulnerability}}
**Exploitability:** {{how an attacker would exploit this — minimal PoC}}
**Fix:**
```{{lang}}
// Before
{{vulnerable code}}

// After
{{fixed code}}
```

---

## 🟠 High Findings (exploitable with low effort)

### H1: {{TITLE}}
**OWASP Category:** {{A0X — Category Name}}
**Tool:** {{tool}} | **File:** `{{path}}:{{line}}`
**Problem:** {{description}}
**Fix:** {{concrete remediation}}

---

## 🟡 Medium Findings (requires specific conditions)

- `{{file}}:{{line}}` — **{{tool}}** — {{description}} → {{fix}}

---

## 🟢 Low / Informational

- `{{file}}:{{line}}` — **{{tool}}** — {{description}}

---

## Manual Checklist Results

See `templates/owasp_checklist.md` for the full per-category checklist.
Summarize any ⚠️ Concern or ❌ Fail items here:

| Category | Item | Status | Notes |
|----------|------|--------|-------|
| A01 | {{item}} | ⚠️ / ❌ | {{notes}} |
| A04 | {{item}} | ⚠️ / ❌ | {{notes}} |
| A07 | {{item}} | ⚠️ / ❌ | {{notes}} |
| A09 | {{item}} | ⚠️ / ❌ | {{notes}} |

---

## Next Steps

- [ ] Fix all Critical findings before merge
- [ ] Address High findings before next release
- [ ] Review Medium findings — fix or accept risk with justification
- [ ] Re-run `owasp_scan.sh` after fixes to verify remediation
- [ ] Ensure test suite passes (`run_tests.sh`)
