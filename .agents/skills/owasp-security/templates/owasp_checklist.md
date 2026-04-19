# OWASP Top 10 2021 — Manual Review Checklist

Mark each item: ✅ Pass | ⚠️ Concern | ❌ Fail | N/A

> **Automated tools cover A02, A03, A05, A06, A08, A10 well.**
> This checklist focuses on the categories that require human judgment:
> A01 (access control logic), A04 (design), A07 (auth flows), A09 (logging).
> Complete all sections even if automated scans found no issues.

---

## A01 — Broken Access Control

- [ ] Every sensitive route/endpoint has an explicit authorization check (not just authentication)
- [ ] Object-level access is verified by ownership, not just by ID (no IDOR: `GET /invoice/42` checks that invoice 42 belongs to the current user)
- [ ] Function-level access control: admin-only endpoints return 403 for non-admin users, not just hide the UI
- [ ] Directory listing is disabled on all web servers
- [ ] CORS policy is restrictive — `Access-Control-Allow-Origin` is not `*` for credentialed requests
- [ ] JWT / session tokens are validated server-side on every request, not just on login
- [ ] Privilege escalation paths are tested: can a regular user reach an admin action by modifying a request parameter?
- [ ] File upload paths cannot be used to overwrite server-side code or config files

---

## A02 — Cryptographic Failures

*(Automated: semgrep, bandit B303/B304/B305/B324 — review any flagged items here)*

- [ ] Sensitive data (passwords, PII, payment info) is encrypted at rest
- [ ] TLS 1.2+ enforced; TLS 1.0/1.1 and SSLv3 disabled
- [ ] Passwords stored using bcrypt, scrypt, Argon2, or PBKDF2 — not MD5/SHA1/SHA256 alone
- [ ] Encryption keys are stored in a secrets manager, not in source code or environment files committed to VCS
- [ ] HTTP Strict Transport Security (HSTS) header is set
- [ ] Sensitive data is not transmitted in URL query parameters (appears in server logs and browser history)

---

## A03 — Injection

*(Automated: semgrep, bandit B608/B602/B605/B703 — review any flagged items here)*

- [ ] All database queries use parameterized statements or an ORM — no string concatenation in SQL
- [ ] Shell commands never interpolate user input directly (`subprocess.run(["cmd", user_arg])` not `shell=True`)
- [ ] Template engines use auto-escaping; user content is never passed to `render_template_string` or equivalent
- [ ] LDAP queries use parameterized filters
- [ ] XML parsers have external entity processing (XXE) disabled
- [ ] `eval()`, `exec()`, `Function()` are absent from production code paths that touch user input

---

## A04 — Insecure Design

*(No automated tool covers this — requires architectural review)*

- [ ] Threat model exists and has been reviewed in the last 6 months
- [ ] Rate limiting is applied to authentication endpoints (login, password reset, OTP)
- [ ] Account lockout or exponential backoff is implemented after repeated failed logins
- [ ] Password reset flows use time-limited, single-use tokens — not security questions
- [ ] Multi-tenancy boundaries are enforced at the data layer, not just the UI layer
- [ ] Sensitive business flows (payment, account deletion) require re-authentication
- [ ] File upload limits (size, type, count) are enforced server-side
- [ ] Error messages do not reveal internal stack traces, file paths, or DB schema to end users

---

## A05 — Security Misconfiguration

*(Automated: semgrep, trivy — review any flagged items here)*

- [ ] Debug mode / verbose error output is disabled in production
- [ ] Default credentials have been changed on all services (DB, admin panels, cloud consoles)
- [ ] Unnecessary HTTP methods (TRACE, PUT on non-API endpoints) are disabled
- [ ] Security headers are set: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`
- [ ] Cloud storage buckets / blob containers are not publicly readable unless intentional
- [ ] Dependency versions are pinned — no `*` or `latest` in production manifests
- [ ] Secrets are not present in Docker image layers (`docker history` check)

---

## A06 — Vulnerable & Outdated Components

*(Automated: npm audit, pip-audit, govulncheck, bundler-audit, cargo audit, osv-scanner)*

- [ ] All automated scanner findings from this category have been reviewed
- [ ] Direct dependencies are up to date (patch versions at minimum)
- [ ] No dependency with a known CVE rated High or Critical is in use
- [ ] A process exists to receive and act on new CVE notifications (e.g., Dependabot, Renovate)
- [ ] Unused dependencies have been removed

---

## A07 — Identification & Authentication Failures

*(Automated: semgrep — review any flagged items here)*

- [ ] Passwords require minimum length ≥ 12 characters and are checked against known-breached lists
- [ ] Multi-factor authentication is available (required for admin accounts)
- [ ] Session tokens are invalidated on logout and after password change
- [ ] Session fixation is prevented — new session ID is issued after login
- [ ] "Remember me" tokens are long-lived but revocable and stored securely (httpOnly, Secure, SameSite)
- [ ] Account enumeration is prevented — login and password-reset endpoints return identical responses for valid and invalid usernames
- [ ] Brute-force protection is in place on all authentication endpoints

---

## A08 — Software & Data Integrity Failures

*(Automated: osv-scanner, trivy)*

- [ ] CI/CD pipeline verifies checksums or signatures of downloaded artifacts
- [ ] Deserialization of untrusted data uses safe formats (JSON, not pickle/Java serialization/YAML with arbitrary tags)
- [ ] Auto-update mechanisms verify signatures before applying updates
- [ ] Third-party scripts (CDN-hosted JS) use Subresource Integrity (SRI) hashes
- [ ] Infrastructure-as-code changes require peer review before deployment

---

## A09 — Security Logging & Monitoring Failures

*(No automated tool fully covers this — requires code review)*

- [ ] Authentication events (login, logout, failed login, password change) are logged with timestamp and IP
- [ ] Authorization failures (403 responses) are logged
- [ ] Sensitive data (passwords, tokens, PII, payment card numbers) is never written to logs
- [ ] Log entries include a correlation ID to trace a request across services
- [ ] Logs are written to an append-only store — application cannot delete its own logs
- [ ] Alerts exist for repeated authentication failures and unusual access patterns
- [ ] Log retention policy meets compliance requirements (e.g., 90 days minimum)

---

## A10 — Server-Side Request Forgery (SSRF)

*(Automated: semgrep, bandit B310 — review any flagged items here)*

- [ ] All outbound HTTP requests validate the destination URL against an allowlist
- [ ] Internal IP ranges (169.254.x.x, 10.x.x.x, 172.16-31.x.x, 192.168.x.x) are blocked from user-supplied URLs
- [ ] DNS rebinding is mitigated (resolve and validate IP before connecting)
- [ ] Cloud metadata endpoints (169.254.169.254) are blocked at the network layer
- [ ] Redirects from user-supplied URLs are not followed automatically
