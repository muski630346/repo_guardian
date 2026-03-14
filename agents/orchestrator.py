"""
RepoGuardian — Orchestrator Agent
Receives GitHub webhook, runs all agents in parallel,
aggregates findings, calculates a fair health score,
posts the final verdict to GitHub PR.

.env required:
    GITHUB_TOKEN=...
    GROQ_API_KEY=...
    LLM_MODEL=groq
"""

import os
import sys
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from db.models import Finding, ReviewResult

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ORCHESTRATOR] %(message)s")
log = logging.getLogger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════════╗
║       REPO GUARDIAN — AUTONOMOUS CODE REVIEW             ║
║           Multi-Agent Intelligence System                ║
╚══════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────
# Colour Terminal Logger
# ─────────────────────────────────────────

def _log(icon, msg, code="0"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\033[{code}m[{ts}] {icon}  {msg}\033[0m")

def log_info(m):    _log("→", m, "36")
def log_ok(m):      _log("✓", m, "32")
def log_warn(m):    _log("⚠", m, "33")
def log_err(m):     _log("✗", m, "31")
def log_agent(m):   _log("🤖", m, "35")
def log_score(m):   _log("📊", m, "34")


# ─────────────────────────────────────────
# Health Score Engine
# ─────────────────────────────────────────
#
# HOW SCORING WORKS (this was the bug causing score = 0):
#
# Each agent now returns findings as Finding objects.
# The orchestrator runs ONE score calculation from ALL findings combined.
# This prevents double-counting: previously PR agent scored 30/100 AND
# security scored -50pts, then the orchestrator applied BOTH — giving 0.
#
# Now: start at 100, subtract once per issue based on severity + agent weight.
# Max deduction is capped at 70 (minimum score = 30 for very bad PRs).
#
# Weights:
#   security high   = 15 × 1.5 = 22.5pts per issue
#   pr_review high  = 15 × 1.0 = 15pts per issue
#   security medium = 7  × 1.5 = 10.5pts per issue
#   pr_review medium= 7  × 1.0 = 7pts per issue
#   low             = 2  × any = 2-3pts per issue

SEVERITY_WEIGHTS  = {"high": 15, "medium": 7, "low": 2}
AGENT_MULTIPLIERS = {
    "security":   1.5,   # security issues penalised 50% extra
    "dependency": 1.3,   # CVEs penalised 30% extra
    "pr_review":  1.0,
    "complexity": 1.0,
    "docs":       0.5,   # docs issues penalised less
}


def calculate_health_score(findings: list[Finding]) -> dict:
    """
    Single score calculation from ALL agent findings combined.
    Called ONCE by the orchestrator after all agents finish.
    No individual agent scores are used — prevents double-penalty.
    """
    if not findings:
        return {
            "score": 100, "grade": "A+", "breakdown": {},
            "summary": "No issues found — clean PR!",
            "highs": 0, "mediums": 0, "lows": 0
        }

    penalty   = 0
    breakdown = {}

    for f in findings:
        weight = SEVERITY_WEIGHTS.get(f.severity, 2) * AGENT_MULTIPLIERS.get(f.agent, 1.0)
        penalty += weight

        bucket = breakdown.setdefault(
            f.agent, {"high": 0, "medium": 0, "low": 0, "penalty": 0}
        )
        bucket[f.severity] = bucket.get(f.severity, 0) + 1
        bucket["penalty"] += weight

    # Cap total penalty at 70 — even a very bad PR gets at least 30/100
    penalty = min(penalty, 70)
    score   = max(30, round(100 - penalty))

    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 50 else "F"

    highs = sum(1 for f in findings if f.severity == "high")
    meds  = sum(1 for f in findings if f.severity == "medium")
    lows  = sum(1 for f in findings if f.severity == "low")

    return {
        "score":     score,
        "grade":     grade,
        "breakdown": breakdown,
        "summary":   f"{len(findings)} issues — {highs} critical, {meds} warnings, {lows} suggestions",
        "highs":     highs,
        "mediums":   meds,
        "lows":      lows,
    }


# ─────────────────────────────────────────
# Agent Runners
# Each returns (list[Finding], agent_name)
# Individual agent scores are IGNORED —
# the orchestrator recalculates score centrally
# ─────────────────────────────────────────

def _run_pr_review(repo_name: str, pr_number: int) -> tuple[list[Finding], str]:
    """Run PR Review Agent — returns Finding objects for orchestrator scoring."""
    from agents.pr_review import run_pr_review_agent

    log_agent("PR Review Agent starting...")
    start  = time.time()
    result = run_pr_review_agent(repo_name, pr_number)

    # Convert ReviewComment objects → Finding objects
    findings = [
        Finding(
            agent      = "pr_review",
            severity   = c.severity,
            message    = c.body,
            file       = c.path,
            line       = c.line,
            suggestion = f"Category: {c.category}",
        )
        for c in result.comments
    ]

    log_ok(f"PR Review done in {round(time.time()-start,1)}s — {len(findings)} issue(s)")
    return findings, "pr_review"


def _run_security(repo_name: str, pr_number: int) -> tuple[list[Finding], str]:
    """Run Security Agent — returns Finding objects for orchestrator scoring."""
    from tools.security import run_security_agent

    log_agent("Security Agent starting...")
    start  = time.time()
    result = run_security_agent(repo_name, pr_number)

    # Convert SecurityIssue objects → Finding objects
    findings = [
        Finding(
            agent      = "security",
            severity   = issue.severity,
            message    = issue.body,
            file       = issue.path,
            line       = issue.line,
            suggestion = f"Rule: {issue.rule} | Category: {issue.category}",
        )
        for issue in result.issues
    ]

    log_ok(f"Security done in {round(time.time()-start,1)}s — {len(findings)} issue(s)")
    return findings, "security"


def _run_dependency(repo_name: str, pr_number: int) -> tuple[list[Finding], str]:
    """Dependency Agent — plug in tools/dependency.py when ready."""
    try:
        from tools.dependency import run_dependency_scan
        log_agent("Dependency Agent starting...")
        start    = time.time()
        findings = run_dependency_scan(repo_name, pr_number)
        log_ok(f"Dependency done in {round(time.time()-start,1)}s — {len(findings)} issue(s)")
        return findings, "dependency"
    except ImportError:
        log_warn("Dependency agent not found — skipping (tools/dependency.py missing)")
        return [], "dependency"


def _run_complexity(repo_name: str, pr_number: int) -> tuple[list[Finding], str]:
    """Complexity Agent — plug in tools/complexity.py when ready."""
    try:
        from tools.complexity import run_complexity_scan
        log_agent("Complexity Agent starting...")
        start    = time.time()
        findings = run_complexity_scan(repo_name, pr_number)
        log_ok(f"Complexity done in {round(time.time()-start,1)}s — {len(findings)} issue(s)")
        return findings, "complexity"
    except ImportError:
        log_warn("Complexity agent not found — skipping (tools/complexity.py missing)")
        return [], "complexity"


# ─────────────────────────────────────────
# GitHub — Post Final Orchestrator Summary
# ─────────────────────────────────────────


def _run_docs(repo_name: str, pr_number: int) -> tuple[list[Finding], str]:
    """Docs Agent — verifies docstrings, README, and inline comments."""
    try:
        from tools.docs import run_docs_scan
        log_agent("Docs Agent starting...")
        start    = time.time()
        findings = run_docs_scan(repo_name, pr_number)
        log_ok(f"Docs done in {round(time.time()-start,1)}s — {len(findings)} issue(s)")
        return findings, "docs"
    except ImportError:
        log_warn("Docs agent not found — skipping (tools/docs.py missing)")
        return [], "docs"


def post_final_verdict(repo_name: str, pr_number: int, score_data: dict,
                       all_findings: list[Finding], elapsed: float):
    """Post the master orchestrator summary comment to GitHub PR."""
    try:
        from github import Github
        g    = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(repo_name)
        pr   = repo.get_pull(pr_number)

        score = score_data["score"]
        grade = score_data["grade"]

        if score >= 85:
            badge = "🟢 APPROVED — Good to merge"
        elif score >= 65:
            badge = "🟡 NEEDS CHANGES — Fix before merging"
        else:
            badge = "🔴 REJECTED — Critical issues found"

        # Per-agent breakdown table
        breakdown_rows = "".join(
            f"| {agent.replace('_',' ').title()} | "
            f"{data.get('high',0)} | {data.get('medium',0)} | {data.get('low',0)} |\n"
            for agent, data in score_data["breakdown"].items()
        )

        agents_run = len([a for a, d in score_data["breakdown"].items()])

        body = f"""## 🛡️ RepoGuardian — Full Automated Review

**Health Score: `{score}/100` (Grade: {grade})** &nbsp; {badge}

### Overview
{score_data['summary']}

### Agent Breakdown
| Agent | 🔴 High | 🟡 Medium | 🔵 Low |
|-------|---------|----------|--------|
{breakdown_rows}| **Total** | **{score_data['highs']}** | **{score_data['mediums']}** | **{score_data['lows']}** |

### Issue Totals
| Severity | Count |
|----------|-------|
| 🔴 High (must fix) | **{score_data['highs']}** |
| 🟡 Medium (should fix) | **{score_data['mediums']}** |
| 🔵 Low (nice to fix) | **{score_data['lows']}** |
| **Total** | **{len(all_findings)}** |

> ⏱️ Review completed in `{elapsed}s` across `{agents_run}` active agent(s).
> Inline comments posted on each affected line by each specialist agent.
> *RepoGuardian Orchestrator — KLH Hackathon 2025 — Powered by Groq + Llama3*
"""
        pr.create_issue_comment(body)
        log_ok("Final verdict posted to GitHub PR.")

    except Exception as e:
        log_err(f"Could not post final verdict: {e}")


# ─────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────

def run_full_review(repo_name: str, pr_number: int) -> ReviewResult:
    """
    MAIN FUNCTION — called by webhook receiver (webhook/receiver.py).

    Runs all agents in parallel, aggregates findings into one list,
    calculates a single unified health score, posts verdict to GitHub.

    Usage:
        from agents.orchestrator import run_full_review
        result = run_full_review("owner/repo", 42)
    """
    print(BANNER)
    log_info(f"PR #{pr_number} received — repo: {repo_name}")
    log_info(f"LLM: {os.getenv('LLM_MODEL', 'groq')}")
    print()

    start        = time.time()
    all_findings = []

    # ── RATE LIMIT STRATEGY ──────────────────────────────────
    # Groq free tier has a strict tokens/minute limit.
    # Running all agents in parallel fires multiple LLM calls
    # simultaneously and instantly causes 429 errors.
    #
    # SOLUTION:
    #   - Dependency (pip-audit, NO LLM) runs in a background thread
    #   - All LLM agents run ONE AT A TIME, 20s apart
    #   - complexity.py has NO internal sleep — orchestrator controls timing
    #
    # LLM call schedule (spread over ~60s):
    #   t=0s   PR Review  → up to 3 chunk calls
    #   t=20s  Security   → 1 call
    #   t=40s  Docs       → 1 call
    #   t=60s  Complexity → 1 call
    #   Total: 6 calls spread over 60s = well within 30 req/min

    print("─" * 60)
    log_info("Dependency Agent starting in background (no LLM)...")
    print("─" * 60)

    with ThreadPoolExecutor(max_workers=1) as dep_executor:
        # Dependency uses pip-audit only — safe to run in background
        dep_future = dep_executor.submit(_run_dependency, repo_name, pr_number)

        print()
        print("─" * 60)
        log_info("LLM agents running sequentially (rate limit protection)...")
        print("─" * 60)
        print()

        # ── LLM Agent 1: PR Review ─────────────────────────────
        log_agent("PR Review Agent starting... [LLM 1/4]")
        try:
            findings, _ = _run_pr_review(repo_name, pr_number)
            all_findings.extend(findings)
            log_info(f"PR Review: {len(findings)} finding(s) collected")
        except Exception as e:
            log_err(f"PR Review crashed: {e} — skipping")

        log_info("Waiting 20s before next LLM agent (rate limit gap)...")
        time.sleep(20)

        # ── LLM Agent 2: Security ──────────────────────────────
        log_agent("Security Agent starting... [LLM 2/4]")
        try:
            findings, _ = _run_security(repo_name, pr_number)
            all_findings.extend(findings)
            log_info(f"Security: {len(findings)} finding(s) collected")
        except Exception as e:
            log_err(f"Security crashed: {e} — skipping")

        log_info("Waiting 20s before next LLM agent (rate limit gap)...")
        time.sleep(20)

        # ── LLM Agent 3: Docs ─────────────────────────────────
        log_agent("Docs Agent starting... [LLM 3/4]")
        try:
            findings, _ = _run_docs(repo_name, pr_number)
            all_findings.extend(findings)
            log_info(f"Docs: {len(findings)} finding(s) collected")
        except Exception as e:
            log_err(f"Docs crashed: {e} — skipping")

        log_info("Waiting 20s before next LLM agent (rate limit gap)...")
        time.sleep(20)

        # ── LLM Agent 4: Complexity / Code Smell ──────────────
        log_agent("Code Smell Agent starting... [LLM 4/4]")
        try:
            findings, _ = _run_complexity(repo_name, pr_number)
            all_findings.extend(findings)
            log_info(f"Complexity: {len(findings)} finding(s) collected")
        except Exception as e:
            log_err(f"Complexity crashed: {e} — skipping")

        # ── Collect Dependency results from background ─────────
        try:
            dep_findings, _ = dep_future.result(timeout=120)
            all_findings.extend(dep_findings)
            log_info(f"Dependency: {len(dep_findings)} finding(s) collected")
        except Exception as e:
            log_err(f"Dependency crashed: {e} — skipping")

    print()

    # ── SINGLE UNIFIED HEALTH SCORE ───────────────────────────
    # Score is calculated ONCE from ALL findings combined.
    # This prevents the double-penalty bug that caused score = 0.
    print("═" * 60)
    score_data = calculate_health_score(all_findings)
    elapsed    = round(time.time() - start, 1)

    log_score(f"HEALTH SCORE : {score_data['score']} / 100  (Grade: {score_data['grade']})")
    log_score(f"Summary      : {score_data['summary']}")
    log_score(f"Total time   : {elapsed}s")
    print("═" * 60)
    print()

    # ── POST FINAL VERDICT TO GITHUB ──────────────────────────
    post_final_verdict(repo_name, pr_number, score_data, all_findings, elapsed)

    # ── BUILD RESULT OBJECT ───────────────────────────────────
    result = ReviewResult(
        pr_number    = pr_number,
        repo         = repo_name,
        findings     = all_findings,
        health_score = score_data["score"],
    )

    result.metadata = {
        "grade":          score_data["grade"],
        "score_summary":  score_data["summary"],
        "score_breakdown":score_data["breakdown"],
        "total_findings": len(all_findings),
        "highs":          score_data.get("highs", 0),
        "mediums":        score_data.get("mediums", 0),
        "lows":           score_data.get("lows", 0),
        "review_time_s":  elapsed,
        "timestamp":      datetime.now().isoformat(),
        "llm_used":       os.getenv("LLM_MODEL", "groq"),
    }

    # ── TERMINAL SUMMARY BOX ──────────────────────────────────
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║  REVIEW COMPLETE  |  PR #{pr_number}  |  {elapsed}s")
    print(f"║  Health Score  : {score_data['score']} / 100  (Grade {score_data['grade']})")
    print(f"║  Total Issues  : {len(all_findings)}")
    print(f"║    Critical    : {score_data.get('highs', 0)}")
    print(f"║    Warnings    : {score_data.get('mediums', 0)}")
    print(f"║    Suggestions : {score_data.get('lows', 0)}")
    print("╚══════════════════════════════════════════════════════════╝")

    log_ok("ReviewResult ready — passing to dashboard (P4)")
    return result


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("\n========================================")
    print("  RepoGuardian — Orchestrator")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python agents/orchestrator.py <owner/repo> <pr_number>")
        print("Example: python agents/orchestrator.py vamshi/myproject 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = int(sys.argv[2])

    missing = [k for k in ["GROQ_API_KEY", "GITHUB_TOKEN"] if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing in .env: {', '.join(missing)}")
        sys.exit(1)

    result = run_full_review(repo_arg, pr_arg)

    print(f"\n  PR       : #{result.pr_number}")
    print(f"  Repo     : {result.repo}")
    print(f"  Score    : {result.health_score}/100")
    print(f"  Findings : {len(result.findings)}")
    print(f"  Grade    : {result.metadata['grade']}")
    print(f"  Time     : {result.metadata['review_time_s']}s")