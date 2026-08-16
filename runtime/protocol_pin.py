"""Helpers for immutable, path-safe DIGR protocol references. No network I/O."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from urllib.parse import quote
from .validation import require_nonempty_text

_SHA40 = re.compile(r'^[0-9a-fA-F]{40}$')
_REPO_TOKEN = re.compile(r'^[A-Za-z0-9._-]+$')


def validate_commit_sha(value: str) -> str:
    value = require_nonempty_text('commit SHA', value)
    if not _SHA40.fullmatch(value):
        raise ValueError('expected a full 40-character Git commit SHA')
    return value.lower()


def _repo_token(name: str, value: object) -> str:
    text = require_nonempty_text(name, value)
    if not _REPO_TOKEN.fullmatch(text) or text in ('.', '..'):
        raise ValueError(f'{name} contains unsafe repository characters')
    return text


def validate_repo_path(path: object) -> str:
    text = require_nonempty_text('path', path)
    if '\\' in text or text.startswith('/') or '\x00' in text:
        raise ValueError('path must be a relative POSIX repository path')
    p = PurePosixPath(text)
    if not p.parts or any(part in ('', '.', '..') for part in p.parts):
        raise ValueError('path contains unsafe segments')
    return p.as_posix()


@dataclass(frozen=True)
class ProtocolRef:
    owner: str
    repo: str
    commit_sha: str
    path: str

    def __post_init__(self):
        object.__setattr__(self, 'owner', _repo_token('owner', self.owner))
        object.__setattr__(self, 'repo', _repo_token('repo', self.repo))
        object.__setattr__(self, 'commit_sha', validate_commit_sha(self.commit_sha))
        object.__setattr__(self, 'path', validate_repo_path(self.path))

    @property
    def raw_url(self) -> str:
        return raw_file_url(self.owner, self.repo, self.commit_sha, self.path)


def raw_file_url(owner: str, repo: str, commit_sha: str, path: str) -> str:
    owner = _repo_token('owner', owner)
    repo = _repo_token('repo', repo)
    sha = validate_commit_sha(commit_sha)
    path = validate_repo_path(path)
    return (
        'https://raw.githubusercontent.com/'
        f'{quote(owner, safe="-._~")}/{quote(repo, safe="-._~")}/{sha}/'
        f'{quote(path, safe="/-._~")}'
    )
