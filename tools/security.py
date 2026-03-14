"""
RepoGuardian — Security Agent
Scans PR diffs for OWASP vulnerabilities, SQL injection,
hardcoded secrets, and insecure code patterns.

.env required:
    GITHUB_TOKEN=...
    GROQ_API_KEY=...
    LLM_MODEL=groq
"""

import os
import re
import json
import time
import logging
from dataclasses import dataclass, field

from groq import Groq
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SECURITY] %(message)s")
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
class SecurityIssue:
    path: str
    line: int
    severity: str      # "high" | "medium" | "low"
    category: str      # "owasp" | "injection" | "secrets" | "insecure_pattern"
    rule: str
    body: str


@dataclass
class SecurityResult:
    repo_name: str
    pr_number: int
    summary: str
    issues: list[SecurityIssue] = field(default_factory=list)
    score_deduction: int = 0


# ─────────────────────────────────────────
# Static Scanner Rules
# Runs on raw diff BEFORE LLM — fast, free, catches obvious patterns
# ─────────────────────────────────────────

STATIC_RULES = [

    # ── SECRETS ──────────────────────────────────────────────
    {
        "rule":     "HARDCODED_API_KEY",
        "category": "secrets",
        "severity": "high",
        "pattern":  re.compile(
            r'(api_key|apikey|api-key|secret_key|access_token|auth_token)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']',
            re.IGNORECASE
        ),
        "message": (
            "Hardcoded API key or secret detected. "
            "Move this to an environment variable using os.getenv(). "
            "Rotate this key immediately — it is now compromised."
        ),
    },
    {
        "rule":     "HARDCODED_PASSWORD",
        "category": "secrets",
        "severity": "high",
        "pattern":  re.compile(
            r'(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']',
            re.IGNORECASE
        ),
        "message": (
            "Hardcoded password in source code. "
            "Use environment variables or a secrets manager. "
            "Never commit credentials to a repository."
        ),
    },
    {
        "rule":     "PRIVATE_KEY_MATERIAL",
        "category": "secrets",
        "severity": "high",
        "pattern":  re.compile(r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'),
        "message": (
            "Private key material found. "
            "Remove immediately, revoke the key, and store it outside the repo."
        ),
    },
    {
        "rule":     "AWS_KEY",
        "category": "secrets",
        "severity": "high",
        "pattern":  re.compile(r'AKIA[0-9A-Z]{16}'),
        "message": (
            "AWS Access Key ID found. "
            "Revoke in AWS console immediately and use IAM roles instead."
        ),
    },

    # ── SQL INJECTION ─────────────────────────────────────────
    {
        "rule":     "SQL_INJECTION",
        "category": "injection",
        "severity": "high",
        "pattern":  re.compile(
            r'(execute|cursor\.execute|db\.execute|query)\s*\(\s*["\'].*(%s|%d|\+|f["\']|\.format)',
            re.IGNORECASE
        ),
        "message": (
            "SQL injection risk: query uses string formatting or concatenation. "
            "Use parameterised queries: cursor.execute('SELECT * FROM t WHERE id=%s', (val,)). "
            "String-built queries allow attackers to manipulate SQL."
        ),
    },
    {
        "rule":     "SQL_STRING_CONCAT",
        "category": "injection",
        "severity": "high",
        "pattern":  re.compile(
            r'(SELECT|INSERT|UPDATE|DELETE|DROP)\s.*["\'\s]\s*\+\s*\w',
            re.IGNORECASE
        ),
        "message": (
            "SQL built with string concatenation — classic injection vulnerability. "
            "Always use parameterised queries or an ORM."
        ),
    },

    # ── XSS ──────────────────────────────────────────────────
    {
        "rule":     "XSS_INNER_HTML",
        "category": "injection",
        "severity": "high",
        "pattern":  re.compile(r'\.innerHTML\s*=\s*[^"\']*(req\.|request\.|params\.|query\.)'),
        "message": (
            "XSS risk: user-controlled data assigned to innerHTML. "
            "Use textContent instead, or sanitise with DOMPurify."
        ),
    },

    # ── OWASP INSECURE PATTERNS ───────────────────────────────
    {
        "rule":     "WEAK_HASH_MD5",
        "category": "owasp",
        "severity": "high",
        "pattern":  re.compile(r'hashlib\.md5\s*\(|MD5\s*\(', re.IGNORECASE),
        "message": (
            "MD5 is a broken hash — do not use for security. "
            "Use bcrypt/argon2 for passwords, SHA-256 for file integrity."
        ),
    },
    {
        "rule":     "WEAK_HASH_SHA1",
        "category": "owasp",
        "severity": "medium",
        "pattern":  re.compile(r'hashlib\.sha1\s*\(', re.IGNORECASE),
        "message": (
            "SHA-1 is deprecated for security. "
            "Use SHA-256 or SHA-3 for integrity, bcrypt/argon2 for passwords."
        ),
    },
    {
        "rule":     "EVAL_USAGE",
        "category": "owasp",
        "severity": "high",
        "pattern":  re.compile(r'\beval\s*\(', re.IGNORECASE),
        "message": (
            "eval() executes arbitrary code — never use with user input. "
            "Use ast.literal_eval() for safe literal evaluation instead."
        ),
    },
    {
        "rule":     "OS_SYSTEM_INJECTION",
        "category": "owasp",
        "severity": "high",
        "pattern":  re.compile(r'os\.system\s*\(|subprocess\.call\s*\(.*shell\s*=\s*True', re.IGNORECASE),
        "message": (
            "Command injection risk: os.system() or subprocess shell=True. "
            "Use subprocess.run() with a list of arguments and shell=False."
        ),
    },
    {
        "rule":     "PICKLE_DESERIALISE",
        "category": "owasp",
        "severity": "high",
        "pattern":  re.compile(r'pickle\.loads?\s*\(', re.IGNORECASE),
        "message": (
            "pickle.load() can execute arbitrary code — never use with untrusted data. "
            "Use JSON or a safe serialisation format instead."
        ),
    },
    {
        "rule":     "DEBUG_ENABLED",
        "category": "owasp",
        "severity": "medium",
        "pattern":  re.compile(r'DEBUG\s*=\s*True|app\.run\s*\(.*debug\s*=\s*True', re.IGNORECASE),
        "message": (
            "Debug mode must never reach production. "
            "Set DEBUG=False and load from environment variables."
        ),
    },
    {
        "rule":     "BARE_EXCEPT",
        "category": "insecure_pattern",
        "severity": "medium",
        "pattern":  re.compile(r'except\s*:'),
        "message": (
            "Bare except: swallows all exceptions including KeyboardInterrupt. "
            "Always catch specific exceptions: except ValueError as e."
        ),
    },
    {
        "rule":     "INSECURE_RANDOM",
        "category": "insecure_pattern",
        "severity": "medium",
        "pattern":  re.compile(r'\brandom\.(random|randint|choice|shuffle)\s*\('),
        "message": (
            "Python's random module is not cryptographically secure. "
            "Use secrets.token_hex() or secrets.token_urlsafe() for security tokens."
        ),
    },
    {
        "rule":     "HTTP_NOT_HTTPS",
        "category": "owasp",
        "severity": "low",
        "pattern":  re.compile(r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)', re.IGNORECASE),
        "message": (
            "Plain HTTP URL detected — use HTTPS to encrypt traffic in transit."
        ),
    },
    {
        "rule":     "JWT_NONE_ALGORITHM",
        "category": "owasp",
        "severity": "high",
        "pattern":  re.compile(r'algorithm\s*=\s*["\']none["\']', re.IGNORECASE),
        "message": (
            "JWT 'none' algorithm disables signature verification. "
            "An attacker can forge any JWT. Use HS256 or RS256."
        ),
    },
]


# ─────────────────────────────────────────
# GitHub — Fetch Diff + Valid Lines Map
# ─────────────────────────────────────────

def fetch_pr_diff(repo_name: str, pr_number: int):
    """
    Fetch PR diff and build a map of valid (file → set of added line numbers).
    Used to validate both static and LLM findings before posting to GitHub.
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

    log.info(f"Fetched diff for PR #{pr_number} — {len(valid_lines_map)} file(s)")
    return "\n".join(diff_parts), pr, valid_lines_map


# ─────────────────────────────────────────
# Static Scanner
# ─────────────────────────────────────────

def run_static_scan(diff: str, valid_lines_map: dict) -> list[dict]:
    """
    Run all regex rules on added lines (+) in the diff.
    Returns raw findings with validated file paths and line numbers.

    Only scans lines starting with + (added lines).
    Maps each finding to the correct file using the FILE: headers in the diff.
    """
    findings       = []
    current_file   = None
    current_line   = 0   # tracks new file line number

    for diff_line in diff.split("\n"):

        # Track current file from FILE: headers
        if diff_line.startswith("FILE: "):
            current_file = diff_line[6:].strip()
            current_line = 0
            continue

        # Track line numbers from hunk headers
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)
        if hunk:
            current_line = int(hunk.group(1)) - 1
            continue

        if diff_line.startswith("-"):
            continue
        elif diff_line.startswith("+"):
            current_line += 1
            clean = diff_line[1:]   # strip the leading +

            # Run every rule on this added line
            for rule in STATIC_RULES:
                if rule["pattern"].search(clean):

                    # Only report if this file+line is in the PR diff
                    if (current_file and
                        current_file in valid_lines_map and
                        current_line in valid_lines_map[current_file]):

                        findings.append({
                            "file":     current_file,
                            "line":     current_line,
                            "rule":     rule["rule"],
                            "category": rule["category"],
                            "severity": rule["severity"],
                            "message":  rule["message"],
                            "snippet":  clean.strip()[:120],
                        })
        else:
            current_line += 1

    log.info(f"Static scan found {len(findings)} raw finding(s)")
    return findings


# ─────────────────────────────────────────
# LLM Security Prompt
# ─────────────────────────────────────────

SECURITY_SYSTEM_PROMPT = """
You are a senior application security engineer specialising in OWASP Top 10 and secure coding.

Review the PR diff for security vulnerabilities NOT already found by static scan.

CRITICAL RULES:
- Only report issues for file paths EXACTLY as shown after "FILE:" in the diff
- Only report line numbers of actual added lines (starting with +) in the diff
- Line numbers must be positive integers greater than 0
- Do NOT invent file names or line numbers

Return ONLY this JSON, nothing else:
{
  "summary": "2-3 sentence security assessment",
  "score_deduction": 0,
  "issues": [
    {
      "path": "exact/path/from/diff.py",
      "line": 10,
      "severity": "high",
      "category": "owasp",
      "rule": "RULE_NAME",
      "comment": "vulnerability, why dangerous, how to fix — max 3 sentences"
    }
  ]
}

Severity: high (exploitable now) | medium (weakens security) | low (hardening)
Do NOT repeat findings from the static scan list. Only add NEW findings.
Return ONLY valid JSON.
"""


# ─────────────────────────────────────────
# LLM Call with Rate Limit Handling
# ─────────────────────────────────────────

def call_llm_security(diff: str, static_findings: list[dict],
                      valid_lines_map: dict, retries=3) -> dict:
    """Send diff to LLM for deep security analysis beyond static rules."""
    client, model_name = get_llm_client_and_model()

    valid_files    = "\n".join(f"- {f}" for f in valid_lines_map.keys())
    static_summary = "\n".join(
        f"- {f['file']}:{f['line']} [{f['rule']}] {f['snippet']}"
        for f in static_findings
    ) or "None."

    prompt = (
        f"VALID FILES (only report issues for these exact paths):\n{valid_files}\n\n"
        f"Static scan already found (do NOT repeat):\n{static_summary}\n\n"
        f"DIFF:\n{diff[:8000]}"
    )

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SECURITY_SYSTEM_PROMPT},
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
                log.warning(f"Rate limit — waiting {wait}s (attempt {attempt+1})")
                time.sleep(wait)
            else:
                log.warning(f"LLM failed attempt {attempt+1}: {e}")
                time.sleep(3)

    log.error("All LLM security attempts failed.")
    return {"summary": "LLM analysis failed.", "score_deduction": 0, "issues": []}


# ─────────────────────────────────────────
# Post Comments to GitHub
# ─────────────────────────────────────────

SEVERITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🔵"}
CATEGORY_LABEL = {
    "owasp":            "OWASP Vulnerability",
    "injection":        "Injection Risk",
    "secrets":          "Hardcoded Secret",
    "insecure_pattern": "Insecure Pattern",
}


def post_inline_comments(pr, issues: list[SecurityIssue]):
    if not issues:
        log.info("No inline comments to post.")
        return

    latest_commit = list(pr.get_commits())[-1]
    posted  = 0
    skipped = 0

    for issue in issues:
        emoji = SEVERITY_EMOJI.get(issue.severity, "⚪")
        label = CATEGORY_LABEL.get(issue.category, issue.category.title())

        body = (
            f"{emoji} **RepoGuardian Security — {label}** | "
            f"`{issue.severity.upper()}` | `{issue.rule}`\n\n"
            f"{issue.body}\n\n"
            f"---\n"
            f"*Posted by RepoGuardian Security Agent — KLH Hackathon 2025*"
        )

        try:
            pr.create_review_comment(
                body=body,
                commit=latest_commit,
                path=issue.path,
                line=issue.line
            )
            posted += 1
            log.info(f"  Posted → {issue.path}:{issue.line} [{issue.severity}] {issue.rule}")

        except GithubException as e:
            skipped += 1
            msg = e.data.get("message", str(e)) if hasattr(e, "data") else str(e)
            log.warning(f"  Skipped {issue.path}:{issue.line} — {msg}")

    log.info(f"Comments posted: {posted} | Skipped: {skipped}")


def post_security_summary(pr, result: SecurityResult):
    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in result.issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1

    score = 100 - result.score_deduction
    if counts["high"] > 0:
        badge = "🔴 SECURITY RISK — DO NOT MERGE"
    elif counts["medium"] > 0:
        badge = "🟡 SECURITY CONCERNS — REVIEW REQUIRED"
    else:
        badge = "🟢 SECURITY PASSED"

    by_category = {}
    for issue in result.issues:
        label = CATEGORY_LABEL.get(issue.category, issue.category)
        by_category.setdefault(label, []).append(issue)

    category_rows = "".join(
        f"| {label} | {len(items)} |\n"
        for label, items in by_category.items()
    )

    body = f"""## 🔐 RepoGuardian — Security Scan Report

**Security Score:** `{score}/100` {badge}

### Summary
{result.summary}

### Severity Breakdown
| Severity | Count |
|----------|-------|
| 🔴 High (block merge) | **{counts['high']}** |
| 🟡 Medium (fix before release) | **{counts['medium']}** |
| 🔵 Low (hardening) | **{counts['low']}** |
| **Total** | **{len(result.issues)}** |

### By Category
| Category | Count |
|----------|-------|
{category_rows}
> Inline comments posted on each vulnerable line.
> *RepoGuardian Security Agent — KLH Hackathon 2025 — Powered by Groq + Llama3*
"""
    pr.create_issue_comment(body)
    log.info("Security summary posted.")


# ─────────────────────────────────────────
# Main Agent
# ─────────────────────────────────────────

def run_security_agent(repo_name: str, pr_number: int) -> SecurityResult:
    """
    MAIN FUNCTION — called by orchestrator.
        from tools.security import run_security_agent
        result = run_security_agent("owner/repo", 1)
    """
    log.info(f"Security Agent started — {repo_name} PR #{pr_number}")

    # Step 1 — Fetch diff + valid lines map
    log.info("Step 1/5 — Fetching PR diff from GitHub...")
    diff, pr, valid_lines_map = fetch_pr_diff(repo_name, pr_number)

    if not diff.strip():
        log.info("No diff found.")
        return SecurityResult(repo_name=repo_name, pr_number=pr_number,
                              summary="No code changes to scan.", issues=[], score_deduction=0)

    # Step 2 — Static scan (fast, free, no LLM)
    log.info("Step 2/5 — Running static security rules...")
    static_findings = run_static_scan(diff, valid_lines_map)

    # Step 3 — LLM deep analysis (single call, not chunked)
    log.info("Step 3/5 — Running LLM deep security analysis...")
    # Wait before LLM call to avoid rate limit conflict with PR agent
    time.sleep(8)
    llm_result = call_llm_security(diff, static_findings, valid_lines_map)

    # Step 4 — Merge static + LLM findings
    log.info("Step 4/5 — Merging findings...")
    all_issues = []

    # Static findings are already validated (file+line confirmed in diff)
    for f in static_findings:
        all_issues.append(SecurityIssue(
            path     = f["file"],
            line     = f["line"],
            severity = f["severity"],
            category = f["category"],
            rule     = f["rule"],
            body     = f"{f['message']}\n\n**Detected snippet:** `{f['snippet']}`"
        ))

    # LLM findings — validate before accepting
    for issue in llm_result.get("issues", []):
        path = issue.get("path", "").strip()
        try:
            line = int(issue.get("line", 0))
        except (ValueError, TypeError):
            continue

        # Validate file and line exist in actual PR diff
        if path not in valid_lines_map:
            log.warning(f"  LLM hallucinated file: '{path}' — rejected")
            continue
        if line not in valid_lines_map.get(path, set()):
            log.warning(f"  LLM invalid line: {path}:{line} — rejected")
            continue

        try:
            all_issues.append(SecurityIssue(
                path     = path,
                line     = line,
                severity = issue.get("severity", "medium"),
                category = issue.get("category", "owasp"),
                rule     = issue.get("rule", "LLM_FINDING"),
                body     = issue["comment"]
            ))
        except (KeyError, TypeError) as e:
            log.warning(f"Skipping bad LLM issue: {e}")

    # Score: high=15pts, medium=8pts, low=3pts — capped at 50
    deduction = sum(
        15 if i.severity == "high" else 8 if i.severity == "medium" else 3
        for i in all_issues
    )
    deduction = min(deduction, 50)

    summary = llm_result.get("summary") or f"Found {len(all_issues)} security issue(s)."

    result = SecurityResult(
        repo_name       = repo_name,
        pr_number       = pr_number,
        summary         = summary,
        issues          = all_issues,
        score_deduction = deduction
    )

    log.info(f"Total issues: {len(all_issues)} | Deduction: {deduction}")

    # Step 5 — Post to GitHub
    log.info("Step 5/5 — Posting to GitHub...")
    post_inline_comments(pr, all_issues)
    post_security_summary(pr, result)

    log.info(f"Security Agent done — {len(all_issues)} issues | -{deduction} pts")
    return result


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("\n========================================")
    print("  RepoGuardian — Security Agent")
    print("========================================\n")

    if len(sys.argv) != 3:
        print("Usage:   python tools/security.py <owner/repo> <pr_number>")
        print("Example: python tools/security.py vamshi/myproject 1")
        sys.exit(1)

    repo_arg = sys.argv[1]
    pr_arg   = int(sys.argv[2])

    missing = [k for k in ["GROQ_API_KEY", "GITHUB_TOKEN"] if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing in .env: {', '.join(missing)}")
        sys.exit(1)

    result = run_security_agent(repo_arg, pr_arg)

    print("\n========================================")
    print("  RESULT")
    print("========================================")
    print(f"  PR             : #{result.pr_number} in {result.repo_name}")
    print(f"  Score deduction: -{result.score_deduction} pts")
    print(f"  Issues found   : {len(result.issues)}")
    print(f"  Summary        : {result.summary}")
    print("========================================")

    for i, issue in enumerate(result.issues, 1):
        emoji = SEVERITY_EMOJI.get(issue.severity, "o")
        print(f"\n  {i}. {emoji} [{issue.severity.upper()}] {issue.path} line {issue.line}")
        print(f"     Rule     : {issue.rule}")
        print(f"     Category : {issue.category}")
        print(f"     Detail   : {issue.body[:100]}...")