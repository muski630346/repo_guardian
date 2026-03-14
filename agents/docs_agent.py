# agents/docs_agent.py
import os
from crewai import Agent, Task, Crew, LLM
from tools.docs_checker import run_docs_check
from dotenv import load_dotenv

load_dotenv()


def build_docs_agent():
    """Create and return the Docs Agent using Groq LLM."""

    llm = LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )

    docs_agent = Agent(
        role="Documentation Quality Reviewer",
        goal=(
            "Ensure every function, class, and module in the Pull Request has proper "
            "docstrings, meaningful inline comments, and that the README is complete. "
            "Produce clear, actionable findings in standard severity format."
        ),
        backstory=(
            "You are a senior engineer who believes undocumented code is broken code. "
            "You have reviewed thousands of PRs and know exactly where documentation "
            "debt hides and how it slows teams down six months later."
        ),
        llm=llm,
        verbose=True
    )

    return docs_agent


def run_docs_agent(file_contents: dict, readme_content: str | None = None) -> list[dict]:
    """
    Main entry point called by the Orchestrator.

    Args:
        file_contents: dict of {filename: file_code_string}
        readme_content: string content of README.md, or None if missing

    Returns:
        List of findings in standard format:
        {"severity": "high/medium/low", "message": "...", "line": 42, "file": "..."}
    """

    # Step 1: Run static AST checks (fast, no LLM needed)
    static_findings = run_docs_check(file_contents, readme_content)

    print(f"\n📋 Static analysis complete — {len(static_findings)} raw findings found.")

    if not static_findings:
        print("✅ No documentation issues found.")
        return []

    # Step 2: Format findings for LLM
    findings_summary = "\n".join([
        f"{i+1}. [{f['severity'].upper()}] {f['file']} line {f['line']}: {f['message']}"
        for i, f in enumerate(static_findings)
    ])

    # Step 3: Build agent and task
    agent = build_docs_agent()

    task = Task(
        description=f"""
You are reviewing documentation quality findings from a Pull Request analysis.

Here are the raw findings from static analysis:
{findings_summary}

Your job:
- For each finding, write ONE short, specific, actionable suggestion on how to fix it.
- Do NOT skip any finding.
- Do NOT add any intro or summary text.
- Respond ONLY as a numbered list matching the exact same order as the findings above.
- Each line must start with the number followed by a period. Example: "1. Add a docstring explaining what parameters this function expects."

Keep each suggestion under 20 words. Be direct.
        """,
        expected_output=(
            "A numbered list of actionable suggestions, one per finding, "
            "in the same order as the input findings. No extra text."
        ),
        agent=agent
    )

    # Step 4: Run the crew
    print("\n🤖 Docs Agent (LLM) is enriching findings with suggestions...\n")
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()

    # Step 5: Parse LLM suggestions and merge into findings
    raw_output = str(result).strip()
    suggestions = []

    for line in raw_output.split("\n"):
        line = line.strip()
        if line and line[0].isdigit() and "." in line:
            # Strip the number prefix e.g. "1. Add docstring" → "Add docstring"
            suggestion_text = line.split(".", 1)[-1].strip()
            suggestions.append(suggestion_text)

    print(f"💡 LLM generated {len(suggestions)} suggestions for {len(static_findings)} findings.\n")

    # Step 6: Attach suggestions to findings
    for i, finding in enumerate(static_findings):
        if i < len(suggestions):
            finding["suggestion"] = suggestions[i]
        else:
            finding["suggestion"] = "Add appropriate documentation for this item."

    return static_findings