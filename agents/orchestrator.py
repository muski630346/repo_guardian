"""
RepoGuardian — Orchestrator Agent
Receives GitHub webhook, runs all agents in sequence,
aggregates findings, calculates a fair health score,
posts the final verdict to GitHub PR.

Agent execution order:
    1. Dependency   (background, no LLM, pip-audit)
    2. PR Review    (LLM 1/4)
    3. Security     (LLM 2/4)
    4. Docs         (LLM 3/4)
    5. Complexity   (LLM 4/4)
    6. Memory       (no LLM — runs after score is known)
    7. Auto-Fix     (no LLM — runs last, raises fix PR if possible)

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
from concurrent.futures import ThreadPoolExecutor

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
    "security":   1.5,
    "dependency": 1.3,
    "pr_review":  1.0,
    "complexity": 1.0,
    "docs":       0.5,
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
        bucket["penalty"]  += weight

    penalty = min(penalty, 70)
    score   = max(30, round(100 - penalty))
    grade   = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 50 else "F"

    highs = sum(1 for f in findings if f.severity == "high")
    meds  = sum(1 for f in findings if f.severity == "medium")
    lows  = sum(1 for f in findings if f.severity == "low")

    return {
        "score":    score,
        "grade":    grade,
        "breakdown": breakdown,
        "summary":  f"{len(findings)} issues — {highs} critical, {meds} warnings, {lows} suggestions",
        "highs":    highs,
        "mediums":  meds,
        "lows":     lows,
    }


# ─────────────────────────────────────────
# Agent Runners — each returns findings
# ─────────────────────────────────────────

def _run_pr_review(repo_name: str, pr_number: int) -> tuple[list[Finding], str]:
    """Run PR Review Agent — returns Finding objects for orchestrator scoring."""
    from agents.pr_review import run_pr_review_agent

    log_agent("PR Review Agent starting...")
    start  = time.time()
    result = run_pr_review_agent(repo_name, pr_number)

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
    """Dependency Agent — pip-audit CVE scanner, no LLM."""
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
    """Complexity Agent — Radon code smell scanner."""
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


def _run_docs(repo_name: str, pr_number: int) -> tuple[list[Finding], str]:
    """Docs Agent — docstring, README, and inline comment coverage."""
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


def _run_memory(repo_name: str, pr_number: int,
                all_findings: list[Finding], health_score: int):
    """
    Memory Agent — runs after score is calculated.
    Tracks developer patterns over time, posts personalised alerts.
    No LLM — no rate limit risk.
    """
    try:
        from tools.memory import run_memory_scan
        log_agent("Memory Agent starting...")
        start  = time.time()
        result = run_memory_scan(repo_name, pr_number, all_findings, health_score)
        log_ok(
            f"Memory done in {round(time.time()-start,1)}s — "
            f"{len(result.recurring_alerts)} alert(s) for @{result.developer}"
        )
        return result
    except ImportError:
        log_warn("Memory agent not found — skipping (tools/memory.py missing)")
        return None


def _run_autofix(repo_name: str, pr_number: int,
                 all_findings: list[Finding]):
    """
    Auto-Fix Agent — runs LAST after all analysis is done.
    Applies safe deterministic fixes and raises a ready-to-merge PR.
    No LLM — no rate limit risk.
    Only fixes: secrets→os.getenv, MD5→SHA256, debug→False,
                http→https, bare except, eval→ast.literal_eval,
                insecure random→secrets
    """
    try:
        from tools.autofix import run_autofix_scan
        log_agent("Auto-Fix Agent starting...")
        start  = time.time()
        result = run_autofix_scan(repo_name, pr_number, all_findings)
        if result.fixes_applied:
            log_ok(
                f"Auto-Fix done in {round(time.time()-start,1)}s — "
                f"{len(result.fixes_applied)} fix(es) | Fix PR: #{result.fix_pr_number}"
            )
        else:
            log_ok(
                f"Auto-Fix done in {round(time.time()-start,1)}s — "
                f"no auto-fixable issues found"
            )
        return result
    except ImportError:
        log_warn("Auto-Fix agent not found — skipping (tools/autofix.py missing)")
        return None


# ─────────────────────────────────────────
# GitHub — Post Final Orchestrator Summary
# ─────────────────────────────────────────

def post_final_verdict(repo_name: str, pr_number: int, score_data: dict,
                       all_findings: list[Finding], elapsed: float,
                       autofix_result=None):
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

        breakdown_rows = "".join(
            f"| {agent.replace('_',' ').title()} | "
            f"{data.get('high',0)} | {data.get('medium',0)} | {data.get('low',0)} |\n"
            for agent, data in score_data["breakdown"].items()
        )

        agents_run = len(score_data["breakdown"])

        # Auto-Fix section in verdict
        autofix_section = ""
        if autofix_result and autofix_result.fixes_applied:
            autofix_section = f"""
### 🤖 Auto-Fix PR
RepoGuardian automatically fixed **{len(autofix_result.fixes_applied)} issue(s)**.
**Fix PR:** {autofix_result.fix_pr_url} (#{autofix_result.fix_pr_number})
> Review and merge the fix PR to resolve these issues automatically.
"""
        elif autofix_result and autofix_result.skipped_rules:
            autofix_section = f"""
### 🤖 Auto-Fix
No auto-fixable issues found. The following require manual fixes:
{chr(10).join(f'- `{r}`' for r in autofix_result.skipped_rules)}
"""

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
{autofix_section}
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

    Full agent execution order:
        [Background] Dependency  — pip-audit, no LLM
        [LLM 1/4]    PR Review   — code logic, naming, structure
        [LLM 2/4]    Security    — OWASP, secrets, injection
        [LLM 3/4]    Docs        — docstrings, README, inline comments
        [LLM 4/4]    Complexity  — code smell, Radon
        [Post-score] Memory      — developer pattern tracking, no LLM
        [Final]      Auto-Fix    — raises fix PR for simple issues, no LLM

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
    # Groq free tier: strict tokens/minute limit.
    # Dependency (no LLM) runs in background thread.
    # LLM agents run ONE AT A TIME, 20s apart.
    # Memory + Auto-Fix run after score — no LLM, no sleep needed.
    #
    # LLM call schedule:
    #   t=0s   PR Review  → up to 3 chunk calls
    #   t=20s  Security   → 1 call
    #   t=40s  Docs       → 1 call
    #   t=60s  Complexity → 1 call

    print("─" * 60)
    log_info("Dependency Agent starting in background (no LLM)...")
    print("─" * 60)

    with ThreadPoolExecutor(max_workers=1) as dep_executor:
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

        # ── LLM Agent 4: Complexity ────────────────────────────
        log_agent("Code Smell Agent starting... [LLM 4/4]")
        try:
            findings, _ = _run_complexity(repo_name, pr_number)
            all_findings.extend(findings)
            log_info(f"Complexity: {len(findings)} finding(s) collected")
        except Exception as e:
            log_err(f"Complexity crashed: {e} — skipping")

        # ── Collect Dependency from background ─────────────────
        try:
            dep_findings, _ = dep_future.result(timeout=120)
            all_findings.extend(dep_findings)
            log_info(f"Dependency: {len(dep_findings)} finding(s) collected")
        except Exception as e:
            log_err(f"Dependency crashed: {e} — skipping")

    print()

    # ── SINGLE UNIFIED HEALTH SCORE ───────────────────────────
    print("═" * 60)
    score_data = calculate_health_score(all_findings)
    elapsed    = round(time.time() - start, 1)

    log_score(f"HEALTH SCORE : {score_data['score']} / 100  (Grade: {score_data['grade']})")
    log_score(f"Summary      : {score_data['summary']}")
    log_score(f"Total time   : {elapsed}s")
    print("═" * 60)
    print()

    # ── MEMORY AGENT — post-score, no LLM ─────────────────────
    print("─" * 60)
    log_agent("Memory Agent starting... [POST-SCORE, no LLM]")
    print("─" * 60)
    memory_result = None
    try:
        memory_result = _run_memory(repo_name, pr_number, all_findings, score_data["score"])
        if memory_result:
            log_ok(
                f"Memory: @{memory_result.developer} | "
                f"{len(memory_result.recurring_alerts)} recurring alert(s) | "
                f"{memory_result.profile_summary.get('total_prs', 1)} total PR(s) tracked"
            )
    except Exception as e:
        log_err(f"Memory Agent crashed: {e} — skipping")

    print()

    # ── AUTO-FIX AGENT — runs last, no LLM ────────────────────
    print("─" * 60)
    log_agent("Auto-Fix Agent starting... [FINAL, no LLM]")
    print("─" * 60)
    autofix_result = None
    try:
        autofix_result = _run_autofix(repo_name, pr_number, all_findings)
        if autofix_result and autofix_result.fixes_applied:
            log_ok(
                f"Auto-Fix: {len(autofix_result.fixes_applied)} fix(es) applied | "
                f"Fix PR: #{autofix_result.fix_pr_number} — {autofix_result.fix_pr_url}"
            )
        elif autofix_result:
            log_ok("Auto-Fix: no auto-fixable issues in this PR")
    except Exception as e:
        log_err(f"Auto-Fix Agent crashed: {e} — skipping")

    print()

    # ── POST FINAL VERDICT TO GITHUB ──────────────────────────
    post_final_verdict(
        repo_name      = repo_name,
        pr_number      = pr_number,
        score_data     = score_data,
        all_findings   = all_findings,
        elapsed        = elapsed,
        autofix_result = autofix_result,
    )

    # ── BUILD RESULT OBJECT ───────────────────────────────────
    result = ReviewResult(
        pr_number    = pr_number,
        repo         = repo_name,
        findings     = all_findings,
        health_score = score_data["score"],
    )

    result.metadata = {
        "grade":            score_data["grade"],
        "score_summary":    score_data["summary"],
        "score_breakdown":  score_data["breakdown"],
        "total_findings":   len(all_findings),
        "highs":            score_data.get("highs", 0),
        "mediums":          score_data.get("mediums", 0),
        "lows":             score_data.get("lows", 0),
        "review_time_s":    elapsed,
        "timestamp":        datetime.now().isoformat(),
        "llm_used":         os.getenv("LLM_MODEL", "groq"),
        # Memory Agent
        "memory_developer": memory_result.developer if memory_result else None,
        "memory_alerts":    len(memory_result.recurring_alerts) if memory_result else 0,
        "memory_profile":   memory_result.profile_summary if memory_result else {},
        # Auto-Fix Agent
        "autofix_count":    len(autofix_result.fixes_applied) if autofix_result else 0,
        "autofix_pr_url":   autofix_result.fix_pr_url if autofix_result else None,
        "autofix_pr_number":autofix_result.fix_pr_number if autofix_result else None,
        "autofix_skipped":  autofix_result.skipped_rules if autofix_result else [],
    }

    # ── TERMINAL SUMMARY BOX ──────────────────────────────────
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║  REVIEW COMPLETE  |  PR #{pr_number}  |  {elapsed}s")
    print(f"║  Health Score  : {score_data['score']} / 100  (Grade {score_data['grade']})")
    print(f"║  Total Issues  : {len(all_findings)}")
    print(f"║    Critical    : {score_data.get('highs', 0)}")
    print(f"║    Warnings    : {score_data.get('mediums', 0)}")
    print(f"║    Suggestions : {score_data.get('lows', 0)}")
    if memory_result:
        print(f"║  Memory Alerts : {len(memory_result.recurring_alerts)} for @{memory_result.developer}")
    if autofix_result and autofix_result.fixes_applied:
        print(f"║  Auto-Fix PR   : #{autofix_result.fix_pr_number} ({len(autofix_result.fixes_applied)} fix(es))")
    elif autofix_result:
        print(f"║  Auto-Fix      : no fixable issues")
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

    print(f"\n  PR           : #{result.pr_number}")
    print(f"  Repo         : {result.repo}")
    print(f"  Score        : {result.health_score}/100")
    print(f"  Findings     : {len(result.findings)}")
    print(f"  Grade        : {result.metadata['grade']}")
    print(f"  Time         : {result.metadata['review_time_s']}s")
    if result.metadata.get("memory_developer"):
        print(f"  Memory       : @{result.metadata['memory_developer']} | "
              f"{result.metadata['memory_alerts']} alert(s)")
    if result.metadata.get("autofix_pr_url"):
        print(f"  Fix PR       : #{result.metadata['autofix_pr_number']} — "
              f"{result.metadata['autofix_pr_url']}")