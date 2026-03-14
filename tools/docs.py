"""
RepoGuardian — Docs Agent
Verifies docstrings, README completeness, and inline comment coverage.
Reports missing doc locations with specific suggestions.

Follows the exact same pattern as security.py and dependency.py:
- Takes repo_name and pr_number directly
- Returns Finding objects to Orchestrator for unified health scoring
- Posts its own summary comment to GitHub PR

.env required:
    GITHUB_TOKEN=...
    GROQ_API_KEY=...
    LLM_MODEL=groq
"""

import os
import re
import ast
import sys
import json
import time
import logging
from dataclasses import dataclass, field
from collections import defaultdict

from groq import Groq
from github import Github, GithubException
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Finding

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DOCS_AGENT] %(message)s")
log = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GROQ_API_KEY or not GITHUB_TOKEN:
    raise RuntimeError("Missing GROQ_API_KEY or GITHUB_TOKEN in .env")

github_client = Github(GITHUB_TOKEN)


# ─────────────────────────────────────────
# LLM Model Selector — same as all other agents
# ─────────────────────────────────────────

def get_llm_client_and_model():
    model = os.getenv("LLM_MODEL", "groq").strip().lower()
    if model == "groq":
        return Groq(api_key=os.getenv("GROQ_API_KEY", "")), "llama-3.3-70b-versatile"
    elif model == "grok":
        return Groq(api_key=os.getenv("XAI_API_KEY", "")), "grok-3-mini"
    elif model == "anthropic":
        return Groq(api_key=os.getenv("ANTHROPIC_API_KEY", "")), "claude-3-haiku-20240307"
    elif model == "ollama":
        return Groq(api_key="ollama"), "codellama"
    else:
        raise ValueError(f"Unknown LLM_MODEL: '{model}'. Valid: groq, grok, anthropic, ollama")


# ─────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────

@dataclass
class DocsIssue:
    path:       str    # file path e.g. "agents/pr_review.py"
    line:       int    # line number in the file
    severity:   str    # "high" | "medium" | "low"
    issue_type: str    # "missing_docstring" | "missing_readme" | "missing_inline"
    name:       str    # function/class name with the issue
    suggestion: str    # exactly what to add


@dataclass
class DocsResult:
    repo_name: str
    pr_number: int
    summary:   str
    issues:    list[DocsIssue] = field(default_factory=list)
    findings:  list[Finding]   = field(default_factory=list)


# ─────────────────────────────────────────
# GitHub — Fetch PR Diff + Valid Lines Map
# Same pattern as security.py fetch_pr_diff()
# ─────────────────────────────────────────

def fetch_pr_diff(repo_name: str, pr_number: int):
    """
    Fetch PR diff and build valid_lines_map.
    valid_lines_map = { "agents/pr_review.py": {5, 10, 23, ...} }
    Only contains lines that are actual added lines (+) in the diff.
    """
    repo = github_client.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    diff_parts      = []
    valid_lines_map = {}

    for f in pr.get_files():
        if not f.patch:
            continue

        filename = f.filename
        diff_parts.append(f"FILE: {filename}")
        diff_parts.append(f.patch)

        valid_lines_map[filename] = set()
        current_new_line = 0

        for diff_line in f.patch.split("\n"):
            hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)
            if hunk:
                current_new_line = int(hunk.group(1)) - 1
                continue
            if diff_line.startswith("-"):
                continue
            elif diff_line.startswith("+"):
                current_new_line += 1
                valid_lines_map[filename].add(current_new_line)
            else:
                current_new_line += 1

    diff_text = "\n".join(diff_parts)
    log.info(f"Fetched diff for PR #{pr_number} — {len(valid_lines_map)} file(s) changed")
    return diff_text, pr, valid_lines_map


# ─────────────────────────────────────────
# STATIC SCANNER 1 — Missing Docstrings (AST)
# Parses Python AST to find public functions/classes with no docstring
# Fast, zero cost, no LLM needed
# ─────────────────────────────────────────

def scan_python_docstrings(diff_text: str, valid_lines_map: dict) -> list[DocsIssue]:
    """
    Use Python AST to detect public functions and classes missing docstrings.
    Only checks .py files changed in the PR.
    Only reports lines that are actual added lines in the diff.
    """
    issues       = []
    python_files = [f for f in valid_lines_map.keys() if f.endswith(".py")]

    for filename in python_files:
        # Extract added code for this file from the diff
        lines        = []
        start_line   = 1
        in_file      = False
        current_line = 0

        for diff_line in diff_text.split("\n"):
            if diff_line.startswith(f"FILE: {filename}"):
                in_file = True
                current_line = 0
                continue
            if diff_line.startswith("FILE: ") and in_file:
                break
            if not in_file:
                continue

            hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)
            if hunk:
                if not lines:
                    start_line = int(hunk.group(1))
                current_line = int(hunk.group(1)) - 1
                continue

            if diff_line.startswith("-"):
                continue
            elif diff_line.startswith("+"):
                current_line += 1
                lines.append(diff_line[1:])   # strip leading +
            else:
                current_line += 1
                lines.append(diff_line)       # context line

        code = "\n".join(lines)
        if not code.strip():
            continue

        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Partial diffs often don't parse — skip silently
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            # Skip private/dunder — only public API needs docstrings
            if node.name.startswith("_"):
                continue

            actual_line = start_line + node.lineno - 1

            # Only report if this line was actually added in this PR
            if actual_line not in valid_lines_map.get(filename, set()):
                continue

            # Check if docstring exists
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )

            if not has_docstring:
                kind     = "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class"
                arg_hint = ""
                if hasattr(node, "args") and node.args.args:
                    arg_names = [a.arg for a in node.args.args if a.arg != "self"]
                    if arg_names:
                        arg_hint = f" Args: {', '.join(arg_names)}."

                issues.append(DocsIssue(
                    path       = filename,
                    line       = actual_line,
                    severity   = "medium",
                    issue_type = "missing_docstring",
                    name       = node.name,
                    suggestion = (
                        f'Add a docstring to {kind} `{node.name}`.{arg_hint} '
                        f'Example: """{kind.title()} description. Returns: description."""'
                    ),
                ))

    log.info(f"AST docstring scan: {len(issues)} missing docstring(s) found")
    return issues


# ─────────────────────────────────────────
# STATIC SCANNER 2 — README Check
# Flags if Python files added but README not touched
# ─────────────────────────────────────────

def scan_readme(valid_lines_map: dict) -> list[DocsIssue]:
    """
    If new .py files were added but README.md was not updated — flag it.
    """
    issues = []

    python_files  = [f for f in valid_lines_map.keys() if f.endswith(".py")]
    readme_files  = [f for f in valid_lines_map.keys()
                     if f.lower() in ("readme.md", "readme.rst", "readme.txt")]

    if python_files and not readme_files:
        issues.append(DocsIssue(
            path       = "README.md",
            line       = 1,
            severity   = "low",
            issue_type = "missing_readme",
            name       = "README.md",
            suggestion = (
                "This PR adds Python files but README.md was not updated. "
                "Consider documenting new functions, usage examples, or API changes."
            ),
        ))

    log.info(f"README scan: {'not updated' if issues else 'updated or no new py files'}")
    return issues


# ─────────────────────────────────────────
# STATIC SCANNER 3 — Inline Comment Coverage
# Flags public functions with >10 added lines but zero # comments
# ─────────────────────────────────────────

def scan_inline_comments(diff_text: str, valid_lines_map: dict) -> list[DocsIssue]:
    """
    Find public functions that have many added lines but zero inline comments.
    Heuristic: >10 added lines + no # comment = flag it.
    """
    issues       = []
    python_files = [f for f in valid_lines_map.keys() if f.endswith(".py")]

    in_file         = False
    current_file    = None
    func_name       = None
    func_start_line = 0
    func_lines      = []
    current_line    = 0

    def flush_func():
        if func_name and len(func_lines) > 10:
            has_comment = any(l.strip().startswith("#") for l in func_lines)
            if not has_comment and func_start_line in valid_lines_map.get(current_file, set()):
                issues.append(DocsIssue(
                    path       = current_file,
                    line       = func_start_line,
                    severity   = "low",
                    issue_type = "missing_inline",
                    name       = func_name,
                    suggestion = (
                        f"Function `{func_name}` has {len(func_lines)} lines but no inline comments. "
                        "Add # comments to explain loops, conditions, and non-obvious logic."
                    ),
                ))

    for diff_line in diff_text.split("\n"):

        if diff_line.startswith("FILE: "):
            flush_func()
            current_file    = diff_line[6:].strip()
            in_file         = current_file in python_files
            func_name       = None
            func_start_line = 0
            func_lines      = []
            current_line    = 0
            continue

        if not in_file:
            continue

        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)
        if hunk:
            current_line = int(hunk.group(1)) - 1
            continue

        if diff_line.startswith("-"):
            continue

        if diff_line.startswith("+"):
            current_line += 1
            clean = diff_line[1:]
        else:
            current_line += 1
            clean = diff_line

        # Detect new public function definition
        func_match = re.match(r"^\s*(?:async\s+)?def\s+([a-zA-Z][a-zA-Z0-9_]*)\s*\(", clean)
        if func_match:
            flush_func()
            func_name       = func_match.group(1)
            func_start_line = current_line
            func_lines      = [clean]
        elif func_name:
            func_lines.append(clean)

    flush_func()

    log.info(f"Inline comment scan: {len(issues)} function(s) lacking comments")
    return issues


# ─────────────────────────────────────────
# LLM — Deep Docs Analysis
# Single call — not chunked to save rate limit budget
# ─────────────────────────────────────────

DOCS_SYSTEM_PROMPT = """
You are a senior technical writer reviewing documentation quality in a GitHub PR diff.

Analyse the diff and return JSON only. No markdown, no extra text.

Look for:
1. Public functions or classes with missing or very poor docstrings
2. Complex logic blocks with no explanation comments
3. README files that are vague, incomplete, or missing usage examples
4. API functions missing parameter or return type documentation

CRITICAL RULES:
- Only report issues for file paths EXACTLY as shown after "FILE:" in the diff
- Only report line numbers of actual added lines (lines starting with +) in the diff
- Line numbers must be positive integers greater than 0
- Do NOT invent file names
- Do NOT repeat issues already found by static scan

Return ONLY this JSON:
{
  "summary": "2-3 sentence documentation quality assessment",
  "issues": [
    {
      "path": "exact/path/from/diff.py",
      "line": 10,
      "severity": "medium",
      "issue_type": "missing_docstring",
      "name": "function_or_class_name",
      "comment": "specific suggestion of exactly what doc to add — max 2 sentences"
    }
  ]
}

issue_type values: missing_docstring | missing_inline | readme_incomplete
Return ONLY valid JSON. Nothing else.
"""


def call_llm_docs(diff: str, static_issues: list[DocsIssue],
                  valid_lines_map: dict, retries: int = 3) -> dict:
    """Single LLM call for deep docs analysis beyond static rules."""
    client, model_name = get_llm_client_and_model()

    valid_files    = "\n".join(f"- {f}" for f in valid_lines_map.keys())
    static_summary = "\n".join(
        f"- {i.path}:{i.line} [{i.issue_type}] {i.name}"
        for i in static_issues
    ) or "None."

    prompt = (
        f"VALID FILES (only use these exact paths):\n{valid_files}\n\n"
        f"Static scan already found (do NOT repeat):\n{static_summary}\n\n"
        f"DIFF:\n{diff[:8000]}"
    )

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": DOCS_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"^```\s*",     "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```$",        "", raw, flags=re.MULTILINE)
            return json.loads(raw.strip())

        except json.JSONDecodeError as e:
            log.warning(f"JSON parse failed attempt {attempt+1}: {e}")
            time.sleep(3)
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower():
                wait = 15 * (attempt + 1)
                log.warning(f"Rate limit — waiting {wait}s")
                time.sleep(wait)
            else:
                log.warning(f"LLM failed attempt {attempt+1}: {e}")
                time.sleep(3)

    log.error("All LLM docs attempts failed.")
    return {"summary": "LLM docs analysis failed.", "issues": []}


# ─────────────────────────────────────────
# Convert DocsIssue → Finding
# Same pattern as dependency.py to_findings()
# ─────────────────────────────────────────

def to_findings(issues: list[DocsIssue]) -> list[Finding]:
    """
    Convert DocsIssue → Finding objects.
    Docs agent = 0.5 multiplier in orchestrator — docs hurt score less than security.
    """
    return [
        Finding(
            agent      = "docs",
            severity   = issue.severity,
            message    = f"[{issue.issue_type}] {issue.name}: {issue.suggestion}",
            file       = issue.path,
            line       = issue.line,
            suggestion = issue.suggestion,
        )
        for issue in issues
    ]


# ─────────────────────────────────────────
# Post Comments to GitHub
# Same pattern as security.py and pr_review.py
# ─────────────────────────────────────────

SEVERITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🔵"}

ISSUE_TYPE_LABEL = {
    "missing_docstring":  "Missing Docstring",
    "missing_readme":     "README Not Updated",
    "missing_inline":     "Missing Inline Comments",
    "readme_incomplete":  "Incomplete README",
}


def post_inline_comments(pr, issues: list[DocsIssue], valid_lines_map: dict):
    """
    Post inline comments only for issues where file + line exist in the diff.
    README issues (line=1, file not in diff) go into summary comment only.
    """
    if not issues:
        log.info("No inline comments to post.")
        return

    latest_commit = list(pr.get_commits())[-1]
    posted  = 0
    skipped = 0

    for issue in issues:
        # Only post inline if file and line are in the actual PR diff
        if (issue.path not in valid_lines_map or
                issue.line not in valid_lines_map.get(issue.path, set())):
            skipped += 1
            continue

        emoji = SEVERITY_EMOJI.get(issue.severity, "🔵")
        label = ISSUE_TYPE_LABEL.get(issue.issue_type, issue.issue_type.replace("_", " ").title())

        body = (
            f"{emoji} **RepoGuardian Docs — {label}** | `{issue.severity.upper()}`\n\n"
            f"**`{issue.name}`** — {issue.suggestion}\n\n"
            f"---\n"
            f"*Posted by RepoGuardian Docs Agent — KLH Hackathon 2025*"
        )

        try:
            pr.create_review_comment(
                body=body,
                commit=latest_commit,
                path=issue.path,
                line=issue.line,
            )
            posted += 1
            log.info(f"  Posted → {issue.path}:{issue.line} [{issue.issue_type}] {issue.name}")
        except GithubException as e:
            skipped += 1
            msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
            log.warning(f"  Skipped {issue.path}:{issue.line} — {msg}")

    log.info(f"Comments posted: {posted} | Skipped: {skipped}")


def post_docs_summary(pr, result: DocsResult):
    """Post docs summary comment — same style as all other agents."""
    counts = defaultdict(int)
    for issue in result.issues:
        counts[issue.issue_type] += 1

    total = len(result.issues)
    badge = ("🟢 GOOD DOCS" if total == 0
             else "🟡 DOCS NEED WORK" if total < 5
             else "🔴 POOR DOCUMENTATION")

    issue_rows = "".join(
        f"| {SEVERITY_EMOJI.get(i.severity,'🔵')} `{i.path}` | "
        f"`{i.name}` | {ISSUE_TYPE_LABEL.get(i.issue_type, i.issue_type)} |\n"
        for i in result.issues
    )

    body = f"""## 📝 RepoGuardian — Documentation Review

**Status:** {badge}

### Summary
{result.summary}

### Issues Found
| Type | Count |
|------|-------|
| 🟡 Missing Docstrings | **{counts['missing_docstring']}** |
| 🔵 Missing Inline Comments | **{counts['missing_inline']}** |
| 🔵 README Not Updated | **{counts['missing_readme']}** |
| **Total** | **{total}** |

### Locations
| File | Name | Issue Type |
|------|------|-----------|
{issue_rows}
> Inline comments posted on each affected line.
> *RepoGuardian Docs Agent — KLH Hackathon 2025*
"""
    pr.create_issue_comment(body)
    log.info("Docs summary comment posted.")


# ─────────────────────────────────────────
# Main Agent — called by Orchestrator
# Exact same signature as security.py and dependency.py
# ─────────────────────────────────────────

def run_docs_agent(repo_name: str, pr_number: int) -> DocsResult:
    """
    MAIN FUNCTION — called by orchestrator.

    Usage:
        from tools.docs import run_docs_agent
        result = run_docs_agent("owner/repo", 1)

    Returns:
        DocsResult with .findings list for Orchestrator health score.
    """
    log.info(f"Docs Agent started — {repo_name} PR #{pr_number}")

    # Step 1 — Fetch diff + valid lines map (same as security.py)
    log.info("Step 1/5 — Fetching PR diff from GitHub...")
    diff, pr, valid_lines_map = fetch_pr_diff(repo_name, pr_number)

    if not diff.strip():
        log.info("No reviewable diff found.")
        return DocsResult(repo_name=repo_name, pr_number=pr_number,
                          summary="No code changes to review.", issues=[], findings=[])

    # Step 2 — Static AST docstring scan
    log.info("Step 2/5 — Scanning for missing docstrings (AST)...")
    docstring_issues = scan_python_docstrings(diff, valid_lines_map)

    # Step 3 — README presence check
    log.info("Step 3/5 — Checking README coverage...")
    readme_issues = scan_readme(valid_lines_map)

    # Step 4 — Inline comment coverage check
    log.info("Step 4/5 — Checking inline comment coverage...")
    inline_issues = scan_inline_comments(diff, valid_lines_map)

    all_static = docstring_issues + readme_issues + inline_issues
    log.info(f"Static docs scan total: {len(all_static)} issue(s)")

    # Step 5 — LLM deep analysis (single call, staggered to avoid rate limits)
    # PR agent uses chunks, Security waits 8s — Docs waits 12s
    log.info("Step 5/5 — Running LLM deep docs analysis...")
    # sleep removed — orchestrator now runs agents sequentially
    llm_result = call_llm_docs(diff, all_static, valid_lines_map)

    # Merge static + LLM findings
    all_issues = list(all_static)

    for issue in llm_result.get("issues", []):
        path = issue.get("path", "").strip()
        try:
            line = int(issue.get("line", 0))
        except (ValueError, TypeError):
            continue

        # Validate path and line against actual PR diff
        if path not in valid_lines_map:
            log.warning(f"  LLM hallucinated path: '{path}' — rejected")
            continue
        if line not in valid_lines_map.get(path, set()):
            log.warning(f"  LLM invalid line: {path}:{line} — rejected")
            continue

        try:
            all_issues.append(DocsIssue(
                path       = path,
                line       = line,
                severity   = issue.get("severity", "low"),
                issue_type = issue.get("issue_type", "missing_docstring"),
                name       = issue.get("name", "unknown"),
                suggestion = issue["comment"],
            ))
        except (KeyError, TypeError) as e:
            log.warning(f"Skipping bad LLM docs issue: {e}")

    summary  = llm_result.get("summary") or f"Found {len(all_issues)} documentation issue(s)."
    findings = to_findings(all_issues)

    result = DocsResult(
        repo_name = repo_name,
        pr_number = pr_number,
        summary   = summary,
        issues    = all_issues,
        findings  = findings,
    )

    log.info(f"Docs Agent found {len(all_issues)} issue(s)")

    # Post to GitHub
    post_inline_comments(pr, all_issues, valid_lines_map)
    post_docs_summary(pr, result)

    log.info("Docs Agent done.")
    return result


# ─────────────────────────────────────────
# Orchestrator-Compatible Wrapper
# Exact same pattern as dependency.py run_dependency_scan()
# ─────────────────────────────────────────

def run_docs_scan(repo_name: str, pr_number: int) -> list[Finding]:
    """
    Thin wrapper called by orchestrator._run_docs().

    Orchestrator calls: findings, agent_name = _run_docs(repo_name, pr_number)
    This returns just the findings list so orchestrator can extend all_findings.
    """
    result = run_docs_agent(repo_name, pr_number)
    return result.findings


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("\n========================================")
    print("  RepoGuardian — Docs Agent")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python tools/docs.py <owner/repo> <pr_number>")
        print("Example: python tools/docs.py vamshi/myproject 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = int(sys.argv[2])

    missing = [k for k in ["GROQ_API_KEY", "GITHUB_TOKEN"] if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing in .env: {', '.join(missing)}")
        sys.exit(1)

    result = run_docs_agent(repo_arg, pr_arg)

    print("\n========================================")
    print("  RESULT")
    print("========================================")
    print(f"  PR          : #{result.pr_number} in {result.repo_name}")
    print(f"  Issues found: {len(result.issues)}")
    print(f"  Summary     : {result.summary}")
    print("========================================")

    for i, issue in enumerate(result.issues, 1):
        emoji = SEVERITY_EMOJI.get(issue.severity, "🔵")
        print(f"\n  {i}. {emoji} [{issue.severity.upper()}] {issue.path} line {issue.line}")
        print(f"     Type      : {issue.issue_type}")
        print(f"     Name      : {issue.name}")
        print(f"     Suggestion: {issue.suggestion}")