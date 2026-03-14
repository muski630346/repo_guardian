from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Finding:
    agent: str          # "security" | "dependency" | "complexity"
    severity: str       # "high" | "medium" | "low"
    message: str        # what the problem is
    file: str           # which file
    line: int           # which line number
    suggestion: str     # how to fix it
    cwe: Optional[str] = None  # e.g. "CWE-89"


@dataclass
class ReviewResult:
    pr_number: int
    repo: str
    findings: List[Finding] = field(default_factory=list)
    health_score: int = 0

    def calculate_health_score(self) -> int:
        deductions = {"high": 15, "medium": 7, "low": 2}
        total = sum(deductions.get(f.severity, 0) for f in self.findings)
        self.health_score = max(0, 100 - total)
        return self.health_score