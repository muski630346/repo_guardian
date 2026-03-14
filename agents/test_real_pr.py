import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from tools.pr_file_loader import load_files_from_pr, load_readme_from_repo
from agents.docs_agent import run_docs_agent
from tools.docs_checker import summarise_findings

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "muski630346/repo_guardian"  # ← change this
PR_NUMBER = 1                                 # ← change this

print(f"📥 Loading PR #{PR_NUMBER} files from {REPO}...")
file_contents = load_files_from_pr(REPO, PR_NUMBER, GITHUB_TOKEN)
readme = load_readme_from_repo(REPO, GITHUB_TOKEN)

print(f"📄 Files loaded: {list(file_contents.keys())}")
print(f"📘 README found: {readme is not None}\n")

print("🔍 Running Docs Agent...\n")
findings = run_docs_agent(file_contents, readme)
summary = summarise_findings(findings)

print(f"\n=== RESULTS ===")
print(f"HIGH: {summary['high']} | MEDIUM: {summary['medium']} | LOW: {summary['low']}\n")

for f in findings:
    print(f"[{f['severity'].upper()}] {f['file']} line {f['line']}: {f['message']}")
    if "suggestion" in f:
        print(f"  → {f['suggestion']}")
    print()