"""
tools/security.py
Complete Security Scanner — covers all 5 areas:
  1. Python code vulnerabilities     (Bandit)
  2. Vulnerable dependencies         (pip-audit)
  3. Advanced security patterns      (custom checks)
  4. Secret detection                (regex + detect-secrets)
  5. Code quality + security         (custom checks)
"""

import os
import re
import json
import tempfile
import subprocess
from typing import List
from db.models import Finding


# ─────────────────────────────────────────────
# MAIN FUNCTION — runs all 5 scanners
# ─────────────────────────────────────────────

def run_full_security_scan(
    code: str,
    filename: str = "pr_code.py",
    requirements: str = ""
) -> List[Finding]:
    """
    Master function — runs all 5 scanners and returns combined findings.

    Args:
        code:         Raw Python source code from the PR
        filename:     Name of the file being scanned
        requirements: Contents of requirements.txt (optional)

    Returns:
        Combined List[Finding] from all scanners
    """
    all_findings = []

    # 1. Python vulnerabilities via Bandit
    all_findings += _scan_bandit(code, filename)

    # 2. Vulnerable dependencies via pip-audit
    if requirements:
        all_findings += _scan_dependencies(requirements)

    # 3. Advanced security patterns
    all_findings += _scan_advanced_patterns(code, filename)

    # 4. Secret detection
    all_findings += _scan_secrets(code, filename)

    # 5. Code quality + security
    all_findings += _scan_code_quality(code, filename)

    return all_findings


# ─────────────────────────────────────────────
# SCANNER 1 — Python vulnerabilities (Bandit)
# ─────────────────────────────────────────────

def _scan_bandit(code: str, filename: str) -> List[Finding]:
    findings = []
    tmp_path = None

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix="rg_bandit_"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-q", tmp_path],
            capture_output=True, text=True, timeout=30
        )

        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data.get("results", []):
                severity = issue.get("issue_severity", "LOW").lower()
                line     = issue.get("line_number", 0)
                message  = issue.get("issue_text", "Unknown issue")
                test_id  = issue.get("test_id", "")
                more_info= issue.get("more_info", "")
                cwe_id   = issue.get("issue_cwe", {}).get("id", "")

                findings.append(Finding(
                    agent      = "security",
                    severity   = severity,
                    message    = f"[VULN] [{test_id}] {message}",
                    file       = filename,
                    line       = line,
                    suggestion = _bandit_suggestion(test_id, more_info),
                    cwe        = f"CWE-{cwe_id}" if cwe_id else None
                ))

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return findings


# ─────────────────────────────────────────────
# SCANNER 2 — Vulnerable dependencies (pip-audit)
# ─────────────────────────────────────────────

def _scan_dependencies(requirements: str) -> List[Finding]:
    findings = []
    tmp_path = None

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="rg_req_"
    ) as tmp:
        tmp.write(requirements)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["pip-audit", "-r", tmp_path, "-f", "json", "--no-deps"],
            capture_output=True, text=True, timeout=60
        )

        if result.stdout.strip():
            data = json.loads(result.stdout)
            for dep in data.get("dependencies", []):
                package = dep.get("name", "unknown")
                version = dep.get("version", "unknown")

                for vuln in dep.get("vulns", []):
                    vuln_id    = vuln.get("id", "")
                    desc       = vuln.get("description", "")[:120]
                    fix_vers   = vuln.get("fix_versions", [])
                    fix_str    = fix_vers[0] if fix_vers else "No fix available yet"

                    findings.append(Finding(
                        agent      = "security",
                        severity   = "high" if vuln_id.startswith("CVE") else "medium",
                        message    = f"[DEPENDENCY] {package}=={version} — {vuln_id}: {desc}",
                        file       = "requirements.txt",
                        line       = 0,
                        suggestion = f"Upgrade {package} to version {fix_str}.",
                        cwe        = None
                    ))

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return findings


# ─────────────────────────────────────────────
# SCANNER 3 — Advanced security patterns
# ─────────────────────────────────────────────

def _scan_advanced_patterns(code: str, filename: str) -> List[Finding]:
    findings = []
    lines = code.splitlines()

    patterns = [
        # SQL Injection patterns
        (r'execute\s*\(\s*["\'].*%.*["\']', "high",
         "[ADVANCED] Possible SQL injection via string formatting in execute().",
         "Use parameterised queries: cursor.execute('SELECT * FROM t WHERE id = %s', (id,))"),

        # Command injection
        (r'os\.system\s*\(', "high",
         "[ADVANCED] os.system() allows command injection.",
         "Use subprocess.run(['cmd', 'arg'], shell=False) instead."),

        # Insecure deserialization
        (r'pickle\.loads?\s*\(', "high",
         "[ADVANCED] Insecure deserialization with pickle.",
         "Never unpickle data from untrusted sources. Use JSON instead."),

        # Path traversal
        (r'open\s*\(.*\+.*\)', "medium",
         "[ADVANCED] Possible path traversal — user input used in file path.",
         "Validate and sanitise file paths. Use os.path.basename() and restrict to safe directories."),

        # Weak crypto
        (r'DES|RC4|Blowfish|3DES', "high",
         "[ADVANCED] Weak or deprecated encryption algorithm detected.",
         "Use AES-256-GCM or ChaCha20-Poly1305 instead."),

        # Debug mode left on
        (r'DEBUG\s*=\s*True', "medium",
         "[ADVANCED] DEBUG mode is enabled.",
         "Set DEBUG = False before deploying to production."),

        # Insecure random for security purposes
        (r'random\.(randint|choice|random)\s*\(', "medium",
         "[ADVANCED] Insecure random number generator used.",
         "Use the secrets module for tokens, passwords, and security-sensitive values."),

        # Open redirect
        (r'redirect\s*\(.*request\.(args|form|get)', "medium",
         "[ADVANCED] Possible open redirect using user-supplied input.",
         "Validate redirect URLs against an allowlist of trusted destinations."),

        # JWT none algorithm
        (r'algorithm\s*=\s*["\']none["\']', "high",
         "[ADVANCED] JWT using 'none' algorithm — completely bypasses signature verification.",
         "Always use a strong algorithm like HS256 or RS256 for JWTs."),

        # Hardcoded IPs
        (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', "low",
         "[ADVANCED] Hardcoded IP address detected.",
         "Move IP addresses to environment variables or config files."),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, severity, message, suggestion in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append(Finding(
                    agent      = "security",
                    severity   = severity,
                    message    = message,
                    file       = filename,
                    line       = i,
                    suggestion = suggestion,
                    cwe        = None
                ))

    return findings


# ─────────────────────────────────────────────
# SCANNER 4 — Secret detection
# ─────────────────────────────────────────────

def _scan_secrets(code: str, filename: str) -> List[Finding]:
    findings = []
    lines = code.splitlines()

    secret_patterns = [
        (r'(api_key|apikey|api-key)\s*=\s*["\'][a-zA-Z0-9_\-]{10,}["\']',
         "API key hardcoded in source code.",
         "Move to environment variable: os.getenv('API_KEY')"),

        (r'(secret_key|secret|SECRET_KEY)\s*=\s*["\'][a-zA-Z0-9_\-]{6,}["\']',
         "Secret key hardcoded in source code.",
         "Move to environment variable: os.getenv('SECRET_KEY')"),

        (r'(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']',
         "Hardcoded password found in source code.",
         "Never hardcode passwords. Use os.getenv('PASSWORD') instead."),

        (r'(token|auth_token|access_token)\s*=\s*["\'][a-zA-Z0-9_\-\.]{10,}["\']',
         "Hardcoded token found in source code.",
         "Move tokens to environment variables and rotate them immediately."),

        (r'(aws_access_key|aws_secret|AKIA)[a-zA-Z0-9]{10,}',
         "AWS credentials hardcoded in source code!",
         "Revoke this key immediately and move to AWS IAM roles or env vars."),

        (r'ghp_[a-zA-Z0-9]{36}',
         "GitHub Personal Access Token hardcoded!",
         "Revoke this token immediately at github.com/settings/tokens."),

        (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
         "Private key hardcoded in source code!",
         "Remove immediately. Store private keys in secure vaults, never in code."),

        (r'(mongodb|mysql|postgresql|postgres|sqlite):\/\/[^\s"\']+:[^\s"\']+@',
         "Database connection string with credentials hardcoded.",
         "Move connection strings to environment variables."),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, message, suggestion in secret_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append(Finding(
                    agent      = "security",
                    severity   = "high",
                    message    = f"[SECRET] {message}",
                    file       = filename,
                    line       = i,
                    suggestion = suggestion,
                    cwe        = "CWE-798"
                ))

    return findings


# ─────────────────────────────────────────────
# SCANNER 5 — Code quality + security
# ─────────────────────────────────────────────

def _scan_code_quality(code: str, filename: str) -> List[Finding]:
    findings = []
    lines = code.splitlines()

    # Check for bare except clauses
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped == "except:" or stripped == "except :":
            findings.append(Finding(
                agent      = "security",
                severity   = "medium",
                message    = "[QUALITY] Bare except clause — catches everything including KeyboardInterrupt.",
                file       = filename,
                line       = i,
                suggestion = "Catch specific exceptions: except ValueError as e: logger.error(e)",
                cwe        = None
            ))

        if "TODO" in line or "FIXME" in line or "HACK" in line:
            findings.append(Finding(
                agent      = "security",
                severity   = "low",
                message    = f"[QUALITY] Unresolved comment found: {stripped[:60]}",
                file       = filename,
                line       = i,
                suggestion = "Resolve all TODO/FIXME/HACK comments before merging to main.",
                cwe        = None
            ))

        if re.search(r'print\s*\(.*password|print\s*\(.*secret|print\s*\(.*token', line, re.IGNORECASE):
            findings.append(Finding(
                agent      = "security",
                severity   = "high",
                message    = "[QUALITY] Sensitive data being printed to console.",
                file       = filename,
                line       = i,
                suggestion = "Remove print statements that expose passwords, secrets, or tokens.",
                cwe        = "CWE-312"
            ))

        if re.search(r'verify\s*=\s*False', line):
            findings.append(Finding(
                agent      = "security",
                severity   = "high",
                message    = "[QUALITY] SSL verification disabled — vulnerable to MITM attacks.",
                file       = filename,
                line       = i,
                suggestion = "Never use verify=False. Fix your SSL certificate instead.",
                cwe        = "CWE-295"
            ))

    # Check function length — functions over 50 lines are a quality risk
    current_func   = None
    func_start     = 0
    func_line_count= 0
    in_function    = False

    for i, line in enumerate(lines, 1):
        if re.match(r'\s*def ', line):
            if in_function and func_line_count > 50:
                findings.append(Finding(
                    agent      = "security",
                    severity   = "low",
                    message    = f"[QUALITY] Function '{current_func}' is {func_line_count} lines long — too complex.",
                    file       = filename,
                    line       = func_start,
                    suggestion = "Break functions longer than 50 lines into smaller, focused functions.",
                    cwe        = None
                ))
            match = re.search(r'def (\w+)', line)
            current_func    = match.group(1) if match else "unknown"
            func_start      = i
            func_line_count = 0
            in_function     = True
        elif in_function:
            func_line_count += 1

    return findings


# ─────────────────────────────────────────────
# HELPER — Bandit suggestion lookup
# ─────────────────────────────────────────────

def _bandit_suggestion(test_id: str, fallback: str) -> str:
    suggestions = {
        "B101": "Remove assert statements from production code. Use if/raise instead.",
        "B102": "Never use exec() — it runs arbitrary code.",
        "B104": "Don't bind to 0.0.0.0 in dev. Use 127.0.0.1 instead.",
        "B105": "Hardcoded password found. Move to environment variable.",
        "B106": "Password in function argument. Use environment variables.",
        "B107": "Password as default argument. Never store passwords in code.",
        "B108": "Unsafe temp file. Use tempfile.mkstemp() instead.",
        "B110": "Bare except/pass swallows errors. At least log the exception.",
        "B201": "Flask debug=True exposes debugger. Set debug=False in production.",
        "B301": "Pickle is unsafe with untrusted data.",
        "B303": "MD5/SHA1 are broken. Use SHA-256 instead.",
        "B311": "random is not cryptographically secure. Use secrets module.",
        "B324": "Weak hash. Switch to hashlib.sha256().",
        "B404": "subprocess imported. Ensure shell=False and validate inputs.",
        "B501": "TLS verification disabled. Never use verify=False.",
        "B506": "yaml.load() is unsafe. Use yaml.safe_load() instead.",
        "B602": "shell=True is dangerous. Use a list of args with shell=False.",
        "B605": "os.system() is unsafe. Use subprocess.run() with a list.",
        "B608": "SQL injection risk. Use parameterised queries.",
        "B701": "Jinja2 autoescape is off. Set autoescape=True to prevent XSS.",
    }
    return suggestions.get(test_id, fallback or "Review Bandit docs for fix guidance.")