"""
RepoGuardian Dependency Agent
Scans PR dependencies for known vulnerabilities using pip-audit
"""

import os
import json
import logging
import tempfile
import subprocess
from dataclasses import dataclass, field

from github import Github
from dotenv import load_dotenv

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
    package: str
    version: str
    vulnerability: str
    severity: str
    fix_version: str


@dataclass
class DependencyResult:
    repo_name: str
    pr_number: int
    issues: list[DependencyIssue] = field(default_factory=list)


# ─────────────────────────────────────────
# Run pip-audit
# ─────────────────────────────────────────

def scan_requirements(requirements_text: str):

    findings = []

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False
    ) as tmp:

        tmp.write(requirements_text)
        tmp_path = tmp.name

    try:

        result = subprocess.run(
            ["pip-audit", "-r", tmp_path, "-f", "json"],
            capture_output=True,
            text=True
        )

        data = json.loads(result.stdout)

        for dep in data.get("dependencies", []):

            name = dep.get("name")
            version = dep.get("version")

            for vuln in dep.get("vulns", []):

                vuln_id = vuln.get("id")
                fix_versions = vuln.get("fix_versions", [])

                findings.append(DependencyIssue(
                    package=name,
                    version=version,
                    vulnerability=vuln_id,
                    severity="high" if vuln_id.startswith("CVE") else "medium",
                    fix_version=fix_versions[0] if fix_versions else "unknown"
                ))

    finally:
        os.remove(tmp_path)

    return findings


# ─────────────────────────────────────────
# Fetch requirements.txt from PR
# ─────────────────────────────────────────

def fetch_requirements(repo_name, pr_number):

    repo = github_client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    for file in pr.get_files():

        if file.filename.endswith("requirements.txt"):

            content = repo.get_contents(file.filename, ref=pr.head.sha)

            return content.decoded_content.decode()

    return None


# ─────────────────────────────────────────
# Post PR Comments
# ─────────────────────────────────────────

def post_dependency_comments(pr, issues):

    if not issues:
        log.info("No dependency issues found.")
        return

    body = "## 📦 RepoGuardian Dependency Scan\n\n"

    for issue in issues:

        body += (
            f"🔴 **{issue.package} {issue.version}**\n"
            f"- Vulnerability: `{issue.vulnerability}`\n"
            f"- Fix: Upgrade to `{issue.fix_version}`\n\n"
        )

    pr.create_issue_comment(body)

    log.info("Dependency report posted.")


# ─────────────────────────────────────────
# Main Agent
# ─────────────────────────────────────────

def run_dependency_agent(repo_name, pr_number):

    log.info(f"Dependency Agent started — {repo_name} PR #{pr_number}")

    repo = github_client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    requirements = fetch_requirements(repo_name, pr_number)

    if not requirements:

        log.info("No requirements.txt found.")
        return DependencyResult(repo_name, pr_number, [])

    issues = scan_requirements(requirements)

    post_dependency_comments(pr, issues)

    log.info(f"Dependency scan finished. Found {len(issues)} issues.")

    return DependencyResult(repo_name, pr_number, issues)


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 3:

        print("Usage:")
        print("python dependency.py owner/repo pr_number")
        exit()

    repo = sys.argv[1]
    pr_number = int(sys.argv[2])

    run_dependency_agent(repo, pr_number)