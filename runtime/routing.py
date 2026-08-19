"""Version-semantic-free repository routing helpers for DIGR 5.0.0-alpha.3.

The router performs only candidate response, exact GitHub location, immutable
pinning metadata, manifest/VERSION integrity, and manifest-declared path
discovery. It deliberately does not interpret DIGR invocation validity, help,
parameters, timing, stop gates, or proof.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any, Mapping, Sequence
from urllib.parse import quote
import json
from .protocol_pin import validate_commit_sha, validate_repo_path
from .validation import require_nonempty_text

AUTHORITATIVE_REPOSITORY = 'Gual-Wells/Deep-Iteration-GPT-Runtime'
AUTHORITATIVE_REPOSITORY_URL = 'https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime'
AUTHORITATIVE_API_BASE = 'https://api.github.com/repos/Gual-Wells/Deep-Iteration-GPT-Runtime'
AUTHORITATIVE_REF = 'stable'
AUTHORITATIVE_REF_API_URL = AUTHORITATIVE_API_BASE + '/git/ref/heads/stable'
AUTHORITATIVE_BRANCH_API_URL = AUTHORITATIVE_API_BASE + '/branches/stable'
MANIFEST_PATH = 'manifest.json'
VERSION_PATH = 'VERSION'
CONTENT_API_TEMPLATE = AUTHORITATIVE_API_BASE + '/contents/{PATH}?ref={SHA}'
PINNED_RAW_TEMPLATE = 'https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/{PATH}'
ROUTE_KEYS = ('DIGR', '深度迭代')


def candidate_route_key(message: str) -> str | None:
    """Return the broad local route key, without validating DIGR syntax.

    Leading Unicode whitespace is ignored. ASCII ``DIGR`` is exact uppercase.
    The remainder of the message is intentionally *not* inspected: over-routing
    is preferred to letting the local layer invent versioned invocation syntax.
    """
    if not isinstance(message, str):
        raise TypeError('message must be str')
    s = message.lstrip()
    if s.startswith('DIGR'):
        return 'DIGR'
    if s.startswith('深度迭代'):
        return '深度迭代'
    return None


def is_candidate_route(message: str) -> bool:
    return candidate_route_key(message) is not None


def content_api_url(commit_sha: str, path: str) -> str:
    """Canonical GitHub Contents API URL for one file at an immutable commit."""
    sha = validate_commit_sha(commit_sha)
    rel = validate_repo_path(path)
    return (
        AUTHORITATIVE_API_BASE
        + '/contents/'
        + quote(rel, safe='/-._~')
        + '?ref='
        + sha
    )


@dataclass(frozen=True)
class RefResolution:
    ref: str
    object_type: str
    commit_sha: str
    source_url: str = AUTHORITATIVE_REF_API_URL

    def __post_init__(self):
        if self.source_url != AUTHORITATIVE_REF_API_URL:
            raise ValueError('unexpected ref source URL')
        if self.ref != 'refs/heads/stable':
            raise ValueError('unexpected GitHub ref')
        if self.object_type != 'commit':
            raise ValueError('stable ref must resolve to a commit object')
        object.__setattr__(self, 'commit_sha', validate_commit_sha(self.commit_sha))


def ref_resolution_from_github_payload(payload: Mapping[str, Any] | bytes) -> RefResolution:
    """Validate the deterministic subset of GitHub's Get-a-reference response."""
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = json.loads(bytes(payload).decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError('GitHub ref response is not valid UTF-8 JSON') from exc
    if not isinstance(payload, Mapping):
        raise TypeError('GitHub ref response must be a mapping or bytes')
    obj = payload.get('object')
    if not isinstance(obj, Mapping):
        raise ValueError('GitHub ref response missing object')
    return RefResolution(
        ref=require_nonempty_text('ref', payload.get('ref')),
        object_type=require_nonempty_text('object.type', obj.get('type')),
        commit_sha=require_nonempty_text('object.sha', obj.get('sha')),
    )


def bytes_sha256(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError('data must be bytes')
    return sha256(bytes(data)).hexdigest()


@dataclass(frozen=True)
class RouteReceipt:
    repository_full_name: str
    requested_ref: str
    pinned_commit: str
    manifest_path: str
    manifest_sha256: str
    version_path: str
    version_sha256: str

    def __post_init__(self):
        repo = require_nonempty_text('repository_full_name', self.repository_full_name)
        if repo != AUTHORITATIVE_REPOSITORY:
            raise ValueError(f'unexpected DIGR repository: {repo}')
        ref = require_nonempty_text('requested_ref', self.requested_ref)
        if ref != AUTHORITATIVE_REF:
            raise ValueError(f'unexpected DIGR routing ref: {ref}')
        mpath = validate_repo_path(self.manifest_path)
        if mpath != MANIFEST_PATH:
            raise ValueError(f'unexpected DIGR manifest path: {mpath}')
        vpath = validate_repo_path(self.version_path)
        if vpath != VERSION_PATH:
            raise ValueError(f'unexpected DIGR VERSION path: {vpath}')
        mdigest = _digest('manifest_sha256', self.manifest_sha256)
        vdigest = _digest('version_sha256', self.version_sha256)
        object.__setattr__(self, 'repository_full_name', repo)
        object.__setattr__(self, 'requested_ref', ref)
        object.__setattr__(self, 'pinned_commit', validate_commit_sha(self.pinned_commit))
        object.__setattr__(self, 'manifest_path', mpath)
        object.__setattr__(self, 'manifest_sha256', mdigest)
        object.__setattr__(self, 'version_path', vpath)
        object.__setattr__(self, 'version_sha256', vdigest)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_receipt_from_ref_resolution(resolution: RefResolution, manifest_data: bytes, version_data: bytes) -> RouteReceipt:
    if not isinstance(resolution, RefResolution):
        raise TypeError('resolution must be RefResolution')
    return RouteReceipt(
        repository_full_name=AUTHORITATIVE_REPOSITORY,
        requested_ref=AUTHORITATIVE_REF,
        pinned_commit=resolution.commit_sha,
        manifest_path=MANIFEST_PATH,
        manifest_sha256=bytes_sha256(manifest_data),
        version_path=VERSION_PATH,
        version_sha256=bytes_sha256(version_data),
    )


def _digest(name: str, value: object) -> str:
    digest = require_nonempty_text(name, value).lower()
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError(f'{name} must be 64 lowercase hex characters')
    return digest


@dataclass(frozen=True)
class DiscoveryPlan:
    bootstrap_entry: str | None
    entrypoint: str
    core: tuple[str, ...]
    help_path: str | None
    startup_slice: tuple[str, ...]
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
        object.__setattr__(self, 'startup_slice', tuple(validate_repo_path(x) for x in self.startup_slice))
        if len(set(self.startup_slice)) != len(self.startup_slice):
            raise ValueError('startup_slice contains duplicate paths')
        if not isinstance(self.legacy_manifest, bool):
            raise TypeError('legacy_manifest must be bool')

    @property
    def staged_startup(self) -> bool:
        return bool(self.startup_slice)

    @property
    def full_protocol_paths(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.entrypoint, *self.core)))

    @property
    def initial_paths(self) -> tuple[str, ...]:
        """Paths the local router must acquire before repository classification.

        Alpha2 manifests declare a minimal startup slice. Older manifests keep
        their historical bootstrap/entry/core loading order so the router does
        not import Alpha2 startup semantics into an older P_run.
        """
        if self.startup_slice:
            return self.startup_slice
        out: list[str] = []
        if self.bootstrap_entry is not None:
            out.append(self.bootstrap_entry)
        out.extend(self.full_protocol_paths)
        return tuple(dict.fromkeys(out))

    @property
    def post_startup_paths(self) -> tuple[str, ...]:
        return self.full_protocol_paths if self.startup_slice else ()

    @property
    def authority_paths(self) -> tuple[str, ...]:
        # Compatibility alias: what must be loaded *before semantic authority
        # can act on this candidate* for the pinned repository version.
        return self.initial_paths

    @property
    def load_paths(self) -> tuple[str, ...]:
        return self.initial_paths

    @property
    def optional_paths(self) -> tuple[str, ...]:
        return (self.help_path,) if self.help_path is not None else ()

    def to_dict(self) -> dict[str, Any]:
        return {
            'bootstrap_entry': self.bootstrap_entry,
            'entrypoint': self.entrypoint,
            'core': list(self.core),
            'help_path': self.help_path,
            'startup_slice': list(self.startup_slice),
            'legacy_manifest': self.legacy_manifest,
            'staged_startup': self.staged_startup,
            'initial_paths': list(self.initial_paths),
            'post_startup_paths': list(self.post_startup_paths),
            'optional_paths': list(self.optional_paths),
        }


def validate_manifest_routing_metadata(manifest: Mapping[str, Any]) -> bool:
    """Validate self-described locator metadata when present.

    Legacy manifests may omit this object. Presence never grants semantic
    authority; it only cross-checks that the pinned manifest describes the same
    transport locator used by the local router.
    """
    meta = manifest.get('routing')
    if meta is None:
        return False
    if not isinstance(meta, Mapping):
        raise ValueError('manifest routing must be an object')
    expected = {
        'repository_full_name': AUTHORITATIVE_REPOSITORY,
        'repository_url': AUTHORITATIVE_REPOSITORY_URL,
        'requested_ref': AUTHORITATIVE_REF,
        'ref_api_url': AUTHORITATIVE_REF_API_URL,
        'branch_api_url': AUTHORITATIVE_BRANCH_API_URL,
        'manifest_path': MANIFEST_PATH,
        'version_path': VERSION_PATH,
        'content_api_template': CONTENT_API_TEMPLATE,
        'pinned_raw_template': PINNED_RAW_TEMPLATE,
        'content_raw_media_type': 'application/vnd.github.raw+json',
        'mutable_ref_policy': 'direct_live_ref_plus_branch_consensus; search_index_forbidden; attempt_required_before_failure',
    }
    for key, value in expected.items():
        if meta.get(key) != value:
            raise ValueError(f'manifest routing locator mismatch: {key}')
    if meta.get('candidate_route_keys') != list(ROUTE_KEYS):
        raise ValueError('manifest routing candidate keys mismatch')
    if meta.get('candidate_match') != 'lstrip_prefix; DIGR_exact_uppercase; remainder_unvalidated':
        raise ValueError('manifest routing candidate match mismatch')
    return True


def discovery_plan_from_manifest(manifest: Mapping[str, Any]) -> DiscoveryPlan:
    """Return only manifest-declared protocol locations; do not interpret semantics."""
    if not isinstance(manifest, Mapping):
        raise TypeError('manifest must be a mapping')
    validate_manifest_routing_metadata(manifest)
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
    raw_startup = manifest.get('startup_slice', ())
    if not isinstance(raw_startup, Sequence) or isinstance(raw_startup, (str, bytes)):
        raise ValueError('manifest startup_slice must be a sequence when present')
    startup = tuple(validate_repo_path(x) for x in raw_startup)
    if startup and boot is not None and boot not in startup:
        raise ValueError('bootstrap_entry must be included in startup_slice')
    return DiscoveryPlan(boot, entry, core, help_path, startup, boot is None)


def load_manifest_for_route(route: RouteReceipt, data: bytes) -> dict[str, Any]:
    if not isinstance(route, RouteReceipt):
        raise TypeError('route must be RouteReceipt')
    raw = bytes(data) if isinstance(data, (bytes, bytearray)) else None
    if raw is None:
        raise TypeError('manifest data must be bytes')
    if bytes_sha256(raw) != route.manifest_sha256:
        raise ValueError('manifest bytes do not match route receipt digest')
    try:
        obj = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('pinned manifest is not valid UTF-8 JSON') from exc
    if not isinstance(obj, dict):
        raise ValueError('pinned manifest root must be an object')
    return obj


def load_version_for_route(route: RouteReceipt, data: bytes) -> str:
    if not isinstance(route, RouteReceipt):
        raise TypeError('route must be RouteReceipt')
    raw = bytes(data) if isinstance(data, (bytes, bytearray)) else None
    if raw is None:
        raise TypeError('VERSION data must be bytes')
    if bytes_sha256(raw) != route.version_sha256:
        raise ValueError('VERSION bytes do not match route receipt digest')
    try:
        value = raw.decode('utf-8').strip()
    except UnicodeDecodeError as exc:
        raise ValueError('pinned VERSION is not valid UTF-8') from exc
    return require_nonempty_text('VERSION', value)


def load_route_metadata(route: RouteReceipt, manifest_data: bytes, version_data: bytes) -> tuple[dict[str, Any], str]:
    manifest = load_manifest_for_route(route, manifest_data)
    version = load_version_for_route(route, version_data)
    declared = require_nonempty_text('manifest version', manifest.get('version'))
    if declared != version:
        raise ValueError('pinned VERSION does not match manifest.version')
    return manifest, version


def discovery_plan_from_manifest_bytes(route: RouteReceipt, manifest_data: bytes, version_data: bytes) -> DiscoveryPlan:
    manifest, _ = load_route_metadata(route, manifest_data, version_data)
    return discovery_plan_from_manifest(manifest)
