"""Safe explicit run-workspace storage for DIGR 5.0.0-Berta2.

The workspace is a persistence substrate, not a decision engine. Its integrity
index lets recovery detect revision/hash drift between stores.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from .validation import require_nonempty_text, require_nonnegative_int

_RUN_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$')
_COMPONENT_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
WORKSPACE_SCHEMA_VERSION = 2
REQUIRED_GENESIS_FILES = (
    'authority.json','invocation.json','startup.json','time/clock.journal.ndjson',
    'state/artifact-index.json','state/run-phase.json',
)
STATE_DIRECTORIES = ('time','sources','dictator','viewpoints','logs','evidence','final','state')
_INDEX_PATH = 'state/artifact-index.json'
TERMINAL_SEAL_PATH = 'state/terminal-seal.json'


def validate_run_id(run_id: str) -> str:
    value = require_nonempty_text('run_id', run_id)
    if not _RUN_ID.fullmatch(value):
        raise ValueError('unsafe run_id')
    return value


def validate_component_id(name: str, value: str) -> str:
    value=require_nonempty_text(name,value)
    if not _COMPONENT_ID.fullmatch(value): raise ValueError(f'unsafe {name}')
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8') + b'\n'


def sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    sha256: str
    kind: str
    revision: int | None = None
    last_event_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'kind': self.kind,
            'revision': self.revision, 'last_event_ref': self.last_event_ref,
        }


@dataclass(frozen=True)
class RunWorkspace:
    root: Path
    run_id: str

    @classmethod
    def create(cls, parent: Path, run_id: str) -> 'RunWorkspace':
        parent = Path(parent).resolve()
        run_id = validate_run_id(run_id)
        parent.mkdir(parents=True, exist_ok=True)
        root = (parent / run_id).resolve()
        if parent not in root.parents:
            raise ValueError('workspace escapes parent')
        root.mkdir(mode=0o700)
        for rel in STATE_DIRECTORIES:
            (root / rel).mkdir(mode=0o700)
        obj=cls(root=root, run_id=run_id)
        obj._write_index({})
        return obj

    @classmethod
    def open_existing(cls, root: Path, run_id: str) -> 'RunWorkspace':
        root = Path(root).resolve()
        run_id = validate_run_id(run_id)
        if root.name != run_id or not root.is_dir():
            raise ValueError('workspace root/run_id mismatch')
        return cls(root=root, run_id=run_id)

    def path(self, rel: str) -> Path:
        rel = require_nonempty_text('relative path', rel)
        p = Path(rel)
        if p.is_absolute() or '..' in p.parts or '.' in p.parts or not p.parts:
            raise ValueError('unsafe workspace relative path')
        out = (self.root / p).resolve()
        if self.root != out and self.root not in out.parents:
            raise ValueError('workspace path escape')
        return out

    def _assert_mutable(self,rel:str)->None:
        if self.path(TERMINAL_SEAL_PATH).is_file():
            raise RuntimeError(f'terminal workspace is sealed; mutation rejected: {rel}')

    def _atomic_write_bytes_unchecked(self,rel:str,data:bytes)->str:
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError('data must be bytes')
        dest = self.path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.tmp-', dir=str(dest.parent))
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(bytes(data)); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, dest)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        return sha256_bytes(bytes(data))

    def atomic_write_bytes(self, rel: str, data: bytes) -> str:
        self._assert_mutable(rel)
        return self._atomic_write_bytes_unchecked(rel,data)

    def write_json(self, rel: str, value: Any, *, kind: str='json', revision: int | None=None, last_event_ref: str | None=None) -> str:
        digest=self.atomic_write_bytes(rel, canonical_json_bytes(value))
        if rel != _INDEX_PATH:
            self.index_existing(rel, kind=kind, revision=revision, last_event_ref=last_event_ref, expected_digest=digest)
        return digest

    def write_text(self, rel: str, text: str, *, kind: str='text', revision: int | None=None, last_event_ref: str | None=None) -> str:
        if not isinstance(text, str): raise TypeError('text must be str')
        digest=self.atomic_write_bytes(rel, text.replace('\r\n','\n').replace('\r','\n').encode('utf-8'))
        if rel != _INDEX_PATH:
            self.index_existing(rel, kind=kind, revision=revision, last_event_ref=last_event_ref, expected_digest=digest)
        return digest

    def read_json(self, rel: str) -> Any:
        return json.loads(self.path(rel).read_text(encoding='utf-8'))

    def _load_index(self) -> dict[str, dict[str, Any]]:
        p=self.path(_INDEX_PATH)
        if not p.is_file(): return {}
        d=json.loads(p.read_text(encoding='utf-8'))
        if d.get('schema_version') != 1 or d.get('run_id') != self.run_id:
            raise ValueError('artifact index identity/version mismatch')
        items=d.get('artifacts')
        if not isinstance(items,list): raise ValueError('artifact index artifacts must be list')
        out={}
        for item in items:
            if not isinstance(item,dict) or 'path' not in item: raise ValueError('malformed artifact index entry')
            if item['path'] in out: raise ValueError('duplicate artifact index path')
            out[item['path']]=item
        return out

    def _write_index(self, mapping: dict[str, dict[str, Any]]) -> None:
        payload={'schema_version':1,'run_id':self.run_id,'artifacts':[mapping[k] for k in sorted(mapping)]}
        self._atomic_write_bytes_unchecked(_INDEX_PATH, canonical_json_bytes(payload))

    def index_existing(self, rel: str, *, kind: str, revision: int | None=None, last_event_ref: str | None=None, expected_digest: str | None=None) -> ArtifactRecord:
        self._assert_mutable(rel)
        rel=require_nonempty_text('artifact path',rel)
        kind=require_nonempty_text('artifact kind',kind)
        if revision is not None: require_nonnegative_int('revision',revision)
        if last_event_ref is not None: last_event_ref=require_nonempty_text('last_event_ref',last_event_ref)
        p=self.path(rel)
        if not p.is_file(): raise FileNotFoundError(p)
        digest=sha256_bytes(p.read_bytes())
        if expected_digest is not None and digest != expected_digest:
            raise ValueError('artifact digest changed before indexing')
        rec=ArtifactRecord(rel,digest,kind,revision,last_event_ref)
        items=self._load_index(); items[rel]=rec.to_dict(); self._write_index(items)
        return rec

    @property
    def terminal_sealed(self)->bool:
        return self.path(TERMINAL_SEAL_PATH).is_file()

    def seal_terminal(self,*,phase:str,binding_sha256:str)->ArtifactRecord:
        """Persist the final API mutation barrier after all terminal artifacts."""
        if self.terminal_sealed:raise RuntimeError('terminal workspace is already sealed')
        phase=require_nonempty_text('terminal phase',phase)
        if phase not in ('DELIVERED','INCOMPLETE','ABORTED'):
            raise ValueError('only terminal phases may seal a workspace')
        binding_sha256=require_nonempty_text('binding_sha256',binding_sha256).lower()
        if len(binding_sha256)!=64 or any(ch not in '0123456789abcdef' for ch in binding_sha256):
            raise ValueError('binding_sha256 must be 64 lowercase hex')
        payload={'schema_version':1,'run_id':self.run_id,'phase':phase,'binding_sha256':binding_sha256}
        data=canonical_json_bytes(payload)
        # Write and index as one final mutation. _write_index deliberately uses
        # the unchecked primitive so the just-created seal can index itself.
        digest=self._atomic_write_bytes_unchecked(TERMINAL_SEAL_PATH,data)
        items=self._load_index()
        rec=ArtifactRecord(TERMINAL_SEAL_PATH,digest,'terminal-seal')
        items[TERMINAL_SEAL_PATH]=rec.to_dict();self._write_index(items)
        return rec

    def artifact_records(self) -> tuple[ArtifactRecord,...]:
        items=self._load_index()
        return tuple(ArtifactRecord(**items[k]) for k in sorted(items))

    def artifact_record(self, rel: str) -> ArtifactRecord:
        rel=require_nonempty_text('artifact path',rel)
        items=self._load_index()
        if rel not in items:
            raise ValueError(f'artifact is not indexed: {rel}')
        rec=ArtifactRecord(**items[rel])
        p=self.path(rel)
        if not p.is_file() or sha256_bytes(p.read_bytes()) != rec.sha256:
            raise ValueError(f'indexed artifact is missing or drifted: {rel}')
        return rec

    def require_indexed_artifact(self, rel: str, *, kind: str | None=None) -> ArtifactRecord:
        rec=self.artifact_record(rel)
        if kind is not None and rec.kind != kind:
            raise ValueError(f'artifact {rel} has kind {rec.kind!r}, expected {kind!r}')
        return rec

    def verify_artifact_index(self) -> bool:
        records=self.artifact_records()
        indexed={rec.path for rec in records}
        for rec in records:
            p=self.path(rec.path)
            if not p.is_file(): raise ValueError(f'indexed artifact missing: {rec.path}')
            if sha256_bytes(p.read_bytes()) != rec.sha256:
                raise ValueError(f'artifact digest mismatch: {rec.path}')
        # The index is intended to cover every authoritative persisted artifact,
        # not just a subset. Crash-left atomic temp files are non-authoritative
        # and may be ignored; symlinks are never valid workspace artifacts.
        actual=set()
        for p in self.root.rglob('*'):
            if p.is_symlink():
                raise ValueError(f'workspace symlink is not allowed: {p.relative_to(self.root).as_posix()}')
            if not p.is_file():
                continue
            rel=p.relative_to(self.root).as_posix()
            if rel==_INDEX_PATH or p.name.startswith('.tmp-'):
                continue
            actual.add(rel)
        extra=sorted(actual-indexed)
        stale=sorted(indexed-actual)
        if extra:
            raise ValueError(f'unindexed workspace artifact(s): {extra}')
        if stale:
            raise ValueError(f'artifact index references non-authoritative/missing artifact(s): {stale}')
        return True
