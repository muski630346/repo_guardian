from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Finding:
    agent: str        # "security" | "dependency" | "complexity" | "pr_review"
    severity: str     # "high" | "medium" | "low"
    message: str
    file: str
    line: int
    suggestion: str = ""

@dataclass
class RepoHealth:
    score: int
    pr_number: int
    findings: List[Finding]

@dataclass
class ReviewResult:
    pr_number: int
    repo: str
    findings: List[Finding]
    health_score: int
    metadata: Dict = field(default_factory=dict)