#!/usr/bin/env python3
"""Build an identity-verifiable DIGR runtime delivery ZIP for one pinned commit."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FIXED_ZIP_TIME=(2026,9,22,0,0,0)


def git_blob_sha(data: bytes) -> str:
    header=f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header+data).hexdigest()


def safe_path(text: str) -> str:
    p=PurePosixPath(text)
    if not text or text.startswith("/") or "\\" in text or any(x in ("",".","..") for x in p.parts):
        raise ValueError(f"unsafe artifact path: {text!r}")
    return p.as_posix()


def build(output: Path, commit_sha: str) -> str:
    commit_sha=commit_sha.strip().lower()
    if len(commit_sha)!=40 or any(c not in "0123456789abcdef" for c in commit_sha):
        raise ValueError("commit_sha must be 40 lowercase hex")
    manifest=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
    paths=[safe_path(p) for p in manifest["deterministic_helpers"]]
    members=[]
    payloads={}
    for rel in paths:
        data=(ROOT/rel).read_bytes()
        members.append({"path":rel,"byte_length":len(data),"git_blob_sha":git_blob_sha(data)})
        payloads[rel]=data
    index={
        "schema_version":1,
        "version":manifest["version"],
        "protocol":manifest["protocol"],
        "commit_sha":commit_sha,
        "members":members,
    }
    payloads["RUNTIME-INDEX.json"]=(json.dumps(index,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
    payloads["VERSION"]=(ROOT/"VERSION").read_bytes()
    payloads["manifest.json"]=(ROOT/"manifest.json").read_bytes()
    output=output.resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): output.unlink()
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for rel in sorted(payloads):
            info=zipfile.ZipInfo(rel,FIXED_ZIP_TIME)
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100644 & 0xFFFF)<<16
            zf.writestr(info,payloads[rel],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    print(json.dumps({"path":str(output),"sha256":digest,"members":len(members),"commit_sha":commit_sha},sort_keys=True))
    return digest


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--commit-sha",required=True)
    args=ap.parse_args()
    build(args.output,args.commit_sha)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
