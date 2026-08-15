"""Small helpers for immutable DIGR protocol references.

This module performs no network I/O and makes no semantic decisions.
"""
from __future__ import annotations
import re

_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")

def validate_commit_sha(value: str) -> str:
    value = value.strip()
    if not _SHA40.fullmatch(value):
        raise ValueError("expected a full 40-character Git commit SHA")
    return value.lower()

def raw_file_url(owner: str, repo: str, commit_sha: str, path: str) -> str:
    sha = validate_commit_sha(commit_sha)
    owner = owner.strip().strip("/")
    repo = repo.strip().strip("/")
    path = path.lstrip("/")
    if not owner or not repo or not path:
        raise ValueError("owner, repo and path must be non-empty")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{path}"
