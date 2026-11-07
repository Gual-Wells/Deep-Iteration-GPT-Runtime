#!/usr/bin/env python3
"""A small, single-writer public-decision journal; never a DIGR executor.

JSONL is optional. A human can instead maintain WORK.md and use the existing
workbench. Views only select recorded facts: they do not infer intent, approve
work, qualify N/R/D/V, dispatch agents, or account for formal active time.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    seen = set()
    for event in events:
        if event["id"] in seen:
            raise ValueError("duplicate event id")
        for ref in event.get("relates", []):
            if ref not in seen:
                raise ValueError(f"unknown earlier event: {ref}")
        seen.add(event["id"])
    return events


def commitment(events: list[dict]) -> dict | None:
    return next((event for event in events if event["kind"] == "commitment"), None)


def append(path: Path, *, kind: str, topic: str, summary: str, effect: str,
           actor: str = "Main", origin: str = "observed", **extra) -> dict:
    """Record a public summary once. Caller has one-writer responsibility.

    The sample's floor check enforces the sample's supplied commitment only.
    It is not an interpreter for DIGR invocations or the running protocol.
    """
    if not all(isinstance(s, str) and s.strip() for s in (kind, topic, summary, effect)):
        raise ValueError("kind/topic/summary/effect must be nonempty")
    events = load(path)
    if kind == "commitment" and commitment(events):
        raise ValueError("do not rewrite this study's recorded commitment")
    known = {event["id"] for event in events}
    if any(ref not in known for ref in extra.get("relates", [])):
        raise ValueError("relates must name existing events")
    baseline = commitment(events)
    if kind == "effort" and baseline:
        previous = next((event for event in reversed(events) if event["kind"] == "effort"), baseline)
        for name, lower in baseline.get("floor", {}).items():
            amount = extra.get("investment", {}).get(name)
            if type(amount) is not int or amount < max(lower, previous.get("investment", {}).get(name, lower)):
                raise ValueError(f"{name} would reduce the sample's floor/current investment")
    event = dict(id=f"T{len(events)+1:04d}", kind=kind, topic=topic,
                 summary=summary, effect=effect, actor=actor, origin=origin,
                 recorded_at=datetime.now(timezone.utc).isoformat(), **extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Deliberately not a multi-writer service. No hidden database/worker/cache.
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False)+"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def block(event: dict) -> str:
    parts = [f"### {event['id']} · {event['kind']} · {event['topic']}",
             f"{event['summary']}", f"后果：{event['effect']}"]
    labels = {"basis": "依据", "relates": "相关事件", "decision": "主线处理",
              "reopen_when": "重开条件", "scope": "适用范围", "unless": "失效条件",
              "investment": "工作投入目标", "method": "方法与资源", "exact_text": "原话",
              "floor": "保留的投入下限", "explicit": "显式参数", "artifact": "产物"}
    for key, label in labels.items():
        if key in event:
            value = event[key]
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            parts.append(f"{label}：{text}")
    return "\n\n".join(parts)


def feedback(events: list[dict]) -> list[dict]:
    """Received is different from handled; explicit relationship, no scoring."""
    decisions = [event for event in events if event["kind"] == "decision"]
    returned = [event for event in events if event["kind"] == "return"]
    rows = []
    for task in (event for event in events if event["kind"] == "dispatch"):
        results = [event for event in returned if task["id"] in event.get("relates", [])]
        if not results:
            rows.append(dict(dispatch=task["id"], task=task["summary"], state="尚无结果记录", refs=[]))
        for result in results:
            handling = [event for event in decisions if result["id"] in event.get("relates", [])]
            rows.append(dict(dispatch=task["id"], result=result["id"],
                             finding=result["summary"],
                             state="已回传，Main处理未记录" if not handling else handling[-1].get("decision", "处理已记录"),
                             main_effect=handling[-1]["effect"] if handling else None,
                             refs=[event["id"] for event in handling]))
    return rows


def view(events: list[dict], *, topic: str | None = None) -> str:
    parts = ["# 可继续的公开判断记录", "此视图按记录取回；recorded_at 是记账时间，不是有效任务计时。"]
    origins = sorted({event.get("origin", "unknown") for event in events})
    parts.append("事件来源："+", ".join(origins))
    baseline = commitment(events)
    if baseline:
        latest = next((event for event in reversed(events) if event["kind"] == "effort"), baseline)
        parts.extend(["## 投入约定与当前资源", block(baseline)])
        if latest is not baseline:
            parts.append(block(latest))
        parts.append("这里没有 N/R/D/V 已完成计数，也没有 S/n/r 或 T/t 已验证时长。")
    parts.append("## 委托与纠正")
    parts.extend(block(event) for event in events if event["kind"] in ("request", "correction"))
    parts.append("## 派发与主线处理")
    for row in feedback(events):
        parts.append("- "+json.dumps(row, ensure_ascii=False))
    parts.append("## 可重开的路径与任务内避坑线索")
    shown = {event["id"] for event in events
             if event["kind"] in ("request", "correction", "commitment", "effort")}
    for event in events:
        if event.get("reopen_when") or event["kind"] in ("reopen", "pitfall"):
            parts.append(block(event))
            shown.add(event["id"])
    selected = [event for event in events if topic is None or event["topic"] == topic]
    # A topic can have arbitrarily named branches; this is selection, not a tree.
    remaining = [event for event in selected if event["id"] not in shown]
    if remaining:
        parts.append("## "+("选定问题的原记录" if topic else "公开判断沿革"))
        parts.extend(block(event) for event in remaining)
    return "\n\n".join(parts)+"\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("--journal", type=Path, required=True)
    add.add_argument("--event", type=Path, required=True, help="one public summary as a JSON object")
    query = sub.add_parser("view")
    query.add_argument("--journal", type=Path, required=True)
    query.add_argument("--topic")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "add":
            values = json.loads(args.event.read_text(encoding="utf-8"))
            print(append(args.journal, **values)["id"])
        else:
            print(view(load(args.journal), topic=args.topic), end="")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"trace prototype: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
