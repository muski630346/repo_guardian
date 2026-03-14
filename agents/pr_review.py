"""
RepoGuardian — PR Review Agent
Analyses code logic, naming conventions, structure, and coding standards.
Posts inline comments directly on GitHub Pull Requests.

.env required:
    GITHUB_TOKEN=...
    GROQ_API_KEY=...
    LLM_MODEL=groq
"""

import os
import json
import re
import time
import logging
from dataclasses import dataclass, field

from groq import Groq
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PR_AGENT] %(message)s")
log = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GROQ_API_KEY or not GITHUB_TOKEN:
    raise RuntimeError("Missing GROQ_API_KEY or GITHUB_TOKEN in .env")

github_client = Github(GITHUB_TOKEN)


# ─────────────────────────────────────────
# LLM Model Selector
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
class ReviewComment:
    path: str
    line: int
    body: str
    severity: str
    category: str


@dataclass
class PRReviewResult:
    repo_name: str
    pr_number: int
    summary: str
    comments: list[ReviewComment] = field(default_factory=list)
    score: int = 100


# ─────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior software engineer performing code reviews on a GitHub Pull Request diff.

Analyse ONLY the files shown in the diff and return JSON only. No markdown, no extra text.

CRITICAL RULES:
- You MUST only report issues for file paths EXACTLY as they appear after "FILE:" in the diff
- Line numbers must match actual added lines (lines starting with +) in the diff
- Line numbers must be positive integers greater than 0
- Do NOT invent file names like filename.py or security_scanner.py
- Do NOT report issues on line 0 or negative lines

Return this exact JSON format:
{
  "summary": "2-3 sentence overall assessment",
  "score_deduction": 10,
  "issues": [
    {
      "path": "exact/path/from/FILE_header.py",
      "line": 10,
      "severity": "high",
      "category": "logic",
      "comment": "specific actionable feedback max 3 sentences. Name the exact function/variable."
    }
  ]
}

Severity: high (security/broken logic) | medium (bad practice) | low (style/naming)
Category: logic | naming | structure | standards

Return ONLY valid JSON. Nothing else.
"""


# ─────────────────────────────────────────
# GitHub — Fetch Diff + Build Valid Lines Map
# ─────────────────────────────────────────

def fetch_pr_diff(repo_name, pr_number):
    """
    Fetch PR diff and build valid_lines_map.

    valid_lines_map = { "agents/pr_review.py": {5, 10, 23, ...} }

    This map contains ONLY lines that are actual added lines (+) in the diff.
    Used to validate LLM output — GitHub rejects comments on lines not in the diff.
    """
    repo = github_client.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    diff_parts      = []
    valid_lines_map = {}

    for file in pr.get_files():
        if not file.patch:
            continue

        filename = file.filename
        diff_parts.append(f"FILE: {filename}")
        diff_parts.append(file.patch)

        # Parse hunk headers to map line numbers correctly
        # Format: @@ -old_start,old_count +new_start,new_count @@
        valid_lines_map[filename] = set()
        current_new_line = 0

        for diff_line in file.patch.split("\n"):
            hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)
            if hunk:
                current_new_line = int(hunk.group(1)) - 1
                continue

            if diff_line.startswith("-"):
                continue                          # deleted line, no new line number
            elif diff_line.startswith("+"):
                current_new_line += 1
                valid_lines_map[filename].add(current_new_line)   # valid added line
            else:
                current_new_line += 1             # context line

    diff_text = "\n".join(diff_parts)
    log.info(f"Fetched diff for PR #{pr_number} — {len(valid_lines_map)} file(s) changed")
    return diff_text, pr, valid_lines_map


# ─────────────────────────────────────────
# Diff Chunking — capped to avoid rate limits
# ─────────────────────────────────────────

def chunk_diff(diff, max_chars=6000):
    chunks  = []
    current = ""

    for line in diff.split("\n"):
        if len(current) + len(line) > max_chars:
            chunks.append(current)
            current = ""
        current += line + "\n"

    if current:
        chunks.append(current)

    # Cap at 3 chunks — Groq free tier allows ~30 req/min
    # Both PR agent and Security agent share the limit
    if len(chunks) > 3:
        log.info(f"Capping {len(chunks)} chunks → 3 to respect Groq rate limits")
        chunks = chunks[:3]

    return chunks


# ─────────────────────────────────────────
# LLM Call with Rate Limit Handling
# ─────────────────────────────────────────

def call_llm(prompt, retries=3):
    client, model_name = get_llm_client_and_model()

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"^```\s*",     "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```$",        "", raw, flags=re.MULTILINE)
            raw = raw.strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            log.warning(f"JSON parse failed attempt {attempt+1}: {e}")
            time.sleep(3)

        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower():
                wait = 15 * (attempt + 1)
                log.warning(f"Rate limit — waiting {wait}s (attempt {attempt+1})")
                time.sleep(wait)
            else:
                log.warning(f"LLM failed attempt {attempt+1}: {e}")
                time.sleep(3)

    log.error("All LLM retry attempts failed.")
    return {"summary": "LLM failed.", "score_deduction": 0, "issues": []}


# ─────────────────────────────────────────
# Validate Issue Against Real PR Diff Lines
# ─────────────────────────────────────────

def is_valid_issue(issue: dict, valid_lines_map: dict) -> bool:
    """
    Returns True only if the issue path and line actually exist in the PR diff.

    This is the core fix for 'Validation Failed' errors from GitHub.
    GitHub rejects create_review_comment() calls when:
      - The file is not part of the PR
      - The line is not an added line in that file's diff
    """
    path = issue.get("path", "").strip()
    try:
        line = int(issue.get("line", 0))
    except (ValueError, TypeError):
        return False

    if not path or line <= 0:
        return False

    if path not in valid_lines_map:
        log.warning(f"  Rejected hallucinated path: '{path}' (not in PR diff)")
        return False

    if line not in valid_lines_map[path]:
        log.warning(f"  Rejected invalid line: {path}:{line} (not an added line)")
        return False

    return True


# ─────────────────────────────────────────
# Post Inline Comments
# ─────────────────────────────────────────

SEVERITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🔵"}
CATEGORY_LABEL = {
    "logic":     "Logic Issue",
    "naming":    "Naming Convention",
    "structure": "Code Structure",
    "standards": "Coding Standard"
}


def post_inline_comments(pr, comments: list[ReviewComment]):
    if not comments:
        log.info("No inline comments to post.")
        return

    latest_commit = list(pr.get_commits())[-1]
    posted  = 0
    skipped = 0

    for c in comments:
        emoji = SEVERITY_EMOJI.get(c.severity, "⚪")
        label = CATEGORY_LABEL.get(c.category, c.category.title())

        body = (
            f"{emoji} **RepoGuardian — {label}** | `{c.severity.upper()}`\n\n"
            f"{c.body}\n\n"
            f"---\n"
            f"*Posted by RepoGuardian PR Review Agent — KLH Hackathon 2025*"
        )

        try:
            pr.create_review_comment(
                body=body,
                commit=latest_commit,
                path=c.path,
                line=c.line
            )
            posted += 1
            log.info(f"  Posted → {c.path}:{c.line} [{c.severity}]")

        except GithubException as e:
            skipped += 1
            msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
            log.warning(f"  Skipped {c.path}:{c.line} — {msg}")

    log.info(f"Comments posted: {posted} | Skipped: {skipped}")


def post_summary(pr, result: PRReviewResult):
    counts = {"high": 0, "medium": 0, "low": 0}
    for c in result.comments:
        counts[c.severity] = counts.get(c.severity, 0) + 1

    score = result.score
    badge = "🟢 GOOD" if score >= 85 else "🟡 NEEDS WORK" if score >= 65 else "🔴 CRITICAL ISSUES"

    body = f"""## 🛡️ RepoGuardian — PR Review Report

**Health Score:** `{score}/100` {badge}

### Summary
{result.summary}

### Issues Found
| Severity | Count |
|----------|-------|
| 🔴 High (must fix) | **{counts['high']}** |
| 🟡 Medium (should fix) | **{counts['medium']}** |
| 🔵 Low (nice to fix) | **{counts['low']}** |
| **Total** | **{len(result.comments)}** |

> Inline comments posted on each affected line.
> *RepoGuardian PR Review Agent — KLH Hackathon 2025 — Powered by Groq + Llama3*
"""
    pr.create_issue_comment(body)
    log.info("Summary comment posted.")


# ─────────────────────────────────────────
# Main Agent
# ─────────────────────────────────────────

def run_pr_review_agent(repo_name, pr_number):
    """
    MAIN FUNCTION — called by orchestrator.
        from agents.pr_review import run_pr_review_agent
        result = run_pr_review_agent("owner/repo", 1)
    """
    log.info(f"PR Review Agent started — {repo_name} PR #{pr_number}")

    # Step 1 — Fetch diff + valid lines map
    log.info("Step 1/4 — Fetching PR diff from GitHub...")
    diff, pr, valid_lines_map = fetch_pr_diff(repo_name, pr_number)

    if not diff.strip():
        log.info("No reviewable diff found.")
        return PRReviewResult(repo_name=repo_name, pr_number=pr_number,
                              summary="No reviewable code changes found.",
                              comments=[], score=100)

    # Step 2 — Chunk diff
    log.info("Step 2/4 — Chunking diff...")
    chunks = chunk_diff(diff)
    log.info(f"Diff split into {len(chunks)} chunk(s)")

    # Step 3 — LLM analysis with valid file list in prompt
    log.info("Step 3/4 — Analysing with LLM...")
    all_comments    = []
    total_deduction = 0
    summary         = ""
    valid_files     = "\n".join(f"- {f}" for f in valid_lines_map.keys())

    for i, chunk in enumerate(chunks):
        log.info(f"  Chunk {i+1}/{len(chunks)}...")

        # Tell the LLM exactly which file paths are valid
        prompt = (
            f"VALID FILES IN THIS PR (only use these exact paths):\n"
            f"{valid_files}\n\n"
            f"DIFF:\n{chunk}"
        )

        llm_result = call_llm(prompt)

        total_deduction += llm_result.get("score_deduction", 0)
        if llm_result.get("summary"):
            summary = llm_result["summary"]

        for issue in llm_result.get("issues", []):
            # Validate before accepting — prevents Validation Failed errors
            if not is_valid_issue(issue, valid_lines_map):
                continue
            try:
                all_comments.append(ReviewComment(
                    path     = issue["path"],
                    line     = int(issue["line"]),
                    body     = issue["comment"],
                    severity = issue.get("severity", "low"),
                    category = issue.get("category", "standards")
                ))
            except (KeyError, ValueError, TypeError) as e:
                log.warning(f"Skipping malformed issue: {e}")

        # Wait between chunks to respect Groq rate limits
        if i < len(chunks) - 1:
            time.sleep(5)

    # Cap PR review deduction at 40 points max
    score = max(0, 100 - min(total_deduction, 40))

    result = PRReviewResult(
        repo_name = repo_name,
        pr_number = pr_number,
        summary   = summary or "PR review complete.",
        comments  = all_comments,
        score     = score
    )

    log.info(f"Found {len(all_comments)} valid issue(s) | Score: {score}/100")

    # Step 4 — Post to GitHub
    log.info("Step 4/4 — Posting to GitHub...")
    post_inline_comments(pr, all_comments)
    post_summary(pr, result)

    log.info(f"PR Review Agent done — Score: {score}/100")
    return result


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("\n========================================")
    print("  RepoGuardian — PR Review Agent")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python agents/pr_review.py <owner/repo> <pr_number>")
        print("Example: python agents/pr_review.py vamshi/myproject 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = int(sys.argv[2])

    missing = [k for k in ["GROQ_API_KEY", "GITHUB_TOKEN"] if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing keys in .env: {', '.join(missing)}")
        sys.exit(1)

    result = run_pr_review_agent(repo_arg, pr_arg)

    print("\n========================================")
    print("  RESULT")
    print("========================================")
    print(f"  PR      : #{result.pr_number} in {result.repo_name}")
    print(f"  Score   : {result.score}/100")
    print(f"  Issues  : {len(result.comments)}")
    print(f"  Summary : {result.summary}")
    print("========================================")

    for i, c in enumerate(result.comments, 1):
        emoji = SEVERITY_EMOJI.get(c.severity, "o")
        print(f"\n  {i}. {emoji} [{c.severity.upper()}] {c.path} line {c.line}")
        print(f"     Type    : {c.category}")
        print(f"     Comment : {c.body}")