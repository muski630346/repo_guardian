"""
RepoGuardian — Git Pull Request PDF Report Agent  (Structured Intelligence Edition)
════════════════════════════════════════════════════════════════════════════════════
Fetches ALL comments from a GitHub Pull Request, intelligently
parses RepoGuardian's structured output (scores, security scans,
inline findings), and generates a polished summarized PDF report.

For PRs WITH review comments (normal reviewed PRs):
  • Cover page with live KPI stats
  • Section 1  — Pull Request Details
  • Section 2  — Review Activity Summary (KPI cards + health score
                 distribution table)
  • Section 3  — Review Timeline (scored reviews with band badges)
  • Section 4  — Security Scan Reports (per-scan severity/category
                 breakdown)
  • Section 5  — PR Review Comments (aggregated per review)
  • Section 6  — Inline Code Review Comments (grouped by file)

For PRs WITHOUT review comments (auto-fix / bot PRs):
  • Cover page
  • Section 1  — Pull Request Details
  • Section 2  — Auto-Fix Changes Overview (PR description, issues
                 fixed list, diff stat KPIs, changed files table)
  • Sections 3-7 still appear with appropriate empty-state messages

Install:
    pip install reportlab PyGithub python-dotenv

Usage (CLI):
    python tools/report_git_agent.py <owner/repo> <pr_number>
    python tools/report_git_agent.py muski630346/repo_guardian 5

Usage (from Orchestrator or Dashboard backend):
    from tools.report_git_agent import run_report_git_agent
    pdf_path = run_report_git_agent("owner/repo", 5)

Output:
    reports/git_pr_<number>_report.pdf

.env required:
    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
"""

import os
import re
import sys
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfcanvas

from github import Auth, Github, GithubException
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [REPORT] %(message)s")
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("Missing GITHUB_TOKEN in .env")

github_client = Github(auth=Auth.Token(GITHUB_TOKEN))

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "reports"
)

# ─────────────────────────────────────────────────────────────────────────────
# Brand Palette
# ─────────────────────────────────────────────────────────────────────────────

NAVY         = colors.HexColor("#0B1120")
INDIGO       = colors.HexColor("#4F46E5")
INDIGO_LIGHT = colors.HexColor("#818CF8")
INDIGO_PALE  = colors.HexColor("#EEF2FF")

SURFACE      = colors.HexColor("#F8FAFC")
CARD         = colors.white
BORDER       = colors.HexColor("#E2E8F0")
MUTED        = colors.HexColor("#94A3B8")
TEXT_DARK    = colors.HexColor("#0F172A")
TEXT_BODY    = colors.HexColor("#334155")

GREEN        = colors.HexColor("#16A34A")
GREEN_PALE   = colors.HexColor("#F0FDF4")
AMBER        = colors.HexColor("#D97706")
AMBER_PALE   = colors.HexColor("#FFFBEB")
RED_H        = colors.HexColor("#DC2626")
RED_PALE     = colors.HexColor("#FEF2F2")
PURPLE       = colors.HexColor("#7C3AED")
PURPLE_PALE  = colors.HexColor("#F5F3FF")
TEAL         = colors.HexColor("#0891B2")
TEAL_PALE    = colors.HexColor("#ECFEFF")
ORANGE       = colors.HexColor("#EA580C")

# Score-band colours
BAND_CFG = {
    "EXCELLENT": (GREEN,  GREEN_PALE,  "EXCELLENT",  "85-100"),
    "GOOD":      (TEAL,   TEAL_PALE,   "GOOD",       "70-84"),
    "FAIR":      (AMBER,  AMBER_PALE,  "FAIR",       "50-69"),
    "POOR":      (RED_H,  RED_PALE,    "POOR",       "0-49"),
}

SEVERITY_CFG = {
    "HIGH":   (RED_H,  RED_PALE,  "High"),
    "MEDIUM": (AMBER,  AMBER_PALE,"Medium"),
    "LOW":    (GREEN,  GREEN_PALE,"Low"),
}

# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoredReview:
    """A PR or Full review that carries a numeric score."""
    timestamp:  str
    author:     str
    kind:       str          # "PR Review" | "Security" | "Full Review"
    score:      int
    band:       str          # EXCELLENT / GOOD / FAIR / POOR
    summary:    str


@dataclass
class SecurityScan:
    """Aggregated data for one security scan comment."""
    number:     int
    score:      int
    band:       str
    timestamp:  str
    summary:    str
    high:       int = 0
    medium:     int = 0
    low:        int = 0
    categories: dict = field(default_factory=dict)  # {label: count}


@dataclass
class PRReviewComment:
    """A single PR review block with issue breakdown."""
    timestamp:  str
    author:     str
    score:      int
    summary:    str
    high:       int = 0
    medium:     int = 0
    low:        int = 0


@dataclass
class InlineComment:
    """A single inline code comment."""
    file_path:  str
    line:       int
    severity:   str
    body:       str


@dataclass
class ChangedFile:
    """One file changed in the PR diff."""
    filename:   str
    status:     str   # added / modified / removed / renamed
    additions:  int
    deletions:  int
    changes:    int


@dataclass
class PRReportData:
    repo_name:      str
    pr_number:      int
    pr_title:       str
    pr_author:      str
    pr_branch_from: str
    pr_branch_to:   str
    pr_state:       str
    pr_created:     str
    pr_updated:     str
    generated_at:   str = ""

    # Aggregated intelligence
    total_comments:     int = 0
    pr_review_count:    int = 0
    security_count:     int = 0
    inline_count:       int = 0
    avg_score:          int = 0

    scored_reviews:     list = field(default_factory=list)   # ScoredReview
    security_scans:     list = field(default_factory=list)   # SecurityScan
    pr_reviews:         list = field(default_factory=list)   # PRReviewComment
    inline_comments:    list = field(default_factory=list)   # InlineComment

    health_distribution: dict = field(default_factory=dict)  # band -> count

    # Auto-fix / diff enrichment (populated when PR has no review comments)
    is_autofix:         bool  = False
    pr_body:            str   = ""
    autofix_issues:     list  = field(default_factory=list)  # list[str] — parsed issue bullets
    changed_files:      list  = field(default_factory=list)  # list[ChangedFile]
    diff_additions:     int   = 0
    diff_deletions:     int   = 0
    commits_count:      int   = 0


# ─────────────────────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _score_to_band(score: int) -> str:
    if score >= 85: return "EXCELLENT"
    if score >= 70: return "GOOD"
    if score >= 50: return "FAIR"
    return "POOR"


def _extract_score(body: str) -> int:
    """Return integer score parsed from comment body, or -1 if none found."""
    for pat in [
        r"[Hh]ealth\s*[Ss]core[:\s]+(\d+)/100",
        r"[Ss]core[:\s]+(\d+)/100",
        r"[Ss]ecurity\s*[Ss]core[:\s]+(\d+)/100",
        r"(\d+)/100",
    ]:
        m = re.search(pat, body)
        if m:
            return min(100, max(0, int(m.group(1))))
    return -1


def _extract_severity_counts(body: str) -> dict:
    """Pull High/Medium/Low counts from a structured comment body."""
    counts = {"high": 0, "medium": 0, "low": 0}
    for pat, key in [
        (r"High[^:]*:\s*(\d+)", "high"),
        (r"Medium[^:]*:\s*(\d+)", "medium"),
        (r"Low[^:]*:\s*(\d+)", "low"),
    ]:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            counts[key] = int(m.group(1))
    return counts


def _extract_categories(body: str) -> dict:
    """Extract category name -> count from security scan bodies."""
    cats = {}
    # Look for lines like "OWASP Vulnerability 7" or "Injection Risk 1"
    for m in re.finditer(
        r"(OWASP Vulnerability|Injection Risk|Insecure Pattern|Hardcoded Secret"
        r"|Authentication Flaw|Cryptographic Failure)[^\d]*(\d+)",
        body, re.IGNORECASE
    ):
        label = m.group(1).strip()
        cats[label] = cats.get(label, 0) + int(m.group(2))
    return cats


def _detect_comment_kind(body: str, review_state: str) -> str:
    """Classify a raw GitHub comment as security / pr_review / full_review / inline."""
    b = body.lower()
    if "security score" in b or "owasp" in b or "injection risk" in b \
            or "insecure pattern" in b or "hardcoded secret" in b:
        return "security"
    if "health score" in b or "grade:" in b or "rejected" in b or "rejected" in b:
        return "full_review"
    if "inline comments posted" in b or "code smell" in b or "code duplication" in b \
            or "long functions" in b:
        return "pr_review"
    if "must fix" in b or "should fix" in b or "nice to fix" in b:
        return "pr_review"
    return "pr_review"


def _short_summary(body: str, max_chars: int = 120) -> str:
    """First meaningful sentence from comment body."""
    body = re.sub(r"```[^`]*```", "", body, flags=re.DOTALL)
    body = re.sub(r"`[^`]+`", "", body)
    body = re.sub(r"#{1,6}\s+", "", body)
    body = re.sub(r"\*+", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    first = (body.split(".")[0] + ".").strip()
    if len(first) > max_chars:
        first = first[:max_chars - 3] + "..."
    return first or body[:max_chars]


# ─────────────────────────────────────────────────────────────────────────────
# Inline comment parser (from the dedicated inline-comment thread body)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_inline_comment(body: str, path: str, line: int) -> InlineComment | None:
    """Turn a review comment on a specific file line into an InlineComment."""
    sev = "MEDIUM"
    b_lower = body.lower()
    if any(w in b_lower for w in ["high", "must fix", "critical", "sql injection",
                                   "eval(", "pickle", "command injection", "hardcoded"]):
        sev = "HIGH"
    elif any(w in b_lower for w in ["low", "nice to fix", "minor", "style"]):
        sev = "LOW"

    clean = body.strip()[:250]
    return InlineComment(file_path=path, line=line, severity=sev, body=clean)


# ─────────────────────────────────────────────────────────────────────────────
# GitHub Fetcher + Aggregator
# ─────────────────────────────────────────────────────────────────────────────

def fetch_pr_data(repo_name: str, pr_number: int) -> PRReportData:
    log.info(f"Fetching PR #{pr_number} from {repo_name}...")

    try:
        repo = github_client.get_repo(repo_name)
    except GithubException as e:
        if e.status == 404:
            raise SystemExit(f"\n  ERROR: Repository '{repo_name}' not found.\n") from None
        raise

    try:
        pr = repo.get_pull(pr_number)
    except GithubException as e:
        if e.status == 404:
            raise SystemExit(f"\n  ERROR: PR #{pr_number} not found.\n") from None
        raise

    pr_body_raw = (pr.body or "").strip()

    # Detect auto-fix PRs by branch name or title pattern
    branch_name = pr.head.ref if pr.head else ""
    is_autofix  = (
        "autofix" in branch_name.lower()
        or "auto-fix" in branch_name.lower()
        or "repoguardian/autofix" in branch_name.lower()
        or "auto-fix" in (pr.title or "").lower()
        or "repoguardian: auto-fix" in (pr.title or "").lower()
    )

    # Parse issue bullets from PR body  (lines starting with - or * or numbered)
    autofix_issues = []
    for line in pr_body_raw.splitlines():
        line = line.strip()
        m = re.match(r"^[-*•]\s+(.+)$", line) or re.match(r"^\d+[.)]\s+(.+)$", line)
        if m:
            autofix_issues.append(m.group(1).strip())

    # Fetch changed files for diff summary
    changed_files = []
    diff_add = diff_del = 0
    try:
        for f in pr.get_files():
            changed_files.append(ChangedFile(
                filename  = f.filename or "",
                status    = f.status   or "modified",
                additions = f.additions or 0,
                deletions = f.deletions or 0,
                changes   = f.changes  or 0,
            ))
            diff_add += f.additions or 0
            diff_del += f.deletions or 0
    except Exception as e:
        log.warning(f"  Could not fetch file list: {e}")

    commits_count = 0
    try:
        commits_count = pr.commits or 0
    except Exception:
        pass

    data = PRReportData(
        repo_name      = repo_name,
        pr_number      = pr_number,
        pr_title       = pr.title or "",
        pr_author      = pr.user.login if pr.user else "unknown",
        pr_branch_from = branch_name,
        pr_branch_to   = pr.base.ref if pr.base else "",
        pr_state       = (pr.state or "").upper(),
        pr_created     = pr.created_at.strftime("%Y-%m-%d %H:%M UTC") if pr.created_at else "",
        pr_updated     = pr.updated_at.strftime("%Y-%m-%d %H:%M UTC") if pr.updated_at else "",
        generated_at   = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"),
        is_autofix     = is_autofix,
        pr_body        = pr_body_raw,
        autofix_issues = autofix_issues,
        changed_files  = changed_files,
        diff_additions = diff_add,
        diff_deletions = diff_del,
        commits_count  = commits_count,
    )

    # ── Collect all issue-level comments (general + RepoGuardian reports) ──
    log.info("  Fetching issue comments...")
    all_issue_comments = list(pr.get_issue_comments())

    security_idx = 0
    scores_for_avg = []

    for c in all_issue_comments:
        body   = (c.body or "").strip()
        ts     = c.created_at.strftime("%Y-%m-%d\n%H:%M") if c.created_at else ""
        author = c.user.login if c.user else "unknown"
        score  = _extract_score(body)
        kind   = _detect_comment_kind(body, "")

        if kind == "security":
            security_idx += 1
            sev   = _extract_severity_counts(body)
            cats  = _extract_categories(body)
            band  = _score_to_band(score) if score >= 0 else "FAIR"
            scan  = SecurityScan(
                number    = security_idx,
                score     = score if score >= 0 else 50,
                band      = band,
                timestamp = c.created_at.strftime("%Y-%m-%d %H:%M UTC") if c.created_at else "",
                summary   = _short_summary(body),
                high      = sev["high"],
                medium    = sev["medium"],
                low       = sev["low"],
                categories= cats,
            )
            data.security_scans.append(scan)
            if score >= 0:
                scores_for_avg.append(score)
            data.scored_reviews.append(ScoredReview(
                timestamp = ts,
                author    = author,
                kind      = "Security",
                score     = scan.score,
                band      = band,
                summary   = f"Security Score: {scan.score}/100",
            ))

        else:  # pr_review or full_review
            is_full = kind == "full_review"
            sev     = _extract_severity_counts(body)
            band    = _score_to_band(score) if score >= 0 else "POOR"
            kind_label = "Full Review" if is_full else "PR Review"

            review = PRReviewComment(
                timestamp = c.created_at.strftime("%Y-%m-%d %H:%M UTC") if c.created_at else "",
                author    = author,
                score     = score if score >= 0 else 0,
                summary   = _short_summary(body),
                high      = sev["high"],
                medium    = sev["medium"],
                low       = sev["low"],
            )
            data.pr_reviews.append(review)

            if score >= 0:
                scores_for_avg.append(score)

            data.scored_reviews.append(ScoredReview(
                timestamp  = ts,
                author     = author,
                kind       = kind_label,
                score      = review.score,
                band       = band,
                summary    = (f"Health Score: {review.score}/100 "
                              f"({'REJECTED' if is_full else 'NEEDS WORK' if review.score < 70 else ''}").strip(),
            ))

    # ── Collect review-level comments (formal reviews) ──
    log.info("  Fetching reviews...")
    for r in pr.get_reviews():
        body  = (r.body or "").strip()
        ts    = r.submitted_at.strftime("%Y-%m-%d\n%H:%M") if r.submitted_at else ""
        author = r.user.login if r.user else "unknown"
        if not body:
            continue
        score  = _extract_score(body)
        kind   = _detect_comment_kind(body, r.state or "")
        sev    = _extract_severity_counts(body)
        band   = _score_to_band(score) if score >= 0 else "POOR"
        data.pr_reviews.append(PRReviewComment(
            timestamp = r.submitted_at.strftime("%Y-%m-%d %H:%M UTC") if r.submitted_at else "",
            author    = author,
            score     = score if score >= 0 else 0,
            summary   = _short_summary(body),
            high      = sev["high"],
            medium    = sev["medium"],
            low       = sev["low"],
        ))
        if score >= 0:
            scores_for_avg.append(score)

    # ── Collect inline review comments ──
    log.info("  Fetching inline comments...")
    for c in pr.get_review_comments():
        body  = (c.body or "").strip()
        if not body:
            continue
        path  = c.path or ""
        line  = c.line or c.original_line or 0
        ic    = _parse_inline_comment(body, path, line)
        if ic:
            data.inline_comments.append(ic)

    # ── Compute aggregates ──
    data.total_comments  = (len(data.pr_reviews) + len(data.security_scans)
                            + len(data.inline_comments))
    data.pr_review_count = len(data.pr_reviews)
    data.security_count  = len(data.security_scans)
    data.inline_count    = len(data.inline_comments)
    data.avg_score       = int(sum(scores_for_avg) / len(scores_for_avg)) if scores_for_avg else 0

    # Health score distribution across all scored reviews
    dist = {"EXCELLENT": 0, "GOOD": 0, "FAIR": 0, "POOR": 0}
    for sr in data.scored_reviews:
        dist[sr.band] = dist.get(sr.band, 0) + 1
    data.health_distribution = dist

    log.info(f"  Aggregated: {data.total_comments} total items "
             f"({data.pr_review_count} reviews, {data.security_count} scans, "
             f"{data.inline_count} inline).")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _strip_emoji(text: str) -> str:
    return re.sub(
        r"[\U00010000-\U0010ffff\u2600-\u27BF\u2B00-\u2BFF\uFE00-\uFE0F]",
        "", str(text),
    )

def _safe(text: str) -> str:
    text = _strip_emoji(str(text))
    return (text
        .replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;"))

def _hex(c):
    try:
        h = c.hexval()
        return h[1:] if h.startswith("x") else h
    except Exception:
        return "334155"

def _trunc(s, n=200):
    s = str(s).rstrip()
    return s[:n-3] + "..." if len(s) > n else s


# ─────────────────────────────────────────────────────────────────────────────
# Paragraph Styles
# ─────────────────────────────────────────────────────────────────────────────

def _S(name, **kw):
    return ParagraphStyle(name, **kw)

STYLES = {
    "label":     _S("lbl",  fontSize=8,   fontName="Helvetica-Bold",
                    textColor=MUTED),
    "value":     _S("val",  fontSize=9.5, fontName="Helvetica",
                    textColor=TEXT_BODY, leading=14),
    "body":      _S("bod",  fontSize=9,   fontName="Helvetica",
                    textColor=TEXT_BODY, leading=13),
    "body_bold": _S("bodb", fontSize=9.5, fontName="Helvetica-Bold",
                    textColor=TEXT_DARK),
    "mono":      _S("mon",  fontSize=8,   fontName="Courier",
                    textColor=TEXT_BODY, leading=12,
                    backColor=colors.HexColor("#F0F4F8"),
                    borderPadding=(3,5,3,5), wordWrap="CJK"),
    "th":        _S("th",   fontSize=8,   fontName="Helvetica-Bold",
                    textColor=colors.white),
    "td":        _S("td",   fontSize=8.5, fontName="Helvetica",
                    textColor=TEXT_BODY),
    "td_c":      _S("tdc",  fontSize=8.5, fontName="Helvetica",
                    textColor=TEXT_BODY, alignment=TA_CENTER),
    "td_mono":   _S("tdm",  fontSize=8,   fontName="Courier",
                    textColor=TEXT_BODY),
    "footer":    _S("foot", fontSize=7,   fontName="Helvetica",
                    textColor=MUTED, alignment=TA_CENTER),
    "empty":     _S("emp",  fontSize=9.5, fontName="Helvetica",
                    textColor=MUTED, alignment=TA_CENTER,
                    spaceBefore=8, spaceAfter=8),
    "scan_title": _S("sct", fontSize=9,  fontName="Helvetica-Bold",
                     textColor=TEXT_DARK, leading=13),
    "scan_body":  _S("scb", fontSize=8.5,fontName="Helvetica",
                     textColor=TEXT_BODY, leading=12),
}


# ─────────────────────────────────────────────────────────────────────────────
# Custom Flowables
# ─────────────────────────────────────────────────────────────────────────────

class SectionHeader(Flowable):
    """Numbered section header with badge + full-width background."""
    def __init__(self, number, title, accent=None, width=None):
        super().__init__()
        self.number = number
        self.title  = title
        self.accent = accent or INDIGO
        self._width = width
        self.height = 34

    def wrap(self, aw, ah):
        self._aw = self._width or aw
        return self._aw, self.height

    def draw(self):
        c  = self.canv
        aw = self._aw
        c.setFillColor(SURFACE)
        c.rect(0, 0, aw, self.height, fill=1, stroke=0)
        c.setFillColor(self.accent)
        c.rect(0, 0, 3, self.height, fill=1, stroke=0)
        badge = 20
        bx    = 10
        by    = (self.height - badge) / 2
        c.setFillColor(self.accent)
        c.roundRect(bx, by, badge, badge, 4, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(bx + badge/2, by + 6, str(self.number))
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(bx + badge + 8, 10, self.title)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.line(0, 0, aw, 0)


class KPICard(Flowable):
    """Metric card with accent strip, value, label, and optional sub-label."""
    def __init__(self, value, label, sub="", accent=None, width=80, height=62):
        super().__init__()
        self.value  = value
        self.label  = label
        self.sub    = sub
        self.accent = accent or INDIGO
        self._w     = width
        self._h     = height

    def wrap(self, aw, ah):
        return self._w, self._h

    def draw(self):
        c = self.canv
        W, H = self._w, self._h
        c.setFillColor(CARD)
        c.roundRect(0, 0, W, H, 5, fill=1, stroke=0)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, W, H, 5, fill=0, stroke=1)
        c.setFillColor(self.accent)
        c.roundRect(0, H-4, W, 4, 2, fill=1, stroke=0)
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 17)
        c.drawCentredString(W/2, H/2 + 4, str(self.value))
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawCentredString(W/2, H/2 - 9, self.label.upper())
        if self.sub:
            c.setFillColor(self.accent)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(W/2, 7, str(self.sub))


class BandBadge(Flowable):
    """Coloured pill badge for a health-score band."""
    def __init__(self, band, width=70, height=16):
        super().__init__()
        self.band  = band
        self._w    = width
        self._h    = height

    def wrap(self, aw, ah):
        return self._w, self._h

    def draw(self):
        c = self.canv
        fg, pale, label, _ = BAND_CFG.get(self.band, (MUTED, SURFACE, self.band, ""))
        c.setFillColor(pale)
        c.roundRect(0, 0, self._w, self._h, 4, fill=1, stroke=0)
        c.setFillColor(fg)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(self._w/2, 4, label)


# ─────────────────────────────────────────────────────────────────────────────
# Cover page
# ─────────────────────────────────────────────────────────────────────────────

def draw_cover(canvas, doc, data: PRReportData, generated: str):
    W, H = A4
    c = canvas

    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Diagonal accent
    c.saveState()
    c.setFillColor(colors.HexColor("#1E1B4B"))
    p = c.beginPath()
    p.moveTo(W * 0.45, H); p.lineTo(W, H); p.lineTo(W, H * 0.45); p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.restoreState()

    c.setFillColor(INDIGO)
    c.rect(0, 0, 6, H, fill=1, stroke=0)

    # Logo
    lx, ly = W/2, H * 0.77
    c.setFillColor(INDIGO)
    c.roundRect(lx - 26, ly - 26, 52, 52, 9, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(lx, ly - 8, "RG")

    c.setFillColor(INDIGO_LIGHT)
    c.setFont("Helvetica", 9)
    c.drawCentredString(W/2, H * 0.77 - 40, "REPOGUARDIAN  |  PULL REQUEST INTELLIGENCE")

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(W/2, H * 0.56, "Pull Request Review Report")

    c.setFillColor(INDIGO_LIGHT)
    c.setFont("Helvetica-Bold", 13)
    title = _strip_emoji(data.pr_title)[:60] + ("..." if len(data.pr_title) > 60 else "")
    c.drawCentredString(W/2, H * 0.495, title)

    c.setFillColor(colors.HexColor("#CBD5E1"))
    c.setFont("Helvetica", 10)
    meta = f"#{data.pr_number}  \u00b7  {data.repo_name}  \u00b7  @{data.pr_author}  \u00b7  {data.pr_state}"
    c.drawCentredString(W/2, H * 0.455, _strip_emoji(meta))

    c.setStrokeColor(colors.HexColor("#1E293B"))
    c.setLineWidth(1)
    c.line(36, H * 0.38, W - 36, H * 0.38)

    # Cover KPI boxes
    stats = [
        (str(data.total_comments), "TOTAL"),
        (str(data.pr_review_count),"PR REVIEWS"),
        (str(data.security_count), "SECURITY"),
        (str(data.inline_count),   "INLINE"),
    ]
    box_w, spacing = 78, 96
    stat_y  = H * 0.31
    start_x = W/2 - spacing * 1.5

    for i, (val, lbl) in enumerate(stats):
        bx = start_x + i * spacing - box_w/2
        c.setFillColor(colors.HexColor("#1E293B"))
        c.roundRect(bx, stat_y - 28, box_w, 44, 5, fill=1, stroke=0)
        c.setFillColor(INDIGO_LIGHT)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(bx + box_w/2, stat_y + 4, val)
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + box_w/2, stat_y - 17, lbl)

    # Bottom strip
    c.setFillColor(colors.HexColor("#0D1117"))
    c.rect(0, 0, W, 30, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(22, 11, "CONFIDENTIAL  --  RepoGuardian Analytics  |  KLH Hackathon 2025")
    c.drawRightString(W - 22, 11, f"Generated: {generated}")


class PageDecorator:
    def __init__(self, repo, pr_number):
        self.repo      = repo
        self.pr_number = pr_number

    def __call__(self, canvas, doc):
        canvas.saveState()
        W = A4[0]
        canvas.setStrokeColor(INDIGO)
        canvas.setLineWidth(2)
        canvas.line(15*mm, A4[1] - 12*mm, W - 15*mm, A4[1] - 12*mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(15*mm, A4[1] - 10*mm,
            f"RepoGuardian  |  PR Report  |  {self.repo}  |  PR #{self.pr_number}")
        canvas.drawRightString(W - 15*mm, A4[1] - 10*mm, f"Page {doc.page}")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 10*mm, W - 15*mm, 10*mm)
        canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — PR Details
# ─────────────────────────────────────────────────────────────────────────────

def section_pr_details(data: PRReportData, story: list, pw: float):
    story += [SectionHeader(1, "Pull Request Details", INDIGO), Spacer(1, 8)]

    state_col = GREEN if data.pr_state == "MERGED" else AMBER if data.pr_state == "OPEN" else MUTED
    rows = [
        ("Title",      _safe(data.pr_title)),
        ("Repository", data.repo_name),
        ("PR Number",  f"#{data.pr_number}"),
        ("Author",     f"@{data.pr_author}"),
        ("Branch",     f"{data.pr_branch_from}  ->  {data.pr_branch_to}"),
        ("State",      f'<font color="#{_hex(state_col)}"><b>{data.pr_state}</b></font>'),
        ("Opened",     data.pr_created),
        ("Updated",    data.pr_updated),
        ("Generated",  data.generated_at),
    ]

    tbl_rows = [[Paragraph(f"<b>{k}</b>", STYLES["label"]),
                 Paragraph(v, STYLES["value"])] for k, v in rows]

    t = Table(tbl_rows, colWidths=[pw * 0.22, pw * 0.78])
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(0,-1), SURFACE),
        ("ROWBACKGROUNDS", (1,0),(1,-1), [CARD, SURFACE]),
        ("GRID",           (0,0),(-1,-1), 0.4, BORDER),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
        ("RIGHTPADDING",   (0,0),(-1,-1), 8),
        ("TOPPADDING",     (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
    ]))
    story += [t, Spacer(1, 16)]


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Review Activity Summary
# ─────────────────────────────────────────────────────────────────────────────

def section_summary(data: PRReportData, story: list, pw: float):
    story += [SectionHeader(2, "Review Activity Summary", TEAL), Spacer(1, 10)]

    # KPI cards row
    kpi_w = (pw - 20) / 5
    kpis = [
        KPICard(data.total_comments,  "Total",        accent=INDIGO, width=kpi_w, height=64),
        KPICard(data.pr_review_count, "PR Reviews",   accent=GREEN,  width=kpi_w, height=64),
        KPICard(data.security_count,  "Security Scans",accent=RED_H, width=kpi_w, height=64),
        KPICard(data.inline_count,    "Inline Code",   accent=PURPLE,width=kpi_w, height=64),
        KPICard(data.avg_score,       "Avg Score",     accent=AMBER, width=kpi_w, height=64),
    ]
    row = Table([kpis], colWidths=[kpi_w]*5, rowHeights=[64])
    row.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    story += [row, Spacer(1, 14)]

    # Health score distribution table
    story.append(Paragraph("<b>Health Score Distribution</b>", STYLES["body_bold"]))
    story.append(Spacer(1, 5))

    total_scored = sum(data.health_distribution.values()) or 1
    dist_rows = [[
        Paragraph("Band",  STYLES["th"]),
        Paragraph("Range", STYLES["th"]),
        Paragraph("Count", STYLES["th"]),
        Paragraph("Pct",   STYLES["th"]),
    ]]
    band_order = ["EXCELLENT", "GOOD", "FAIR", "POOR"]
    band_ranges = {"EXCELLENT": "85-100", "GOOD": "70-84", "FAIR": "50-69", "POOR": "0-49"}
    for band in band_order:
        fg, pale, label, rng = BAND_CFG[band]
        cnt = data.health_distribution.get(band, 0)
        pct = int(cnt / total_scored * 100)
        dist_rows.append([
            Paragraph(f'<font color="#{_hex(fg)}"><b>{label}</b></font>', STYLES["td"]),
            Paragraph(rng,         STYLES["td_c"]),
            Paragraph(str(cnt),    STYLES["td_c"]),
            Paragraph(f"{pct}%",   STYLES["td_c"]),
        ])

    dt = Table(dist_rows, colWidths=[pw*0.35, pw*0.20, pw*0.22, pw*0.23], repeatRows=1)
    dt.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),   TEAL),
        ("ROWBACKGROUNDS", (0,1),(-1,-1),  [CARD, SURFACE]),
        ("GRID",           (0,0),(-1,-1),  0.3, BORDER),
        ("LEFTPADDING",    (0,0),(-1,-1),  6),
        ("TOPPADDING",     (0,0),(-1,-1),  4),
        ("BOTTOMPADDING",  (0,0),(-1,-1),  4),
        ("VALIGN",         (0,0),(-1,-1),  "MIDDLE"),
    ]))
    story += [dt, Spacer(1, 16)]


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Review Timeline
# ─────────────────────────────────────────────────────────────────────────────

def section_timeline(data: PRReportData, story: list, pw: float):
    scored = [sr for sr in data.scored_reviews if sr.score >= 0]
    story += [
        SectionHeader(3, f"Review Timeline  ({len(scored)} scored reviews)", INDIGO),
        Spacer(1, 8),
    ]

    if not scored:
        story.append(Paragraph("No scored reviews found.", STYLES["empty"]))
        story.append(Spacer(1, 16))
        return

    header = [
        Paragraph("Time",    STYLES["th"]),
        Paragraph("Author",  STYLES["th"]),
        Paragraph("Type",    STYLES["th"]),
        Paragraph("Score",   STYLES["th"]),
        Paragraph("Band",    STYLES["th"]),
        Paragraph("Summary", STYLES["th"]),
    ]
    tbl_rows = [header]

    for sr in scored:
        fg, pale, label, _ = BAND_CFG.get(sr.band, (MUTED, SURFACE, sr.band, ""))
        score_str = f'<font color="#{_hex(fg)}"><b>{sr.score}</b></font>'
        band_str  = f'<font color="#{_hex(fg)}"><b>{label}</b></font>'
        tbl_rows.append([
            Paragraph(_safe(sr.timestamp), STYLES["td"]),
            Paragraph(_safe(sr.author),    STYLES["td"]),
            Paragraph(_safe(sr.kind),      STYLES["td"]),
            Paragraph(score_str,           STYLES["td_c"]),
            Paragraph(band_str,            STYLES["td_c"]),
            Paragraph(_safe(_trunc(sr.summary, 80)), STYLES["td"]),
        ])

    col_w = [pw*0.14, pw*0.13, pw*0.12, pw*0.07, pw*0.11, pw*0.43]
    t = Table(tbl_rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),   INDIGO),
        ("ROWBACKGROUNDS", (0,1),(-1,-1),  [CARD, SURFACE]),
        ("GRID",           (0,0),(-1,-1),  0.3, BORDER),
        ("LEFTPADDING",    (0,0),(-1,-1),  5),
        ("TOPPADDING",     (0,0),(-1,-1),  3),
        ("BOTTOMPADDING",  (0,0),(-1,-1),  3),
        ("VALIGN",         (0,0),(-1,-1),  "MIDDLE"),
        ("FONTSIZE",       (0,1),(-1,-1),  8),
    ]))
    story += [t, Spacer(1, 16)]


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Security Scan Reports
# ─────────────────────────────────────────────────────────────────────────────

def section_security(data: PRReportData, story: list, pw: float):
    story += [
        SectionHeader(4, f"Security Scan Reports  ({len(data.security_scans)} scans)", RED_H),
        Spacer(1, 8),
    ]

    if not data.security_scans:
        story.append(Paragraph("No security scans found.", STYLES["empty"]))
        story.append(Spacer(1, 16))
        return

    for scan in data.security_scans:
        fg, pale, label, _ = BAND_CFG.get(scan.band, (MUTED, SURFACE, scan.band, ""))
        total_issues = scan.high + scan.medium + scan.low

        # Scan header row
        header_data = [[
            Paragraph(
                f'<b>Security Scan #{scan.number}</b>  '
                f'<font color="#{_hex(fg)}">{scan.score}/100 -- {label}</font>  '
                f'  {scan.timestamp}',
                STYLES["scan_title"]
            ),
        ]]
        ht = Table(header_data, colWidths=[pw])
        ht.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), pale),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, fg),
        ]))

        # Summary text
        summary_para = Paragraph(_safe(_trunc(scan.summary, 200)), STYLES["scan_body"])

        # Severity breakdown
        sev_rows = [[
            Paragraph("Severity", STYLES["th"]),
            Paragraph("Count",    STYLES["th"]),
        ]]
        for sev_label, count, sev_color in [
            ("High (block merge)",       scan.high,   RED_H),
            ("Medium (fix before release)", scan.medium, AMBER),
            ("Low (hardening)",          scan.low,    GREEN),
            ("Total",                    total_issues, INDIGO),
        ]:
            col = f'<font color="#{_hex(sev_color)}"><b>{count}</b></font>'
            sev_rows.append([
                Paragraph(sev_label, STYLES["td"]),
                Paragraph(col,       STYLES["td_c"]),
            ])

        st = Table(sev_rows, colWidths=[pw*0.55, pw*0.20], repeatRows=1)
        st.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),  RED_H),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [CARD, SURFACE]),
            ("GRID",           (0,0),(-1,-1), 0.3, BORDER),
            ("LEFTPADDING",    (0,0),(-1,-1), 6),
            ("TOPPADDING",     (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
            ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ]))

        # Category breakdown (if any)
        cat_table = None
        if scan.categories:
            cat_rows = [[
                Paragraph("Category", STYLES["th"]),
                Paragraph("Count",    STYLES["th"]),
            ]]
            for cat, cnt in scan.categories.items():
                cat_rows.append([
                    Paragraph(_safe(cat), STYLES["td"]),
                    Paragraph(str(cnt),   STYLES["td_c"]),
                ])
            cat_table = Table(cat_rows, colWidths=[pw*0.55, pw*0.20], repeatRows=1)
            cat_table.setStyle(TableStyle([
                ("BACKGROUND",     (0,0),(-1,0),  ORANGE),
                ("ROWBACKGROUNDS", (0,1),(-1,-1), [CARD, SURFACE]),
                ("GRID",           (0,0),(-1,-1), 0.3, BORDER),
                ("LEFTPADDING",    (0,0),(-1,-1), 6),
                ("TOPPADDING",     (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
                ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
            ]))

        block = [
            ht, Spacer(1, 4),
            summary_para, Spacer(1, 6),
        ]

        # Side-by-side severity + category
        inner_cols = [st]
        inner_widths = [pw * 0.75]
        if cat_table:
            inner_cols = [[st, Spacer(1, 4), cat_table]]
            inner_widths = [pw * 0.75]
            side = Table([[st, Spacer(0.5, 0), cat_table]],
                         colWidths=[pw*0.48, 6, pw*0.44])
            side.setStyle(TableStyle([
                ("VALIGN", (0,0),(-1,-1), "TOP"),
                ("LEFTPADDING", (0,0),(-1,-1), 0),
                ("RIGHTPADDING",(0,0),(-1,-1), 0),
            ]))
            block.append(side)
        else:
            block.append(st)

        block += [Spacer(1, 12), HRFlowable(width="100%", thickness=0.3, color=BORDER), Spacer(1, 8)]
        story.append(KeepTogether(block))

    story.append(Spacer(1, 8))


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — PR Review Comments
# ─────────────────────────────────────────────────────────────────────────────

def section_pr_reviews(data: PRReportData, story: list, pw: float):
    story += [
        SectionHeader(5, f"PR Review Comments  ({len(data.pr_reviews)} reviews)", GREEN),
        Spacer(1, 8),
    ]

    if not data.pr_reviews:
        story.append(Paragraph("No PR review comments found.", STYLES["empty"]))
        story.append(Spacer(1, 16))
        return

    for rev in data.pr_reviews:
        fg, pale, label, _ = BAND_CFG.get(_score_to_band(rev.score), (MUTED, SURFACE, "", ""))
        total_issues = rev.high + rev.medium + rev.low
        score_txt = (f'<font color="#{_hex(fg)}"><b>{rev.score}/100</b></font>'
                     if rev.score >= 0 else "—")

        hdr = [[
            Paragraph(
                f'PR REVIEW  @{_safe(rev.author)}  {_safe(rev.timestamp)}  {score_txt}',
                STYLES["scan_title"]
            )
        ]]
        ht = Table(hdr, colWidths=[pw])
        ht.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), pale),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, fg),
        ]))

        body_para = Paragraph(_safe(_trunc(rev.summary, 200)), STYLES["scan_body"])

        sev_rows = [[Paragraph("Severity", STYLES["th"]), Paragraph("Count", STYLES["th"])]]
        for lbl, cnt, col in [
            ("High (must fix)",    rev.high,   RED_H),
            ("Medium (should fix)",rev.medium, AMBER),
            ("Low (nice to fix)",  rev.low,    GREEN),
            ("Total",              total_issues, INDIGO),
        ]:
            sev_rows.append([
                Paragraph(lbl, STYLES["td"]),
                Paragraph(f'<font color="#{_hex(col)}"><b>{cnt}</b></font>', STYLES["td_c"]),
            ])
        st = Table(sev_rows, colWidths=[pw*0.55, pw*0.20], repeatRows=1)
        st.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),  GREEN),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [CARD, SURFACE]),
            ("GRID",           (0,0),(-1,-1), 0.3, BORDER),
            ("LEFTPADDING",    (0,0),(-1,-1), 6),
            ("TOPPADDING",     (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
            ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ]))

        block = [
            ht, Spacer(1, 4), body_para, Spacer(1, 6), st,
            Spacer(1, 10), HRFlowable(width="100%", thickness=0.3, color=BORDER), Spacer(1, 8),
        ]
        story.append(KeepTogether(block[:4]))   # keep header + body together
        story.extend(block[4:])

    story.append(Spacer(1, 8))


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — Inline Code Review Comments
# ─────────────────────────────────────────────────────────────────────────────

def section_inline(data: PRReportData, story: list, pw: float):
    story += [
        SectionHeader(6, f"Inline Code Review Comments  ({data.inline_count} comments)", PURPLE),
        Spacer(1, 8),
    ]

    if not data.inline_comments:
        story.append(Paragraph("No inline comments found.", STYLES["empty"]))
        story.append(Spacer(1, 16))
        return

    # Group by file
    file_map: dict[str, list[InlineComment]] = defaultdict(list)
    for ic in data.inline_comments:
        file_map[ic.file_path or "unknown"].append(ic)

    for fp, comments in sorted(file_map.items()):
        story.append(Paragraph(
            f'<font color="#{_hex(PURPLE)}"><b>File: {_safe(fp)}  ({len(comments)} comments)</b></font>',
            STYLES["body_bold"],
        ))
        story.append(Spacer(1, 4))

        header = [
            Paragraph("Line",     STYLES["th"]),
            Paragraph("Severity", STYLES["th"]),
            Paragraph("Comment",  STYLES["th"]),
        ]
        tbl_rows = [header]
        for ic in sorted(comments, key=lambda x: x.line):
            fg, pale, sev_label = SEVERITY_CFG.get(ic.severity, (MUTED, SURFACE, ic.severity))
            sev_str = f'<font color="#{_hex(fg)}"><b>{sev_label}</b></font>'
            tbl_rows.append([
                Paragraph(str(ic.line) if ic.line else "—", STYLES["td_c"]),
                Paragraph(sev_str, STYLES["td_c"]),
                Paragraph(_safe(_trunc(ic.body, 160)), STYLES["td"]),
            ])

        ft = Table(tbl_rows, colWidths=[pw*0.07, pw*0.12, pw*0.81], repeatRows=1)
        ft.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),   PURPLE),
            ("ROWBACKGROUNDS", (0,1),(-1,-1),  [CARD, SURFACE]),
            ("GRID",           (0,0),(-1,-1),  0.3, BORDER),
            ("LEFTPADDING",    (0,0),(-1,-1),  5),
            ("TOPPADDING",     (0,0),(-1,-1),  3),
            ("BOTTOMPADDING",  (0,0),(-1,-1),  3),
            ("VALIGN",         (0,0),(-1,-1),  "TOP"),
            ("FONTSIZE",       (0,1),(-1,-1),  8),
        ]))
        story += [ft, Spacer(1, 12)]

    story.append(Spacer(1, 8))


# ─────────────────────────────────────────────────────────────────────────────
# Section 2b — Changes Overview  (auto-fix / zero-comment PRs)
# ─────────────────────────────────────────────────────────────────────────────

def section_changes(data: PRReportData, story: list, pw: float, sec_num: int = 2):
    """
    Shown instead of (or before) the empty review sections when a PR has no
    review comments — e.g. bot-generated auto-fix branches.
    Renders: PR description, issues fixed list, diff stat KPI row, changed files table.
    """
    label = "Auto-Fix Changes Overview" if data.is_autofix else "Changes Overview"
    story += [SectionHeader(sec_num, label, INDIGO), Spacer(1, 10)]

    # ── PR type badge ──────────────────────────────────────────────────────
    if data.is_autofix:
        badge_text = (
            "This is a RepoGuardian auto-fix pull request. It was created automatically "
            "to resolve issues identified during a prior PR review. No human review "
            "comments exist on this PR."
        )
        badge_rows = [[Paragraph(badge_text, STYLES["body"])]]
        bt = Table(badge_rows, colWidths=[pw])
        bt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), INDIGO_PALE),
            ("LINEBEFOERE",   (0,0),(-1,-1), 3, INDIGO),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ]))
        story += [bt, Spacer(1, 10)]

    # ── PR description / body ──────────────────────────────────────────────
    if data.pr_body:
        story.append(Paragraph("<b>PR Description</b>", STYLES["body_bold"]))
        story.append(Spacer(1, 4))
        # Render non-bullet lines as body text
        for line in data.pr_body.splitlines():
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 3))
                continue
            # Skip lines that are already captured as issue bullets
            if re.match(r"^[-*•]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
                continue
            story.append(Paragraph(_safe(_trunc(stripped, 200)), STYLES["body"]))
        story.append(Spacer(1, 10))

    # ── Issues fixed list ──────────────────────────────────────────────────
    if data.autofix_issues:
        story.append(Paragraph(
            f"<b>Issues Fixed  ({len(data.autofix_issues)})</b>", STYLES["body_bold"]
        ))
        story.append(Spacer(1, 5))
        issue_rows = [[
            Paragraph("#",     STYLES["th"]),
            Paragraph("Issue", STYLES["th"]),
        ]]
        for i, issue in enumerate(data.autofix_issues, 1):
            issue_rows.append([
                Paragraph(str(i), STYLES["td_c"]),
                Paragraph(_safe(_trunc(issue, 200)), STYLES["td"]),
            ])
        it = Table(issue_rows, colWidths=[pw * 0.07, pw * 0.93], repeatRows=1)
        it.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),   INDIGO),
            ("ROWBACKGROUNDS", (0,1),(-1,-1),  [CARD, SURFACE]),
            ("GRID",           (0,0),(-1,-1),  0.3, BORDER),
            ("LEFTPADDING",    (0,0),(-1,-1),  6),
            ("TOPPADDING",     (0,0),(-1,-1),  4),
            ("BOTTOMPADDING",  (0,0),(-1,-1),  4),
            ("VALIGN",         (0,0),(-1,-1),  "MIDDLE"),
        ]))
        story += [it, Spacer(1, 14)]

    # ── Diff stat KPI row ──────────────────────────────────────────────────
    kpi_w = (pw - 20) / 4
    kpis = [
        KPICard(len(data.changed_files), "Files Changed",  accent=INDIGO,  width=kpi_w, height=64),
        KPICard(data.diff_additions,     "Lines Added",    accent=GREEN,   width=kpi_w, height=64),
        KPICard(data.diff_deletions,     "Lines Removed",  accent=RED_H,   width=kpi_w, height=64),
        KPICard(data.commits_count,      "Commits",        accent=PURPLE,  width=kpi_w, height=64),
    ]
    kpi_row = Table([kpis], colWidths=[kpi_w]*4, rowHeights=[64])
    kpi_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    story += [kpi_row, Spacer(1, 14)]

    # ── Changed files table ────────────────────────────────────────────────
    if data.changed_files:
        story.append(Paragraph("<b>Changed Files</b>", STYLES["body_bold"]))
        story.append(Spacer(1, 5))

        STATUS_COLOR = {
            "added":    GREEN,
            "modified": AMBER,
            "removed":  RED_H,
            "renamed":  TEAL,
        }
        file_rows = [[
            Paragraph("File",      STYLES["th"]),
            Paragraph("Status",    STYLES["th"]),
            Paragraph("+Added",    STYLES["th"]),
            Paragraph("-Removed",  STYLES["th"]),
            Paragraph("Changes",   STYLES["th"]),
        ]]
        for cf in sorted(data.changed_files, key=lambda x: x.filename):
            sc = STATUS_COLOR.get(cf.status.lower(), MUTED)
            status_str = f'<font color="#{_hex(sc)}"><b>{cf.status.upper()}</b></font>'
            add_str    = f'<font color="#{_hex(GREEN)}">+{cf.additions}</font>'
            del_str    = f'<font color="#{_hex(RED_H)}">-{cf.deletions}</font>'
            file_rows.append([
                Paragraph(_safe(cf.filename), STYLES["td_mono"]),
                Paragraph(status_str,         STYLES["td_c"]),
                Paragraph(add_str,            STYLES["td_c"]),
                Paragraph(del_str,            STYLES["td_c"]),
                Paragraph(str(cf.changes),    STYLES["td_c"]),
            ])

        ft = Table(
            file_rows,
            colWidths=[pw*0.52, pw*0.12, pw*0.12, pw*0.12, pw*0.12],
            repeatRows=1,
        )
        ft.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),   PURPLE),
            ("ROWBACKGROUNDS", (0,1),(-1,-1),  [CARD, SURFACE]),
            ("GRID",           (0,0),(-1,-1),  0.3, BORDER),
            ("LEFTPADDING",    (0,0),(-1,-1),  5),
            ("TOPPADDING",     (0,0),(-1,-1),  3),
            ("BOTTOMPADDING",  (0,0),(-1,-1),  3),
            ("VALIGN",         (0,0),(-1,-1),  "MIDDLE"),
            ("FONTSIZE",       (0,1),(-1,-1),  8),
        ]))
        story += [ft, Spacer(1, 16)]
    else:
        story.append(Paragraph("No file changes available.", STYLES["empty"]))
        story.append(Spacer(1, 16))


# ─────────────────────────────────────────────────────────────────────────────
# PDF Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_pdf(data: PRReportData, output_path: str) -> str:
    parent = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(parent, exist_ok=True)

    MARGIN = 18 * mm
    PAGE_W = A4[0] - 2 * MARGIN

    decorator = PageDecorator(data.repo_name, data.pr_number)
    generated = datetime.now().strftime("%d %b %Y  %H:%M UTC")

    doc = SimpleDocTemplate(
        output_path,
        pagesize        = A4,
        leftMargin      = MARGIN,
        rightMargin     = MARGIN,
        topMargin       = 22 * mm,
        bottomMargin    = 15 * mm,
        title           = f"RepoGuardian Report — PR #{data.pr_number}",
        author          = "RepoGuardian",
        subject         = data.pr_title,
    )

    story = []

    def on_first_page(c, d):
        draw_cover(c, d, data, generated)

    story.append(Spacer(1, 1))
    story.append(PageBreak())

    has_reviews = bool(
        data.pr_reviews or data.security_scans
        or data.inline_comments or data.scored_reviews
    )

    section_pr_details(data, story, PAGE_W)

    if has_reviews:
        # Normal review-heavy PR: full structured sections
        section_summary(data, story, PAGE_W)
        section_timeline(data, story, PAGE_W)
        section_security(data, story, PAGE_W)
        section_pr_reviews(data, story, PAGE_W)
        section_inline(data, story, PAGE_W)
    else:
        # No comments (auto-fix PR or brand-new PR): show changes overview
        section_changes(data, story, PAGE_W, sec_num=2)
        # Still emit the review sections so the report structure is consistent,
        # but they will cleanly show "nothing found" messages.
        section_summary(data, story, PAGE_W)
        section_timeline(data, story, PAGE_W)
        section_security(data, story, PAGE_W)
        section_pr_reviews(data, story, PAGE_W)
        section_inline(data, story, PAGE_W)

    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"RepoGuardian Pull Request Report  |  {data.repo_name}  PR #{data.pr_number}  |  "
        f"Generated {generated}  |  KLH Hackathon 2025  |  Confidential",
        STYLES["footer"],
    ))

    doc.build(story, onFirstPage=on_first_page, onLaterPages=decorator)
    log.info(f"PDF written: {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_report_git_agent(repo_name: str, pr_number: int, output_dir: str = None) -> str:
    out_dir  = output_dir or REPORTS_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"git_pr_{pr_number}_report.pdf")
    log.info(f"Git Report Agent starting — {repo_name} PR #{pr_number}")
    print(f"[report_git_agent] output path: {out_path}", flush=True)
    data     = fetch_pr_data(repo_name, pr_number)
    pdf_path = build_pdf(data, out_path)
    print(f"[report_git_agent] PDF written: {pdf_path}", flush=True)
    log.info(f"Done — {pdf_path}")
    return pdf_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  RepoGuardian — Git PR PDF Report Agent")
    print("=" * 60 + "\n")

    if len(sys.argv) < 3:
        print("Usage:   python tools/report_git_agent.py <owner/repo> <pr_number>")
        print("Example: python tools/report_git_agent.py muski630346/repo_guardian 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = sys.argv[2]

    if "/" not in repo_arg or len(repo_arg.split("/")) != 2:
        print(f"  ERROR: '{repo_arg}' is not a valid repo (format: owner/repo)")
        sys.exit(1)

    try:
        pr_num = int(pr_arg)
        if pr_num < 1: raise ValueError
    except ValueError:
        print(f"  ERROR: '{pr_arg}' is not a valid PR number.")
        sys.exit(1)

    out_dir = sys.argv[3] if len(sys.argv) > 3 else None
    pdf     = run_report_git_agent(repo_arg, pr_num, output_dir=out_dir)

    print(f"\n  PDF generated: {pdf}")
    print(f"  Repo : {repo_arg}")
    print(f"  PR # : {pr_num}")
    print("=" * 60)