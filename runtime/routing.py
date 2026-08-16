"""Version-semantic-free repository routing records for DIGR 4.1.0.

This module knows only how to validate immutable repository provenance and how
to discover protocol file paths declared by a pinned manifest. It does not
interpret DIGR invocation syntax, timing rules, parameters, stop gates or proof.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any, Mapping, Sequence
import json
from .protocol_pin import validate_commit_sha, validate_repo_path
from .validation import require_nonempty_text

AUTHORITATIVE_REPOSITORY = 'Gual-Wells/Deep-Iteration-GPT-Runtime'
AUTHORITATIVE_REF = 'stable'
MANIFEST_PATH = 'manifest.json'


def manifest_sha256(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError('manifest data must be bytes')
    return sha256(bytes(data)).hexdigest()


@dataclass(frozen=True)
class RouteReceipt:
    repository_full_name: str
    requested_ref: str
    pinned_commit: str
    manifest_path: str
    manifest_sha256: str

    def __post_init__(self):
        repo = require_nonempty_text('repository_full_name', self.repository_full_name)
        if repo != AUTHORITATIVE_REPOSITORY:
            raise ValueError(f'unexpected DIGR repository: {repo}')
        ref = require_nonempty_text('requested_ref', self.requested_ref)
        if ref != AUTHORITATIVE_REF:
            raise ValueError(f'unexpected DIGR routing ref: {ref}')
        path = validate_repo_path(self.manifest_path)
        if path != MANIFEST_PATH:
            raise ValueError(f'unexpected DIGR manifest path: {path}')
        digest = require_nonempty_text('manifest_sha256', self.manifest_sha256).lower()
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('manifest_sha256 must be 64 lowercase hex characters')
        object.__setattr__(self, 'repository_full_name', repo)
        object.__setattr__(self, 'requested_ref', ref)
        object.__setattr__(self, 'pinned_commit', validate_commit_sha(self.pinned_commit))
        object.__setattr__(self, 'manifest_path', path)
        object.__setattr__(self, 'manifest_sha256', digest)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiscoveryPlan:
    bootstrap_entry: str | None
    entrypoint: str
    core: tuple[str, ...]
    help_path: str | None
    legacy_manifest: bool

    def __post_init__(self):
        if self.bootstrap_entry is not None:
            object.__setattr__(self, 'bootstrap_entry', validate_repo_path(self.bootstrap_entry))
        object.__setattr__(self, 'entrypoint', validate_repo_path(self.entrypoint))
        if not isinstance(self.core, tuple) or not self.core:
            raise ValueError('core must be a non-empty tuple')
        object.__setattr__(self, 'core', tuple(validate_repo_path(x) for x in self.core))
        if len(set(self.core)) != len(self.core):
            raise ValueError('core contains duplicate paths')
        if self.help_path is not None:
            object.__setattr__(self, 'help_path', validate_repo_path(self.help_path))
        if not isinstance(self.legacy_manifest, bool):
            raise TypeError('legacy_manifest must be bool')

    @property
    def load_paths(self) -> tuple[str, ...]:
        out: list[str] = []
        if self.bootstrap_entry is not None:
            out.append(self.bootstrap_entry)
        out.append(self.entrypoint)
        out.extend(self.core)
        if self.help_path is not None:
            out.append(self.help_path)
        # preserve order while deduplicating entry/core/help overlap safely
        return tuple(dict.fromkeys(out))

    def to_dict(self) -> dict[str, Any]:
        return {
            'bootstrap_entry': self.bootstrap_entry,
            'entrypoint': self.entrypoint,
            'core': list(self.core),
            'help_path': self.help_path,
            'legacy_manifest': self.legacy_manifest,
            'load_paths': list(self.load_paths),
        }


def discovery_plan_from_manifest(manifest: Mapping[str, Any]) -> DiscoveryPlan:
    """Return only manifest-declared protocol locations; do not interpret semantics.

    4.1+ manifests may declare ``bootstrap_entry``. Legacy manifests are routed
    through their existing ``entrypoint`` + ``core`` declarations. This is a
    discovery compatibility rule, not a protocol-semantic fallback.
    """
    if not isinstance(manifest, Mapping):
        raise TypeError('manifest must be a mapping')
    entry = validate_repo_path(manifest.get('entrypoint'))
    raw_core = manifest.get('core')
    if not isinstance(raw_core, Sequence) or isinstance(raw_core, (str, bytes)) or not raw_core:
        raise ValueError('manifest core must be a non-empty sequence')
    core = tuple(validate_repo_path(x) for x in raw_core)
    boot = manifest.get('bootstrap_entry')
    if boot is not None:
        boot = validate_repo_path(boot)
    help_path = manifest.get('help')
    if help_path is not None:
        help_path = validate_repo_path(help_path)
    return DiscoveryPlan(boot, entry, core, help_path, boot is None)

def load_manifest_for_route(route: RouteReceipt, data: bytes) -> dict[str, Any]:
    """Verify raw manifest bytes against the route receipt, then parse JSON."""
    if not isinstance(route, RouteReceipt):
        raise TypeError('route must be RouteReceipt')
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError('manifest data must be bytes')
    raw = bytes(data)
    if manifest_sha256(raw) != route.manifest_sha256:
        raise ValueError('manifest bytes do not match route receipt digest')
    try:
        obj = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('pinned manifest is not valid UTF-8 JSON') from exc
    if not isinstance(obj, dict):
        raise ValueError('pinned manifest root must be an object')
    return obj


def discovery_plan_from_manifest_bytes(route: RouteReceipt, data: bytes) -> DiscoveryPlan:
    return discovery_plan_from_manifest(load_manifest_for_route(route, data))

