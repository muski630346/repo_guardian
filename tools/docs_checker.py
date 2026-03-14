
import ast
import os
from typing import Any

def check_docstrings(file_contents: dict[str, str]) -> list[dict]:
    """
    Check Python files for missing docstrings.
    Returns list of findings in the standard dict format.
    """
    findings = []

    for filename, code in file_contents.items():
        if not filename.endswith(".py"):
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                has_docstring = (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if not has_docstring:
                    findings.append({
                        "severity": "medium",
                        "message": f"Missing docstring in `{node.name}`",
                        "line": node.lineno,
                        "file": filename,
                        "type": "missing_docstring"
                    })

    return findings


def check_inline_comments(file_contents: dict[str, str]) -> list[dict]:
    """
    Flag functions longer than 10 lines with zero inline comments.
    """
    findings = []

    for filename, code in file_contents.items():
        if not filename.endswith(".py"):
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue

        lines = code.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno - 1
                end = node.end_lineno
                func_lines = lines[start:end]
                func_length = len(func_lines)
                comment_count = sum(1 for l in func_lines if "#" in l)

                if func_length > 10 and comment_count == 0:
                    findings.append({
                        "severity": "low",
                        "message": f"Function `{node.name}` is {func_length} lines with no inline comments",
                        "line": node.lineno,
                        "file": filename,
                        "type": "no_inline_comments"
                    })

    return findings


def check_readme(repo_files: list[str], readme_content: str | None) -> list[dict]:
    """
    Check README completeness.
    """
    findings = []

    if readme_content is None:
        findings.append({
            "severity": "high",
            "message": "README.md is missing entirely from the repository",
            "line": 0,
            "file": "README.md",
            "type": "missing_readme"
        })
        return findings

    required_sections = ["installation", "usage", "setup", "requirements"]
    readme_lower = readme_content.lower()

    for section in required_sections:
        if section not in readme_lower:
            findings.append({
                "severity": "low",
                "message": f"README.md appears to be missing a `{section}` section",
                "line": 0,
                "file": "README.md",
                "type": "incomplete_readme"
            })

    return findings


def run_docs_check(file_contents: dict[str, str], readme_content: str | None = None) -> list[dict]:
    """
    Master function — runs all doc checks and returns combined findings.
    """
    findings = []
    findings += check_docstrings(file_contents)
    findings += check_inline_comments(file_contents)
    findings += check_readme(list(file_contents.keys()), readme_content)
    return findings
def summarise_findings(findings: list[dict]) -> dict:
    """
    Returns a count breakdown by severity.
    Useful for dashboard health score later.
    """
    summary = {"high": 0, "medium": 0, "low": 0, "total": len(findings)}
    for f in findings:
        sev = f.get("severity", "low")
        summary[sev] = summary.get(sev, 0) + 1
    return summary