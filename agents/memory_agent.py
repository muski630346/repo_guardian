import json
import os
from datetime import datetime
from typing import Optional

MEMORY_FILE = "developer_memory.json"


def load_memory(filepath: str = MEMORY_FILE) -> list:
    """Load memory from file. Returns empty list if file doesn't exist."""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []


def save_memory(memory: list, filepath: str = MEMORY_FILE) -> None:
    """Persist memory list to JSON file."""
    with open(filepath, "w") as f:
        json.dump(memory, f, indent=4)


def memory_agent(developer: str, issue: str, filepath: str = MEMORY_FILE) -> list:
    """
    Track developer issues with occurrence count and timestamps.

    Args:
        developer: Name or ID of the developer.
        issue: Description of the issue encountered.
        filepath: Path to the JSON memory file.

    Returns:
        Full memory list after recording the issue.
    """
    if not developer or not issue:
        raise ValueError("Both 'developer' and 'issue' must be non-empty strings.")

    memory = load_memory(filepath)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in memory:
        if item["developer"] == developer and item["issue"] == issue:
            item["count"] += 1
            item["last_seen"] = now
            break
    else:
        memory.append({
            "developer": developer,
            "issue": issue,
            "count": 1,
            "first_seen": now,
            "last_seen": now,
        })

    save_memory(memory, filepath)
    return memory


def get_developer_history(developer: str, filepath: str = MEMORY_FILE) -> list:
    """
    Retrieve all issues logged for a specific developer.

    Args:
        developer: Name or ID of the developer.
        filepath: Path to the JSON memory file.

    Returns:
        List of issue records for the developer, sorted by count descending.
    """
    memory = load_memory(filepath)
    history = [item for item in memory if item["developer"] == developer]
    return sorted(history, key=lambda x: x["count"], reverse=True)


def get_top_issues(limit: int = 5, filepath: str = MEMORY_FILE) -> list:
    """
    Get the most frequently occurring issues across all developers.

    Args:
        limit: Number of top issues to return.
        filepath: Path to the JSON memory file.

    Returns:
        List of top issue records sorted by count descending.
    """
    memory = load_memory(filepath)
    return sorted(memory, key=lambda x: x["count"], reverse=True)[:limit]


def delete_issue(developer: str, issue: str, filepath: str = MEMORY_FILE) -> bool:
    """
    Remove a specific issue record for a developer.

    Args:
        developer: Name or ID of the developer.
        issue: The issue string to delete.
        filepath: Path to the JSON memory file.

    Returns:
        True if the record was found and deleted, False otherwise.
    """
    memory = load_memory(filepath)
    updated = [
        item for item in memory
        if not (item["developer"] == developer and item["issue"] == issue)
    ]

    if len(updated) == len(memory):
        return False  # Nothing was removed

    save_memory(updated, filepath)
    return True


def summarize(filepath: str = MEMORY_FILE) -> dict:
    """
    Return a high-level summary of all tracked data.

    Returns:
        Dict with total_issues, unique_developers, most_active_developer, top_issue.
    """
    memory = load_memory(filepath)
    if not memory:
        return {"total_issues": 0, "unique_developers": 0}

    developers = {item["developer"] for item in memory}
    top = max(memory, key=lambda x: x["count"])
    dev_counts = {}
    for item in memory:
        dev_counts[item["developer"]] = dev_counts.get(item["developer"], 0) + item["count"]
    most_active = max(dev_counts, key=dev_counts.get)

    return {
        "total_issues": len(memory),
        "unique_developers": len(developers),
        "most_active_developer": most_active,
        "top_issue": {"developer": top["developer"], "issue": top["issue"], "count": top["count"]},
    }


# ── Quick demo ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Log some issues
    memory_agent("alice", "NullPointerException in login module")
    memory_agent("bob", "Timeout on DB connection")
    memory_agent("alice", "NullPointerException in login module")
    memory_agent("alice", "CSS misalignment on dashboard")
    memory_agent("bob", "Timeout on DB connection")
    memory_agent("bob", "Timeout on DB connection")

    print("=== Alice's History ===")
    for record in get_developer_history("alice"):
        print(f"  [{record['count']}x] {record['issue']}")

    print("\n=== Top Issues (all devs) ===")
    for record in get_top_issues(3):
        print(f"  [{record['count']}x] {record['developer']}: {record['issue']}")

    print("\n=== Summary ===")
    print(summarize())