"""
RepoGuardian — Voice Agent
Reads EVERYTHING from db/memory_store.json.
Passes actual finding messages, files, lines, severities to LLM.
Manager gets precise answers — no hallucination, no generic responses.

Install:
    pip install groq SpeechRecognition pyaudio gtts pygame python-dotenv

Run:
    python voice_agent/voice_agent.py           # auto-detect
    python voice_agent/voice_agent.py --text    # text mode
    python voice_agent/voice_agent.py --voice   # voice mode
"""

import os
import sys
import json
import logging
import tempfile
import argparse
from collections import defaultdict

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VOICE] %(message)s")
log = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY in .env")

client = Groq(api_key=GROQ_API_KEY)

MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "db", "memory_store.json"
)


# ─────────────────────────────────────────
# Load Memory
# ─────────────────────────────────────────

def load_memory() -> dict:
    if not os.path.exists(MEMORY_PATH):
        log.warning(f"Memory store not found: {MEMORY_PATH}")
        return {}
    with open(MEMORY_PATH, "r") as f:
        return json.load(f)


# ─────────────────────────────────────────
# Extract ALL findings from pr_history
# This is the key fix — reads inside pr_history[].findings
# not just the top-level category_counts
# ─────────────────────────────────────────

def extract_all_findings(profile: dict) -> list[dict]:
    """Pull every single finding from every PR in history."""
    all_findings = []
    for pr in profile.get("pr_history", []):
        for f in pr.get("findings", []):
            f["pr_number"] = pr.get("pr_number", "?")
            f["pr_score"]  = pr.get("score", "?")
            all_findings.append(f)
    return all_findings


def score_trend(pr_history: list) -> str:
    scores = [r.get("score", 0) for r in pr_history[-5:]]
    if len(scores) < 2:
        return "not enough data"
    arrow = " -> ".join(str(s) for s in scores)
    if scores[-1] > scores[0]:   return f"improving ({arrow})"
    if scores[-1] < scores[0]:   return f"declining ({arrow})"
    return f"stable ({arrow})"


# ─────────────────────────────────────────
# Build Rich Context — passes ACTUAL data
# ─────────────────────────────────────────

def build_context(store: dict, question: str) -> str:
    """
    Reads the full memory JSON including all findings inside pr_history.
    Builds a rich context with actual file names, messages, line numbers.
    """
    if not store:
        return "NO DATA: Memory store is empty. No PRs have been reviewed yet."

    q_lower = question.lower()

    # ── Single developer ──────────────────────────────────────
    for username, profile in store.items():
        if username.lower() in q_lower:
            pr_history   = profile.get("pr_history", [])
            all_findings = extract_all_findings(profile)

            if not all_findings:
                return f"DATA: @{username} exists but has no findings recorded yet."

            # Score stats
            recent_scores = [r.get("score", 0) for r in pr_history[-5:]]
            avg_score     = round(sum(recent_scores) / len(recent_scores), 1) if recent_scores else 0
            latest_pr     = pr_history[-1] if pr_history else {}

            # Group findings by severity
            high   = [f for f in all_findings if f.get("severity") == "high"]
            medium = [f for f in all_findings if f.get("severity") == "medium"]
            low    = [f for f in all_findings if f.get("severity") == "low"]

            # Group by file
            by_file: dict = defaultdict(list)
            for f in all_findings:
                by_file[f.get("file", "unknown")].append(f)

            # Group by agent
            by_agent: dict = defaultdict(list)
            for f in all_findings:
                by_agent[f.get("agent", "unknown")].append(f)

            # Group by category
            by_category: dict = defaultdict(list)
            for f in all_findings:
                for cat in f.get("categories", [f.get("agent", "unknown")]):
                    by_category[cat].append(f)

            # Format high severity details
            high_details = "\n".join(
                f"  - [{f.get('file','?')} line {f.get('line','?')}] "
                f"({f.get('agent','?')}) {f.get('message','')[:150]}"
                for f in high[:8]
            ) or "  none"

            # Format medium severity details
            medium_details = "\n".join(
                f"  - [{f.get('file','?')} line {f.get('line','?')}] "
                f"({f.get('agent','?')}) {f.get('message','')[:150]}"
                for f in medium[:5]
            ) or "  none"

            # Format file breakdown
            file_details = "\n".join(
                f"  - {fname}: {len(findings)} issue(s) "
                f"({sum(1 for x in findings if x.get('severity')=='high')} high, "
                f"{sum(1 for x in findings if x.get('severity')=='medium')} medium, "
                f"{sum(1 for x in findings if x.get('severity')=='low')} low)"
                for fname, findings in by_file.items()
            )

            # Format agent breakdown
            agent_details = "\n".join(
                f"  - {agent}: {len(findings)} finding(s). "
                f"Sample: {findings[0].get('message','')[:120]}"
                for agent, findings in by_agent.items()
            )

            # Format category breakdown
            category_details = "\n".join(
                f"  - {cat}: {len(findings)} occurrence(s). "
                f"Example: {findings[0].get('message','')[:120]}"
                for cat, findings in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)
                if cat not in {"security", "pr_review", "dependency", "docs", "complexity"}
            )

            # PR history summary
            pr_summary = "\n".join(
                f"  - PR #{pr.get('pr_number','?')} in {pr.get('repo','?')}: "
                f"score {pr.get('score','?')}/100, "
                f"{len(pr.get('findings',[]))} findings"
                for pr in pr_history[-5:]
            )

            return f"""
DEVELOPER DATA FOR @{username}:

=== SCORES ===
Average health score (last 5 PRs): {avg_score}/100
Score trend: {score_trend(pr_history)}
Total PRs reviewed: {profile.get('total_prs', 0)}
Total findings ever: {profile.get('total_findings', 0)}
Latest PR: #{latest_pr.get('pr_number','?')} scored {latest_pr.get('score','?')}/100

=== SEVERITY BREAKDOWN ===
High severity (critical): {len(high)} issues
Medium severity (warnings): {len(medium)} issues
Low severity (minor): {len(low)} issues

=== HIGH SEVERITY ISSUES (must fix) ===
{high_details}

=== MEDIUM SEVERITY ISSUES (should fix) ===
{medium_details}

=== FILES WITH ISSUES ===
{file_details}

=== FINDINGS BY AGENT ===
{agent_details}

=== FINDINGS BY CATEGORY ===
{category_details}

=== PR HISTORY (last 5) ===
{pr_summary}

=== FIRST SEEN / LAST SEEN ===
First PR reviewed: {profile.get('first_seen','?')[:10]}
Latest PR reviewed: {profile.get('last_seen','?')[:10]}
""".strip()

    # ── Team context ──────────────────────────────────────────
    team_lines = []
    all_scores = []

    for username, profile in store.items():
        pr_history    = profile.get("pr_history", [])
        all_findings  = extract_all_findings(profile)
        recent_scores = [r.get("score", 0) for r in pr_history[-5:]]
        avg           = round(sum(recent_scores) / len(recent_scores), 1) if recent_scores else 0
        high_count    = sum(1 for f in all_findings if f.get("severity") == "high")
        all_scores.append((username, avg))

        # Top category
        cat_counts: dict = defaultdict(int)
        for f in all_findings:
            for cat in f.get("categories", []):
                if cat not in {"security", "pr_review", "dependency", "docs", "complexity"}:
                    cat_counts[cat] += 1
        top_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "none"

        team_lines.append(
            f"  @{username}: {profile.get('total_prs',0)} PRs reviewed, "
            f"avg score {avg}/100, "
            f"trend: {score_trend(pr_history)}, "
            f"{high_count} critical issues, "
            f"top problem: {top_cat} ({cat_counts.get(top_cat,0)} times)"
        )

    team_avg = round(sum(s for _, s in all_scores) / len(all_scores), 1)
    best     = max(all_scores, key=lambda x: x[1])
    worst    = min(all_scores, key=lambda x: x[1])

    # Team-wide most common issue
    team_cats: dict = defaultdict(int)
    for profile in store.values():
        for f in extract_all_findings(profile):
            for cat in f.get("categories", []):
                if cat not in {"security", "pr_review", "dependency", "docs", "complexity"}:
                    team_cats[cat] += 1
    top_team = max(team_cats, key=team_cats.get) if team_cats else "none"

    return f"""
TEAM DATA ({len(store)} developers):

=== TEAM OVERVIEW ===
Team average health score: {team_avg}/100
Best performer: @{best[0]} ({best[1]}/100)
Needs most attention: @{worst[0]} ({worst[1]}/100)
Most common team problem: {top_team} ({team_cats.get(top_team,0)} occurrences)

=== INDIVIDUAL DEVELOPERS ===
{chr(10).join(team_lines)}
""".strip()


# ─────────────────────────────────────────
# System Prompt — Anti-Hallucination
# ─────────────────────────────────────────

SYSTEM_PROMPT = """
You are RepoGuardian, a voice assistant for engineering managers.
You answer questions about developer code quality.

CRITICAL ANTI-HALLUCINATION RULES:
- Use ONLY the exact data provided — never invent numbers, file names, or issue descriptions
- If a specific file is mentioned in the data, name it exactly
- If specific messages are in the data, reference them directly
- NEVER say "typically" or "usually" or "in general" — only speak about THIS developer's actual data
- If something is not in the data, say "that information is not in the memory store"

ANSWER RULES:
- Answer ONLY what was specifically asked
- Asked about security?     → use ONLY the security findings section
- Asked about a file?       → use ONLY that file's findings from the FILES section
- Asked about logic?        → use ONLY logic entries from FINDINGS BY CATEGORY
- Asked about score?        → use ONLY the scores section
- Asked about high issues?  → use ONLY the HIGH SEVERITY ISSUES section
- Asked for a summary?      → give overview using all sections
- 2 to 4 sentences maximum
- No bullet points, no markdown, no symbols
- Plain spoken English only — this is read aloud
- End with one specific recommendation based on the actual data
"""


# ─────────────────────────────────────────
# LLM Call
# ─────────────────────────────────────────

def ask_llm(question: str, context: str) -> str:
    try:
        response = client.chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": (
                    f"DEVELOPER DATA FROM MEMORY STORE:\n\n"
                    f"{context}\n\n"
                    f"MANAGER'S QUESTION: {question}\n\n"
                    f"Answer ONLY what was asked using ONLY the data above. "
                    f"Name specific files and issues from the data. "
                    f"2 to 4 sentences. Plain English. No markdown."
                )},
            ],
            temperature = 0.1,
            max_tokens  = 200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"LLM failed: {e}")
        return "Sorry, I could not generate an answer right now."


# ─────────────────────────────────────────
# Speak
# ─────────────────────────────────────────

def speak(text: str):
    try:
        from gtts import gTTS
        import pygame

        tts = gTTS(text=text, lang="en", slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tts.save(tmp.name)
            tmp_path = tmp.name

        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        os.remove(tmp_path)
    except ImportError:
        pass
    except Exception as e:
        log.warning(f"TTS failed: {e}")


# ─────────────────────────────────────────
# Listen
# ─────────────────────────────────────────

def listen() -> str | None:
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.pause_threshold  = 1.0

        print("🎤  Listening...")

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio.get_wav_data())
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model = "whisper-large-v3",
                    file  = f,
                )
            text = result.text.strip()
            print(f"📝  You said: \"{text}\"")
            return text
        finally:
            os.remove(tmp_path)

    except ImportError:
        print("⚠️  Install: pip install SpeechRecognition pyaudio")
        return None
    except Exception as e:
        print(f"⚠️  Audio error: {e}")
        return None


# ─────────────────────────────────────────
# Full Pipeline
# ─────────────────────────────────────────

def process(question: str):
    print(f"\n{'─' * 55}")
    store    = load_memory()
    context  = build_context(store, question)
    print("🧠  Thinking...")
    response = ask_llm(question, context)
    print(f"\n🤖  RepoGuardian:\n    {response}\n")
    speak(response)


# ─────────────────────────────────────────
# Text Mode
# ─────────────────────────────────────────

def run_text_mode():
    print("\n" + "=" * 55)
    print("  RepoGuardian Voice Agent  —  TEXT MODE")
    print("=" * 55)

    store = load_memory()
    if store:
        print(f"\n  Developers : {', '.join('@' + u for u in store.keys())}")
        total = sum(len(extract_all_findings(p)) for p in store.values())
        print(f"  Findings   : {total} total across all PRs")
    else:
        print("\n  No memory data. Run RepoGuardian on a PR first.")

    print("\n  Try these questions:")
    if store:
        username = list(store.keys())[0]
        print(f"    What security issues does {username} have?")
        print(f"    Which files have the most problems for {username}?")
        print(f"    What high severity issues does {username} have?")
        print(f"    What logic issues were found for {username}?")
        print(f"    Give me a full summary of {username}")
        print(f"    Is {username} improving?")
    print("\n  Type 'quit' to exit")
    print("-" * 55)

    while True:
        try:
            question = input("\nYou: ").strip()
            if not question:
                continue
            if question.lower() in ["quit", "exit", "q"]:
                print("Goodbye.")
                break
            process(question)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break


# ─────────────────────────────────────────
# Voice Mode
# ─────────────────────────────────────────

def run_voice_mode():
    print("\n" + "=" * 55)
    print("  RepoGuardian Voice Agent  —  VOICE MODE")
    print("=" * 55)

    store = load_memory()
    if store:
        print(f"\n  Developers : {', '.join('@' + u for u in store.keys())}")
    else:
        print("\n  No memory data. Run RepoGuardian on a PR first.")

    print("\n  Press Ctrl+C to quit")
    print("-" * 55)

    speak("RepoGuardian is ready. Ask me about your developers.")

    while True:
        try:
            print()
            question = listen()
            if not question:
                print("Nothing heard — try again.")
                continue
            if any(w in question.lower() for w in ["quit", "exit", "stop", "goodbye"]):
                speak("Goodbye.")
                break
            process(question)
        except KeyboardInterrupt:
            print("\nGoodbye.")
            speak("Goodbye.")
            break


# ─────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoGuardian Voice Agent")
    parser.add_argument("--text",  action="store_true", help="Force text mode")
    parser.add_argument("--voice", action="store_true", help="Force voice mode")
    args = parser.parse_args()

    if args.text:
        run_text_mode()
    elif args.voice:
        run_voice_mode()
    else:
        mic_available = False
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            mic_available = p.get_device_count() > 0
            p.terminate()
        except Exception:
            pass

        if mic_available:
            print("Microphone detected — starting VOICE MODE")
            run_voice_mode()
        else:
            print("No microphone — starting TEXT MODE")
            run_text_mode()