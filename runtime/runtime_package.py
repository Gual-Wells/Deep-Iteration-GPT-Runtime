"""Single-boundary verifier for an exact-commit DIGR runtime package.

This module is intentionally standalone and stdlib-only so a host can bridge
one pinned verifier plus one recursive Git tree observation, then attest the
whole runtime archive without fetching/verifying every helper separately.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from hashlib import sha1,sha256
import argparse,json
from pathlib import Path,PurePosixPath
from typing import Any,Mapping
import zipfile

def _hex(name:str,value:object,n:int)->str:
    v=str(value).strip().lower()
    if len(v)!=n or any(c not in '0123456789abcdef' for c in v):
        raise ValueError(f'{name} must be {n} lowercase hex')
    return v

def _safe(path:str)->str:
    p=PurePosixPath(path)
    if not path or path.startswith('/') or '\\' in path or any(x in ('','.','..') for x in p.parts):
        raise ValueError(f'unsafe archive path: {path!r}')
    return p.as_posix()

def _blob(data:bytes)->str:
    return sha1(f'blob {len(data)}\0'.encode('ascii')+data).hexdigest()

def _tree_map(tree:Mapping[str,Any])->dict[str,str]:
    raw=tree.get('tree')
    if not isinstance(raw,list): raise ValueError('recursive Git tree JSON requires tree[]')
    out={}
    for item in raw:
        if isinstance(item,Mapping) and item.get('type')=='blob':
            out[_safe(item['path'])]=_hex('tree blob sha',item['sha'],40)
    return out

@dataclass(frozen=True)
class RuntimePackageAttestationReceipt:
    schema_version:int
    commit_sha:str
    package_sha256:str
    version:str
    protocol:str
    helper_count:int
    protocol_member_count:int
    manifest_sha256:str
    protocol_bundle_sha256:str
    def to_dict(self): return asdict(self)

def attest_runtime_package(archive:Path,*,expected_commit_sha:str,git_tree:Mapping[str,Any])->RuntimePackageAttestationReceipt:
    expected_commit_sha=_hex('expected_commit_sha',expected_commit_sha,40)
    archive=Path(archive)
    raw_archive=archive.read_bytes()
    tree=_tree_map(git_tree)
    with zipfile.ZipFile(archive,'r') as zf:
        names=[_safe(x.filename) for x in zf.infolist() if not x.is_dir()]
        if len(names)!=len(set(names)): raise ValueError('duplicate runtime archive member')
        payload={n:zf.read(n) for n in names}
    try:index=json.loads(payload['RUNTIME-INDEX.json'].decode('utf-8'))
    except (KeyError,UnicodeDecodeError,json.JSONDecodeError) as exc: raise ValueError('invalid RUNTIME-INDEX.json') from exc
    if index.get('schema_version')!=2: raise ValueError('unsupported runtime index schema')
    if _hex('runtime commit',index.get('commit_sha'),40)!=expected_commit_sha: raise ValueError('runtime commit mismatch')
    try:manifest_bytes=payload['manifest.json'];version_bytes=payload['VERSION']
    except KeyError as exc: raise ValueError('runtime package missing manifest/VERSION') from exc
    try:manifest=json.loads(manifest_bytes.decode('utf-8'))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise ValueError('invalid packaged manifest') from exc
    version=version_bytes.decode('utf-8').strip()
    if manifest.get('version')!=version or index.get('version')!=version or index.get('protocol')!=manifest.get('protocol'):
        raise ValueError('package version/protocol identity mismatch')

    def verify_meta(path:str,meta:Mapping[str,Any]):
        data=payload.get(path)
        if data is None: raise ValueError(f'missing package member {path}')
        if len(data)!=meta.get('byte_length') or sha256(data).hexdigest()!=meta.get('sha256') or _blob(data)!=meta.get('git_blob_sha'):
            raise ValueError(f'package member identity mismatch: {path}')
        if tree.get(path)!=meta.get('git_blob_sha'):
            raise ValueError(f'package member does not match pinned Git tree: {path}')

    verify_meta('manifest.json',index['manifest'])
    verify_meta('VERSION',index['version_file'])
    helpers=manifest.get('deterministic_helpers')
    members=index.get('members')
    if not isinstance(helpers,list) or not isinstance(members,list) or [x.get('path') for x in members]!=helpers:
        raise ValueError('runtime helper list does not equal manifest deterministic_helpers')
    for meta in members: verify_meta(_safe(meta['path']),meta)

    bmeta=index.get('protocol_bundle')
    if not isinstance(bmeta,Mapping): raise ValueError('runtime index lacks protocol bundle metadata')
    bundle_path=_safe(bmeta.get('path'))
    if bundle_path!=manifest.get('execution_bundle',{}).get('path'): raise ValueError('protocol bundle path mismatch')
    verify_meta(bundle_path,bmeta)
    bundle=json.loads(payload[bundle_path].decode('utf-8'))
    expected=[manifest['entrypoint'],*manifest['core']]
    raw_members=bundle.get('members')
    if not isinstance(raw_members,list) or [x.get('path') for x in raw_members]!=expected:
        raise ValueError('execution bundle does not match entrypoint/core order')
    for item in raw_members:
        p=_safe(item['path']);data=item.get('content','').encode('utf-8')
        if len(data)!=item.get('byte_length') or sha256(data).hexdigest()!=item.get('sha256'):
            raise ValueError(f'execution bundle member digest mismatch: {p}')
        if tree.get(p)!=_blob(data): raise ValueError(f'execution bundle member differs from authoritative Git blob: {p}')

    expected_names=set(helpers)|{'RUNTIME-INDEX.json','manifest.json','VERSION',bundle_path}
    if set(payload)!=expected_names: raise ValueError('runtime archive contains unexpected or missing members')
    return RuntimePackageAttestationReceipt(
        1,expected_commit_sha,sha256(raw_archive).hexdigest(),version,manifest['protocol'],
        len(helpers),len(expected),sha256(manifest_bytes).hexdigest(),sha256(payload[bundle_path]).hexdigest()
    )

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--archive',required=True,type=Path)
    ap.add_argument('--commit-sha',required=True)
    ap.add_argument('--tree-json',required=True,type=Path)
    ns=ap.parse_args()
    tree=json.loads(ns.tree_json.read_text(encoding='utf-8'))
    print(json.dumps(attest_runtime_package(ns.archive,expected_commit_sha=ns.commit_sha,git_tree=tree).to_dict(),sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
