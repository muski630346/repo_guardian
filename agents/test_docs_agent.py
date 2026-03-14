# test_docs_agent.py
import sys
import os

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.docs_agent import run_docs_agent
from tools.docs_checker import summarise_findings

sample_code = {
    "agents/pr_review.py": '''
def review_pull_request(diff):
    x = diff.split("\\n")
    results = []
    for line in x:
        if "password" in line:
            results.append(line)
        if "secret" in line:
            results.append(line)
        if "token" in line:
            results.append(line)
        if "api_key" in line:
            results.append(line)
    return results

class ReviewAgent:
    def run(self):
        pass
''',
    "agents/orchestrator.py": '''
def orchestrate(pr_diff):
    return pr_diff
'''
}

readme = "# RepoGuardian\nA cool project."

print("🔍 Running Docs Agent...\n")
findings = run_docs_agent(sample_code, readme)
summary = summarise_findings(findings)

print(f"\n=== RESULTS ===")
print(f"HIGH: {summary['high']} | MEDIUM: {summary['medium']} | LOW: {summary['low']}\n")

for f in findings:
    print(f"[{f['severity'].upper()}] {f['file']} line {f['line']}: {f['message']}")
    if "suggestion" in f:
        print(f"  → {f['suggestion']}")
    print()