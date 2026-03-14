from tools.security import run_full_security_scan

# Intentionally buggy code covering all 5 areas
code = """
import subprocess
import hashlib
import pickle
import random

# SECRET — hardcoded credentials
API_KEY = "sk-abc123secretkey456"
PASSWORD = "supersecret123"
AWS_KEY = "AKIAiosfodnn7EXAMPLE"

# VULN — SQL injection
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

# VULN — shell injection
def run_cmd(cmd):
    subprocess.call(cmd, shell=True)

# VULN — weak hash
def hash_password(p):
    return hashlib.md5(p.encode()).hexdigest()

# ADVANCED — insecure deserialization
def load_data(data):
    return pickle.loads(data)

# QUALITY — bare except
def risky():
    try:
        pass
    except:
        pass

# QUALITY — printing secret
def debug():
    print("password:", PASSWORD)

# QUALITY — SSL disabled
import requests
def call_api():
    requests.get("https://api.example.com", verify=False)

# QUALITY — TODO left in
# TODO: fix this before release
# FIXME: this is broken

DEBUG = True
"""

# Also test with vulnerable requirements
requirements = """
flask==0.12.2
django==2.0.0
requests==2.18.0
"""

print("=" * 60)
print("  RepoGuardian — Full Security Scan")
print("=" * 60)
print()

findings = run_full_security_scan(code, "app.py", requirements)

# Group by category
categories = {
    "VULN":       [],
    "SECRET":     [],
    "ADVANCED":   [],
    "QUALITY":    [],
    "DEPENDENCY": [],
}

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
            print(f"  {icon} Line {f.line}: {f.message}")
            print(f"     Fix: {f.suggestion}")
            print()

from db.models import ReviewResult
result = ReviewResult(pr_number=1, repo="test/repo", findings=findings)
score  = result.calculate_health_score()
print(f"  📊 Repo Health Score: {score}/100")
print(f"  Total issues found:   {len(findings)}")