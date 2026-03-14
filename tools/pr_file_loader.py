# tools/pr_file_loader.py
import requests

def load_files_from_pr(repo: str, pr_number: int, github_token: str) -> dict[str, str]:
    """
    Fetches changed files from a real GitHub Pull Request.
    Returns {filename: file_content} dict ready for docs_agent.
    
    Args:
        repo: "owner/repo-name"  e.g. "snigdha/repo-guardian"
        pr_number: the PR number
        github_token: your GitHub personal access token
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get list of changed files in PR
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    file_contents = {}

    for file in response.json():
        filename = file["filename"]

        # Only process Python files
        if not filename.endswith(".py"):
            continue

        # Get raw file content
        raw_url = file.get("raw_url")
        if raw_url:
            raw_response = requests.get(raw_url, headers=headers)
            if raw_response.status_code == 200:
                file_contents[filename] = raw_response.text

    return file_contents


def load_readme_from_repo(repo: str, github_token: str) -> str | None:
    """
    Fetches README.md content from the repo root.
    Returns content string or None if not found.
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.raw"
    }

    url = f"https://api.github.com/repos/{repo}/contents/README.md"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.text
    return None