"""
RepoGuardian — Memory Agent
Tracks each developer's recurring issue patterns over time.
Personalises feedback by surfacing "you keep doing this" alerts.
Stores history in a local JSON file (db/memory_store.json).

Called by the Orchestrator AFTER all other agents finish.
Reads all_findings, identifies the PR author, updates their history,
and posts a personalised memory comment to the GitHub PR.

.env required:
    GITHUB_TOKEN=...

No LLM required — purely pattern-based analytics.
"""

import os
import sys
import json
import logging
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from github import Github, GithubException
from dotenv import load_dotenv

# db.models is one level up — same pattern as all other agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Finding

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MEMORY] %(message)s")
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError("Missing GITHUB_TOKEN in .env")

github_client = Github(GITHUB_TOKEN)

# ─────────────────────────────────────────
# Storage — simple JSON file in db/
# ─────────────────────────────────────────

MEMORY_STORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "db", "memory_store.json"
)


# ─────────────────────────────────────────
# Thresholds — how many times before we flag as "recurring"
# ─────────────────────────────────────────

RECURRING_THRESHOLD   = 3    # issue category seen 3+ times → recurring alert
STREAK_THRESHOLD      = 2    # same issue in last N PRs in a row → streak alert
MAX_PR_HISTORY        = 50   # max PRs stored per developer


# ─────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────

@dataclass
class PRRecord:
    """One PR's worth of findings — stored in developer history."""
    pr_number:  int
    repo:       str
    timestamp:  str
    score:      int
    findings:   list[dict]   # serialised Finding dicts


@dataclass
class DeveloperProfile:
    """
    Everything we know about one developer across all their PRs.
    Keyed by GitHub username.
    """
    username:       str
    total_prs:      int                    = 0
    total_findings: int                    = 0
    pr_history:     list[PRRecord]         = field(default_factory=list)
    # category_counts: { "security": 12, "injection": 5, ... }
    category_counts: dict[str, int]        = field(default_factory=dict)
    # severity_counts: { "high": 3, "medium": 8, "low": 15 }
    severity_counts: dict[str, int]        = field(default_factory=dict)
    # agent_counts: { "security": 7, "docs": 12, ... }
    agent_counts:    dict[str, int]        = field(default_factory=dict)
    # streak_tracker: last N PRs' category sets — used for streak detection
    last_pr_categories: list[list[str]]    = field(default_factory=list)
    first_seen:     str                    = ""
    last_seen:      str                    = ""


@dataclass
class RecurringAlert:
    """A single recurring issue alert for a developer."""
    category:    str    # e.g. "security / injection"
    count:       int    # total occurrences in history
    trend:       str    # "streak" | "recurring" | "improving"
    message:     str    # human-readable alert message
    suggestion:  str    # actionable fix


@dataclass
class MemoryResult:
    """Returned to Orchestrator."""
    developer:        str
    recurring_alerts: list[RecurringAlert]
    profile_summary:  dict     # stats for dashboard
    comment_posted:   bool


# ─────────────────────────────────────────
# Storage — Load / Save
# ─────────────────────────────────────────

def load_memory_store() -> dict:
    """Load the full memory store from JSON. Returns {} if file doesn't exist."""
    if not os.path.exists(MEMORY_STORE_PATH):
        log.info(f"Memory store not found — starting fresh at {MEMORY_STORE_PATH}")
        return {}
    try:
        with open(MEMORY_STORE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Could not read memory store: {e} — starting fresh")
        return {}


def save_memory_store(store: dict):
    """Save the full memory store back to JSON. Creates db/ dir if needed."""
    os.makedirs(os.path.dirname(MEMORY_STORE_PATH), exist_ok=True)
    try:
        with open(MEMORY_STORE_PATH, "w") as f:
            json.dump(store, f, indent=2, default=str)
        log.info(f"Memory store saved → {MEMORY_STORE_PATH}")
    except OSError as e:
        log.error(f"Could not save memory store: {e}")


def load_profile(username: str) -> DeveloperProfile:
    """Load one developer's profile from the store. Creates blank if new dev."""
    store = load_memory_store()
    if username not in store:
        log.info(f"New developer: {username} — creating profile")
        return DeveloperProfile(username=username, first_seen=datetime.now().isoformat())

    data    = store[username]
    profile = DeveloperProfile(
        username         = username,
        total_prs        = data.get("total_prs", 0),
        total_findings   = data.get("total_findings", 0),
        category_counts  = data.get("category_counts", {}),
        severity_counts  = data.get("severity_counts", {}),
        agent_counts     = data.get("agent_counts", {}),
        last_pr_categories = data.get("last_pr_categories", []),
        first_seen       = data.get("first_seen", ""),
        last_seen        = data.get("last_seen", ""),
    )

    for pr_data in data.get("pr_history", []):
        profile.pr_history.append(PRRecord(
            pr_number = pr_data["pr_number"],
            repo      = pr_data["repo"],
            timestamp = pr_data["timestamp"],
            score     = pr_data["score"],
            findings  = pr_data["findings"],
        ))

    return profile


def save_profile(profile: DeveloperProfile):
    """Save one developer's profile back into the store."""
    store  = load_memory_store()
    pr_history_serialised = [
        {
            "pr_number": r.pr_number,
            "repo":      r.repo,
            "timestamp": r.timestamp,
            "score":     r.score,
            "findings":  r.findings,
        }
        for r in profile.pr_history
    ]

    store[profile.username] = {
        "username":           profile.username,
        "total_prs":          profile.total_prs,
        "total_findings":     profile.total_findings,
        "pr_history":         pr_history_serialised,
        "category_counts":    profile.category_counts,
        "severity_counts":    profile.severity_counts,
        "agent_counts":       profile.agent_counts,
        "last_pr_categories": profile.last_pr_categories,
        "first_seen":         profile.first_seen,
        "last_seen":          profile.last_seen,
    }

    save_memory_store(store)


# ─────────────────────────────────────────
# GitHub — Get PR Author
# ─────────────────────────────────────────

def get_pr_author(repo_name: str, pr_number: int) -> str:
    """Return the GitHub username of the PR author."""
    try:
        repo   = github_client.get_repo(repo_name)
        pr     = repo.get_pull(pr_number)
        author = pr.user.login
        log.info(f"PR #{pr_number} author: {author}")
        return author
    except GithubException as e:
        log.error(f"Could not get PR author: {e}")
        return "unknown"


# ─────────────────────────────────────────
# Extract Category Labels from Findings
# Maps agent + severity/message → human category tags
# ─────────────────────────────────────────

CATEGORY_KEYWORDS = {
    # Security
    "injection":           ["injection", "sql", "xss", "innerHTML"],
    "secrets":             ["hardcoded", "api_key", "password", "private key", "aws key", "secret"],
    "owasp":               ["md5", "sha1", "eval", "pickle", "debug", "owasp"],
    "insecure_pattern":    ["shell=true", "os.system", "subprocess"],
    # Code quality
    "naming":              ["naming", "convention", "variable name", "function name"],
    "logic":               ["logic", "bug", "error handling", "exception", "null", "none check"],
    "structure":           ["structure", "complexity", "refactor", "extract", "class design"],
    "standards":           ["standard", "pep8", "style", "import", "unused"],
    # Docs
    "docstring":           ["docstring", "missing doc", "undocumented"],
    "readme":              ["readme", "documentation missing"],
    "inline_comment":      ["inline comment", "missing comment"],
    # Dependencies
    "cve":                 ["cve-", "vulnerability", "vulnerable", "pip-audit"],
    "advisory":            ["pysec", "advisory", "outdated"],
}


def extract_categories(finding: Finding) -> list[str]:
    """
    Given a Finding, return a list of category tags.
    Uses the finding's agent name + message text for matching.
    """
    tags    = []
    text    = (finding.message + " " + (finding.suggestion or "")).lower()
    agent   = finding.agent.lower()

    # Agent-based base tag
    tags.append(agent)

    # Keyword-based sub-category tags
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            tags.append(category)

    return list(set(tags))


# ─────────────────────────────────────────
# Update Developer Profile
# ─────────────────────────────────────────

def update_profile(
    profile:    DeveloperProfile,
    repo_name:  str,
    pr_number:  int,
    health_score: int,
    findings:   list[Finding],
) -> DeveloperProfile:
    """
    Ingest this PR's findings into the developer's long-term profile.
    Updates: counts, history, streak tracker, timestamps.
    """
    now = datetime.now().isoformat()

    # Build Finding dicts for storage
    serialised_findings = []
    this_pr_categories  = set()

    for f in findings:
        cats = extract_categories(f)
        this_pr_categories.update(cats)

        # Update counts
        for cat in cats:
            profile.category_counts[cat] = profile.category_counts.get(cat, 0) + 1

        profile.severity_counts[f.severity] = (
            profile.severity_counts.get(f.severity, 0) + 1
        )
        profile.agent_counts[f.agent] = profile.agent_counts.get(f.agent, 0) + 1

        serialised_findings.append({
            "agent":      f.agent,
            "severity":   f.severity,
            "message":    f.message,
            "file":       f.file,
            "line":       f.line,
            "suggestion": f.suggestion,
            "categories": cats,
        })

    # Add PR to history
    profile.pr_history.append(PRRecord(
        pr_number = pr_number,
        repo      = repo_name,
        timestamp = now,
        score     = health_score,
        findings  = serialised_findings,
    ))

    # Keep only last MAX_PR_HISTORY PRs
    if len(profile.pr_history) > MAX_PR_HISTORY:
        profile.pr_history = profile.pr_history[-MAX_PR_HISTORY:]

    # Update streak tracker — keep last 5 PRs' category sets
    profile.last_pr_categories.append(list(this_pr_categories))
    if len(profile.last_pr_categories) > 5:
        profile.last_pr_categories = profile.last_pr_categories[-5:]

    # Update aggregate stats
    profile.total_prs      += 1
    profile.total_findings += len(findings)
    profile.last_seen       = now
    if not profile.first_seen:
        profile.first_seen  = now

    log.info(
        f"Profile updated for {profile.username} — "
        f"{profile.total_prs} PR(s), {profile.total_findings} total findings"
    )

    return profile


# ─────────────────────────────────────────
# Pattern Analysis — Detect Recurring Issues
# ─────────────────────────────────────────

# Human-readable suggestions per category
CATEGORY_SUGGESTIONS = {
    "injection":        "Use parameterised queries and sanitise all user input. Consider using an ORM.",
    "secrets":          "Store secrets in environment variables. Use python-dotenv or a secrets manager. Add .env to .gitignore.",
    "owasp":            "Review OWASP Top 10. Avoid MD5/SHA1, eval(), pickle with untrusted data.",
    "insecure_pattern": "Avoid shell=True in subprocess. Use argument lists: subprocess.run(['cmd', 'arg']).",
    "naming":           "Follow PEP 8 naming: snake_case for functions/variables, PascalCase for classes.",
    "logic":            "Add error handling for edge cases. Check for None/null before accessing attributes.",
    "structure":        "Break functions > 30 lines into smaller units. Each function should do one thing.",
    "standards":        "Run flake8 or pylint before committing. Fix unused imports and long lines.",
    "docstring":        "Add docstrings to all public functions: what it does, args, and return value.",
    "readme":           "Update README when adding new features, endpoints, or configuration.",
    "inline_comment":   "Add comments for non-obvious logic. Explain WHY, not WHAT.",
    "cve":              "Run `pip-audit` before pushing. Keep requirements.txt pinned and up to date.",
    "advisory":         "Upgrade packages regularly. Set up Dependabot or pip-audit in CI.",
    "security":         "Review OWASP Top 10 and run Bandit on your code before opening PRs.",
    "dependency":       "Pin all dependencies in requirements.txt and scan for CVEs before merging.",
    "docs":             "Make documentation part of your definition of done — not an afterthought.",
    "pr_review":        "Review your own diff before pushing. Check for logic gaps and naming consistency.",
    "complexity":       "Keep cyclomatic complexity low. Refactor functions with many branches.",
}


def detect_streaks(profile: DeveloperProfile) -> list[RecurringAlert]:
    """
    Detect categories that appeared in STREAK_THRESHOLD or more recent PRs in a row.
    Uses last_pr_categories (last 5 PRs).
    A streak means: the same issue type keeps appearing in consecutive PRs.
    """
    alerts  = []
    history = profile.last_pr_categories

    if len(history) < STREAK_THRESHOLD:
        return []   # not enough history yet

    # Check last STREAK_THRESHOLD PRs
    recent_slice = history[-STREAK_THRESHOLD:]

    # Find categories that appear in ALL recent PRs
    if not recent_slice:
        return []

    common = set(recent_slice[0])
    for pr_cats in recent_slice[1:]:
        common &= set(pr_cats)

    # Exclude generic agent tags — only flag specific sub-categories
    generic_agents = {"security", "pr_review", "dependency", "docs", "complexity"}
    streaking      = common - generic_agents

    for cat in streaking:
        count = profile.category_counts.get(cat, 0)
        alerts.append(RecurringAlert(
            category   = cat,
            count      = count,
            trend      = "streak",
            message    = (
                f"🔁 **Streak detected:** `{cat}` issues appeared in your last "
                f"{STREAK_THRESHOLD} PRs in a row ({count} total occurrences). "
                f"This pattern suggests a habit that needs a fix."
            ),
            suggestion = CATEGORY_SUGGESTIONS.get(cat, "Review this category carefully."),
        ))

    return alerts


def detect_recurring(profile: DeveloperProfile) -> list[RecurringAlert]:
    """
    Detect categories that have crossed the RECURRING_THRESHOLD total count.
    Flags anything seen 3+ times across all PRs (but not already caught as a streak).
    """
    alerts         = []
    generic_agents = {"security", "pr_review", "dependency", "docs", "complexity"}

    for category, count in profile.category_counts.items():
        if category in generic_agents:
            continue
        if count >= RECURRING_THRESHOLD:
            alerts.append(RecurringAlert(
                category   = category,
                count      = count,
                trend      = "recurring",
                message    = (
                    f"⚠️ **Recurring pattern:** `{category}` has appeared "
                    f"**{count} times** across {profile.total_prs} PR(s). "
                    f"This is your most common issue type."
                ),
                suggestion = CATEGORY_SUGGESTIONS.get(category, "Review this category carefully."),
            ))

    # Sort by count descending — most repeated first
    alerts.sort(key=lambda a: a.count, reverse=True)
    return alerts


def detect_improvements(profile: DeveloperProfile) -> list[RecurringAlert]:
    """
    Detect categories that were once frequent but haven't appeared recently.
    Positive reinforcement — "you've improved on X!"
    """
    alerts  = []
    history = profile.last_pr_categories

    if len(history) < 3 or profile.total_prs < 4:
        return []   # not enough history for improvement detection

    # Categories in older PRs (all except last 2)
    older_cats  = set()
    for pr_cats in history[:-2]:
        older_cats.update(pr_cats)

    # Categories in most recent 2 PRs
    recent_cats = set()
    for pr_cats in history[-2:]:
        recent_cats.update(pr_cats)

    generic_agents = {"security", "pr_review", "dependency", "docs", "complexity"}

    # Categories that were in older PRs but NOT in last 2
    improved = older_cats - recent_cats - generic_agents

    for cat in improved:
        count = profile.category_counts.get(cat, 0)
        if count >= 2:   # only praise if it was actually a real pattern
            alerts.append(RecurringAlert(
                category   = cat,
                count      = count,
                trend      = "improving",
                message    = (
                    f"✅ **Improvement noticed:** `{cat}` was a recurring issue "
                    f"({count} past occurrences) but hasn't appeared in your last 2 PRs. "
                    f"Great work!"
                ),
                suggestion = "Keep it up — make this improvement permanent.",
            ))

    return alerts


def analyse_patterns(profile: DeveloperProfile) -> list[RecurringAlert]:
    """
    Run all pattern detectors and return combined alerts.
    Order: streaks first (most urgent), then recurring, then improvements.
    Deduplicates — if a category is already in a streak alert, skip recurring.
    """
    streak_alerts     = detect_streaks(profile)
    recurring_alerts  = detect_recurring(profile)
    improvement_alerts = detect_improvements(profile)

    # Deduplicate: skip recurring if already in streaks
    streak_cats = {a.category for a in streak_alerts}
    deduped_recurring = [a for a in recurring_alerts if a.category not in streak_cats]

    return streak_alerts + deduped_recurring + improvement_alerts


# ─────────────────────────────────────────
# Build Profile Summary (for dashboard / orchestrator metadata)
# ─────────────────────────────────────────

def build_profile_summary(profile: DeveloperProfile) -> dict:
    """Build a stats dict — consumed by Orchestrator metadata and P4 dashboard."""
    top_categories = sorted(
        profile.category_counts.items(), key=lambda x: x[1], reverse=True
    )[:5]

    # Score trend from last 5 PRs
    recent_scores = [r.score for r in profile.pr_history[-5:]]
    score_trend   = "stable"
    if len(recent_scores) >= 2:
        if recent_scores[-1] > recent_scores[0]:
            score_trend = "improving"
        elif recent_scores[-1] < recent_scores[0]:
            score_trend = "declining"

    return {
        "username":        profile.username,
        "total_prs":       profile.total_prs,
        "total_findings":  profile.total_findings,
        "top_categories":  [{"category": k, "count": v} for k, v in top_categories],
        "severity_counts": profile.severity_counts,
        "agent_counts":    profile.agent_counts,
        "recent_scores":   recent_scores,
        "score_trend":     score_trend,
        "first_seen":      profile.first_seen,
        "last_seen":       profile.last_seen,
    }


# ─────────────────────────────────────────
# Build GitHub Comment — Personalised Memory Report
# ─────────────────────────────────────────

def build_memory_comment(
    developer:        str,
    profile:          DeveloperProfile,
    alerts:           list[RecurringAlert],
    this_pr_findings: list[Finding],
    health_score:     int,
) -> str:
    """
    Build the personalised markdown comment posted to the PR.
    Sections:
      1. Personalised greeting with their stats
      2. This PR's quick summary
      3. Recurring alerts (streaks, patterns, improvements)
      4. Top issue categories across all PRs
    """
    # ── Header ──────────────────────────────────────────────────
    greeting = f"👋 Hey @{developer}!"
    if profile.total_prs == 1:
        greeting += " This is your **first PR** reviewed by RepoGuardian — welcome!"
    elif profile.total_prs < 5:
        greeting += f" I've reviewed **{profile.total_prs} PRs** from you so far."
    else:
        greeting += (
            f" I've reviewed **{profile.total_prs} PRs** from you "
            f"and tracked **{profile.total_findings} findings** over time."
        )

    # ── This PR section ─────────────────────────────────────────
    severity_counts = defaultdict(int)
    for f in this_pr_findings:
        severity_counts[f.severity] += 1

    score_emoji = "🟢" if health_score >= 85 else "🟡" if health_score >= 65 else "🔴"

    this_pr_section = f"""\n### This PR
| Metric | Value |
|--------|-------|
| Health Score | {score_emoji} **{health_score}/100** |
| 🔴 High | **{severity_counts.get('high', 0)}** |
| 🟡 Medium | **{severity_counts.get('medium', 0)}** |
| 🔵 Low | **{severity_counts.get('low', 0)}** |
| Total Findings | **{len(this_pr_findings)}** |
"""

    # ── Alerts section ───────────────────────────────────────────
    if alerts:
        streak_alerts      = [a for a in alerts if a.trend == "streak"]
        recurring_alerts   = [a for a in alerts if a.trend == "recurring"]
        improvement_alerts = [a for a in alerts if a.trend == "improving"]

        alert_parts = []

        if streak_alerts:
            alert_parts.append("#### 🔁 Streak Alerts — Same Issue, Multiple PRs in a Row")
            for a in streak_alerts:
                alert_parts.append(f"\n{a.message}\n> 💡 **Fix:** {a.suggestion}\n")

        if recurring_alerts:
            alert_parts.append("#### ⚠️ Recurring Patterns — Your Most Common Issues")
            for a in recurring_alerts:
                alert_parts.append(f"\n{a.message}\n> 💡 **Fix:** {a.suggestion}\n")

        if improvement_alerts:
            alert_parts.append("#### ✅ Improvements — Keep It Up!")
            for a in improvement_alerts:
                alert_parts.append(f"\n{a.message}\n")

        alerts_section = "\n### Personalised Alerts\n" + "\n".join(alert_parts)
    else:
        if profile.total_prs < 3:
            alerts_section = (
                "\n### Personalised Alerts\n"
                f"> ℹ️ I need **{3 - profile.total_prs} more PR(s)** "
                "from you before I can detect patterns. Keep going!\n"
            )
        else:
            alerts_section = (
                "\n### Personalised Alerts\n"
                "> 🌟 No recurring patterns detected — great consistency!\n"
            )

    # ── Top categories across all PRs ───────────────────────────
    top_categories = sorted(
        profile.category_counts.items(), key=lambda x: x[1], reverse=True
    )[:5]

    if top_categories and profile.total_prs >= 2:
        rows = "".join(
            f"| `{cat}` | {count} |\n"
            for cat, count in top_categories
        )
        history_section = f"""\n### Your Top Issue Categories (All-Time)
| Category | Count |
|----------|-------|
{rows}"""
    else:
        history_section = ""

    # ── Score trend ─────────────────────────────────────────────
    recent_scores = [r.score for r in profile.pr_history[-5:]]
    if len(recent_scores) >= 3:
        trend_line = " → ".join(str(s) for s in recent_scores)
        if recent_scores[-1] > recent_scores[0]:
            trend_icon = "📈"
            trend_text = "improving"
        elif recent_scores[-1] < recent_scores[0]:
            trend_icon = "📉"
            trend_text = "declining"
        else:
            trend_icon = "➡️"
            trend_text = "stable"

        trend_section = f"""\n### Your Score Trend (Last {len(recent_scores)} PRs)
{trend_icon} **{trend_text.title()}** — `{trend_line}`\n"""
    else:
        trend_section = ""

    # ── Assemble full comment ────────────────────────────────────
    body = f"""## 🧠 RepoGuardian — Developer Memory Report

{greeting}

---
{this_pr_section}{alerts_section}{history_section}{trend_section}
---
> *RepoGuardian Memory Agent — Tracking patterns since {profile.first_seen[:10]}*
> *Total PRs analysed for @{developer}: {profile.total_prs} | Total findings tracked: {profile.total_findings}*
> *KLH Hackathon 2025 — Powered by RepoGuardian*
"""
    return body


# ─────────────────────────────────────────
# Post Memory Comment to GitHub PR
# ─────────────────────────────────────────

def post_memory_comment(
    repo_name:    str,
    pr_number:    int,
    developer:    str,
    profile:      DeveloperProfile,
    alerts:       list[RecurringAlert],
    findings:     list[Finding],
    health_score: int,
):
    """Post the personalised memory report as a PR comment."""
    try:
        repo = github_client.get_repo(repo_name)
        pr   = repo.get_pull(pr_number)

        body = build_memory_comment(developer, profile, alerts, findings, health_score)
        pr.create_issue_comment(body)
        log.info(f"Memory report posted for @{developer}.")

    except GithubException as e:
        log.error(f"Could not post memory comment: {e}")


# ─────────────────────────────────────────
# Main Agent — called by Orchestrator
# ─────────────────────────────────────────

def run_memory_agent(
    repo_name:    str,
    pr_number:    int,
    findings:     list[Finding],
    health_score: int,
) -> MemoryResult:
    """
    MAIN FUNCTION — called by orchestrator AFTER all other agents finish.

    Usage:
        from tools.memory import run_memory_agent
        result = run_memory_agent("owner/repo", 1, all_findings, score)

    Args:
        repo_name:    GitHub repo in "owner/repo" format
        pr_number:    PR number
        findings:     Combined list of Finding objects from ALL agents
        health_score: Final unified health score from calculate_health_score()

    Returns:
        MemoryResult with .recurring_alerts and .profile_summary
    """
    log.info(f"Memory Agent started — {repo_name} PR #{pr_number}")

    # Step 1 — Identify the PR author
    log.info("Step 1/5 — Getting PR author from GitHub...")
    developer = get_pr_author(repo_name, pr_number)

    # Step 2 — Load existing developer profile
    log.info(f"Step 2/5 — Loading profile for @{developer}...")
    profile = load_profile(developer)
    log.info(
        f"Profile loaded — {profile.total_prs} past PR(s), "
        f"{profile.total_findings} past finding(s)"
    )

    # Step 3 — Update profile with this PR's findings
    log.info("Step 3/5 — Updating developer profile...")
    profile = update_profile(profile, repo_name, pr_number, health_score, findings)

    # Step 4 — Analyse patterns and generate alerts
    log.info("Step 4/5 — Analysing patterns...")
    alerts = analyse_patterns(profile)

    if alerts:
        for alert in alerts:
            log.info(
                f"  [{alert.trend.upper()}] {alert.category} "
                f"— {alert.count} occurrence(s)"
            )
    else:
        log.info("  No recurring patterns detected yet.")

    # Step 5 — Post personalised comment + save profile
    log.info("Step 5/5 — Posting memory report to GitHub PR...")
    post_memory_comment(repo_name, pr_number, developer, profile, alerts, findings, health_score)
    save_profile(profile)

    profile_summary = build_profile_summary(profile)

    log.info(
        f"Memory Agent done — @{developer} | "
        f"{len(alerts)} alert(s) | {profile.total_prs} total PR(s)"
    )

    return MemoryResult(
        developer        = developer,
        recurring_alerts = alerts,
        profile_summary  = profile_summary,
        comment_posted   = True,
    )


# ─────────────────────────────────────────
# Orchestrator-Compatible Wrapper
# ─────────────────────────────────────────

def run_memory_scan(
    repo_name:    str,
    pr_number:    int,
    findings:     list[Finding],
    health_score: int,
) -> MemoryResult:
    """
    Thin wrapper — same pattern as run_dependency_scan() and run_docs_scan().
    Called by orchestrator._run_memory() after all other agents complete.
    """
    return run_memory_agent(repo_name, pr_number, findings, health_score)


# ─────────────────────────────────────────
# CLI — for standalone testing
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("\n========================================")
    print("  RepoGuardian — Memory Agent")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python tools/memory.py <owner/repo> <pr_number>")
        print("Example: python tools/memory.py vamshi/myproject 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = int(sys.argv[2])

    if not os.environ.get("GITHUB_TOKEN"):
        print("ERROR: Missing GITHUB_TOKEN in .env")
        sys.exit(1)

    # For CLI testing — create dummy findings to simulate orchestrator output
    dummy_findings = [
        Finding(agent="security",   severity="high",   message="Hardcoded API key detected.", file="app.py", line=10, suggestion="Use os.getenv()"),
        Finding(agent="docs",       severity="medium",  message="Missing docstring on fetch_data().", file="utils.py", line=24, suggestion="Add docstring"),
        Finding(agent="pr_review",  severity="low",    message="Naming convention issue: use snake_case.", file="models.py", line=5, suggestion="Rename to snake_case"),
    ]

    result = run_memory_agent(repo_arg, pr_arg, dummy_findings, health_score=72)

    print("\n========================================")
    print("  RESULT")
    print("========================================")
    print(f"  Developer      : @{result.developer}")
    print(f"  Alerts found   : {len(result.recurring_alerts)}")
    print(f"  Comment posted : {result.comment_posted}")
    print()

    for i, alert in enumerate(result.recurring_alerts, 1):
        icon = "🔁" if alert.trend == "streak" else "⚠️" if alert.trend == "recurring" else "✅"
        print(f"  {i}. {icon} [{alert.trend.upper()}] {alert.category} — {alert.count}x")
        print(f"     {alert.suggestion}")

    print("\n  Profile Summary:")
    for k, v in result.profile_summary.items():
        print(f"    {k}: {v}")