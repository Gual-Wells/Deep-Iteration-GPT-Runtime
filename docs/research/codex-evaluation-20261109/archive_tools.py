"""Package, verify, and safely extract the owned empirical study."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
PIN = "b258276632054f7f8d1d8a060e01b98b9c7aa3be"
FIXED_TIME = (2026, 11, 9, 0, 0, 0)
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".jsonl", ".html", ".toml", ".css", ".svg"}
TOKEN_PATTERNS = [
    re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{28,}"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{35,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=]{40,}"),
]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")

def safe_member(name):
    p = PurePosixPath(name)
    if not name or "\\" in name or p.is_absolute() or any(x in ("", ".", "..") for x in p.parts):
        raise ValueError("Unsafe archive member: " + name)
    if any(":" in part for part in p.parts):
        raise ValueError("Drive path in archive")
    return p

def check_secret(data, path):
    if any(pattern.search(data) for pattern in TOKEN_PATTERNS):
        raise RuntimeError("Credential-shaped material requires review; path only: " + str(path))

def zip_bytes(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(entries.items()):
            safe_member(name)
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)

def readable_markdown(text, source, owner):
    """Make display-copy references portable; exact originals remain in the ZIP."""
    def link(match):
        label, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        target = target.strip("<>")
        raw_path, _, fragment = target.partition("#")
        portable = raw_path.replace("\\", "/")
        if re.match(r"^/[A-Za-z]:/", portable):
            portable = portable[1:]
        q = Path(portable)
        if not q.is_absolute():
            q = owner.parent / q
        q = q.resolve()
        try:
            rel = q.relative_to(source)
        except ValueError:
            return label + "（原位置：" + target + "）"
        try:
            pin_rel = owner.relative_to(source / "pin")
        except ValueError:
            pin_rel = None
        if pin_rel is not None and not q.is_file():
            remote_rel = rel.relative_to("pin").as_posix()
            return "[" + label + "](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/" + PIN + "/" + remote_rel + ("#" + fragment if fragment else "") + ")"
        if q.is_file() and ".git" not in rel.parts and "__pycache__" not in rel.parts:
            relative = os.path.relpath(q, owner.parent).replace("\\", "/")
            return "[" + label + "](" + relative + ("#" + fragment if fragment else "") + ")"
        return label + "（原位置：" + target + "）"
    return re.sub(r"\[([^\]]*)\]\(([^)]+)\)", link, text)

def opaque(value):
    if isinstance(value, str) and re.fullmatch(r"gAAAA[A-Za-z0-9_=-]{80,}", value):
        return {"omitted": "encrypted_transport_field", "sha256": digest(value.encode()), "characters": len(value)}
    if isinstance(value, dict):
        return {key: opaque(item) for key, item in value.items()}
    if isinstance(value, list):
        return [opaque(item) for item in value]
    return value

def export_public_events(path, discussion_only=False):
    kept, removed = [], {}
    for line in path.open(encoding="utf-8"):
        obj = json.loads(line)
        kind, p = obj.get("type"), obj.get("payload", {})
        out = None
        if kind == "session_meta" and not discussion_only:
            source = p.get("source", {})
            spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
            out = {"type": "session_meta", "payload": {"id": p.get("id"), "model_provider": p.get("model_provider"), "spawn": spawn}}
        elif kind == "turn_context" and not discussion_only:
            out = {"type": kind, "payload": {k: p.get(k) for k in ("turn_id", "model", "effort")}}
        elif kind == "event_msg" and not discussion_only:
            if p.get("type") == "token_count":
                info = p.get("info") or {}
                out = {"type": kind, "payload": {"type": "token_count", "info": {k: info.get(k) for k in ("total_token_usage", "last_token_usage", "last_usage_includes_reasoning", "model_context_window")}}}
            elif p.get("type") == "task_complete":
                out = {"type": kind, "payload": {k: p.get(k) for k in ("type", "turn_id", "last_agent_message")}}
        elif kind == "response_item":
            typ = p.get("type")
            if typ == "message":
                role, phase = p.get("role"), p.get("phase")
                is_public_assistant = role == "assistant" and phase in ("commentary", "final_answer")
                is_discussion_user = discussion_only and role == "user"
                if is_public_assistant or is_discussion_user:
                    content = [dict(x) for x in p.get("content", []) if x.get("type") in ("input_text", "output_text", "text")]
                    for part in content:
                        part["text"] = re.sub(r"<oai-mem-citation>.*?</oai-mem-citation>", "", part.get("text", ""), flags=re.S).rstrip()
                    text = "".join(x.get("text", "") for x in content)
                    private_context = text.startswith(("# AGENTS.md instructions", "<environment_context>", "<external_codex_apps", "Companion Page snapshot"))
                    if text and not private_context:
                        out = {"type": kind, "payload": {"type": typ, "role": role, "phase": phase, "content": content}}
            elif not discussion_only and typ in ("function_call", "custom_tool_call", "function_call_output", "custom_tool_call_output"):
                public = dict(p)
                if typ == "function_call" and isinstance(public.get("arguments"), str):
                    try:
                        public["arguments"] = json.dumps(opaque(json.loads(public["arguments"])), ensure_ascii=False)
                    except ValueError:
                        pass
                out = {"type": kind, "payload": public}
        if out is None:
            key = kind + ":" + str(p.get("type", ""))
            removed[key] = removed.get(key, 0) + 1
            continue
        out["timestamp"] = obj.get("timestamp")
        raw = json.dumps(out, ensure_ascii=False).encode("utf-8")
        check_secret(raw, path)
        kept.append(raw + b"\n")
    return b"".join(kept), removed

def build(source, discussion_log=None):
    source = source.resolve()
    if source == HERE or HERE in source.parents or source in HERE.parents:
        raise ValueError("Study source and archive destination must be separate")
    snapshot = HERE / "snapshots/original-study.zip"
    if snapshot.exists():
        raise FileExistsError("Archive already built; inspect rather than overwrite")
    entries, inventory, excluded = {}, [], []
    for path in sorted(source.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise RuntimeError("Reparse point is not a study file: " + str(path))
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if rel.parts[:2] == ("qa", "browser-profile"):
            excluded.append({"path": rel.as_posix(), "bytes": path.stat().st_size})
            continue
        if path.name.lower() in ("auth.json", ".env", ".env.local", "credentials.json", "id_rsa", "id_ed25519"):
            raise RuntimeError("Credential file is outside archive scope: " + rel.as_posix())
        raw = path.read_bytes()
        check_secret(raw, rel)
        name = rel.as_posix()
        entries[name] = raw
        record = {"path": name, "bytes": len(raw), "sha256": digest(raw), "readable_copy": None}
        if ".git" not in rel.parts and "__pycache__" not in rel.parts and path.suffix not in (".pyc", ".pyo"):
            target = HERE / "readable" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() in TEXT_SUFFIXES or path.name in ("VERSION", ".gitignore", ".gitattributes"):
                text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
                if path.suffix.lower() == ".md":
                    text = readable_markdown(text, source, path)
                if text and not text.endswith("\n"):
                    text += "\n"
                display = text.encode("utf-8")
            else:
                display = raw
            target.write_bytes(display)
            record["readable_copy"] = {"path": target.relative_to(HERE).as_posix(), "sha256": digest(display), "byte_identical": display == raw}
        inventory.append(record)
    zip_bytes(snapshot, entries)
    with zipfile.ZipFile(snapshot) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == set(entries)
        assert all(digest(z.read(record["path"])) == record["sha256"] for record in inventory)
    assert all(digest((source / record["path"]).read_bytes()) == record["sha256"] for record in inventory)
    trace_entries, trace_inventory = {}, []
    records = json.loads((source / "telemetry.json").read_text(encoding="utf-8"))["records"]
    for record in records:
        path = Path(record["file"])
        content, removed = export_public_events(path)
        name = record["agent_path"].strip("/").replace("/", "__") + ".jsonl"
        trace_entries[name] = content
        trace_inventory.append({"agent_path": record["agent_path"], "thread_id": record["id"], "path": name, "source_log_sha256": digest(path.read_bytes()), "export_sha256": digest(content), "removed_record_counts": removed})
    if discussion_log:
        content, removed = export_public_events(discussion_log, discussion_only=True)
        trace_entries["public-discussion.jsonl"] = content
        trace_inventory.append({"agent_path": "/root public discussion only", "path": "public-discussion.jsonl", "export_sha256": digest(content), "removed_record_counts": removed})
    trace_zip = HERE / "snapshots/public-trajectories.zip"
    zip_bytes(trace_zip, trace_entries)
    manifest = {
        "schema": 1, "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_date": "2026-11-09", "protocol_pin": "0.7.0@" + PIN,
        "current_entry": "README.md", "current_report": "readable/report.html",
        "current_conclusion": "The default-profile efficacy comparison is not valid; preserve the user's function-header/cutoff correction. Local code observations remain.",
        "authoritative_snapshot": {"path": snapshot.relative_to(HERE).as_posix(), "bytes": snapshot.stat().st_size, "sha256": digest(snapshot.read_bytes()), "files": len(inventory)},
        "nested_fixture_git_count": len(list(source.rglob(".git"))),
        "source_inventory": inventory,
        "readable_copy_policy": "Derived UTF-8/LF display copies, with portable Markdown links. Do not compare their bytes to original study hashes or grade from this display copy; extract the authoritative ZIP.",
        "excluded_environment": {"prefix": "qa/browser-profile/", "reason": "Browser runtime profile and cache, not experimental evidence", "file_count": len(excluded), "bytes": sum(row["bytes"] for row in excluded)},
        "public_trajectories": {"path": trace_zip.relative_to(HERE).as_posix(), "bytes": trace_zip.stat().st_size, "sha256": digest(trace_zip.read_bytes()), "records": trace_inventory,
            "policy": "Subject/descendant public messages, tool calls/results, numeric usage; root public discussion only. No user global AGENTS, developer/system context, hidden reasoning, account rate-limit state, or plaintext recovery of encrypted transport. Encrypted delegate fields are replaced by digest/length metadata."},
        "original_credentials_published": False,
        "original_source_changed": False
    }
    write_json(HERE / "archive-manifest.json", manifest)
    print(json.dumps({"snapshot_files": len(inventory), "snapshot_bytes": snapshot.stat().st_size, "readable_files": sum(row["readable_copy"] is not None for row in inventory), "trajectory_exports": len(trace_entries), "excluded_browser_files": len(excluded)}, ensure_ascii=False))

def verify():
    manifest = json.loads((HERE / "archive-manifest.json").read_text(encoding="utf-8"))
    meta = manifest["authoritative_snapshot"]
    snapshot = HERE / meta["path"]
    assert digest(snapshot.read_bytes()) == meta["sha256"]
    with zipfile.ZipFile(snapshot) as z:
        assert z.testzip() is None
        records = manifest["source_inventory"]
        assert set(z.namelist()) == {row["path"] for row in records}
        for row in records:
            safe_member(row["path"])
            assert digest(z.read(row["path"])) == row["sha256"]
            if row["readable_copy"]:
                display = HERE / row["readable_copy"]["path"]
                assert digest(display.read_bytes()) == row["readable_copy"]["sha256"]
    traces = manifest["public_trajectories"]
    assert digest((HERE / traces["path"]).read_bytes()) == traces["sha256"]
    with zipfile.ZipFile(HERE / traces["path"]) as z:
        assert z.testzip() is None
        for row in traces["records"]:
            assert digest(z.read(row["path"])) == row["export_sha256"]
    assert not list((HERE / "readable").rglob(".git"))
    print(json.dumps({"verified": True, "original_files": meta["files"], "fixture_git_histories": manifest["nested_fixture_git_count"], "public_exports": len(traces["records"])}, ensure_ascii=False))
    return manifest

def extract(destination):
    manifest = verify()
    destination = destination.resolve()
    if os.name == "nt" and destination.drive.upper() != "D:":
        raise ValueError("On this host experimental data must be stored on D:")
    if destination.exists():
        raise FileExistsError("Replay directory must be new")
    destination.mkdir(parents=True)
    with zipfile.ZipFile(HERE / manifest["authoritative_snapshot"]["path"]) as z:
        for info in z.infolist():
            safe_member(info.filename)
        z.extractall(destination)
    assert all(digest((destination / row["path"]).read_bytes()) == row["sha256"] for row in manifest["source_inventory"])
    print(json.dumps({"extracted": str(destination), "source_bytes_verified": True}, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build"); b.add_argument("--source", type=Path, required=True); b.add_argument("--discussion-log", type=Path)
    sub.add_parser("verify")
    e = sub.add_parser("extract"); e.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build": build(args.source, args.discussion_log)
    elif args.command == "verify": verify()
    else: extract(args.out)

if __name__ == "__main__":
    main()
