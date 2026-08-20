"""Deterministic DIGR 5.0.0-alpha.4 execution-protocol bundle verification.

The repository keeps entrypoint/core modules as independent source files for
review, diffing and tests.  Release/runtime transport may carry those logical
members in one immutable, commit-pinned bundle.  This module verifies that the
bundle is exactly the manifest-declared execution protocol and emits the receipt
that gates post-genesis parameter resolution.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

from .protocol_pin import validate_commit_sha, validate_repo_path
from .validation import require_nonempty_text

EXECUTION_BUNDLE_SCHEMA = 1
EXECUTION_PROTOCOL_LOAD_SCHEMA = 1


def bytes_sha256(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError('data must be bytes')
    return sha256(bytes(data)).hexdigest()


def _digest(name: str, value: object) -> str:
    text=require_nonempty_text(name,value).lower()
    if len(text)!=64 or any(c not in '0123456789abcdef' for c in text):
        raise ValueError(f'{name} must be 64 lowercase hex')
    return text


@dataclass(frozen=True)
class ProtocolMemberReceipt:
    path: str
    sha256: str
    byte_length: int

    def __post_init__(self):
        object.__setattr__(self,'path',validate_repo_path(self.path))
        object.__setattr__(self,'sha256',_digest('member sha256',self.sha256))
        if not isinstance(self.byte_length,int) or self.byte_length < 0:
            raise ValueError('member byte_length must be a non-negative int')

    def to_dict(self) -> dict[str,Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls,d:Mapping[str,Any]) -> 'ProtocolMemberReceipt':
        return cls(d['path'],d['sha256'],d['byte_length'])


@dataclass(frozen=True)
class ExecutingProtocolLoadReceipt:
    schema_version: int
    commit_sha: str
    manifest_sha256: str
    version: str
    protocol: str
    source_mode: str
    container_path: str | None
    container_sha256: str | None
    members: tuple[ProtocolMemberReceipt,...]

    def __post_init__(self):
        if self.schema_version != EXECUTION_PROTOCOL_LOAD_SCHEMA:
            raise ValueError('unsupported executing protocol load schema')
        object.__setattr__(self,'commit_sha',validate_commit_sha(self.commit_sha))
        object.__setattr__(self,'manifest_sha256',_digest('manifest sha256',self.manifest_sha256))
        object.__setattr__(self,'version',require_nonempty_text('version',self.version))
        object.__setattr__(self,'protocol',require_nonempty_text('protocol',self.protocol))
        if self.source_mode not in ('bundle','individual'):
            raise ValueError('source_mode must be bundle/individual')
        if self.container_path is not None:
            object.__setattr__(self,'container_path',validate_repo_path(self.container_path))
        if self.container_sha256 is not None:
            object.__setattr__(self,'container_sha256',_digest('container sha256',self.container_sha256))
        if self.source_mode == 'bundle':
            if self.container_path is None or self.container_sha256 is None:
                raise ValueError('bundle load requires container path/digest')
        else:
            if self.container_path is not None or self.container_sha256 is not None:
                raise ValueError('individual load cannot claim bundle container')
        object.__setattr__(self,'members',tuple(self.members))
        if not self.members:
            raise ValueError('executing protocol receipt requires members')
        if any(not isinstance(x,ProtocolMemberReceipt) for x in self.members):
            raise TypeError('members must contain ProtocolMemberReceipt')
        paths=[x.path for x in self.members]
        if len(paths)!=len(set(paths)):
            raise ValueError('executing protocol receipt has duplicate member paths')

    @property
    def member_paths(self) -> tuple[str,...]:
        return tuple(x.path for x in self.members)

    def to_dict(self) -> dict[str,Any]:
        return {
            'schema_version':self.schema_version,
            'commit_sha':self.commit_sha,
            'manifest_sha256':self.manifest_sha256,
            'version':self.version,
            'protocol':self.protocol,
            'source_mode':self.source_mode,
            'container_path':self.container_path,
            'container_sha256':self.container_sha256,
            'members':[x.to_dict() for x in self.members],
        }

    @classmethod
    def from_dict(cls,d:Mapping[str,Any]) -> 'ExecutingProtocolLoadReceipt':
        return cls(
            d['schema_version'],d['commit_sha'],d['manifest_sha256'],d['version'],d['protocol'],
            d['source_mode'],d.get('container_path'),d.get('container_sha256'),
            tuple(ProtocolMemberReceipt.from_dict(x) for x in d['members']),
        )


@dataclass(frozen=True)
class ExecutionProtocolBundle:
    receipt: ExecutingProtocolLoadReceipt
    files: tuple[tuple[str,bytes],...]

    def __post_init__(self):
        if not isinstance(self.receipt,ExecutingProtocolLoadReceipt):
            raise TypeError('receipt must be ExecutingProtocolLoadReceipt')
        object.__setattr__(self,'files',tuple((validate_repo_path(p),bytes(b)) for p,b in self.files))
        if tuple(p for p,_ in self.files) != self.receipt.member_paths:
            raise ValueError('bundle files do not match receipt members')
        for (p,b),m in zip(self.files,self.receipt.members):
            if len(b)!=m.byte_length or bytes_sha256(b)!=m.sha256:
                raise ValueError(f'logical member bytes drift: {p}')


def _manifest_identity(manifest_bytes: bytes) -> tuple[dict[str,Any],str,str]:
    if not isinstance(manifest_bytes,(bytes,bytearray)):
        raise TypeError('manifest_bytes must be bytes')
    try: manifest=json.loads(bytes(manifest_bytes).decode('utf-8'))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError('manifest is not valid UTF-8 JSON') from exc
    if not isinstance(manifest,dict):
        raise ValueError('manifest root must be an object')
    return manifest,require_nonempty_text('manifest version',manifest.get('version')),require_nonempty_text('manifest protocol',manifest.get('protocol'))


def _expected_bundle_metadata(manifest:Mapping[str,Any],expected_paths:Sequence[str]) -> tuple[str,int]:
    meta=manifest.get('execution_bundle')
    if not isinstance(meta,Mapping):
        raise ValueError('manifest execution_bundle metadata required')
    path=validate_repo_path(meta.get('path'))
    schema=meta.get('schema')
    if schema != EXECUTION_BUNDLE_SCHEMA:
        raise ValueError('unsupported manifest execution bundle schema')
    raw_members=meta.get('members')
    if not isinstance(raw_members,Sequence) or isinstance(raw_members,(str,bytes)):
        raise ValueError('execution_bundle members must be a sequence')
    members=tuple(validate_repo_path(x) for x in raw_members)
    expected=tuple(validate_repo_path(x) for x in expected_paths)
    if members != expected:
        raise ValueError('manifest execution_bundle members do not equal entrypoint/core order')
    return path,schema


def verify_execution_bundle(bundle_bytes: bytes, *, commit_sha: str, manifest_bytes: bytes,
                            expected_paths: Sequence[str]) -> ExecutionProtocolBundle:
    sha=validate_commit_sha(commit_sha)
    manifest,version,protocol=_manifest_identity(manifest_bytes)
    bundle_path,_=_expected_bundle_metadata(manifest,expected_paths)
    if not isinstance(bundle_bytes,(bytes,bytearray)):
        raise TypeError('bundle_bytes must be bytes')
    raw=bytes(bundle_bytes)
    try: obj=json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError('execution bundle is not valid UTF-8 JSON') from exc
    if not isinstance(obj,Mapping):
        raise ValueError('execution bundle root must be an object')
    if obj.get('schema_version') != EXECUTION_BUNDLE_SCHEMA:
        raise ValueError('execution bundle schema mismatch')
    if obj.get('version') != version or obj.get('protocol') != protocol:
        raise ValueError('execution bundle version/protocol mismatch')
    raw_members=obj.get('members')
    if not isinstance(raw_members,list):
        raise ValueError('execution bundle members must be a list')
    expected=tuple(validate_repo_path(x) for x in expected_paths)
    if len(raw_members)!=len(expected):
        raise ValueError('execution bundle member count mismatch')
    files=[]; receipts=[]
    for expected_path,item in zip(expected,raw_members):
        if not isinstance(item,Mapping):
            raise ValueError('execution bundle member must be an object')
        path=validate_repo_path(item.get('path'))
        if path != expected_path:
            raise ValueError(f'execution bundle member order/path mismatch: {path} != {expected_path}')
        content=item.get('content')
        if not isinstance(content,str):
            raise ValueError(f'execution bundle member content must be UTF-8 text: {path}')
        data=content.encode('utf-8')
        digest=_digest('bundle member sha256',item.get('sha256'))
        if bytes_sha256(data)!=digest:
            raise ValueError(f'execution bundle member digest mismatch: {path}')
        length=item.get('byte_length')
        if length != len(data):
            raise ValueError(f'execution bundle member length mismatch: {path}')
        files.append((path,data));receipts.append(ProtocolMemberReceipt(path,digest,length))
    receipt=ExecutingProtocolLoadReceipt(
        EXECUTION_PROTOCOL_LOAD_SCHEMA,sha,bytes_sha256(manifest_bytes),version,protocol,'bundle',bundle_path,
        bytes_sha256(raw),tuple(receipts),
    )
    return ExecutionProtocolBundle(receipt,tuple(files))


def receipt_from_individual_files(*, commit_sha: str, manifest_bytes: bytes,
                                  expected_paths: Sequence[str], files: Iterable[tuple[str,bytes]]) -> ExecutionProtocolBundle:
    """Compatibility path for pinned manifests that do not declare a bundle."""
    sha=validate_commit_sha(commit_sha)
    _,version,protocol=_manifest_identity(manifest_bytes)
    expected=tuple(validate_repo_path(x) for x in expected_paths)
    vals=tuple((validate_repo_path(p),bytes(b)) for p,b in files)
    if tuple(p for p,_ in vals)!=expected:
        raise ValueError('individual protocol files do not match expected paths')
    receipts=tuple(ProtocolMemberReceipt(p,bytes_sha256(b),len(b)) for p,b in vals)
    receipt=ExecutingProtocolLoadReceipt(
        EXECUTION_PROTOCOL_LOAD_SCHEMA,sha,bytes_sha256(manifest_bytes),version,protocol,'individual',None,None,receipts,
    )
    return ExecutionProtocolBundle(receipt,vals)
