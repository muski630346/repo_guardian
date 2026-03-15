"""
RepoGuardian — PDF Report Agent
Generates a full developer performance report from memory_store.json.
Light theme — clean white background, dark text, fully print-ready.

Usage:
    python tools/report_agent.py                          # all developers
    python tools/report_agent.py --user codewithVamshi5   # one developer
    python tools/report_agent.py --user codewithVamshi5 --output my_report.pdf

Install:
    pip install reportlab matplotlib
"""

import os
import sys
import json
import logging
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [REPORT] %(message)s")
log = logging.getLogger(__name__)

DB_DIR      = Path(__file__).parent.parent / "db"
MEMORY_PATH = DB_DIR / "memory_store.json"
OUTPUT_DIR  = Path(__file__).parent.parent / "reports"

# ── Light theme colour palette ────────────────────────────────────────────────
# Backgrounds
C_WHITE       = colors.white
C_PAGE_BG     = colors.white
C_CARD_BG     = colors.HexColor("#f8fafc")      # very light gray card
C_HEADER_BG   = colors.HexColor("#1e3a5f")      # dark navy — header strip only
C_ACCENT_BG   = colors.HexColor("#eff6ff")      # light blue tint

# Text — all dark for maximum readability
C_TITLE       = colors.HexColor("#0f172a")      # near-black
C_HEADING     = colors.HexColor("#1e293b")      # dark slate
C_BODY        = colors.HexColor("#334155")      # slate-700
C_MUTED       = colors.HexColor("#64748b")      # slate-500
C_SUBTLE      = colors.HexColor("#94a3b8")      # slate-400

# Accent / data colours (used only for charts and badges)
C_BLUE        = colors.HexColor("#2563eb")
C_GREEN       = colors.HexColor("#16a34a")
C_AMBER       = colors.HexColor("#d97706")
C_RED         = colors.HexColor("#dc2626")
C_PURPLE      = colors.HexColor("#7c3aed")
C_ORANGE      = colors.HexColor("#ea580c")
C_TEAL        = colors.HexColor("#0891b2")

# Borders
C_BORDER      = colors.HexColor("#e2e8f0")
C_BORDER_DARK = colors.HexColor("#cbd5e1")

# Severity colours
SEV_COLORS = {
    "high":   "#dc2626",
    "medium": "#d97706",
    "low":    "#2563eb",
}

AGENT_COLORS_HEX = {
    "pr_review":  "#2563eb",
    "security":   "#dc2626",
    "dependency": "#ea580c",
    "complexity": "#7c3aed",
    "docs":       "#16a34a",
    "memory":     "#64748b",
    "autofix":    "#0891b2",
}

AGENT_LABELS = {
    "pr_review":  "PR Review",
    "security":   "Security",
    "dependency": "Dependency",
    "complexity": "Code Smell",
    "docs":       "Docs",
    "memory":     "Memory",
    "autofix":    "Auto-Fix",
}

PAGE_W = A4[0] - 60   # usable width with 30pt margins each side


# ─────────────────────────────────────────
# Data Loading + Processing
# ─────────────────────────────────────────

def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        log.error(f"Memory store not found: {MEMORY_PATH}")
        return {}
    with open(MEMORY_PATH) as f:
        return json.load(f)


def extract_findings(profile: dict) -> list:
    findings = []
    for pr in profile.get("pr_history", []):
        for f in pr.get("findings", []):
            f2 = dict(f)
            f2["pr_number"] = pr.get("pr_number")
            f2["pr_score"]  = pr.get("score", 0)
            f2["timestamp"] = pr.get("timestamp", "")
            findings.append(f2)
    return findings


def process_profile(username: str, profile: dict) -> dict:
    pr_history   = profile.get("pr_history", [])
    all_findings = extract_findings(profile)

    scores    = [pr.get("score", 0) for pr in pr_history]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    if len(scores) >= 2:
        trend = "Improving" if scores[-1] > scores[0] else "Declining" if scores[-1] < scores[0] else "Stable"
    else:
        trend = "New Developer"

    sev_counts = {"high": 0, "medium": 0, "low": 0}
    for f in all_findings:
        s = f.get("severity", "low")
        sev_counts[s] = sev_counts.get(s, 0) + 1

    agent_counts = defaultdict(int)
    agent_sev    = defaultdict(lambda: {"high": 0, "medium": 0, "low": 0})
    for f in all_findings:
        a = f.get("agent", "unknown")
        s = f.get("severity", "low")
        agent_counts[a] += 1
        agent_sev[a][s] += 1

    category_counts = defaultdict(int)
    for f in all_findings:
        for cat in f.get("categories", [f.get("agent", "unknown")]):
            category_counts[cat] += 1

    file_counts = defaultdict(int)
    file_sev    = defaultdict(lambda: {"high": 0, "medium": 0, "low": 0})
    for f in all_findings:
        fname = f.get("file", "unknown")
        s     = f.get("severity", "low")
        file_counts[fname] += 1
        file_sev[fname][s] += 1

    score_trend = [
        {"run": f"Run {i+1}", "score": pr.get("score", 0), "total": len(pr.get("findings", []))}
        for i, pr in enumerate(pr_history)
    ]

    recurring = [
        {"category": cat, "count": count}
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        if count >= 3 and cat not in {"security", "pr_review", "dependency", "docs", "complexity"}
    ][:8]

    top_files     = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    high_findings = sorted(
        [f for f in all_findings if f.get("severity") == "high"],
        key=lambda x: x.get("timestamp", ""), reverse=True
    )[:10]

    return {
        "username":        username,
        "total_prs":       profile.get("total_prs", 0),
        "total_findings":  len(all_findings),
        "avg_score":       avg_score,
        "latest_score":    scores[-1] if scores else 0,
        "trend":           trend,
        "first_seen":      profile.get("first_seen", "")[:10],
        "last_seen":       profile.get("last_seen", "")[:10],
        "scores":          scores,
        "score_trend":     score_trend,
        "sev_counts":      sev_counts,
        "agent_counts":    dict(agent_counts),
        "agent_sev":       {k: dict(v) for k, v in agent_sev.items()},
        "category_counts": dict(category_counts),
        "file_counts":     dict(file_counts),
        "file_sev":        {k: dict(v) for k, v in file_sev.items()},
        "top_files":       top_files,
        "recurring":       recurring,
        "high_findings":   high_findings,
        "all_findings":    all_findings,
    }


# ─────────────────────────────────────────
# Chart Helpers — light theme
# ─────────────────────────────────────────

CHART_BG   = "#ffffff"
GRID_COLOR = "#e2e8f0"
TEXT_COLOR = "#334155"
TICK_COLOR = "#64748b"
SPINE_CLR  = "#cbd5e1"

def _fig(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=TICK_COLOR, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE_CLR)
    return fig, ax


def _save(fig, tag: str) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=f"_{tag}.png", delete=False)
    fig.savefig(tmp.name, dpi=150, bbox_inches="tight",
                facecolor=CHART_BG, edgecolor="none")
    plt.close(fig)
    return tmp.name


def chart_score_trend(data: dict) -> str:
    runs   = [d["run"]   for d in data["score_trend"]]
    scores = [d["score"] for d in data["score_trend"]]
    if not runs:
        return None

    fig, ax = _fig(7.5, 3.0)
    color   = "#16a34a" if data["avg_score"] >= 65 else "#dc2626"

    ax.plot(runs, scores, color=color, linewidth=2.5, marker="o",
            markersize=7, markerfacecolor=color,
            markeredgecolor="#ffffff", markeredgewidth=2)
    ax.fill_between(runs, scores, alpha=0.08, color=color)

    ax.axhline(85, color="#16a34a", linewidth=0.8, linestyle="--", alpha=0.6, label="Good (85)")
    ax.axhline(65, color="#d97706", linewidth=0.8, linestyle="--", alpha=0.6, label="Acceptable (65)")

    ax.set_ylim(0, 110)
    ax.set_ylabel("Health Score", color=TEXT_COLOR, fontsize=9)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.6)
    ax.legend(fontsize=8, labelcolor=TEXT_COLOR, facecolor=CHART_BG,
              edgecolor=SPINE_CLR, framealpha=1)

    for run, score in zip(runs, scores):
        ax.annotate(str(score), (run, score), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=8,
                    color=color, fontweight="bold")

    plt.tight_layout()
    return _save(fig, "score_trend")


def chart_severity_pie(data: dict) -> str:
    sev  = data["sev_counts"]
    vals = [sev.get("high",0), sev.get("medium",0), sev.get("low",0)]
    lbs  = ["High", "Medium", "Low"]
    cols = ["#dc2626", "#d97706", "#2563eb"]

    filtered = [(v,l,c) for v,l,c in zip(vals,lbs,cols) if v>0]
    if not filtered:
        return None
    vals, lbs, cols = zip(*filtered)

    fig, ax = plt.subplots(figsize=(4.2, 3.5))
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)

    wedges, texts, autotexts = ax.pie(
        vals, labels=lbs, colors=cols, autopct="%1.0f%%",
        startangle=90,
        wedgeprops={"edgecolor": "#ffffff", "linewidth": 2},
        pctdistance=0.78,
    )
    for t in texts:
        t.set_color(TEXT_COLOR)
        t.set_fontsize(9)
        t.set_fontweight("bold")
    for at in autotexts:
        at.set_color("#ffffff")
        at.set_fontsize(8)
        at.set_fontweight("bold")

    centre = plt.Circle((0,0), 0.5, fc=CHART_BG)
    ax.add_patch(centre)
    total = sum(vals)
    ax.text(0, 0.05,  str(total),   ha="center", va="center",
            color=TEXT_COLOR, fontsize=14, fontweight="bold")
    ax.text(0, -0.18, "total",      ha="center", va="center",
            color=TICK_COLOR, fontsize=8)

    plt.tight_layout()
    return _save(fig, "sev_pie")


def chart_agent_breakdown(data: dict) -> str:
    ac = data["agent_counts"]
    if not ac:
        return None

    agents = list(ac.keys())
    counts = [ac[a] for a in agents]
    labels = [AGENT_LABELS.get(a, a) for a in agents]
    cols   = [AGENT_COLORS_HEX.get(a, "#64748b") for a in agents]

    fig, ax = _fig(7.0, max(2.5, len(agents)*0.55))

    bars = ax.barh(labels, counts, color=cols, alpha=0.85, height=0.55)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                str(count), va="center", ha="left",
                color=TEXT_COLOR, fontsize=9, fontweight="bold")

    ax.set_xlabel("Total Findings", color=TEXT_COLOR, fontsize=9)
    ax.tick_params(colors=TICK_COLOR, labelsize=9)
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.6)
    ax.invert_yaxis()

    plt.tight_layout()
    return _save(fig, "agents")


def chart_radar(data: dict) -> str:
    cat = data["category_counts"]
    dimensions = [
        ("Security",    max(0, 100 - cat.get("security",0)*5   - cat.get("owasp",0)*3)),
        ("Code Review", max(0, 100 - cat.get("logic",0)*2      - cat.get("naming",0)*1)),
        ("Docs",        max(0, 100 - cat.get("docs",0)*2       - cat.get("docstring",0)*2)),
        ("Structure",   max(0, 100 - cat.get("structure",0)*3)),
        ("Standards",   max(0, 100 - cat.get("standards",0)*3)),
        ("Patterns",    max(0, 100 - cat.get("insecure_pattern",0)*5)),
    ]
    labels = [d[0] for d in dimensions]
    values = [min(100, d[1]) for d in dimensions]
    values += values[:1]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(4.2, 4.0), subplot_kw={"polar": True})
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor("#f8fafc")

    color = "#16a34a" if data["avg_score"] >= 65 else "#dc2626"
    ax.plot(angles, values, color=color, linewidth=2)
    ax.fill(angles, values, color=color, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=TEXT_COLOR, fontsize=8, fontweight="600")
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25","50","75","100"], color=TICK_COLOR, fontsize=7)
    ax.grid(color=GRID_COLOR, linewidth=0.8)
    ax.spines["polar"].set_color(SPINE_CLR)

    plt.tight_layout()
    return _save(fig, "radar")


def chart_top_files(data: dict) -> str:
    top = data["top_files"][:6]
    if not top:
        return None

    fnames = [os.path.basename(f[0]) for f in top]
    totals = [f[1] for f in top]
    highs  = [data["file_sev"].get(f[0], {}).get("high",   0) for f in top]
    meds   = [data["file_sev"].get(f[0], {}).get("medium", 0) for f in top]
    lows_  = [t-h-m for t,h,m in zip(totals,highs,meds)]

    x = np.arange(len(fnames))
    fig, ax = _fig(7.5, 2.8)

    ax.barh(x, highs, color="#dc2626", label="High",   height=0.5, alpha=0.85)
    ax.barh(x, meds,  color="#d97706", label="Medium", height=0.5, alpha=0.85, left=highs)
    ax.barh(x, lows_, color="#2563eb", label="Low",    height=0.5, alpha=0.85,
            left=[h+m for h,m in zip(highs,meds)])

    ax.set_yticks(x)
    ax.set_yticklabels(fnames, color=TEXT_COLOR, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Issue Count", color=TEXT_COLOR, fontsize=9)
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.6)
    ax.legend(fontsize=8, labelcolor=TEXT_COLOR, facecolor=CHART_BG,
              edgecolor=SPINE_CLR, loc="lower right")

    plt.tight_layout()
    return _save(fig, "files")


def chart_category_bar(data: dict) -> str:
    cats = {k: v for k, v in data["category_counts"].items()
            if k not in {"security","pr_review","dependency","docs","complexity"}}
    if not cats:
        return None

    top    = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:10]
    labels = [t[0].replace("_"," ").title() for t in top]
    values = [t[1] for t in top]
    cols   = ["#dc2626" if v>=20 else "#d97706" if v>=10 else "#2563eb" for v in values]

    fig, ax = _fig(7.5, 3.0)
    bars = ax.bar(labels, values, color=cols, alpha=0.85, width=0.6)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                str(val), ha="center", va="bottom",
                color=TEXT_COLOR, fontsize=8, fontweight="bold")

    ax.set_ylabel("Count", color=TEXT_COLOR, fontsize=9)
    ax.tick_params(axis="x", rotation=30, colors=TICK_COLOR, labelsize=8)
    ax.tick_params(axis="y", colors=TICK_COLOR, labelsize=8)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.6)

    plt.tight_layout()
    return _save(fig, "cats")


# ─────────────────────────────────────────
# PDF Style Definitions — light theme
# ─────────────────────────────────────────

def make_styles() -> dict:
    S = {}

    # Cover
    S["cover_name"]  = ParagraphStyle("cover_name",
        fontSize=32, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER, spaceAfter=6)

    S["cover_sub"]   = ParagraphStyle("cover_sub",
        fontSize=13, fontName="Helvetica",
        textColor=colors.HexColor("#bfdbfe"), alignment=TA_CENTER, spaceAfter=4)

    S["cover_date"]  = ParagraphStyle("cover_date",
        fontSize=10, fontName="Helvetica",
        textColor=colors.HexColor("#93c5fd"), alignment=TA_CENTER)

    # Headings
    S["section"]     = ParagraphStyle("section",
        fontSize=16, fontName="Helvetica-Bold",
        textColor=C_TITLE, spaceBefore=20, spaceAfter=8)

    S["subsection"]  = ParagraphStyle("subsection",
        fontSize=12, fontName="Helvetica-Bold",
        textColor=C_HEADING, spaceBefore=12, spaceAfter=6)

    # Body
    S["body"]        = ParagraphStyle("body",
        fontSize=10, fontName="Helvetica",
        textColor=C_BODY, spaceAfter=6, leading=16)

    S["body_bold"]   = ParagraphStyle("body_bold",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=C_TITLE, spaceAfter=4)

    S["muted"]       = ParagraphStyle("muted",
        fontSize=9, fontName="Helvetica",
        textColor=C_MUTED)

    S["caption"]     = ParagraphStyle("caption",
        fontSize=9, fontName="Helvetica",
        textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=10)

    # Table cells
    S["th"]          = ParagraphStyle("th",
        fontSize=9, fontName="Helvetica-Bold",
        textColor=colors.white)

    S["td"]          = ParagraphStyle("td",
        fontSize=9, fontName="Helvetica",
        textColor=C_BODY)

    S["td_mono"]     = ParagraphStyle("td_mono",
        fontSize=8, fontName="Helvetica",
        textColor=C_MUTED)

    S["td_msg"]      = ParagraphStyle("td_msg",
        fontSize=8, fontName="Helvetica",
        textColor=C_BODY, leading=12)

    # Footer
    S["footer"]      = ParagraphStyle("footer",
        fontSize=8, fontName="Helvetica",
        textColor=C_MUTED, alignment=TA_CENTER)

    return S


# ─────────────────────────────────────────
# Reusable PDF Components
# ─────────────────────────────────────────

def divider(color=C_BORDER_DARK, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=8, spaceBefore=2)


def section_header(number: str, title: str, color: colors.Color, styles: dict):
    """Dark-background section header bar."""
    tbl = Table([[
        Paragraph(f"{number}",     ParagraphStyle("n", fontSize=11, fontName="Helvetica-Bold",
                                                  textColor=color)),
        Paragraph(f"  {title}",    ParagraphStyle("t", fontSize=14, fontName="Helvetica-Bold",
                                                  textColor=C_TITLE)),
    ]], colWidths=[30, PAGE_W - 30])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_CARD_BG),
        ("LINEBELOW",     (0,0), (-1,-1), 2.5, color),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return tbl


def kpi_row(metrics: list) -> Table:
    """
    metrics = [(label, value, value_color_hex), ...]
    Renders a row of metric boxes with dark label, coloured value.
    """
    n = len(metrics)
    w = PAGE_W / n - 4

    value_cells = []
    label_cells = []
    for label, value, vc in metrics:
        value_cells.append(
            Paragraph(str(value),
                ParagraphStyle("v", fontSize=26, fontName="Helvetica-Bold",
                               textColor=colors.HexColor(vc), alignment=TA_CENTER))
        )
        label_cells.append(
            Paragraph(label,
                ParagraphStyle("l", fontSize=9, fontName="Helvetica",
                               textColor=C_MUTED, alignment=TA_CENTER))
        )

    tbl = Table([value_cells, label_cells], colWidths=[w] * n)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_CARD_BG),
        ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",     (0,0), (-1,-1), 0.5, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return tbl


def severity_table(sev: dict, S: dict) -> Table:
    header = [
        Paragraph("Severity",         S["th"]),
        Paragraph("Count",            S["th"]),
        Paragraph("Impact Level",     S["th"]),
        Paragraph("Required Action",  S["th"]),
    ]
    rows = [
        header,
        [Paragraph("High",    ParagraphStyle("h", fontSize=9, fontName="Helvetica-Bold",
                               textColor=C_RED)),
         Paragraph(str(sev.get("high",0)),    ParagraphStyle("hv", fontSize=9, fontName="Helvetica-Bold", textColor=C_RED)),
         "Critical",  "Block merge — fix immediately"],
        [Paragraph("Medium",  ParagraphStyle("m", fontSize=9, fontName="Helvetica-Bold",
                               textColor=C_AMBER)),
         Paragraph(str(sev.get("medium",0)),  ParagraphStyle("mv", fontSize=9, fontName="Helvetica-Bold", textColor=C_AMBER)),
         "Warning",   "Fix before release"],
        [Paragraph("Low",     ParagraphStyle("l", fontSize=9, fontName="Helvetica-Bold",
                               textColor=C_BLUE)),
         Paragraph(str(sev.get("low",0)),     ParagraphStyle("lv", fontSize=9, fontName="Helvetica-Bold", textColor=C_BLUE)),
         "Minor",     "Fix when possible"],
        [Paragraph("<b>Total</b>", ParagraphStyle("t", fontSize=9, fontName="Helvetica-Bold", textColor=C_TITLE)),
         Paragraph(f"<b>{sum(sev.values())}</b>", ParagraphStyle("tv", fontSize=9, fontName="Helvetica-Bold", textColor=C_TITLE)),
         "—", "—"],
    ]

    tbl = Table(rows, colWidths=[80, 60, 100, 295])
    _apply_light_table(tbl, header_bg=colors.HexColor("#1e3a5f"),
                       alt=[C_WHITE, C_CARD_BG])
    return tbl


def agent_table(agent_counts: dict, agent_sev: dict, S: dict) -> Table:
    header = [
        Paragraph("Agent",   S["th"]),
        Paragraph("Total",   S["th"]),
        Paragraph("High",    S["th"]),
        Paragraph("Medium",  S["th"]),
        Paragraph("Low",     S["th"]),
    ]
    rows = [header]
    for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
        sv = agent_sev.get(agent, {})
        rows.append([
            Paragraph(AGENT_LABELS.get(agent, agent), S["td"]),
            Paragraph(str(count),              ParagraphStyle("c", fontSize=9, fontName="Helvetica-Bold", textColor=C_TITLE)),
            Paragraph(str(sv.get("high",0)),   ParagraphStyle("h", fontSize=9, fontName="Helvetica-Bold", textColor=C_RED)),
            Paragraph(str(sv.get("medium",0)), ParagraphStyle("m", fontSize=9, fontName="Helvetica-Bold", textColor=C_AMBER)),
            Paragraph(str(sv.get("low",0)),    ParagraphStyle("l", fontSize=9, fontName="Helvetica-Bold", textColor=C_BLUE)),
        ])

    tbl = Table(rows, colWidths=[140, 60, 70, 80, 60])
    _apply_light_table(tbl, header_bg=colors.HexColor("#1e3a5f"),
                       alt=[C_WHITE, C_CARD_BG])
    return tbl


def findings_table(findings: list, S: dict) -> Table:
    header = [
        Paragraph("Sev",        S["th"]),
        Paragraph("Agent",      S["th"]),
        Paragraph("File:Line",  S["th"]),
        Paragraph("Issue Description", S["th"]),
    ]
    rows = [header]
    for f in findings[:10]:
        sev   = f.get("severity","low").upper()
        agent = AGENT_LABELS.get(f.get("agent",""), f.get("agent",""))
        fname = os.path.basename(f.get("file","?"))
        line  = f.get("line","?")
        msg   = f.get("message","")[:95] + ("…" if len(f.get("message",""))>95 else "")
        sc    = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#2563eb"}.get(sev,"#64748b")

        rows.append([
            Paragraph(f'<font color="{sc}"><b>{sev}</b></font>',
                      ParagraphStyle("s", fontSize=8, fontName="Helvetica-Bold")),
            Paragraph(agent,        ParagraphStyle("a", fontSize=8, textColor=C_BODY)),
            Paragraph(f"{fname}:{line}",
                      ParagraphStyle("f", fontSize=7, fontName="Helvetica", textColor=C_MUTED)),
            Paragraph(msg,          S["td_msg"]),
        ])

    tbl = Table(rows, colWidths=[48, 80, 95, 312])
    _apply_light_table(tbl, header_bg=colors.HexColor("#1e3a5f"),
                       alt=[C_WHITE, C_CARD_BG], valign="TOP")
    return tbl


def recurring_table(recurring: list, S: dict) -> Table:
    if not recurring:
        return Paragraph("No recurring issues detected.", S["body"])

    header = [
        Paragraph("Category",       S["th"]),
        Paragraph("Occurrences",    S["th"]),
        Paragraph("Risk Level",     S["th"]),
        Paragraph("Recommendation", S["th"]),
    ]
    rows = [header]
    for r in recurring:
        count = r["count"]
        risk  = "High" if count >= 20 else "Medium" if count >= 10 else "Low"
        rc    = "#dc2626" if risk=="High" else "#d97706" if risk=="Medium" else "#2563eb"
        rows.append([
            Paragraph(r["category"].replace("_"," ").title(), S["td"]),
            Paragraph(f"<b>{count}</b>", ParagraphStyle("rv", fontSize=9, fontName="Helvetica-Bold",
                       textColor=colors.HexColor(rc))),
            Paragraph(f'<font color="{rc}"><b>{risk}</b></font>',
                      ParagraphStyle("rr", fontSize=9, fontName="Helvetica-Bold")),
            Paragraph("Address in next sprint", S["td"]),
        ])

    tbl = Table(rows, colWidths=[130, 80, 80, 245])
    _apply_light_table(tbl, header_bg=colors.HexColor("#1e3a5f"),
                       alt=[C_WHITE, C_CARD_BG])
    return tbl


def file_table(top_files: list, file_sev: dict, S: dict) -> Table:
    header = [
        Paragraph("File",   S["th"]),
        Paragraph("Total",  S["th"]),
        Paragraph("High",   S["th"]),
        Paragraph("Medium", S["th"]),
        Paragraph("Low",    S["th"]),
        Paragraph("Risk",   S["th"]),
    ]
    rows = [header]
    for fname, total in top_files:
        sv   = file_sev.get(fname, {})
        h, m, l = sv.get("high",0), sv.get("medium",0), sv.get("low",0)
        risk = "High" if h >= 3 else "Medium" if h >= 1 else "Low"
        rc   = "#dc2626" if risk=="High" else "#d97706" if risk=="Medium" else "#16a34a"
        rows.append([
            Paragraph(os.path.basename(fname), S["td_mono"]),
            Paragraph(str(total), S["td"]),
            Paragraph(str(h), ParagraphStyle("fh", fontSize=9, fontName="Helvetica-Bold", textColor=C_RED)),
            Paragraph(str(m), ParagraphStyle("fm", fontSize=9, fontName="Helvetica-Bold", textColor=C_AMBER)),
            Paragraph(str(l), ParagraphStyle("fl", fontSize=9, fontName="Helvetica-Bold", textColor=C_BLUE)),
            Paragraph(f'<font color="{rc}"><b>{risk}</b></font>',
                      ParagraphStyle("fr", fontSize=9, fontName="Helvetica-Bold")),
        ])

    tbl = Table(rows, colWidths=[190, 50, 50, 60, 50, 65])
    _apply_light_table(tbl, header_bg=colors.HexColor("#1e3a5f"),
                       alt=[C_WHITE, C_CARD_BG])
    return tbl


def _apply_light_table(tbl: Table, header_bg=None, alt=None, valign="MIDDLE"):
    """Apply consistent light-theme styling to any table."""
    style = [
        ("FONTNAME",      (0,0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_BODY),
        ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER_DARK),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), valign),
    ]
    if header_bg:
        style += [
            ("BACKGROUND",  (0,0), (-1, 0), header_bg),
            ("TEXTCOLOR",   (0,0), (-1, 0), colors.white),
        ]
    if alt:
        style += [("ROWBACKGROUNDS", (0,1), (-1,-1), alt)]
    tbl.setStyle(TableStyle(style))


def img(path: str, width: float) -> Image:
    i = Image(path)
    ratio = i.imageHeight / i.imageWidth
    i.drawWidth  = width
    i.drawHeight = width * ratio
    return i


def side_by_side(left, right, lw=320, rw=210):
    tbl = Table([[left, right]], colWidths=[lw, rw])
    tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))
    return tbl


# ─────────────────────────────────────────
# Cover Page
# ─────────────────────────────────────────

def build_cover(data: dict, S: dict) -> list:
    score = data["avg_score"]
    sc    = "#16a34a" if score >= 85 else "#2563eb" if score >= 65 else "#dc2626"
    trend_icon = {"Improving":"↑", "Declining":"↓", "Stable":"→", "New Developer":"★"}.get(data["trend"],"→")

    story = [Spacer(1, 20)]

    # Dark navy header band
    header_tbl = Table([[
        Paragraph("🛡  RepoGuardian",
            ParagraphStyle("logo", fontSize=13, fontName="Helvetica-Bold",
                           textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("Developer Performance Report",
            ParagraphStyle("rpt", fontSize=11, fontName="Helvetica",
                           textColor=colors.HexColor("#93c5fd"), alignment=TA_CENTER)),
    ]], colWidths=[PAGE_W/2, PAGE_W/2])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#1e3a5f")),
        ("TOPPADDING",    (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 36))

    # Developer name — large dark text on white
    story.append(Paragraph(f"@{data['username']}",
        ParagraphStyle("devname", fontSize=38, fontName="Helvetica-Bold",
                       textColor=C_TITLE, alignment=TA_CENTER, spaceAfter=6)))

    story.append(divider(colors.HexColor(sc), thickness=2))
    story.append(Spacer(1, 24))

    # Score card — white background, dark text
    score_tbl = Table([
        [Paragraph(str(score),
            ParagraphStyle("sv", fontSize=64, fontName="Helvetica-Bold",
                           textColor=colors.HexColor(sc), alignment=TA_CENTER))],
        [Paragraph("Average Health Score  /  100",
            ParagraphStyle("sl", fontSize=11, fontName="Helvetica",
                           textColor=C_MUTED, alignment=TA_CENTER))],
        [Paragraph(f"{trend_icon}  Trend: {data['trend']}",
            ParagraphStyle("st", fontSize=12, fontName="Helvetica-Bold",
                           textColor=colors.HexColor(sc), alignment=TA_CENTER))],
    ], colWidths=[300])
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_CARD_BG),
        ("BOX",           (0,0), (-1,-1), 1.5, colors.HexColor(sc)),
        ("TOPPADDING",    (0,0), (-1,-1), 20),
        ("BOTTOMPADDING", (0,0), (-1,-1), 20),
    ]))
    # Center the score card
    wrapper = Table([[score_tbl]], colWidths=[PAGE_W])
    wrapper.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING",  (0,0),(-1,-1), (PAGE_W-300)//2),
        ("RIGHTPADDING", (0,0),(-1,-1), (PAGE_W-300)//2),
    ]))
    story.append(wrapper)
    story.append(Spacer(1, 28))

    # Meta row
    story.append(kpi_row([
        ("PRs Reviewed",  data["total_prs"],                    "#1e293b"),
        ("Total Findings",data["total_findings"],               "#dc2626"),
        ("Critical (High)",data["sev_counts"].get("high",0),    "#dc2626"),
        ("Warnings",       data["sev_counts"].get("medium",0),  "#d97706"),
        ("Active Since",   data["first_seen"],                  "#1e293b"),
    ]))
    story.append(Spacer(1, 24))

    # Report date
    story.append(Paragraph(
        f"Report generated: {datetime.now().strftime('%B %d, %Y  at  %H:%M')}",
        ParagraphStyle("rd", fontSize=10, fontName="Helvetica",
                       textColor=C_MUTED, alignment=TA_CENTER)))

    story.append(PageBreak())
    return story


# ─────────────────────────────────────────
# PDF Assembly
# ─────────────────────────────────────────

def build_pdf(data: dict, output_path: str):
    log.info(f"Building PDF for @{data['username']} → {output_path}")
    S = make_styles()

    log.info("Generating charts...")
    charts = {
        "score_trend": chart_score_trend(data),
        "sev_pie":     chart_severity_pie(data),
        "agents":      chart_agent_breakdown(data),
        "radar":       chart_radar(data),
        "files":       chart_top_files(data),
        "cats":        chart_category_bar(data),
    }

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=30, rightMargin=30,
        topMargin=30,  bottomMargin=30,
        title=f"RepoGuardian — @{data['username']}",
        author="RepoGuardian AI",
    )

    story = []

    # ── COVER ─────────────────────────────────────────────────
    story += build_cover(data, S)

    # ── 1. EXECUTIVE SUMMARY ──────────────────────────────────
    story.append(section_header("1", "Executive Summary", C_BLUE, S))
    story.append(Spacer(1, 10))

    score    = data["avg_score"]
    sc_hex   = "#16a34a" if score >= 85 else "#2563eb" if score >= 65 else "#dc2626"
    trend_map = {
        "Improving":    "showing positive improvement — keep up the good work.",
        "Declining":    "showing a declining trend — immediate attention recommended.",
        "Stable":       "maintaining a consistent score — focus on high-severity issues.",
        "New Developer":"a new developer with limited history — baseline being established.",
    }

    story.append(Paragraph(
        f"Developer <b>@{data['username']}</b> has been reviewed across "
        f"<b>{data['total_prs']} PR run(s)</b> since {data['first_seen']}, "
        f"generating <b>{data['total_findings']} total findings</b>. "
        f"The average health score is "
        f'<font color="{sc_hex}"><b>{score}/100</b></font> — '
        f"{trend_map.get(data['trend'],'')}",
        S["body"]))

    story.append(Spacer(1, 8))
    story.append(severity_table(data["sev_counts"], S))
    story.append(Spacer(1, 14))

    # Score trend + pie chart
    story.append(Paragraph("Score Progression & Severity Distribution", S["subsection"]))
    row_items = []
    if charts["score_trend"]:
        row_items.append(img(charts["score_trend"], width=315))
    if charts["sev_pie"]:
        row_items.append(img(charts["sev_pie"], width=200))
    if len(row_items) == 2:
        story.append(side_by_side(row_items[0], row_items[1], lw=325, rw=210))
    elif row_items:
        story.append(row_items[0])
    story.append(Paragraph("Fig 1: Health score per run  ·  Fig 2: Severity distribution", S["caption"]))

    story.append(PageBreak())

    # ── 2. AGENT ANALYSIS ─────────────────────────────────────
    story.append(section_header("2", "Agent Analysis", C_PURPLE, S))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "Breakdown of findings contributed by each RepoGuardian agent. "
        "Agents with the highest finding counts should be prioritised in code review training.",
        S["body"]))
    story.append(Spacer(1, 8))

    story.append(agent_table(data["agent_counts"], data["agent_sev"], S))
    story.append(Spacer(1, 14))

    if charts["agents"]:
        story.append(img(charts["agents"], width=PAGE_W))
        story.append(Paragraph("Fig 3: Total findings per agent", S["caption"]))

    story.append(PageBreak())

    # ── 3. CODE QUALITY DIMENSIONS ───────────────────────────
    story.append(section_header("3", "Code Quality Dimensions", C_GREEN, S))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "The radar chart scores six quality dimensions from 0–100. "
        "Each dimension starts at 100 and is penalised by findings in that category. "
        "A larger filled area indicates better overall quality.",
        S["body"]))
    story.append(Spacer(1, 8))

    row_items = []
    if charts["radar"]:
        row_items.append(img(charts["radar"], width=240))
    if charts["cats"]:
        row_items.append(img(charts["cats"], width=285))
    if len(row_items) == 2:
        story.append(side_by_side(row_items[0], row_items[1], lw=250, rw=290))
    elif row_items:
        story.append(row_items[0])
    story.append(Paragraph("Fig 4: Quality radar  ·  Fig 5: Top issue categories", S["caption"]))

    story.append(Spacer(1, 12))

    if data["recurring"]:
        story.append(Paragraph("Recurring Issues (3+ occurrences)", S["subsection"]))
        story.append(Paragraph(
            "These categories appeared repeatedly across multiple PR reviews. "
            "Addressing them will produce the largest improvement in health scores.",
            S["body"]))
        story.append(recurring_table(data["recurring"], S))

    story.append(PageBreak())

    # ── 4. FILE-LEVEL ANALYSIS ────────────────────────────────
    story.append(section_header("4", "File-Level Analysis", C_ORANGE, S))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "Files with the highest number of findings. "
        "Files containing many high-severity issues should be prioritised for refactoring.",
        S["body"]))
    story.append(Spacer(1, 8))

    if charts["files"]:
        story.append(img(charts["files"], width=PAGE_W))
        story.append(Paragraph("Fig 6: Top files by issue count", S["caption"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("File Details", S["subsection"]))
    story.append(file_table(data["top_files"], data["file_sev"], S))

    story.append(PageBreak())

    # ── 5. CRITICAL FINDINGS ──────────────────────────────────
    story.append(section_header("5", "Critical Findings", C_RED, S))
    story.append(Spacer(1, 10))

    n_high = len(data["high_findings"])
    story.append(Paragraph(
        f"The following {min(10, n_high)} high-severity finding(s) must be resolved "
        "before any PR is approved for merge.",
        S["body"]))
    story.append(Spacer(1, 8))

    if data["high_findings"]:
        story.append(findings_table(data["high_findings"], S))
    else:
        story.append(Paragraph(
            "✓  No high-severity findings recorded — excellent security posture!",
            ParagraphStyle("ok", fontSize=11, fontName="Helvetica-Bold",
                           textColor=C_GREEN, spaceBefore=8)))

    story.append(Spacer(1, 20))

    # ── 6. RECOMMENDATIONS ────────────────────────────────────
    story.append(section_header("6", "Recommendations", C_TEAL, S))
    story.append(Spacer(1, 10))

    recs = []
    if data["sev_counts"].get("high",0) > 0:
        recs.append(f"Fix all <b>{data['sev_counts']['high']} high-severity issues</b> before the next PR — these block merge approval.")
    if data["recurring"]:
        top = data["recurring"][0]["category"].replace("_"," ").title()
        recs.append(f"Address the recurring pattern <b>{top}</b> ({data['recurring'][0]['count']} occurrences) — schedule a dedicated refactor sprint.")
    if data["trend"] == "Declining":
        recs.append("Score is <b>declining</b> — apply code review standards consistently and consider pair-programming sessions.")
    if data["agent_counts"].get("security",0) > 5:
        recs.append(f"Security agent found <b>{data['agent_counts']['security']} issues</b> — prioritise a security-focused code review session covering OWASP Top 10.")
    if data["agent_counts"].get("docs",0) > 5:
        recs.append("Improve <b>documentation coverage</b> — add docstrings to all public functions and update README for every new feature.")
    if data["top_files"]:
        hotspot = os.path.basename(data["top_files"][0][0])
        recs.append(f"Focus refactoring effort on <b>{hotspot}</b> — it has the highest issue concentration across all runs.")
    if not recs:
        recs.append("Code quality is in good shape. Maintain current standards and resolve low-severity items incrementally.")

    for i, rec in enumerate(recs, 1):
        # Numbered recommendation box
        box = Table([[
            Paragraph(str(i),    ParagraphStyle("rn", fontSize=11, fontName="Helvetica-Bold",
                                                textColor=C_BLUE, alignment=TA_CENTER)),
            Paragraph(rec,       ParagraphStyle("rt", fontSize=10, fontName="Helvetica",
                                                textColor=C_BODY, leading=16)),
        ]], colWidths=[28, PAGE_W - 28])
        box.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,0), C_ACCENT_BG),
            ("BACKGROUND",    (1,0), (1,0), C_WHITE),
            ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
            ("INNERGRID",     (0,0), (-1,-1), 0, C_WHITE),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, C_BORDER),
        ]))
        story.append(box)

    # ── Footer ────────────────────────────────────────────────
    story.append(Spacer(1, 28))
    story.append(divider())
    story.append(Paragraph(
        f"Generated by RepoGuardian AI  ·  KLH Hackathon 2025  ·  "
        f"Powered by Groq + Llama3  ·  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        S["footer"]))

    log.info("Writing PDF...")
    doc.build(story)

    # Cleanup
    for path in charts.values():
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    log.info(f"PDF saved → {output_path}")


# ─────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────

def run_report_agent(username: str = None, output_path: str = None) -> list:
    OUTPUT_DIR.mkdir(exist_ok=True)
    memory = load_memory()

    if not memory:
        log.error("memory_store.json is empty. Run orchestrator on a PR first.")
        return []

    if username and username not in memory:
        log.error(f"@{username} not found. Available: {', '.join(memory.keys())}")
        return []

    targets = {username: memory[username]} if username else memory
    outputs = []

    for uname, profile in targets.items():
        log.info(f"Processing @{uname}...")
        data = process_profile(uname, profile)

        path = output_path or str(
            OUTPUT_DIR / f"report_{uname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        build_pdf(data, path)
        outputs.append(path)
        print(f"\n  ✓  PDF saved: {path}")

    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoGuardian PDF Report Agent")
    parser.add_argument("--user",   type=str, help="Developer username (default: all)")
    parser.add_argument("--output", type=str, help="Output PDF path (default: auto-named)")
    args = parser.parse_args()

    print("\n========================================")
    print("  RepoGuardian — PDF Report Agent")
    print("========================================\n")

    outputs = run_report_agent(username=args.user, output_path=args.output)

    if outputs:
        print(f"\n  Generated {len(outputs)} report(s):")
        for p in outputs:
            print(f"    {p}")
    else:
        print("\n  No reports generated.")