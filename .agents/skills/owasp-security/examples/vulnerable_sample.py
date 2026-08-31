"""
vulnerable_sample.py — Intentionally insecure Python file for testing owasp_scan.sh.

This file contains deliberate OWASP Top 10 vulnerabilities for demonstration purposes.
DO NOT use any of these patterns in production code.
"""

import hashlib
import sqlite3
import subprocess
import os

# ── A02: Cryptographic Failure — hardcoded secret + weak hash ─────────────────

# Split across concatenation so bandit (B105/B106) still flags the hardcoded value
# while avoiding a single contiguous secret string that would match secret-scanner regex.
API_KEY = "sk-prod-" + "abc123supersecretkey9999"     # A02: hardcoded secret (demo) # gitleaks:allow
# DB_PASSWORD is long enough to match the grep-fallback secret pattern in owasp_scan.sh
DB_PASSWORD = "super-secret-db-password-demo"         # A02: hardcoded credential (demo) # gitleaks:allow

def hash_password(password):
    # A02: MD5 is cryptographically broken for password storage
    return hashlib.md5(password.encode()).hexdigest()


# ── A03: SQL Injection ────────────────────────────────────────────────────────

def get_user(username):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # A03: string concatenation in SQL query — injectable
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()


# ── A03: OS Command Injection ─────────────────────────────────────────────────

def ping_host(host):
    # A03: shell=True with user-controlled input — command injection
    result = subprocess.run("ping -c 1 " + host, shell=True, capture_output=True)
    return result.stdout


# ── A03: eval() on user input ─────────────────────────────────────────────────

def calculate(expression):
    # A03: eval() on untrusted input allows arbitrary code execution
    return eval(expression)


# ── A10: SSRF — unvalidated URL fetch ────────────────────────────────────────

def fetch_url(url):
    import urllib.request
    # A10: no validation — attacker can fetch internal metadata endpoints
    # e.g., http://169.254.169.254/latest/meta-data/
    return urllib.request.urlopen(url).read()


# ── A09: Sensitive data in logs ───────────────────────────────────────────────

def login(username, password):
    import logging
    # A09: password written to log
    logging.info(f"Login attempt: username={username} password={password}")
    return hash_password(password) == hash_password("correct-password")
