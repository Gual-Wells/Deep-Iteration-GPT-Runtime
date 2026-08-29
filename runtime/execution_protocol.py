"""Deterministic DIGR 5.0.0-Berta2 execution-protocol bundle verification.

The repository keeps entrypoint/core modules as independent source files for
review, diffing and tests.  Release/runtime transport may carry those logical
members in one immutable, commit-pinned bundle.  This module verifies that the
bundle is exactly the manifest-declared execution protocol and emits the receipt
that gates post-genesis parameter resolution.
"""
from __future__ import annotations

import base64
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


def execution_set_sha256(members: Iterable[ProtocolMemberReceipt | Mapping[str,Any]]) -> str:
    """Hash the ordered execution receipt set using the stable.1 vector.

    The vector is a UTF-8 JSON array containing only path/sha256/byte_length,
    with ``ensure_ascii=False``, sorted object keys, compact separators and no
    trailing newline. Array order is authoritative.
    """
    records=[]
    for member in members:
        if isinstance(member,ProtocolMemberReceipt):
            receipt=member
        elif isinstance(member,Mapping):
            receipt=ProtocolMemberReceipt(member.get('path'),member.get('sha256'),member.get('byte_length'))
        else:
            raise TypeError('execution set members must be receipts or mappings')
        records.append(receipt.to_dict())
    canonical=json.dumps(
        records,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False,
    ).encode('utf-8')
    return bytes_sha256(canonical)


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
    # The receipt must carry the exact manifest bytes whose digest is already
    # bound by RouteReceipt.  Without these bytes a structurally valid receipt
    # cannot prove that its member list is complete (the Alpha 4 bypass).
    manifest_bytes_base64: str | None = None
    container_byte_length: int | None = None

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
            if self.container_byte_length is not None:
                if not isinstance(self.container_byte_length,int) or isinstance(self.container_byte_length,bool) or self.container_byte_length<=0:
                    raise ValueError('bundle container_byte_length must be a positive int')
        else:
            if self.container_path is not None or self.container_sha256 is not None:
                raise ValueError('individual load cannot claim bundle container')
            if self.container_byte_length is not None:
                raise ValueError('individual load cannot claim bundle byte length')
        object.__setattr__(self,'members',tuple(self.members))
        if not self.members:
            raise ValueError('executing protocol receipt requires members')
        if any(not isinstance(x,ProtocolMemberReceipt) for x in self.members):
            raise TypeError('members must contain ProtocolMemberReceipt')
        paths=[x.path for x in self.members]
        if len(paths)!=len(set(paths)):
            raise ValueError('executing protocol receipt has duplicate member paths')
        if self.manifest_bytes_base64 is not None:
            require_nonempty_text('manifest_bytes_base64',self.manifest_bytes_base64)
            # Validate eagerly so malformed evidence is never persisted.
            self.verify_complete_members()

    @property
    def member_paths(self) -> tuple[str,...]:
        return tuple(x.path for x in self.members)

    def _bound_manifest(self) -> Mapping[str,Any]:
        if self.manifest_bytes_base64 is None:
            raise ValueError('protocol-load receipt lacks bound manifest bytes')
        try:
            raw=base64.b64decode(self.manifest_bytes_base64,validate=True)
        except (ValueError,TypeError) as exc:
            raise ValueError('protocol-load receipt manifest evidence is not valid base64') from exc
        if bytes_sha256(raw)!=self.manifest_sha256:
            raise ValueError('protocol-load receipt manifest evidence digest mismatch')
        try:
            manifest=json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise ValueError('protocol-load receipt manifest evidence is not UTF-8 JSON') from exc
        if not isinstance(manifest,Mapping):
            raise ValueError('protocol-load receipt manifest root must be an object')
        if manifest.get('version')!=self.version or manifest.get('protocol')!=self.protocol:
            raise ValueError('protocol-load receipt manifest version/protocol mismatch')
        return manifest

    def verify_complete_members(self) -> tuple[str,...]:
        """Prove that ``members`` is exactly manifest entrypoint + core.

        Identity-only receipts are intentionally insufficient: completeness is
        checked from manifest bytes whose SHA-256 is already in RouteReceipt.
        This method is used again at the run binding boundary, not merely when
        the transport bundle is decoded.
        """
        manifest=self._bound_manifest()
        if manifest.get('schema') == 'digr-runtime-descriptor/v1':
            artifacts=manifest.get('artifacts')
            if not isinstance(artifacts,Mapping):
                raise ValueError('runtime descriptor artifacts must be an object')
            if self.source_mode!='bundle':
                raise ValueError('runtime descriptor requires bundled execution protocol')
            bundle_meta=artifacts.get('execution_bundle')
            if not isinstance(bundle_meta,Mapping):
                raise ValueError('runtime descriptor execution_bundle must be an object')
            if validate_repo_path(bundle_meta.get('path'))!=self.container_path:
                raise ValueError('protocol-load container disagrees with runtime descriptor')
            if _digest('descriptor execution bundle sha256',bundle_meta.get('sha256'))!=self.container_sha256:
                raise ValueError('protocol-load container digest disagrees with runtime descriptor')
            declared_length=bundle_meta.get('byte_length')
            if (not isinstance(declared_length,int) or isinstance(declared_length,bool) or declared_length<=0
                    or self.container_byte_length!=declared_length):
                raise ValueError('protocol-load container length disagrees with runtime descriptor')
            declared_count=bundle_meta.get('member_count')
            if not isinstance(declared_count,int) or isinstance(declared_count,bool) or declared_count<=0:
                raise ValueError('runtime descriptor member_count must be a positive int')
            if len(self.members)!=declared_count:
                raise ValueError('protocol-load member count disagrees with runtime descriptor')
            declared_set=_digest('descriptor execution_set_sha256',bundle_meta.get('execution_set_sha256'))
            if execution_set_sha256(self.members)!=declared_set:
                raise ValueError('protocol-load execution member set disagrees with runtime descriptor')
            return self.member_paths
        entrypoint=validate_repo_path(manifest.get('entrypoint'))
        core=manifest.get('core')
        if not isinstance(core,list) or not core:
            raise ValueError('bound manifest core must be a non-empty list')
        expected=(entrypoint,*(validate_repo_path(x) for x in core))
        if len(expected)!=len(set(expected)):
            raise ValueError('bound manifest execution members contain duplicates')
        if self.member_paths!=expected:
            raise ValueError('protocol-load receipt members are not the complete manifest execution set')
        meta=manifest.get('execution_bundle')
        if self.source_mode=='bundle':
            if not isinstance(meta,Mapping):
                raise ValueError('bundle receipt requires bound manifest execution_bundle metadata')
            if validate_repo_path(meta.get('path'))!=self.container_path:
                raise ValueError('protocol-load receipt container path disagrees with bound manifest')
            declared=meta.get('members')
            if declared is not None:
                if (not isinstance(declared,list)
                        or tuple(validate_repo_path(x) for x in declared)!=expected):
                    raise ValueError('bound manifest execution_bundle members are incomplete or reordered')
        return expected

    @property
    def completeness_verified(self) -> bool:
        try:
            self.verify_complete_members()
        except (TypeError,ValueError):
            return False
        return True

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
            'manifest_bytes_base64':self.manifest_bytes_base64,
            'container_byte_length':self.container_byte_length,
        }

    @classmethod
    def from_dict(cls,d:Mapping[str,Any]) -> 'ExecutingProtocolLoadReceipt':
        return cls(
            d['schema_version'],d['commit_sha'],d['manifest_sha256'],d['version'],d['protocol'],
            d['source_mode'],d.get('container_path'),d.get('container_sha256'),
            tuple(ProtocolMemberReceipt.from_dict(x) for x in d['members']),
            d.get('manifest_bytes_base64'),
            d.get('container_byte_length'),
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
    expected=tuple(validate_repo_path(x) for x in expected_paths)
    raw_members=meta.get('members')
    if raw_members is not None:
        if not isinstance(raw_members,Sequence) or isinstance(raw_members,(str,bytes)):
            raise ValueError('execution_bundle members must be a sequence')
        members=tuple(validate_repo_path(x) for x in raw_members)
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
        bytes_sha256(raw),tuple(receipts),base64.b64encode(bytes(manifest_bytes)).decode('ascii'),len(raw),
    )
    return ExecutionProtocolBundle(receipt,tuple(files))


def verify_descriptor_execution_bundle(
    bundle_bytes: bytes, *, commit_sha: str, descriptor_bytes: bytes,
) -> ExecutionProtocolBundle:
    """Verify the stable.1 descriptor-declared immutable execution bundle."""
    sha=validate_commit_sha(commit_sha)
    if not isinstance(descriptor_bytes,(bytes,bytearray)):
        raise TypeError('descriptor_bytes must be bytes')
    descriptor_raw=bytes(descriptor_bytes)
    try: descriptor=json.loads(descriptor_raw.decode('utf-8'))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError('runtime descriptor is not valid UTF-8 JSON') from exc
    if not isinstance(descriptor,Mapping) or descriptor.get('schema')!='digr-runtime-descriptor/v1':
        raise ValueError('unsupported runtime descriptor schema')
    version=require_nonempty_text('descriptor version',descriptor.get('version'))
    protocol=require_nonempty_text('descriptor protocol',descriptor.get('protocol'))
    artifacts=descriptor.get('artifacts')
    if not isinstance(artifacts,Mapping):
        raise ValueError('runtime descriptor artifacts must be an object')
    bundle_meta=artifacts.get('execution_bundle')
    if not isinstance(bundle_meta,Mapping):
        raise ValueError('runtime descriptor execution_bundle must be an object')
    bundle_path=validate_repo_path(bundle_meta.get('path'))

    if not isinstance(bundle_bytes,(bytes,bytearray)):
        raise TypeError('bundle_bytes must be bytes')
    raw=bytes(bundle_bytes)
    try: obj=json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError('execution bundle is not valid UTF-8 JSON') from exc
    if not isinstance(obj,Mapping) or obj.get('schema_version')!=EXECUTION_BUNDLE_SCHEMA:
        raise ValueError('execution bundle schema mismatch')
    if obj.get('version')!=version or obj.get('protocol')!=protocol:
        raise ValueError('execution bundle version/protocol mismatch')
    raw_members=obj.get('members')
    if not isinstance(raw_members,list) or not raw_members:
        raise ValueError('execution bundle members must be a non-empty list')
    files=[];receipts=[];seen=set()
    for item in raw_members:
        if not isinstance(item,Mapping):
            raise ValueError('execution bundle member must be an object')
        path=validate_repo_path(item.get('path'))
        if path in seen:
            raise ValueError('execution bundle contains duplicate member path')
        seen.add(path)
        content=item.get('content')
        if not isinstance(content,str):
            raise ValueError(f'execution bundle member content must be UTF-8 text: {path}')
        data=content.encode('utf-8')
        digest=_digest('bundle member sha256',item.get('sha256'))
        if bytes_sha256(data)!=digest:
            raise ValueError(f'execution bundle member digest mismatch: {path}')
        length=item.get('byte_length')
        if length!=len(data):
            raise ValueError(f'execution bundle member length mismatch: {path}')
        files.append((path,data));receipts.append(ProtocolMemberReceipt(path,digest,length))
    receipt=ExecutingProtocolLoadReceipt(
        EXECUTION_PROTOCOL_LOAD_SCHEMA,sha,bytes_sha256(descriptor_raw),version,protocol,
        'bundle',bundle_path,bytes_sha256(raw),tuple(receipts),
        base64.b64encode(descriptor_raw).decode('ascii'),len(raw),
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
        base64.b64encode(bytes(manifest_bytes)).decode('ascii'),None,
    )
    return ExecutionProtocolBundle(receipt,vals)
