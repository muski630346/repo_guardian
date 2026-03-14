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

groq_client = Groq(api_key=GROQ_API_KEY)
github_client = Github(GITHUB_TOKEN)


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
# Prompt
# ─────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior software engineer performing code reviews.

Return JSON only.

Format:
{
 "summary": "brief summary",
 "score_deduction": number,
 "issues":[
   {
     "path": "file.py",
     "line": 10,
     "severity": "high|medium|low",
     "category": "logic|naming|structure|standards",
     "comment": "actionable feedback"
   }
 ]
}
"""


# ─────────────────────────────────────────
# Diff Chunking
# ─────────────────────────────────────────

def chunk_diff(diff, max_chars=6000):

    chunks = []
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

def call_groq(prompt, retries=3):

    for attempt in range(retries):

        try:
            response = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            raw = response.choices[0].message.content.strip()

            raw = re.sub(r"^```json", "", raw)
            raw = re.sub(r"```$", "", raw)

            return json.loads(raw)

        except Exception as e:
            log.warning(f"Groq call failed attempt {attempt+1}: {e}")
            time.sleep(2)

    return {"summary": "LLM failed", "score_deduction": 0, "issues": []}


# ─────────────────────────────────────────
# GitHub Functions
# ─────────────────────────────────────────

def fetch_pr_diff(repo_name, pr_number):

    repo = github_client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    diff_parts = []

    for file in pr.get_files():
        if file.patch:
            diff_parts.append(f"FILE: {file.filename}")
            diff_parts.append(file.patch)

    return "\n".join(diff_parts), pr


def post_inline_comments(pr, comments):

    if not comments:
        return

    latest_commit = list(pr.get_commits())[-1]

    for c in comments:

        try:
            pr.create_review_comment(
                body=f"🛡 RepoGuardian\n\n{c.body}",
                commit=latest_commit,
                path=c.path,
                line=c.line
            )

        except GithubException as e:
            log.warning(f"Failed comment {c.path}:{c.line}")


def post_summary(pr, result):

    body = f"""
## RepoGuardian Automated Review

Score: **{result.score}/100**

Summary:
{result.summary}

Issues Found: **{len(result.comments)}**
"""

    pr.create_issue_comment(body)


# ─────────────────────────────────────────
# Main Agent
# ─────────────────────────────────────────

def run_pr_review_agent(repo_name, pr_number):

    log.info("Fetching PR diff")

    diff, pr = fetch_pr_diff(repo_name, pr_number)

    if not diff:
        log.info("No diff found")
        return

    chunks = chunk_diff(diff)

    all_comments = []
    total_deduction = 0
    summary = ""

    for chunk in chunks:

        result = call_groq(chunk)

        total_deduction += result.get("score_deduction", 0)
        summary = result.get("summary", summary)

        for issue in result.get("issues", []):

            try:
                all_comments.append(
                    ReviewComment(
                        path=issue["path"],
                        line=int(issue["line"]),
                        body=issue["comment"],
                        severity=issue.get("severity", "low"),
                        category=issue.get("category", "standards")
                    )
                )
            except:
                pass

    score = max(0, 100 - total_deduction)

    result = PRReviewResult(
        repo_name=repo_name,
        pr_number=pr_number,
        summary=summary,
        comments=all_comments,
        score=score
    )

    post_inline_comments(pr, all_comments)
    post_summary(pr, result)

    return result


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 3:
        print("Usage: python pr_review.py owner/repo pr_number")
        exit()

    repo = sys.argv[1]
    pr_number = int(sys.argv[2])

    result = run_pr_review_agent(repo, pr_number)

    print("\nReview Complete")
    print("Score:", result.score)
    print("Issues:", len(result.comments))