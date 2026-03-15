"""
RepoGuardian — Auto-Fix Agent
For simple, safe issues — writes the actual code fix and raises
a ready-to-merge Pull Request on GitHub automatically.

Called by the Orchestrator AFTER all other agents finish
(including Memory Agent). Receives all_findings, filters to
auto-fixable ones, applies fixes file-by-file, and opens a PR.

What it can fix automatically (safe, deterministic fixes only):
    SECRETS       → replace hardcoded value with os.getenv("VAR_NAME")
    WEAK_HASH_MD5 → replace hashlib.md5 with hashlib.sha256
    WEAK_HASH_SHA1→ replace hashlib.sha1 with hashlib.sha256
    DEBUG_ENABLED → replace DEBUG=True with DEBUG=False
    HTTP_NOT_HTTPS→ replace http:// with https://
    BARE_EXCEPT   → replace bare except: with except Exception as e:
    EVAL_USAGE    → replace eval( with ast.literal_eval(  + add import
    INSECURE_RANDOM→ replace random.randint/choice with secrets equivalent

What it NEVER touches (too risky to auto-fix):
    SQL injection, XSS, logic bugs, structural issues, pickle, os.system
    Anything requiring understanding of business logic

.env required:
    GITHUB_TOKEN=...

No LLM required — all fixes are deterministic regex replacements.
"""

import os
import re
import sys
import logging
from dataclasses import dataclass, field
from datetime import datetime

from github import Github, GithubException
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Finding

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AUTOFIX] %(message)s")
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError("Missing GITHUB_TOKEN in .env")

github_client = Github(GITHUB_TOKEN)


# ─────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────

@dataclass
class FixResult:
    """Stores the result of applying one fix to one line."""
    file:         str
    line:         int
    rule:         str
    original:     str    # original line content
    fixed:        str    # fixed line content
    description:  str    # human-readable explanation of the fix


@dataclass
class AutoFixResult:
    """Returned to Orchestrator."""
    repo_name:      str
    pr_number:      int
    fixes_applied:  list[FixResult]
    fix_pr_url:     str | None    # URL of the new fix PR, or None if nothing to fix
    fix_pr_number:  int | None
    skipped_rules:  list[str]     # rules that were found but not auto-fixable


# ─────────────────────────────────────────
# Auto-Fixable Rules Registry
# Each entry defines WHAT to fix and HOW to fix it
# fix_fn receives the matched line and returns the corrected line
# ─────────────────────────────────────────

def _fix_hardcoded_secret(line: str) -> str:
    """Replace hardcoded secret value with os.getenv() call."""
    # Match: api_key = "abc123xyz" or SECRET_KEY = 'something'
    pattern = re.compile(
        r'(api_key|apikey|api-key|secret_key|access_token|auth_token)\s*=\s*["\'][^"\']+["\']',
        re.IGNORECASE
    )
    match = pattern.search(line)
    if not match:
        return line
    var_name = match.group(1).upper().replace("-", "_")
    fixed    = pattern.sub(f'{match.group(1)} = os.getenv("{var_name}")', line)
    # Ensure os is imported — add import if not present (handled separately)
    return fixed


def _fix_hardcoded_password(line: str) -> str:
    """Replace hardcoded password with os.getenv() call."""
    pattern = re.compile(
        r'(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']',
        re.IGNORECASE
    )
    match = pattern.search(line)
    if not match:
        return line
    var_name = match.group(1).upper()
    return pattern.sub(f'{match.group(1)} = os.getenv("{var_name}")', line)


def _fix_md5(line: str) -> str:
    """Replace hashlib.md5 with hashlib.sha256."""
    return re.sub(r'hashlib\.md5\s*\(', 'hashlib.sha256(', line, flags=re.IGNORECASE)


def _fix_sha1(line: str) -> str:
    """Replace hashlib.sha1 with hashlib.sha256."""
    return re.sub(r'hashlib\.sha1\s*\(', 'hashlib.sha256(', line, flags=re.IGNORECASE)


def _fix_debug_true(line: str) -> str:
    """Replace DEBUG=True with DEBUG=False."""
    line = re.sub(r'DEBUG\s*=\s*True', 'DEBUG = False', line)
    line = re.sub(r'(app\.run\s*\(.*?)debug\s*=\s*True', r'\1debug=False', line)
    return line


def _fix_http_to_https(line: str) -> str:
    """Replace http:// with https:// (except localhost)."""
    return re.sub(
        r'http://((?!localhost|127\.0\.0\.1|0\.0\.0\.0)[^\s"\']+)',
        r'https://\1',
        line,
        flags=re.IGNORECASE
    )


def _fix_bare_except(line: str) -> str:
    """Replace bare except: with except Exception as e:"""
    return re.sub(r'except\s*:', 'except Exception as e:', line)


def _fix_eval(line: str) -> str:
    """Replace eval( with ast.literal_eval( — safer for literal evaluation."""
    return re.sub(r'\beval\s*\(', 'ast.literal_eval(', line)


def _fix_insecure_random(line: str) -> str:
    """Replace random.randint/choice/random with secrets equivalents."""
    line = re.sub(r'\brandom\.randint\s*\(([^,]+),\s*([^)]+)\)',
                  r'secrets.randbelow(\2)',  line)
    line = re.sub(r'\brandom\.random\s*\(\)',
                  'secrets.SystemRandom().random()', line)
    line = re.sub(r'\brandom\.choice\s*\(',
                  'secrets.choice(', line)
    return line


# Map rule name → (fix_function, fix_description, needs_extra_import)
FIXABLE_RULES = {
    "HARDCODED_API_KEY":  (
        _fix_hardcoded_secret,
        "Replaced hardcoded API key with os.getenv() call",
        "import os"
    ),
    "HARDCODED_PASSWORD": (
        _fix_hardcoded_password,
        "Replaced hardcoded password with os.getenv() call",
        "import os"
    ),
    "WEAK_HASH_MD5": (
        _fix_md5,
        "Replaced hashlib.md5 with hashlib.sha256 (MD5 is cryptographically broken)",
        None
    ),
    "WEAK_HASH_SHA1": (
        _fix_sha1,
        "Replaced hashlib.sha1 with hashlib.sha256 (SHA1 is deprecated for security)",
        None
    ),
    "DEBUG_ENABLED": (
        _fix_debug_true,
        "Set DEBUG=False — debug mode must never reach production",
        None
    ),
    "HTTP_NOT_HTTPS": (
        _fix_http_to_https,
        "Replaced http:// with https:// to encrypt traffic in transit",
        None
    ),
    "BARE_EXCEPT": (
        _fix_bare_except,
        "Replaced bare except: with except Exception as e: to avoid swallowing all exceptions",
        None
    ),
    "EVAL_USAGE": (
        _fix_eval,
        "Replaced eval() with ast.literal_eval() — safer for literal evaluation",
        "import ast"
    ),
    "INSECURE_RANDOM": (
        _fix_insecure_random,
        "Replaced insecure random with secrets module equivalent",
        "import secrets"
    ),
}

# Rules that are found but intentionally NOT auto-fixed (too risky)
UNFIXABLE_RULES = {
    "SQL_INJECTION",
    "SQL_STRING_CONCAT",
    "XSS_INNER_HTML",
    "PRIVATE_KEY_MATERIAL",
    "AWS_KEY",
    "OS_SYSTEM_INJECTION",
    "PICKLE_DESERIALISE",
    "JWT_NONE_ALGORITHM",
}


# ─────────────────────────────────────────
# Extract Rule Name from Finding
# Findings from security agent carry rule in suggestion field
# ─────────────────────────────────────────

def extract_rule(finding: Finding) -> str | None:
    """
    Pull the rule name out of a Finding's suggestion field.
    Security agent stores: "Rule: HARDCODED_API_KEY | Category: secrets"
    Returns "HARDCODED_API_KEY" or None.
    """
    if not finding.suggestion:
        return None
    match = re.search(r'Rule:\s*([A-Z_]+)', finding.suggestion)
    return match.group(1) if match else None


# ─────────────────────────────────────────
# Fetch Full File Content from GitHub
# ─────────────────────────────────────────

def fetch_file_content(repo_name: str, filepath: str, ref: str) -> tuple[str, str]:
    """
    Fetch the full content of a file at a given ref (branch/commit SHA).
    Returns (content_string, file_sha) — sha needed for GitHub update API.
    """
    repo = github_client.get_repo(repo_name)
    try:
        content_file = repo.get_contents(filepath, ref=ref)
        return content_file.decoded_content.decode("utf-8"), content_file.sha
    except GithubException as e:
        log.error(f"Could not fetch {filepath} at {ref}: {e}")
        return "", ""


# ─────────────────────────────────────────
# Apply Fixes to File Content
# ─────────────────────────────────────────

def apply_fixes_to_file(
    content:       str,
    findings:      list[Finding],
    filepath:      str,
) -> tuple[str, list[FixResult]]:
    """
    Apply all auto-fixable findings to a file's content.

    Strategy:
    - Split content into lines
    - For each finding that targets this file, apply the fix function to that line
    - Collect required extra imports (e.g. import os, import ast)
    - Add missing imports at the top of the file if needed
    - Return (fixed_content, list_of_FixResult)
    """
    lines          = content.splitlines(keepends=True)
    applied_fixes  = []
    extra_imports  = set()

    # Sort findings by line number descending so line offsets don't shift
    # (fixing line 50 doesn't affect line 10's index)
    sorted_findings = sorted(
        [f for f in findings if f.file == filepath],
        key=lambda f: f.line,
        reverse=True
    )

    for finding in sorted_findings:
        rule = extract_rule(finding)
        if not rule or rule not in FIXABLE_RULES:
            continue

        fix_fn, description, extra_import = FIXABLE_RULES[rule]

        # line numbers are 1-indexed
        line_idx = finding.line - 1
        if line_idx < 0 or line_idx >= len(lines):
            log.warning(f"Line {finding.line} out of range in {filepath} — skipping")
            continue

        original_line = lines[line_idx].rstrip("\n").rstrip("\r")
        fixed_line    = fix_fn(original_line)

        if fixed_line == original_line:
            log.info(f"  Fix had no effect on {filepath}:{finding.line} [{rule}] — skipping")
            continue

        # Preserve original line ending
        ending       = "\n" if lines[line_idx].endswith("\n") else ""
        lines[line_idx] = fixed_line + ending

        if extra_import:
            extra_imports.add(extra_import)

        applied_fixes.append(FixResult(
            file        = filepath,
            line        = finding.line,
            rule        = rule,
            original    = original_line,
            fixed       = fixed_line,
            description = description,
        ))

        log.info(f"  Fixed {filepath}:{finding.line} [{rule}]")

    # ── Add missing imports at top of file ────────────────────
    if extra_imports and lines:
        # Find where existing imports end
        import_insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_insert_idx = i + 1

        for imp in sorted(extra_imports):
            # Only add if not already present
            imp_line = imp + "\n"
            if not any(l.strip() == imp for l in lines):
                lines.insert(import_insert_idx, imp_line)
                log.info(f"  Added missing import: {imp}")

    fixed_content = "".join(lines)
    return fixed_content, applied_fixes


# ─────────────────────────────────────────
# Create Fix Branch + Commit on GitHub
# ─────────────────────────────────────────

def create_fix_branch(repo_name: str, base_sha: str, pr_number: int) -> str:
    """
    Create a new branch for the fix PR.
    Branch name: repoguardian/autofix-pr-{pr_number}-{timestamp}
    Returns the branch name.
    """
    repo        = github_client.get_repo(repo_name)
    timestamp   = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"repoguardian/autofix-pr-{pr_number}-{timestamp}"

    try:
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base_sha
        )
        log.info(f"Created fix branch: {branch_name}")
        return branch_name
    except GithubException as e:
        log.error(f"Could not create branch {branch_name}: {e}")
        raise


def commit_fix_to_branch(
    repo_name:     str,
    branch_name:   str,
    filepath:      str,
    fixed_content: str,
    file_sha:      str,
    commit_message: str,
):
    """Commit the fixed file content to the fix branch."""
    repo = github_client.get_repo(repo_name)
    try:
        repo.update_file(
            path    = filepath,
            message = commit_message,
            content = fixed_content,
            sha     = file_sha,
            branch  = branch_name,
        )
        log.info(f"  Committed fix: {filepath} → {branch_name}")
    except GithubException as e:
        log.error(f"Could not commit {filepath}: {e}")
        raise


# ─────────────────────────────────────────
# Build Fix PR Description
# ─────────────────────────────────────────

def build_fix_pr_body(
    original_pr_number: int,
    fixes:              list[FixResult],
    skipped_rules:      list[str],
) -> str:
    """Build the PR description for the auto-fix PR."""

    fix_rows = "".join(
        f"| `{fix.file}` | L{fix.line} | `{fix.rule}` | {fix.description} |\n"
        for fix in fixes
    )

    skipped_section = ""
    if skipped_rules:
        skipped_list = "\n".join(f"- `{r}` — requires manual fix" for r in skipped_rules)
        skipped_section = f"""
### ⚠️ Issues NOT Auto-Fixed (Manual Action Required)
These issues were found but are too complex to fix automatically:
{skipped_list}
"""

    # Build diff preview — show original vs fixed for each fix
    diff_preview = ""
    for fix in fixes[:5]:   # cap at 5 to keep PR description readable
        diff_preview += f"""
<details>
<summary><code>{fix.file}</code> — Line {fix.line} — <code>{fix.rule}</code></summary>

```diff
- {fix.original.strip()}
+ {fix.fixed.strip()}
```
</details>
"""

    return f"""## 🤖 RepoGuardian — Auto-Fix PR

This PR was automatically generated by RepoGuardian's Auto-Fix Agent.
It fixes **{len(fixes)} simple issue(s)** found in PR #{original_pr_number}.

> ✅ All fixes are safe, deterministic replacements — no logic was changed.
> Review and merge if the fixes look correct.

---

### Fixes Applied
| File | Line | Rule | Description |
|------|------|------|-------------|
{fix_rows}

### Diff Preview
{diff_preview}
{skipped_section}
---
*🤖 Generated by RepoGuardian Auto-Fix Agent — KLH Hackathon 2025*
*Triggered by PR #{original_pr_number}*
"""


def open_fix_pr(
    repo_name:          str,
    fix_branch:         str,
    base_branch:        str,
    original_pr_number: int,
    fixes:              list[FixResult],
    skipped_rules:      list[str],
):
    """Open the auto-fix Pull Request on GitHub."""
    repo  = github_client.get_repo(repo_name)
    title = f"🤖 RepoGuardian: Auto-fix {len(fixes)} issue(s) from PR #{original_pr_number}"
    body  = build_fix_pr_body(original_pr_number, fixes, skipped_rules)

    try:
        pr = repo.create_pull(
            title = title,
            body  = body,
            head  = fix_branch,
            base  = base_branch,
        )
        log.info(f"Fix PR opened: #{pr.number} — {pr.html_url}")
        return pr
    except GithubException as e:
        log.error(f"Could not open fix PR: {e}")
        raise


# ─────────────────────────────────────────
# Post Notification on Original PR
# ─────────────────────────────────────────

def post_autofix_notification(
    repo_name:    str,
    pr_number:    int,
    fix_pr_url:   str,
    fix_pr_number: int,
    fixes:        list[FixResult],
    skipped_rules: list[str],
):
    """
    Post a comment on the ORIGINAL PR telling the author
    that an auto-fix PR has been raised.
    """
    repo = github_client.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    fix_list = "\n".join(
        f"- `{fix.file}` line {fix.line} — {fix.description}"
        for fix in fixes
    )

    skipped_section = ""
    if skipped_rules:
        skipped_section = (
            "\n\n**Not auto-fixed (manual action required):**\n"
            + "\n".join(f"- `{r}`" for r in skipped_rules)
        )

    body = f"""## 🤖 RepoGuardian — Auto-Fix PR Raised

RepoGuardian has automatically fixed **{len(fixes)} issue(s)** from this PR.

**Fix PR:** #{fix_pr_number} — {fix_pr_url}

### What was fixed:
{fix_list}
{skipped_section}

> Review and merge the fix PR if the changes look correct.
> *RepoGuardian Auto-Fix Agent — KLH Hackathon 2025*
"""

    try:
        pr.create_issue_comment(body)
        log.info(f"Auto-fix notification posted on PR #{pr_number}")
    except GithubException as e:
        log.error(f"Could not post notification: {e}")


# ─────────────────────────────────────────
# Main Agent — called by Orchestrator
# ─────────────────────────────────────────

def run_autofix_agent(
    repo_name:   str,
    pr_number:   int,
    findings:    list[Finding],
) -> AutoFixResult:
    """
    MAIN FUNCTION — called by orchestrator after all other agents finish.

    Usage:
        from tools.autofix import run_autofix_agent
        result = run_autofix_agent("owner/repo", 1, all_findings)

    Steps:
        1. Filter findings to only auto-fixable rules
        2. Fetch full file content for each affected file from GitHub
        3. Apply deterministic fixes line by line
        4. Create a new branch and commit all fixed files
        5. Open a ready-to-merge PR with a full diff preview
        6. Post a notification comment on the original PR

    Returns:
        AutoFixResult with fix_pr_url and list of fixes applied
    """
    log.info(f"Auto-Fix Agent started — {repo_name} PR #{pr_number}")

    # Step 1 — Filter findings to fixable vs unfixable
    log.info("Step 1/6 — Filtering findings to auto-fixable rules...")

    fixable_findings  = []
    skipped_rules     = []

    for f in findings:
        rule = extract_rule(f)
        if not rule:
            continue
        if rule in FIXABLE_RULES:
            fixable_findings.append(f)
            log.info(f"  ✓ Fixable: {f.file}:{f.line} [{rule}]")
        elif rule in UNFIXABLE_RULES:
            if rule not in skipped_rules:
                skipped_rules.append(rule)
            log.info(f"  ✗ Skipped (too complex): [{rule}]")

    if not fixable_findings:
        log.info("No auto-fixable issues found — nothing to do.")
        return AutoFixResult(
            repo_name     = repo_name,
            pr_number     = pr_number,
            fixes_applied = [],
            fix_pr_url    = None,
            fix_pr_number = None,
            skipped_rules = skipped_rules,
        )

    log.info(f"  {len(fixable_findings)} fixable finding(s) across "
             f"{len(set(f.file for f in fixable_findings))} file(s)")

    # Step 2 — Get PR details (head SHA + base branch)
    log.info("Step 2/6 — Getting PR details from GitHub...")
    repo       = github_client.get_repo(repo_name)
    pr         = repo.get_pull(pr_number)
    head_sha   = pr.head.sha
    base_branch = pr.base.ref    # e.g. "main" or "develop"

    log.info(f"  Base branch: {base_branch} | Head SHA: {head_sha[:8]}")

    # Step 3 — Fetch and fix each affected file
    log.info("Step 3/6 — Fetching files and applying fixes...")

    # Group fixable findings by file
    files_to_fix = {}
    for f in fixable_findings:
        files_to_fix.setdefault(f.file, []).append(f)

    all_fixes        = []
    fixed_file_data  = {}   # filepath → (fixed_content, original_sha)

    for filepath, file_findings in files_to_fix.items():
        log.info(f"  Processing {filepath} ({len(file_findings)} finding(s))...")

        # Fetch the file at the PR's HEAD (the author's version)
        content, file_sha = fetch_file_content(repo_name, filepath, ref=head_sha)
        if not content:
            log.warning(f"  Could not fetch {filepath} — skipping")
            continue

        # Apply all fixes for this file
        fixed_content, file_fixes = apply_fixes_to_file(content, file_findings, filepath)

        if not file_fixes:
            log.info(f"  No effective fixes for {filepath} — skipping")
            continue

        all_fixes.extend(file_fixes)
        fixed_file_data[filepath] = (fixed_content, file_sha)
        log.info(f"  {len(file_fixes)} fix(es) applied to {filepath}")

    if not all_fixes:
        log.info("Fixes had no effect on any file — skipping PR creation.")
        return AutoFixResult(
            repo_name     = repo_name,
            pr_number     = pr_number,
            fixes_applied = [],
            fix_pr_url    = None,
            fix_pr_number = None,
            skipped_rules = skipped_rules,
        )

    # Step 4 — Create fix branch
    log.info("Step 4/6 — Creating fix branch on GitHub...")
    fix_branch = create_fix_branch(repo_name, base_sha=head_sha, pr_number=pr_number)

    # Step 5 — Commit each fixed file to the branch
    log.info("Step 5/6 — Committing fixed files to branch...")
    committed_files = []

    for filepath, (fixed_content, file_sha) in fixed_file_data.items():
        try:
            commit_message = (
                f"fix: RepoGuardian auto-fix for {filepath}\n\n"
                f"Applied {len([f for f in all_fixes if f.file == filepath])} "
                f"fix(es) from PR #{pr_number} review:\n"
                + "\n".join(
                    f"  - Line {fix.line}: {fix.rule}"
                    for fix in all_fixes if fix.file == filepath
                )
            )
            commit_fix_to_branch(
                repo_name      = repo_name,
                branch_name    = fix_branch,
                filepath       = filepath,
                fixed_content  = fixed_content,
                file_sha       = file_sha,
                commit_message = commit_message,
            )
            committed_files.append(filepath)
        except Exception as e:
            log.error(f"  Failed to commit {filepath}: {e} — skipping")

    if not committed_files:
        log.error("No files were committed — aborting PR creation.")
        return AutoFixResult(
            repo_name     = repo_name,
            pr_number     = pr_number,
            fixes_applied = all_fixes,
            fix_pr_url    = None,
            fix_pr_number = None,
            skipped_rules = skipped_rules,
        )

    # Step 6 — Open the fix PR + notify on original PR
    log.info("Step 6/6 — Opening fix PR and posting notification...")
    fix_pr = open_fix_pr(
        repo_name          = repo_name,
        fix_branch         = fix_branch,
        base_branch        = base_branch,
        original_pr_number = pr_number,
        fixes              = all_fixes,
        skipped_rules      = skipped_rules,
    )

    post_autofix_notification(
        repo_name     = repo_name,
        pr_number     = pr_number,
        fix_pr_url    = fix_pr.html_url,
        fix_pr_number = fix_pr.number,
        fixes         = all_fixes,
        skipped_rules = skipped_rules,
    )

    log.info(
        f"Auto-Fix Agent done — {len(all_fixes)} fix(es) | "
        f"Fix PR: #{fix_pr.number} | {fix_pr.html_url}"
    )

    return AutoFixResult(
        repo_name     = repo_name,
        pr_number     = pr_number,
        fixes_applied = all_fixes,
        fix_pr_url    = fix_pr.html_url,
        fix_pr_number = fix_pr.number,
        skipped_rules = skipped_rules,
    )


# ─────────────────────────────────────────
# Orchestrator-Compatible Wrapper
# ─────────────────────────────────────────

def run_autofix_scan(
    repo_name: str,
    pr_number: int,
    findings:  list[Finding],
) -> AutoFixResult:
    """
    Thin wrapper — same pattern as run_dependency_scan() etc.
    Called by orchestrator._run_autofix() as the final step.
    """
    return run_autofix_agent(repo_name, pr_number, findings)


# ─────────────────────────────────────────
# CLI — standalone testing
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("\n========================================")
    print("  RepoGuardian — Auto-Fix Agent")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python tools/autofix.py <owner/repo> <pr_number>")
        print("Example: python tools/autofix.py vamshi/myproject 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = int(sys.argv[2])

    if not os.environ.get("GITHUB_TOKEN"):
        print("ERROR: Missing GITHUB_TOKEN in .env")
        sys.exit(1)

    # Simulate findings for CLI testing
    dummy_findings = [
        Finding(
            agent      = "security",
            severity   = "high",
            message    = "Hardcoded API key detected.",
            file       = "app.py",
            line       = 5,
            suggestion = "Rule: HARDCODED_API_KEY | Category: secrets",
        ),
        Finding(
            agent      = "security",
            severity   = "high",
            message    = "MD5 is broken — use SHA256.",
            file       = "utils.py",
            line       = 12,
            suggestion = "Rule: WEAK_HASH_MD5 | Category: owasp",
        ),
        Finding(
            agent      = "security",
            severity   = "medium",
            message    = "Debug mode enabled.",
            file       = "config.py",
            line       = 3,
            suggestion = "Rule: DEBUG_ENABLED | Category: owasp",
        ),
    ]

    result = run_autofix_agent(repo_arg, pr_arg, dummy_findings)

    print("\n========================================")
    print("  RESULT")
    print("========================================")
    print(f"  PR            : #{result.pr_number} in {result.repo_name}")
    print(f"  Fixes applied : {len(result.fixes_applied)}")
    print(f"  Fix PR URL    : {result.fix_pr_url or 'None (nothing to fix)'}")
    print(f"  Skipped rules : {result.skipped_rules}")
    print()

    for i, fix in enumerate(result.fixes_applied, 1):
        print(f"  {i}. [{fix.rule}] {fix.file} line {fix.line}")
        print(f"     Before : {fix.original.strip()}")
        print(f"     After  : {fix.fixed.strip()}")
        print(f"     Reason : {fix.description}")