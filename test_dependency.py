from tools.dependency import run_dependency_scan

requirements = """
flask==0.12.2
django==2.0.0
requests>=2.18.0
pycrypto
numpy
urllib3==1.21.1
pyyaml
"""

print("=" * 60)
print("  RepoGuardian — Dependency Scan")
print("=" * 60)
print()

findings = run_dependency_scan(requirements, "requirements.txt")

categories = {"CVE": [], "UNPINNED": [], "DANGEROUS": []}
for f in findings:
    for cat in categories:
        if cat in f.message:
            categories[cat].append(f)
            break

icons = {"high": "🔴", "medium": "🟡", "low": "🔵"}

for cat, items in categories.items():
    if items:
        print(f"── {cat} ({len(items)} issues) " + "─" * 30)
        for f in items:
            icon = icons.get(f.severity, "⚪")
            print(f"  {icon} {f.message}")
            print(f"     Fix: {f.suggestion}")
            print()

from db.models import ReviewResult
result = ReviewResult(pr_number=1, repo="test/repo", findings=findings)
score = result.calculate_health_score()
print(f"📊 Health Score: {score}/100  |  Total issues: {len(findings)}")