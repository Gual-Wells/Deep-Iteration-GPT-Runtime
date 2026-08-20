"""Immutable repository-delegated protocol authority records for DIGR 5.0.0-alpha.4."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .protocol_pin import validate_commit_sha
from .routing import AUTHORITATIVE_REPOSITORY, RouteReceipt, load_route_metadata
from .validation import require_nonempty_text

@dataclass(frozen=True)
class ProtocolIdentity:
    protocol: str
    version: str
    repository_full_name: str
    commit_sha: str

    def __post_init__(self):
        object.__setattr__(self, 'protocol', require_nonempty_text('protocol', self.protocol))
        object.__setattr__(self, 'version', require_nonempty_text('version', self.version))
        repo = require_nonempty_text('repository_full_name', self.repository_full_name)
        if repo != AUTHORITATIVE_REPOSITORY:
            raise ValueError(f'P_run must come from authoritative repository {AUTHORITATIVE_REPOSITORY}')
        object.__setattr__(self, 'repository_full_name', repo)
        object.__setattr__(self, 'commit_sha', validate_commit_sha(self.commit_sha))

@dataclass(frozen=True)
class ProtocolAuthority:
    route: RouteReceipt
    P_run: ProtocolIdentity

    def __post_init__(self):
        if not isinstance(self.route, RouteReceipt):
            raise TypeError('route must be RouteReceipt')
        if not isinstance(self.P_run, ProtocolIdentity):
            raise TypeError('P_run must be ProtocolIdentity')
        if self.P_run.repository_full_name != self.route.repository_full_name:
            raise ValueError('P_run repository does not match route receipt')
        if self.P_run.commit_sha != self.route.pinned_commit:
            raise ValueError('P_run commit does not match route receipt')

    def to_dict(self) -> dict[str, Any]:
        return {'route': self.route.to_dict(), 'P_run': asdict(self.P_run)}


def authority_from_route_bytes(route: RouteReceipt, manifest_data: bytes, version_data: bytes) -> ProtocolAuthority:
    manifest, version = load_route_metadata(route, manifest_data, version_data)
    ident = ProtocolIdentity(
        protocol=require_nonempty_text('manifest protocol', manifest.get('protocol')),
        version=version,
        repository_full_name=route.repository_full_name,
        commit_sha=route.pinned_commit,
    )
    return ProtocolAuthority(route=route, P_run=ident)
