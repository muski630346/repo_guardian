"""
tools/dependency.py
Dependency Scanner — checks requirements.txt for vulnerable packages.
Uses pip-audit for real CVE checking.
P2 owns this file entirely.
"""

import json
import tempfile
import subprocess
import os
import re
from typing import List
from db.models import Finding


def run_dependency_scan(requirements: str, filename: str = "requirements.txt") -> List[Finding]:
    """
    Master function — runs all dependency checks.
    Args:
        requirements: Raw contents of requirements.txt as a string
        filename:     File label for the report
    Returns:
        Combined List[Finding]
    """
    all_findings = []
    all_findings += _scan_cve(requirements, filename)
    all_findings += _scan_unpinned(requirements, filename)
    all_findings += _scan_dangerous_packages(requirements, filename)
    return all_findings


# ─────────────────────────────────────────────
# SCANNER 1 — Real CVE check (pip-audit)
# ─────────────────────────────────────────────

def _scan_cve(requirements: str, filename: str) -> List[Finding]:
    findings = []
    tmp_path = None

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="rg_dep_"
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
                    vuln_id  = vuln.get("id", "")
                    desc     = vuln.get("description", "")[:120]
                    fix_vers = vuln.get("fix_versions", [])
                    fix_str  = fix_vers[0] if fix_vers else "No fix available yet"

                    findings.append(Finding(
                        agent      = "dependency",
                        severity   = "high" if vuln_id.startswith("CVE") else "medium",
                        message    = f"[CVE] {package}=={version} — {vuln_id}: {desc}",
                        file       = filename,
                        line       = 0,
                        suggestion = f"Upgrade {package} to version {fix_str}.",
                        cwe        = None
                    ))

    except subprocess.TimeoutExpired:
        findings.append(Finding(
            agent      = "dependency",
            severity   = "low",
            message    = "[CVE] Dependency scan timed out.",
            file       = filename,
            line       = 0,
            suggestion = "Run pip-audit manually: pip-audit -r requirements.txt",
            cwe        = None
        ))

    except (json.JSONDecodeError, Exception):
        pass

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return findings


# ─────────────────────────────────────────────
# SCANNER 2 — Unpinned versions
# ─────────────────────────────────────────────

def _scan_unpinned(requirements: str, filename: str) -> List[Finding]:
    findings = []
    lines = requirements.splitlines()

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if not any(op in line for op in ["==", ">=", "<=", "~=", "!="]):
            package = line.split("[")[0].strip()
            findings.append(Finding(
                agent      = "dependency",
                severity   = "medium",
                message    = f"[UNPINNED] '{package}' has no version pinned.",
                file       = filename,
                line       = i,
                suggestion = f"Pin the version: {package}==<version>. Run 'pip show {package}' to find current version.",
                cwe        = None
            ))

        elif ">=" in line and "," not in line:
            package = line.split(">=")[0].strip()
            version = line.split(">=")[1].strip()
            findings.append(Finding(
                agent      = "dependency",
                severity   = "low",
                message    = f"[UNPINNED] '{package}>={version}' has no upper bound.",
                file       = filename,
                line       = i,
                suggestion = f"Add upper bound: {package}>={version},<{_next_major(version)}",
                cwe        = None
            ))

    return findings


# ─────────────────────────────────────────────
# SCANNER 3 — Known dangerous packages
# ─────────────────────────────────────────────

def _scan_dangerous_packages(requirements: str, filename: str) -> List[Finding]:
    findings = []
    lines = requirements.splitlines()

    dangerous = {
        "pycrypto":  ("high",   "pycrypto is abandoned and has known vulnerabilities.",
                      "Replace with 'pycryptodome' — a maintained fork."),
        "pydes":     ("high",   "pyDES implements DES which is a broken cipher.",
                      "Use AES-256 via the cryptography package instead."),
        "telnetlib": ("high",   "Telnet sends data in plaintext including passwords.",
                      "Use paramiko for SSH instead."),
        "ftplib":    ("medium", "FTP sends credentials in plaintext.",
                      "Use SFTP via paramiko instead."),
        "xmlrpc":    ("medium", "XML-RPC is vulnerable to XML injection attacks.",
                      "Use a REST API with JSON instead."),
        "cgi":       ("medium", "The cgi module is deprecated and has security issues.",
                      "Use Flask or FastAPI instead."),
        "imp":       ("low",    "The imp module is deprecated since Python 3.4.",
                      "Use importlib instead."),
        "distutils": ("low",    "distutils is deprecated and removed in Python 3.12.",
                      "Use setuptools instead."),
    }

    for i, line in enumerate(lines, 1):
        line_clean = line.strip().lower()
        if not line_clean or line_clean.startswith("#"):
            continue

        package_name = re.split(r"[>=<!~\[]", line_clean)[0].strip()

        if package_name in dangerous:
            severity, message, suggestion = dangerous[package_name]
            findings.append(Finding(
                agent      = "dependency",
                severity   = severity,
                message    = f"[DANGEROUS] {package_name} — {message}",
                file       = filename,
                line       = i,
                suggestion = suggestion,
                cwe        = None
            ))

    return findings


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────

def _next_major(version: str) -> str:
    try:
        major = int(version.split(".")[0])
        return f"{major + 1}.0.0"
    except (ValueError, IndexError):
        return "999"