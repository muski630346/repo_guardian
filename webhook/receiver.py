"""
RepoGuardian — Dashboard API Server
Serves real-time metrics to the React dashboard.
Pure file reads — no LLM, no agents, no GitHub calls.

Run:
    uvicorn webhook.receiver:app --reload --port 8000
"""

import os, sys, json, logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [API] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="RepoGuardian Dashboard API")
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:3000","*"],
    allow_methods=["GET", "POST"], allow_headers=["*"])

DB_DIR       = Path(__file__).parent.parent / "db"
MEMORY_STORE = DB_DIR / "memory_store.json"
LAST_RUN     = DB_DIR / "last_run.json"

AGENT_META = {
    "pr_review":  {"label": "PR Review Agent",   "model": "llama-3.3-70b",   "color": "#3b82f6"},
    "security":   {"label": "Security Agent",     "model": "semgrep + llama", "color": "#ef4444"},
    "dependency": {"label": "Dependency Agent",   "model": "pip-audit",       "color": "#f97316"},
    "docs":       {"label": "Docs Agent",         "model": "llama-3.3-70b",   "color": "#22c55e"},
    "memory":     {"label": "Memory Agent",       "model": "json store",      "color": "#64748b"},
    "autofix":    {"label": "Auto-Fix Agent",     "model": "regex engine",    "color": "#06b6d4"},
}


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Could not read {path}: {e}")
        return {}


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/dashboard")
def get_dashboard():
    memory  = _read(MEMORY_STORE)
    lastrun = _read(LAST_RUN)

    # ── Aggregate all findings and PR history from memory_store ──
    pull_requests    = []
    all_raw_findings = []

    for developer, dev_data in memory.items():
        seen = set()
        for pr in dev_data.get("pr_history", []):
            pr_num = pr["pr_number"]
            repo   = pr.get("repo", "unknown")
            key    = (pr_num, repo)
            findings = pr.get("findings", [])
            all_raw_findings.extend(findings)

            if key in seen:
                continue
            seen.add(key)

            highs   = sum(1 for f in findings if f["severity"] == "high")
            mediums = sum(1 for f in findings if f["severity"] == "medium")
            lows    = sum(1 for f in findings if f["severity"] == "low")
            score   = pr.get("score", 0)
            verdict = "Approved" if score >= 85 else "Needs Work" if score >= 65 else "Rejected"

            pull_requests.append({
                "id": pr_num, "name": f"PR #{pr_num} — {repo}",
                "branch": repo, "author": developer,
                "score": score, "verdict": verdict,
                "date": pr.get("timestamp", "")[:16].replace("T", " "),
                "critical": highs, "highs": highs,
                "mediums": mediums, "lows": lows,
            })

    pull_requests.sort(key=lambda x: x["date"], reverse=True)
    pull_requests = pull_requests[:10]

    # ── Agent counts — use agent_counts from memory_store directly ──
    # memory_store already tracks per-agent finding totals accurately
    combined_agent_counts  = {}
    combined_severity_counts = {"high": 0, "medium": 0, "low": 0}
    total_prs_tracked = 0

    for dev_data in memory.values():
        for k, v in dev_data.get("agent_counts", {}).items():
            combined_agent_counts[k] = combined_agent_counts.get(k, 0) + v
        for sev, v in dev_data.get("severity_counts", {}).items():
            if sev in combined_severity_counts:
                combined_severity_counts[sev] += v
        total_prs_tracked = max(total_prs_tracked,
                                dev_data.get("total_prs", 0))

    # Per-agent severity breakdown — compute from raw findings
    agent_sev = {}
    for f in all_raw_findings:
        a   = f.get("agent", "unknown")
        sev = f.get("severity", "low")
        if a not in agent_sev:
            agent_sev[a] = {"high": 0, "medium": 0, "low": 0}
        agent_sev[a][sev] = agent_sev[a].get(sev, 0) + 1

    # ── Autofix data from last_run (if available) ──────────────
    autofix_count   = lastrun.get("autofix_count", 0)
    autofix_pr_url  = lastrun.get("autofix_pr_url")
    memory_alerts   = lastrun.get("memory_alerts", 0)
    memory_developer= lastrun.get("memory_developer")

    # ── Agents data — NOTE: no complexity (removed per request) ──
    agents_data = []
    total_all   = 0
    for agent_key, meta in AGENT_META.items():
        total = combined_agent_counts.get(agent_key, 0)

        # Special handling: autofix and memory may have 0 findings
        # but still show real data from last_run
        extra = {}
        if agent_key == "autofix":
            extra = {"fixes_applied": autofix_count, "fix_pr_url": autofix_pr_url}
            # autofix is active if it ran and found fixable issues
            status = "active" if autofix_count > 0 else ("ran" if lastrun else "standby")
        elif agent_key == "memory":
            extra = {"recurring_alerts": memory_alerts, "developer": memory_developer}
            status = "active" if memory_alerts > 0 else ("ran" if lastrun and memory_developer else "standby")
        elif agent_key == "dependency":
            status = "ran" if lastrun else "standby"   # dep always runs, may find 0
        else:
            status = "active" if total > 0 else "standby"

        sev = agent_sev.get(agent_key, {})
        total_all += total
        agents_data.append({
            "name":    meta["label"],
            "model":   meta["model"],
            "color":   meta["color"],
            "findings": total,
            "status":  status,
            "highs":   sev.get("high", 0),
            "mediums": sev.get("medium", 0),
            "lows":    sev.get("low", 0),
            **extra,
        })

    agents_data.append({
        "name": "Orchestrator", "model": "coordinator",
        "color": "#94a3b8",
        "findings": total_all,
        "status": "active" if total_all > 0 else "standby",
        "highs": 0, "mediums": 0, "lows": 0,
    })

    # ── Findings list ─────────────────────────────────────────
    findings_list = [
        {
            "id": i + 1,
            "severity": f.get("severity", "low").upper(),
            "agent":    AGENT_META.get(f.get("agent", ""), {}).get("label", f.get("agent", "")),
            "file":     f.get("file", "unknown"),
            "line":     f.get("line", 0),
            "message":  f.get("message", "")[:120],
            "fix":      f.get("suggestion", ""),
        }
        for i, f in enumerate(all_raw_findings)
    ]

    # ── Pie chart — agent finding counts ─────────────────────
    pie_data = [
        {"name": meta["label"], "value": combined_agent_counts.get(k, 0), "color": meta["color"]}
        for k, meta in AGENT_META.items()
        if combined_agent_counts.get(k, 0) > 0
    ]

    # ── Radar — score per agent category ─────────────────────
    radar_map = [
        ("security",  "Security"),
        ("pr_review", "Review"),
        ("dependency","Dependencies"),
        ("docs",      "Docs"),
        ("memory",    "Memory"),
        ("autofix",   "Auto-Fix"),
    ]
    radar_data = []
    for agent_key, label in radar_map:
        sev     = agent_sev.get(agent_key, {})
        penalty = sev.get("high",0)*15 + sev.get("medium",0)*7 + sev.get("low",0)*2
        radar_data.append({"subject": label, "A": max(0, min(100, 100 - penalty))})

    # ── Health Trend + Issues Per PR ─────────────────────────
    health_trend  = [{"name": f"PR-{p['id']}", "score": p["score"]} for p in pull_requests]
    issues_per_pr = [
        {"name": f"PR-{p['id']}", "critical": p["critical"],
         "high": p["highs"], "medium": p["mediums"], "low": p["lows"]}
        for p in pull_requests
    ]

    # ── Live log ──────────────────────────────────────────────
    live_log = [
        {
            "agent": AGENT_META.get(f.get("agent",""), {}).get("label", f.get("agent","")),
            "desc":  f.get("message","")[:60] + ("..." if len(f.get("message",""))>60 else ""),
            "time":  "recent",
            "dot":   AGENT_META.get(f.get("agent",""), {}).get("color", "#94a3b8"),
        }
        for f in all_raw_findings[-5:][::-1]
    ]

    # ── Stats ─────────────────────────────────────────────────
    avg_score = (round(sum(p["score"] for p in pull_requests) / len(pull_requests))
                 if pull_requests else 0)

    return {
        "pull_requests":  pull_requests,
        "health_trend":   health_trend,
        "issues_per_pr":  issues_per_pr,
        "findings":       findings_list[:50],
        "agents_data":    agents_data,
        "pie_data":       pie_data,
        "radar_data":     radar_data,
        "live_log":       live_log,
        "last_run":       lastrun,
        "stats": {
            "total_prs":      len(pull_requests),
            "total_findings": len(findings_list),
            "avg_score":      avg_score,
            "critical_count": combined_severity_counts.get("high", 0),
            "last_score":     lastrun.get("score", avg_score),
            "last_elapsed":   lastrun.get("elapsed", 0),
            "autofix_count":  autofix_count,
            "memory_alerts":  memory_alerts,
        }
    }



# ─────────────────────────────────────────
# POST /api/chat — Voice Agent proxy
# Uses the exact same logic as voice_agent.py
# build_context() + ask_llm() — reads memory_store.json
# ─────────────────────────────────────────

from fastapi import Body

@app.post("/api/chat")
def chat(payload: dict = Body(...)):
    """
    Uses voice_agent.py logic directly.
    Frontend sends: { "question": "What security issues does vamshi have?" }
    Returns: { "reply": "..." }
    """
    try:
        # Import the voice agent functions directly
        sys.path.insert(0, str(Path(__file__).parent.parent / "voice_agent"))
        from voice_agent import build_context, ask_llm, load_memory

        question = payload.get("question", "").strip()
        if not question:
            return {"reply": "Please ask a question."}

        log.info(f"Chat question: {question}")

        store   = load_memory()
        context = build_context(store, question)
        reply   = ask_llm(question, context)

        log.info(f"Chat reply: {reply[:80]}...")
        return {"reply": reply}

    except ImportError as e:
        log.error(f"Could not import voice_agent: {e}")
        # Fallback — inline implementation if voice_agent.py not importable
        return _chat_fallback(payload)
    except Exception as e:
        log.error(f"Chat error: {e}")
        return {"reply": f"Error: {str(e)[:120]}"}


def _chat_fallback(payload: dict) -> dict:
    """Fallback chat using memory_store directly if voice_agent import fails."""
    try:
        from groq import Groq
        from collections import defaultdict

        question = payload.get("question", "").strip()
        store    = _read(MEMORY_STORE)

        if not store:
            return {"reply": "No PR data available yet. Run the orchestrator on a PR first."}

        # Build context from memory store
        lines = []
        for username, profile in store.items():
            all_findings = []
            for pr in profile.get("pr_history", []):
                for f in pr.get("findings", []):
                    all_findings.append(f)

            scores  = [pr.get("score", 0) for pr in profile.get("pr_history", [])]
            avg_s   = round(sum(scores)/len(scores), 1) if scores else 0
            highs   = [f for f in all_findings if f.get("severity") == "high"]
            mediums = [f for f in all_findings if f.get("severity") == "medium"]

            lines.append(f"Developer @{username}: {len(all_findings)} total findings, avg score {avg_s}/100")
            lines.append(f"  High severity: {len(highs)} issues")
            lines.append(f"  Medium severity: {len(mediums)} issues")
            for f in highs[:3]:
                lines.append(f"  - [{f.get('file','?')} line {f.get('line','?')}] {f.get('message','')[:100]}")

        context = "\n".join(lines)

        client   = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are RepoGuardian AI. Answer questions about code review results using only the data provided. Be concise (2-3 sentences). No markdown."},
                {"role": "user",   "content": f"DATA:\n{context}\n\nQUESTION: {question}"},
            ],
            max_tokens=200,
            temperature=0.2,
        )
        return {"reply": response.choices[0].message.content.strip()}

    except Exception as e:
        return {"reply": f"Chat unavailable: {str(e)[:80]}"}




# ─────────────────────────────────────────
# GET /api/users — list all developers
# ─────────────────────────────────────────

@app.get("/api/users")
def get_users():
    """Returns list of all developers tracked in memory_store."""
    memory = _read(MEMORY_STORE)
    users  = []
    for username, profile in memory.items():
        pr_history = profile.get("pr_history", [])
        scores     = [pr.get("score", 0) for pr in pr_history]
        avg_score  = round(sum(scores) / len(scores), 1) if scores else 0
        latest_score = scores[-1] if scores else 0

        # Trend
        if len(scores) >= 2:
            trend = "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable"
        else:
            trend = "new"

        users.append({
            "username":      username,
            "total_prs":     profile.get("total_prs", 0),
            "total_findings":profile.get("total_findings", 0),
            "avg_score":     avg_score,
            "latest_score":  latest_score,
            "trend":         trend,
            "first_seen":    profile.get("first_seen", "")[:10],
            "last_seen":     profile.get("last_seen", "")[:10],
            "severity_counts": profile.get("severity_counts", {}),
            "agent_counts":    profile.get("agent_counts", {}),
        })
    return {"users": users}


# ─────────────────────────────────────────
# GET /api/user/{username} — full profile
# ─────────────────────────────────────────

@app.get("/api/user/{username}")
def get_user(username: str):
    """
    Returns full individual developer dashboard data.
    All metrics computed from memory_store.json pr_history.
    """
    memory  = _read(MEMORY_STORE)
    profile = memory.get(username)
    if not profile:
        return {"error": f"Developer @{username} not found in memory store."}

    pr_history   = profile.get("pr_history", [])
    all_findings = []
    for pr in pr_history:
        for f in pr.get("findings", []):
            f2 = dict(f)
            f2["pr_number"] = pr.get("pr_number")
            f2["pr_score"]  = pr.get("score", 0)
            f2["timestamp"] = pr.get("timestamp", "")
            all_findings.append(f2)

    scores = [pr.get("score", 0) for pr in pr_history]
    avg_score = round(sum(scores)/len(scores), 1) if scores else 0

    # Trend
    if len(scores) >= 2:
        trend = "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable"
    else:
        trend = "new"

    # Score trend for chart
    score_trend = [
        {"name": f"PR-{pr.get('pr_number', i+1)}-run{i+1}",
         "score": pr.get("score", 0),
         "date": pr.get("timestamp", "")[:10]}
        for i, pr in enumerate(pr_history)
    ]

    # Severity breakdown
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for f in all_findings:
        sev = f.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Agent breakdown
    agent_counts = {}
    agent_sev    = {}
    for f in all_findings:
        agent = f.get("agent", "unknown")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1
        if agent not in agent_sev:
            agent_sev[agent] = {"high": 0, "medium": 0, "low": 0}
        sev = f.get("severity", "low")
        agent_sev[agent][sev] = agent_sev[agent].get(sev, 0) + 1

    # Category breakdown
    category_counts = {}
    for f in all_findings:
        for cat in f.get("categories", [f.get("agent", "unknown")]):
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # File breakdown — which files have the most issues
    file_counts = {}
    file_sev    = {}
    for f in all_findings:
        fname = f.get("file", "unknown")
        file_counts[fname] = file_counts.get(fname, 0) + 1
        if fname not in file_sev:
            file_sev[fname] = {"high": 0, "medium": 0, "low": 0}
        sev = f.get("severity", "low")
        file_sev[fname][sev] = file_sev[fname].get(sev, 0) + 1

    top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    files_data = [
        {"file":    fname,
         "total":   count,
         "high":    file_sev[fname].get("high", 0),
         "medium":  file_sev[fname].get("medium", 0),
         "low":     file_sev[fname].get("low", 0)}
        for fname, count in top_files
    ]

    # Issues per PR chart
    issues_per_pr = []
    seen = set()
    for i, pr in enumerate(pr_history):
        f_list  = pr.get("findings", [])
        pr_key  = f"{pr.get('pr_number')}-{i}"
        if pr_key in seen:
            continue
        seen.add(pr_key)
        issues_per_pr.append({
            "name":     f"Run {i+1}",
            "score":    pr.get("score", 0),
            "high":     sum(1 for f in f_list if f.get("severity")=="high"),
            "medium":   sum(1 for f in f_list if f.get("severity")=="medium"),
            "low":      sum(1 for f in f_list if f.get("severity")=="low"),
            "total":    len(f_list),
        })

    # Pie — agent distribution
    agent_pie = [
        {"name":  AGENT_META.get(k, {}).get("label", k),
         "value": v,
         "color": AGENT_META.get(k, {}).get("color", "#94a3b8")}
        for k, v in agent_counts.items() if v > 0
    ]

    # Radar — quality per category
    radar_data = [
        {"subject": "Security",      "A": max(0, 100 - category_counts.get("security", 0)*5 - category_counts.get("owasp", 0)*3)},
        {"subject": "Code Review",   "A": max(0, 100 - category_counts.get("logic", 0)*2 - category_counts.get("naming", 0)*1)},
        {"subject": "Docs",          "A": max(0, 100 - category_counts.get("docs", 0)*2 - category_counts.get("docstring", 0)*2)},
        {"subject": "Structure",     "A": max(0, 100 - category_counts.get("structure", 0)*3)},
        {"subject": "Standards",     "A": max(0, 100 - category_counts.get("standards", 0)*3)},
        {"subject": "Security Patterns","A": max(0, 100 - category_counts.get("insecure_pattern", 0)*5)},
    ]
    # Cap at 100
    for r in radar_data:
        r["A"] = min(100, r["A"])

    # Top issues — high severity first
    top_findings = sorted(all_findings, key=lambda f: (
        0 if f.get("severity")=="high" else 1 if f.get("severity")=="medium" else 2
    ))[:20]

    findings_list = [
        {
            "id":       i+1,
            "severity": f.get("severity","low").upper(),
            "agent":    AGENT_META.get(f.get("agent",""), {}).get("label", f.get("agent","")),
            "file":     f.get("file","unknown"),
            "line":     f.get("line", 0),
            "message":  f.get("message","")[:120],
            "fix":      f.get("suggestion",""),
            "pr_number":f.get("pr_number"),
        }
        for i, f in enumerate(top_findings)
    ]

    # Recurring issues — categories seen 3+ times
    recurring = [
        {"category": cat, "count": count, "severity": "high" if count >= 10 else "medium" if count >= 5 else "low"}
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        if count >= 3 and cat not in {"security","pr_review","dependency","docs","complexity"}
    ][:8]

    return {
        "username":       username,
        "total_prs":      profile.get("total_prs", 0),
        "total_findings": len(all_findings),
        "avg_score":      avg_score,
        "latest_score":   scores[-1] if scores else 0,
        "trend":          trend,
        "first_seen":     profile.get("first_seen","")[:10],
        "last_seen":      profile.get("last_seen","")[:10],
        "score_trend":    score_trend,
        "issues_per_pr":  issues_per_pr,
        "severity_counts":severity_counts,
        "agent_counts":   agent_counts,
        "agent_sev":      agent_sev,
        "category_counts":category_counts,
        "files_data":     files_data,
        "agent_pie":      agent_pie,
        "radar_data":     radar_data,
        "findings":       findings_list,
        "recurring":      recurring,
        "last_pr_categories": profile.get("last_pr_categories", []),
    }


# ─────────────────────────────────────────
# GET /api/report/{username} — PDF download
# ─────────────────────────────────────────

import tempfile
import shutil
import subprocess
from fastapi import HTTPException
from fastapi.background import BackgroundTasks

def _cleanup(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass

@app.get("/api/report/{username}")
def download_report(username: str, background_tasks: BackgroundTasks):
    # ── 1. Validate user ─────────────────────────────────────
    memory = _read(MEMORY_STORE)
    if not memory:
        raise HTTPException(status_code=404, detail="No data in memory store.")
    if username not in memory:
        raise HTTPException(status_code=404, detail=f"Developer @{username} not found.")

    # ── 2. Find report_agent.py — search common locations ────
    project_root = Path(__file__).parent.parent
    candidates = [
        project_root / "tools" / "report_agent.py",
        project_root / "report_agent.py",
        project_root / "agents" / "report_agent.py",
        project_root / "scripts" / "report_agent.py",
    ]
    agent_path = next((p for p in candidates if p.exists()), None)
    if agent_path is None:
        raise HTTPException(status_code=500,
            detail=f"report_agent.py not found. Searched: {[str(p) for p in candidates]}")

    # ── 3. Create temp output path ───────────────────────────
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix=f"rg_{username}_")
    os.close(tmp_fd)

    # ── 4. Run exactly like the terminal does ────────────────
    try:
        # Force UTF-8 on Windows to handle unicode chars (✓ etc.) in report_agent output
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        result = subprocess.run(
            [sys.executable, str(agent_path), "--user", username, "--output", tmp_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(project_root),
            env=env,
        )
        log.info(f"report_agent stdout: {result.stdout[-300:] if result.stdout else ''}")
        if result.returncode != 0:
            _cleanup(tmp_path)
            log.error(f"report_agent stderr: {result.stderr}")
            raise HTTPException(status_code=500,
                detail=f"report_agent.py exited with code {result.returncode}: {result.stderr[-200:]}")
    except subprocess.TimeoutExpired:
        _cleanup(tmp_path)
        raise HTTPException(status_code=500, detail="PDF generation timed out (120s).")
    except HTTPException:
        raise
    except Exception as e:
        _cleanup(tmp_path)
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")

    # ── 5. Validate the output is a real PDF ─────────────────
    try:
        size = os.path.getsize(tmp_path)
        with open(tmp_path, "rb") as f:
            header = f.read(4)
        if header != b"%PDF" or size < 100:
            _cleanup(tmp_path)
            raise HTTPException(status_code=500,
                detail="Generated file is not a valid PDF. Check server logs.")
    except HTTPException:
        raise
    except Exception as e:
        _cleanup(tmp_path)
        raise HTTPException(status_code=500, detail=f"PDF validation error: {e}")

    # ── 6. Stream back and clean up after ────────────────────
    background_tasks.add_task(_cleanup, tmp_path)
    filename = f"RepoGuardian_{username}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return FileResponse(
        path=tmp_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────
# GET /api/pr-limit — PR limit gate check
# Returns open PR count vs configured limit.
# Frontend polls this every 30s to decide
# whether to show the PRScreenBlock overlay.
# ─────────────────────────────────────────

PR_LIMIT = int(os.getenv("PR_LIMIT", "5"))   # set PR_LIMIT=8 in .env to override

@app.get("/api/pr-limit")
def get_pr_limit():
    """
    Returns current open PR count, configured limit, and
    the list of open PRs so the frontend can render them.
    """
    memory = _read(MEMORY_STORE)

    all_prs = []
    seen    = set()

    for developer, dev_data in memory.items():
        for pr in dev_data.get("pr_history", []):
            pr_num = pr["pr_number"]
            repo   = pr.get("repo", "unknown")
            key    = (pr_num, repo)
            if key in seen:
                continue
            seen.add(key)

            score   = pr.get("score", 0)
            verdict = "Approved" if score >= 85 else "Needs Work" if score >= 65 else "Rejected"

            all_prs.append({
                "id":      pr_num,
                "author":  developer,
                "branch":  repo,
                "score":   score,
                "verdict": verdict,
                "date":    pr.get("timestamp", "")[:16].replace("T", " "),
            })

    all_prs.sort(key=lambda x: x["date"], reverse=True)

    # "Open" PRs = those not Approved (still need work or rejected)
    open_prs  = [p for p in all_prs if p["verdict"] != "Approved"]
    open_count = len(open_prs)
    exceeded   = open_count >= PR_LIMIT

    return {
        "open":     open_count,
        "limit":    PR_LIMIT,
        "exceeded": exceeded,
        "prs":      open_prs[:10],    # send top 10 for display
    }


# ─────────────────────────────────────────
# GET /api/git-report/{owner}/{repo}/{pr_number}
# Runs report_git_agent.py against a live
# GitHub PR and streams the PDF back.
# ─────────────────────────────────────────

@app.get("/api/git-report/{owner}/{repo}/{pr_number}")
def download_git_report(owner: str, repo: str, pr_number: int, background_tasks: BackgroundTasks):
    """
    Generates a Git PR PDF report by fetching live GitHub PR comments
    via report_git_agent.py and returns it as a downloadable PDF.
    """
    repo_full = f"{owner}/{repo}"

    # ── Find the correct Python executable (venv-aware) ───────────────────
    project_root = Path(__file__).parent.parent

    # Try venv Python first (Windows and Unix), then fall back to sys.executable
    venv_pythons = [
        project_root / "venv" / "Scripts" / "python.exe",   # Windows venv
        project_root / "venv" / "bin" / "python",            # Unix venv
        project_root / ".venv" / "Scripts" / "python.exe",   # Windows .venv
        project_root / ".venv" / "bin" / "python",           # Unix .venv
    ]
    python_exe = next((str(p) for p in venv_pythons if p.exists()), sys.executable)
    log.info(f"[git-report] Using Python: {python_exe}")

    # ── Find report_git_agent.py ──────────────────────────────────────────
    candidates = [
        project_root / "tools" / "report_git_agent.py",
        project_root / "report_git_agent.py",
        project_root / "agents" / "report_git_agent.py",
    ]
    agent_path = next((p for p in candidates if p.exists()), None)
    if agent_path is None:
        raise HTTPException(status_code=500,
            detail=f"report_git_agent.py not found. Searched: {[str(p) for p in candidates]}")
    log.info(f"[git-report] Agent path: {agent_path}")

    # ── Create a dedicated temp dir so we know exactly where the PDF lands ─
    tmp_dir = tempfile.mkdtemp(prefix="git_report_")
    tmp_pdf = os.path.join(tmp_dir, f"git_pr_{pr_number}_report.pdf")

    def cleanup_dir():
        import shutil as _shutil
        try: _shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception: pass

    # ── Run as subprocess ─────────────────────────────────────────────────
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"]       = "1"

        cmd = [python_exe, str(agent_path), repo_full, str(pr_number), tmp_dir]
        log.info(f"[git-report] Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            cwd=str(project_root),
            env=env,
        )

        log.info(f"[git-report] stdout:\n{result.stdout[-500:] if result.stdout else '(none)'}")

        if result.returncode != 0:
            cleanup_dir()
            log.error(f"[git-report] stderr:\n{result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Git report agent failed (exit {result.returncode}): {result.stderr[-400:]}"
            )
    except subprocess.TimeoutExpired:
        cleanup_dir()
        raise HTTPException(status_code=500, detail="Git report timed out (180s). GitHub API may be slow.")
    except HTTPException:
        raise
    except Exception as e:
        cleanup_dir()
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")

    # ── Find the generated PDF ────────────────────────────────────────────
    pdf_path = None
    for f in os.listdir(tmp_dir):
        if f.endswith(".pdf"):
            pdf_path = os.path.join(tmp_dir, f)
            break

    # Fallback: check project reports/ dir
    if not pdf_path:
        fallback = project_root / "reports" / f"git_pr_{pr_number}_report.pdf"
        if fallback.exists():
            pdf_path = str(fallback)

    if not pdf_path:
        cleanup_dir()
        log.error(f"[git-report] No PDF in {tmp_dir}. stdout: {result.stdout[:300]}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF was not created. Agent output: {result.stdout[-300:] or '(empty)'}"
        )

    log.info(f"[git-report] PDF found: {pdf_path}")

    # ── Validate PDF ──────────────────────────────────────────────────────
    try:
        size = os.path.getsize(pdf_path)
        with open(pdf_path, "rb") as f:
            header = f.read(4)
        if header != b"%PDF":
            cleanup_dir()
            raise HTTPException(status_code=500, detail="Output file is not a valid PDF.")
        if size < 500:
            cleanup_dir()
            raise HTTPException(status_code=500, detail=f"PDF appears empty ({size} bytes).")
    except HTTPException:
        raise
    except Exception as e:
        cleanup_dir()
        raise HTTPException(status_code=500, detail=f"PDF validation error: {e}")

    # ── Stream back ───────────────────────────────────────────────────────
    background_tasks.add_task(cleanup_dir)
    filename = f"GitReport_{owner}_{repo}_PR{pr_number}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webhook.receiver:app", host="0.0.0.0", port=8000, reload=True)