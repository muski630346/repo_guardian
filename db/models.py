from dataclasses import dataclass

@dataclass
class Finding:
    agent: str        # "security" | "dependency" | "complexity" | "review"
    severity: str     # "high" | "medium" | "low"
    message: str
    file: str
    line: int

@dataclass  
class RepoHealth:
    score: int        # 0–100
    pr_number: int
    findings: list[Finding]