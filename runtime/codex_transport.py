"""Live, commit-pinned transport for the Codex experimental profile.

Acquisition does not classify an invocation or start a DIGR run. The model
reads the pinned startup slice first and selects a subsequent stage. The
existing stable transport remains a different entrypoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable

from .execution_protocol import verify_execution_bundle
from .protocol_pin import raw_file_url, validate_commit_sha, validate_repo_path
from .repository_transport import (
    FetchRequest, TransportResponse, UrllibDirectFetcher,
    normalize_pinned_file_bytes,
)

REPOSITORY = 'Gual-Wells/Deep-Iteration-GPT-Runtime'
REF = 'codex/codex-host-adaptation'
API = 'https://api.github.com/repos/' + REPOSITORY
REF_URL = API + '/git/ref/heads/' + REF
BRANCH_URL = API + '/branches/' + REF
MANIFEST = 'codex/manifest.json'
VERSION = 'codex/VERSION'


def _profile_path(value: object) -> str:
    path = validate_repo_path(value)
    if not path.startswith('codex/'):
        raise ValueError('Codex profile member must be inside codex/')
    return path


def profile_layout(manifest: dict, version: str) -> dict[str, Any]:
    """Validate declared paths and identity, without enforcing local semantics."""
    if not isinstance(manifest, dict) or manifest.get('version') != version or not version:
        raise ValueError('Codex manifest/VERSION identity mismatch')
    protocol = manifest.get('protocol')
    if not isinstance(protocol, str) or not protocol.startswith('digr-codex-native-v'):
        raise ValueError('not a Codex native profile')
    if manifest.get('version_path') != VERSION:
        raise ValueError('unexpected Codex version path')
    paths = {}
    for key in ('startup_slice', 'core'):
        values = manifest.get(key)
        if not isinstance(values, list) or not values:
            raise ValueError(f'Codex {key} must be a nonempty path list')
        paths[key] = [_profile_path(x) for x in values]
        if len(set(paths[key])) != len(paths[key]):
            raise ValueError(f'duplicate Codex {key} path')
    for key in ('entrypoint', 'help', 'light_instructions', 'experimental_router', 'workbench_guide'):
        paths[key] = _profile_path(manifest.get(key))
    required = {VERSION, *paths['startup_slice'], *paths['core'],
                *(paths[key] for key in ('entrypoint', 'help', 'light_instructions',
                                        'experimental_router', 'workbench_guide'))}
    bundle = manifest.get('execution_bundle')
    if bundle is not None:
        if not isinstance(bundle, dict) or bundle.get('schema') != 1:
            raise ValueError('unsupported Codex execution bundle')
        path = _profile_path(bundle.get('path'))
        if bundle.get('members') != [paths['entrypoint'], *paths['core']]:
            raise ValueError('Codex execution bundle member declaration drift')
        required.add(path)
        paths['execution_bundle'] = path
    hashes = manifest.get('file_sha256')
    if not isinstance(hashes, dict) or set(hashes) != required:
        raise ValueError('Codex profile hash set does not match declared files')
    for path, digest in hashes.items():
        _profile_path(path)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError(f'invalid Codex file hash: {path}')
    return paths


@dataclass(frozen=True)
class CodexAcquisition:
    sha: str
    version: str
    stage: str
    manifest: dict[str, Any]
    files: dict[str, bytes]
    observations: tuple[dict[str, Any], ...]
    continuation: bool = False

    def summary(self) -> dict[str, Any]:
        return {'repository': REPOSITORY, 'ref': REF, 'sha': self.sha,
                'version': self.version, 'stage': self.stage,
                'files': list(self.files), 'observations': list(self.observations),
                'file_sha256': {path: sha256(raw).hexdigest() for path, raw in self.files.items()},
                'new_live_ref_resolution': not self.continuation,
                'invocation_classified': False, 'run_started': False,
                'host_permissions_changed': False}

    def export(self, output: Path) -> Path:
        """Write one new acquisition directory, never replace an existing one."""
        output = Path(output).resolve()
        output.mkdir(parents=True, exist_ok=False)
        for rel, raw in self.files.items():
            path = output / _profile_path(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)
        receipt = output / 'acquisition.json'
        receipt.write_text(json.dumps(self.summary(), ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8', newline='\n')
        return receipt


def load_acquisition(directory: Path) -> CodexAcquisition:
    """Resume stored bytes of this acquisition; never resolve a new invocation.

    This is local continuity/integrity, not independent proof that a saved
    receipt is authentic or a mutable branch is still at this commit.
    """
    directory = Path(directory).resolve()
    record = json.loads((directory / 'acquisition.json').read_text(encoding='utf-8'))
    if record.get('repository') != REPOSITORY or record.get('ref') != REF:
        raise ValueError('stored acquisition belongs to another repository/ref')
    sha = validate_commit_sha(record['sha'])
    paths, hashes = record.get('files'), record.get('file_sha256')
    if not isinstance(paths, list) or not isinstance(hashes, dict) or set(paths) != set(hashes):
        raise ValueError('stored acquisition file declaration mismatch')
    files = {}
    for path in paths:
        rel = _profile_path(path)
        target = (directory / rel).resolve()
        if not target.is_relative_to(directory):
            raise ValueError('stored acquisition path escapes directory')
        raw = target.read_bytes()
        if sha256(raw).hexdigest() != hashes[path]:
            raise ValueError(f'stored acquisition bytes changed: {path}')
        files[path] = raw
    manifest = json.loads(files[MANIFEST])
    version = files[VERSION].decode('utf-8').strip()
    layout = profile_layout(manifest, version)
    if record.get('version') != version or record.get('stage') not in ('startup', 'help', 'execution'):
        raise ValueError('stored acquisition stage/identity mismatch')
    for path in [VERSION, *layout['startup_slice']]:
        if path not in files or sha256(files[path]).hexdigest() != manifest['file_sha256'][path]:
            raise ValueError(f'stored acquisition missing valid startup file: {path}')
    return CodexAcquisition(sha, version, record['stage'], manifest, files,
                            tuple(record.get('observations', [])), continuation=True)


class CodexRepositoryTransport:
    """One actual live resolution followed by only immutable file reads."""
    def __init__(self, fetch: Callable[[FetchRequest], TransportResponse] | None = None):
        self.fetch = fetch if fetch is not None else UrllibDirectFetcher()
        self.observations: list[dict[str, Any]] = []

    def _get(self, url: str, purpose: str, *, mutable: bool = False) -> bytes:
        request = FetchRequest(url, purpose, 'application/vnd.github+json' if mutable
                               else 'application/vnd.github.raw+json', mutable)
        observation = {'url': url, 'purpose': purpose,
                       'observed_at': datetime.now(timezone.utc).isoformat()}
        try:
            response = self.fetch(request)
            observation.update(status=response.status, source_kind=response.source_kind,
                               freshness=response.freshness,
                               response_sha256=sha256(response.body).hexdigest())
            if response.request_url != url:
                raise ValueError(f'repository response URL mismatch: {purpose}')
            if response.status != 200:
                raise ValueError(f'HTTP {response.status}: {purpose}')
            if not response.direct:
                raise ValueError(f'not a direct repository response: {purpose}')
            allowed = ('live_direct',) if mutable else ('live_direct', 'immutable_sha')
            if response.freshness not in allowed:
                raise ValueError(f'untrusted repository freshness: {purpose}')
            observation['success'] = True
            return response.body
        except Exception as exc:
            observation.update(success=False, failure=str(exc))
            raise
        finally:
            self.observations.append(observation)

    def resolve_ref(self, *, connector: bool = False) -> str:
        """Corroborate both GitHub endpoints in this resolution attempt."""
        if connector:
            # Only a real repository-native connector may take the one-HEAD
            # path. A saved JSON file or a search result is not this response.
            raw = self._get(BRANCH_URL, 'Codex connector branch HEAD', mutable=True)
            if self.observations[-1]['source_kind'] != 'github_connector':
                raise ValueError('connector HEAD requires an actual GitHub connector transport')
            branch = json.loads(raw)
            if branch.get('name') != REF:
                raise ValueError('unexpected Codex branch identity')
            return validate_commit_sha(branch['commit']['sha'])
        ref = json.loads(self._get(REF_URL, 'Codex ref HEAD', mutable=True))
        branch = json.loads(self._get(BRANCH_URL, 'Codex branch HEAD', mutable=True))
        if ref.get('ref') != 'refs/heads/' + REF or ref.get('object', {}).get('type') != 'commit':
            raise ValueError('unexpected Codex ref identity')
        if branch.get('name') != REF:
            raise ValueError('unexpected Codex branch identity')
        left = validate_commit_sha(ref['object']['sha'])
        right = validate_commit_sha(branch['commit']['sha'])
        if left != right:
            raise ValueError('Codex ref/branch HEAD mismatch; acquire again, do not mix pins')
        return left

    def _file(self, commit_sha: str, path: str, *, digest: str | None = None) -> bytes:
        path = _profile_path(path)
        raw = self._get(raw_file_url(*REPOSITORY.split('/'), commit_sha, path), 'Codex ' + path)
        data = normalize_pinned_file_bytes(raw, path)
        data.decode('utf-8')
        if digest is not None and sha256(data).hexdigest() != digest:
            raise ValueError(f'Codex pinned file hash mismatch: {path}')
        return data

    def acquire(self, stage: str = 'startup', *, startup: CodexAcquisition | None = None,
                connector: bool = False) -> CodexAcquisition:
        if stage not in ('startup', 'help', 'execution'):
            raise ValueError('stage must be startup, help or execution')
        if startup is None:
            self.observations = []
            sha = self.resolve_ref(connector=connector)
            manifest_raw = self._file(sha, MANIFEST)
            version_raw = self._file(sha, VERSION)
            version = version_raw.decode('utf-8').strip()
            manifest = json.loads(manifest_raw)
            layout = profile_layout(manifest, version)
            if sha256(version_raw).hexdigest() != manifest['file_sha256'][VERSION]:
                raise ValueError('Codex VERSION hash mismatch')
            files = {MANIFEST: manifest_raw, VERSION: version_raw}
            for path in layout['startup_slice']:
                files[path] = self._file(sha, path, digest=manifest['file_sha256'][path])
        else:
            # Continue the exact already-acquired pin; no mutable-ref re-read.
            sha, version, manifest = startup.sha, startup.version, startup.manifest
            validate_commit_sha(sha)
            layout = profile_layout(manifest, version)
            files = dict(startup.files)
            self.observations = list(startup.observations)
        if stage == 'help':
            path = layout['help']
            files[path] = self._file(sha, path, digest=manifest['file_sha256'][path])
        elif stage == 'execution':
            members = [layout['entrypoint'], *layout['core']]
            bundle_path = layout.get('execution_bundle')
            if bundle_path:
                data = self._file(sha, bundle_path, digest=manifest['file_sha256'][bundle_path])
                bundle = verify_execution_bundle(data, commit_sha=sha,
                    manifest_bytes=files[MANIFEST], expected_paths=members)
                files[bundle_path] = data
                for path, raw in bundle.files:
                    if sha256(raw).hexdigest() != manifest['file_sha256'][path]:
                        raise ValueError(f'Codex execution member/manifest hash mismatch: {path}')
                    files[path] = raw
            else:
                for path in members:
                    files[path] = self._file(sha, path, digest=manifest['file_sha256'][path])
        return CodexAcquisition(sha, version, stage, manifest, files, tuple(self.observations),
                                continuation=startup is not None)
