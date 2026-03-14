"""
RepoGuardian — Dependency Agent
Scans PR dependencies for known CVE vulnerabilities using pip-audit.
Posts a summary comment to the GitHub PR.
Returns Finding objects to the Orchestrator for unified health scoring.

.env required:
    GITHUB_TOKEN=...

Install:
    pip install pip-audit PyGithub python-dotenv
"""

import os
import json
import logging
import tempfile
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field

from github import Github, GithubException
from dotenv import load_dotenv

# db.models is one level up — same pattern as orchestrator.py
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Finding

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DEPENDENCY] %(message)s")
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError("Missing GITHUB_TOKEN in .env")

github_client = Github(GITHUB_TOKEN)


# ─────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────

@dataclass
class DependencyIssue:
    package:       str
    version:       str
    vulnerability: str   # CVE ID e.g. CVE-2023-12345
    severity:      str   # "high" | "medium" | "low"
    fix_version:   str   # recommended upgrade version


@dataclass
class DependencyResult:
    repo_name:  str
    pr_number:  int
    issues:     list[DependencyIssue] = field(default_factory=list)
    findings:   list[Finding]         = field(default_factory=list)
    # findings → returned to Orchestrator for unified health score calculation


# ─────────────────────────────────────────
# pip-audit Scanner
# ─────────────────────────────────────────

def scan_requirements(requirements_text: str) -> list[DependencyIssue]:
    """
    Write requirements to a temp file, run pip-audit, parse JSON output.
    Returns a list of DependencyIssue objects — one per CVE found.
    """
    issues = []

    # Write to temp file — pip-audit needs a real file path
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(requirements_text)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["pip-audit", "-r", tmp_path, "-f", "json", "--progress-spinner", "off"],
            capture_output=True,
            text=True,
            timeout=60   # don't hang forever if pip-audit is slow
        )

        # pip-audit exits with code 1 if vulnerabilities are found — that is normal
        if not result.stdout.strip():
            log.warning("pip-audit returned no output — is it installed? Run: pip install pip-audit")
            return []

        data = json.loads(result.stdout)

        for dep in data.get("dependencies", []):
            name    = dep.get("name", "unknown")
            version = dep.get("version", "unknown")

            for vuln in dep.get("vulns", []):
                vuln_id       = vuln.get("id", "UNKNOWN")
                fix_versions  = vuln.get("fix_versions", [])
                description   = vuln.get("description", "")

                # CVE IDs = high, PYSEC IDs = medium (less severe advisory)
                severity = "high" if vuln_id.startswith("CVE") else "medium"

                issues.append(DependencyIssue(
                    package       = name,
                    version       = version,
                    vulnerability = vuln_id,
                    severity      = severity,
                    fix_version   = fix_versions[0] if fix_versions else "no fix available",
                ))

    except subprocess.TimeoutExpired:
        log.error("pip-audit timed out after 60s")
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse pip-audit output: {e}")
        log.error(f"Raw output was: {result.stdout[:300]}")
    except FileNotFoundError:
        log.error("pip-audit not found — install it: pip install pip-audit")
    finally:
        # Always clean up temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return issues


# ─────────────────────────────────────────
# Convert DependencyIssue → Finding
# (same pattern as security.py and pr_review.py)
# ─────────────────────────────────────────

def to_findings(issues: list[DependencyIssue], filename: str) -> list[Finding]:
    """
    Convert DependencyIssue objects → Finding objects.
    The Orchestrator uses Finding objects for unified health score calculation.
    file = requirements.txt path, line = 0 (no specific line for dep issues).
    """
    return [
        Finding(
            agent      = "dependency",
            severity   = issue.severity,
            message    = (
                f"{issue.package} {issue.version} has vulnerability {issue.vulnerability}. "
                f"Upgrade to {issue.fix_version}."
            ),
            file       = filename,
            line       = 0,        # dependency issues have no specific line number
            suggestion = f"Run: pip install {issue.package}>={issue.fix_version}",
        )
        for issue in issues
    ]


# ─────────────────────────────────────────
# Fetch requirements.txt from PR
# ─────────────────────────────────────────

# Dependency files to look for — checks all of these
DEPENDENCY_FILES = [
    "requirements.txt",
    "requirements/base.txt",
    "requirements/prod.txt",
    "requirements/production.txt",
]


def fetch_requirements(repo_name: str, pr_number: int) -> tuple[str | None, str | None]:
    """
    Look for requirements.txt (or variants) in the PR files.
    Returns (file_content, filename) or (None, None) if not found.
    """
    repo = github_client.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    for f in pr.get_files():
        # Match any of the known dependency file names
        if any(f.filename.endswith(dep_file) for dep_file in DEPENDENCY_FILES):
            try:
                content = repo.get_contents(f.filename, ref=pr.head.sha)
                log.info(f"Found dependency file: {f.filename}")
                return content.decoded_content.decode("utf-8"), f.filename
            except GithubException as e:
                log.warning(f"Could not read {f.filename}: {e}")

    return None, None


# ─────────────────────────────────────────
# Build GitHub Summary Comment
# ─────────────────────────────────────────

def build_dependency_report(issues: list[DependencyIssue]) -> str:
    """Build a markdown summary comment — same style as security and pr_review agents."""

    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1

    if counts["high"] > 0:
        badge = "🔴 VULNERABLE DEPENDENCIES — DO NOT MERGE"
    elif counts["medium"] > 0:
        badge = "🟡 ADVISORY DEPENDENCIES — REVIEW REQUIRED"
    else:
        badge = "🟢 NO KNOWN VULNERABILITIES"

    # Group by package so each package appears once with all its CVEs
    grouped = defaultdict(list)
    for issue in issues:
        grouped[(issue.package, issue.version)].append(issue)

    package_rows = ""
    for (package, version), vulns in grouped.items():
        vuln_list    = ", ".join(f"`{v.vulnerability}`" for v in vulns)
        fix_version  = vulns[0].fix_version
        severity_icon = "🔴" if any(v.severity == "high" for v in vulns) else "🟡"
        package_rows += (
            f"| {severity_icon} `{package}` | `{version}` | {vuln_list} | "
            f"`{fix_version}` |\n"
        )

    body = f"""## 📦 RepoGuardian — Dependency Scan Report

**Status:** {badge}

### Vulnerability Summary
| Severity | Count |
|----------|-------|
| 🔴 High (CVE) | **{counts['high']}** |
| 🟡 Medium (Advisory) | **{counts['medium']}** |
| **Total** | **{len(issues)}** |

### Vulnerable Packages
| Package | Current Version | Vulnerability | Fix Version |
|---------|----------------|---------------|-------------|
{package_rows}
### How to Fix
Run the following to upgrade all vulnerable packages:
```bash
pip install --upgrade {' '.join(set(f"{i.package}>={i.fix_version}" for i in issues if i.fix_version != "no fix available"))}
```

> *RepoGuardian Dependency Agent — KLH Hackathon 2025 — Powered by pip-audit*
"""
    return body


def post_dependency_comment(pr, issues: list[DependencyIssue]):
    """Post the dependency report as a PR comment — same pattern as other agents."""
    if not issues:
        log.info("No dependency issues — skipping comment.")
        return

    body = build_dependency_report(issues)

    try:
        pr.create_issue_comment(body)
        log.info("Dependency report posted to PR.")
    except GithubException as e:
        log.error(f"Could not post dependency comment: {e}")


# ─────────────────────────────────────────
# Main Agent — called by Orchestrator
# ─────────────────────────────────────────

def run_dependency_agent(repo_name: str, pr_number: int) -> DependencyResult:
    """
    MAIN FUNCTION — called by orchestrator.

    Usage:
        from tools.dependency import run_dependency_agent
        result = run_dependency_agent("owner/repo", 1)

    Returns:
        DependencyResult with .findings list for Orchestrator health score.
    """
    log.info(f"Dependency Agent started — {repo_name} PR #{pr_number}")

    # Step 1 — Find requirements.txt in the PR
    log.info("Step 1/4 — Checking PR for dependency files...")
    requirements_text, filename = fetch_requirements(repo_name, pr_number)

    if not requirements_text:
        log.info("No requirements.txt found in this PR — nothing to scan.")
        return DependencyResult(repo_name=repo_name, pr_number=pr_number,
                                issues=[], findings=[])

    # Step 2 — Run pip-audit against the requirements file
    log.info(f"Step 2/4 — Running pip-audit on {filename}...")
    issues = scan_requirements(requirements_text)
    log.info(f"pip-audit found {len(issues)} vulnerability/vulnerabilities")

    # Step 3 — Convert to Finding objects for Orchestrator
    log.info("Step 3/4 — Converting to Finding objects...")
    findings = to_findings(issues, filename)

    # Step 4 — Post summary comment to GitHub PR
    log.info("Step 4/4 — Posting report to GitHub PR...")
    repo = github_client.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)
    post_dependency_comment(pr, issues)

    log.info(f"Dependency Agent done — {len(issues)} issue(s) found")

    return DependencyResult(
        repo_name = repo_name,
        pr_number = pr_number,
        issues    = issues,
        findings  = findings,   # passed to Orchestrator for health score
    )


# ─────────────────────────────────────────
# Orchestrator-Compatible Wrapper
# (matches the exact signature orchestrator.py expects)
# ─────────────────────────────────────────

def run_dependency_scan(repo_name: str, pr_number: int) -> list[Finding]:
    """
    Thin wrapper called by orchestrator._run_dependency().

    Orchestrator expects: findings, agent_name = _run_dependency(repo, pr)
    This returns just the findings list so orchestrator can extend all_findings.
    """
    result = run_dependency_agent(repo_name, pr_number)
    return result.findings


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("\n========================================")
    print("  RepoGuardian — Dependency Agent")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python tools/dependency.py <owner/repo> <pr_number>")
        print("Example: python tools/dependency.py vamshi/myproject 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = int(sys.argv[2])

    if not os.environ.get("GITHUB_TOKEN"):
        print("ERROR: Missing GITHUB_TOKEN in .env")
        sys.exit(1)

    result = run_dependency_agent(repo_arg, pr_arg)

    print("\n========================================")
    print("  RESULT")
    print("========================================")
    print(f"  PR          : #{result.pr_number} in {result.repo_name}")
    print(f"  Issues found: {len(result.issues)}")
    print("========================================")

    for i, issue in enumerate(result.issues, 1):
        icon = "🔴" if issue.severity == "high" else "🟡"
        print(f"\n  {i}. {icon} [{issue.severity.upper()}] {issue.package} {issue.version}")
        print(f"     CVE        : {issue.vulnerability}")
        print(f"     Fix version: {issue.fix_version}")