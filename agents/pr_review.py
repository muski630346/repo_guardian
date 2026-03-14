"""
RepoGuardian PR Review Agent
AI-powered pull request reviewer using Groq + GitHub API
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
# LLM Model Selector (reads LLM_MODEL from .env)
# ─────────────────────────────────────────

def get_llm_client_and_model():
    """
    Reads LLM_MODEL from .env and returns (client, model_name).

    .env options:
        LLM_MODEL=groq       → llama-3.3-70b-versatile  (default, FREE)
        LLM_MODEL=grok       → grok-3-mini  (xAI, uses XAI_API_KEY)
        LLM_MODEL=anthropic  → claude-3-haiku  (uses ANTHROPIC_API_KEY)
        LLM_MODEL=ollama     → codellama  (local, no API key needed)
    """
    model = os.getenv("LLM_MODEL", "groq").strip().lower()

    if model == "groq":
        client     = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        model_name = "llama-3.3-70b-versatile"
        log.info(f"LLM: Groq → {model_name}")
        return client, model_name

    elif model == "grok":
        client     = Groq(api_key=os.getenv("XAI_API_KEY", ""))
        model_name = "grok-3-mini"
        log.info(f"LLM: xAI Grok → {model_name}")
        return client, model_name

    elif model == "anthropic":
        client     = Groq(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        model_name = "claude-3-haiku-20240307"
        log.info(f"LLM: Anthropic → {model_name}")
        return client, model_name

    elif model == "ollama":
        client     = Groq(api_key="ollama")
        model_name = "codellama"
        log.info(f"LLM: Ollama (local) → {model_name}")
        return client, model_name

    else:
        raise ValueError(
            f"Unknown LLM_MODEL: '{model}'. "
            f"Valid options in .env: groq, grok, anthropic, ollama"
        )


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
You are a senior software engineer performing code reviews.

Analyse the code diff and return JSON only. No markdown. No explanation outside JSON.

Return this exact format:
{
  "summary": "2-3 sentence overall assessment",
  "score_deduction": 10,
  "issues": [
    {
      "path": "filename.py",
      "line": 10,
      "severity": "high",
      "category": "logic",
      "comment": "specific actionable feedback in max 3 sentences"
    }
  ]
}

Severity levels:
- high   : security risk, broken logic, will cause bugs in production
- medium : bad practice, maintainability issue
- low    : style, naming, minor standard violation

Categories:
- logic     : wrong conditions, bad return values, missing edge cases
- naming    : non-descriptive names, wrong case style
- structure : too many params, deep nesting, dead code
- standards : insecure patterns (MD5, hardcoded secrets, raw SQL), missing docstrings, unused imports

Rules:
- Only flag REAL issues. Do not invent problems.
- Always name the exact variable or function in your comment.
- Always suggest the fix.
- Return ONLY valid JSON. Nothing else.
"""


# ─────────────────────────────────────────
# Diff Chunking (handles large PRs)
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

    return chunks


# ─────────────────────────────────────────
# LLM Call with Retry
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
                max_tokens=4096,
            )

            raw = response.choices[0].message.content.strip()

            # Clean any accidental markdown fences
            raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"^```\s*",     "", raw, flags=re.MULTILINE)
            raw = re.sub(r"```$",        "", raw, flags=re.MULTILINE)
            raw = raw.strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            log.warning(f"JSON parse failed attempt {attempt+1}: {e}")
            time.sleep(2)

        except Exception as e:
            log.warning(f"LLM call failed attempt {attempt+1}: {e}")
            time.sleep(2)

    log.error("All LLM retry attempts failed.")
    return {"summary": "LLM failed to respond.", "score_deduction": 0, "issues": []}


# ─────────────────────────────────────────
# GitHub — Fetch PR Diff
# ─────────────────────────────────────────

def fetch_pr_diff(repo_name, pr_number):
    repo = github_client.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    diff_parts = []
    for file in pr.get_files():
        if file.patch:
            diff_parts.append(f"FILE: {file.filename}")
            diff_parts.append(file.patch)

    diff_text = "\n".join(diff_parts)
    log.info(f"Fetched diff for PR #{pr_number}")
    return diff_text, pr


# ─────────────────────────────────────────
# GitHub — Post Inline Comments
# ─────────────────────────────────────────

SEVERITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🔵"}

CATEGORY_LABEL = {
    "logic":     "Logic Issue",
    "naming":    "Naming Convention",
    "structure": "Code Structure",
    "standards": "Coding Standard"
}


def post_inline_comments(pr, comments):
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
            f"*Posted automatically by RepoGuardian PR Review Agent*"
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
            log.warning(f"  Skipped {c.path}:{c.line} — {e.data.get('message', str(e))}")

    log.info(f"Comments posted: {posted} | Skipped: {skipped}")


# ─────────────────────────────────────────
# GitHub — Post Summary Comment
# ─────────────────────────────────────────

def post_summary(pr, result):
    counts = {"high": 0, "medium": 0, "low": 0}
    for c in result.comments:
        counts[c.severity] = counts.get(c.severity, 0) + 1

    score = result.score
    if score >= 85:
        badge = "🟢 GOOD"
    elif score >= 65:
        badge = "🟡 NEEDS WORK"
    else:
        badge = "🔴 CRITICAL ISSUES"

    body = f"""## 🛡️ RepoGuardian — Automated PR Review

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
# Main Agent — called by Orchestrator
# ─────────────────────────────────────────

def run_pr_review_agent(repo_name, pr_number):
    """
    MAIN FUNCTION — call this from the Orchestrator.

    Usage:
        from agents.pr_review import run_pr_review_agent
        result = run_pr_review_agent("owner/repo", 1)
    """
    log.info(f"PR Review Agent started — {repo_name} PR #{pr_number}")

    # Step 1 — Fetch diff from GitHub
    log.info("Step 1/4 — Fetching PR diff from GitHub...")
    diff, pr = fetch_pr_diff(repo_name, pr_number)

    if not diff.strip():
        log.info("No reviewable diff found.")
        return PRReviewResult(
            repo_name=repo_name,
            pr_number=pr_number,
            summary="No reviewable code changes found.",
            comments=[],
            score=100
        )

    # Step 2 — Chunk diff (handles large PRs)
    log.info("Step 2/4 — Chunking diff...")
    chunks = chunk_diff(diff)
    log.info(f"Diff split into {len(chunks)} chunk(s)")

    # Step 3 — Send each chunk to LLM
    log.info("Step 3/4 — Analysing with LLM...")
    all_comments    = []
    total_deduction = 0
    summary         = ""

    for i, chunk in enumerate(chunks):
        log.info(f"  Chunk {i+1}/{len(chunks)}...")
        llm_result = call_llm(chunk)

        total_deduction += llm_result.get("score_deduction", 0)
        summary = llm_result.get("summary", summary)

        for issue in llm_result.get("issues", []):
            try:
                all_comments.append(ReviewComment(
                    path     = issue["path"],
                    line     = int(issue["line"]),
                    body     = issue["comment"],
                    severity = issue.get("severity", "low"),
                    category = issue.get("category", "standards")
                ))
            except (KeyError, ValueError, TypeError) as e:
                log.warning(f"Skipping bad issue: {e}")

    score = max(0, 100 - total_deduction)

    result = PRReviewResult(
        repo_name = repo_name,
        pr_number = pr_number,
        summary   = summary,
        comments  = all_comments,
        score     = score
    )

    log.info(f"Found {len(all_comments)} issue(s) | Score: {score}/100")

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
    print("  RepoGuardian — PR Review Agent 🛡️")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python pr_review.py <owner/repo> <pr_number>")
        print("Example: python pr_review.py vamshi/myproject 1")
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