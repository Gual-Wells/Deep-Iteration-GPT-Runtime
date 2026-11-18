#!/usr/bin/env python3
"""Collect selected native aggregate usage and render task-scoped cost reports.

No API requests, message content extraction, or implicit chat discovery.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_usage import build_usage_report, collect_usage, record_rate_limits, render_usage_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    collect = sub.add_parser('collect', help='project aggregates from one explicitly selected native JSONL')
    collect.add_argument('--root', required=True, type=Path)
    collect.add_argument('--rollout', required=True, type=Path)
    collect.add_argument('--actor', required=True)
    collect.add_argument('--start', help='ISO timestamp with timezone; inclusive')
    collect.add_argument('--end', help='ISO timestamp with timezone; inclusive')
    collect.add_argument('--turn-id', action='append', default=[])
    collect.add_argument('--token-baseline', type=Path, help='prior cumulative aggregate JSON, not message content')
    collect.add_argument('--model', help='fill missing host metadata only')
    collect.add_argument('--effort', help='fill missing host metadata only')
    collect.add_argument('--speed', help='fill missing host metadata only')
    collect.add_argument('--account', default='current-account')
    collect.add_argument('--limit-id', action='append', default=None,
                         help='explicitly known eligible metered bucket; repeat for multiple known buckets')
    snapshot = sub.add_parser('snapshot', help='project an actual rate-limit read result')
    snapshot.add_argument('--root', required=True, type=Path)
    snapshot.add_argument('--input', required=True, type=Path)
    snapshot.add_argument('--at', required=True, help='actual observation ISO timestamp with timezone')
    snapshot.add_argument('--account', default='current-account')
    snapshot.add_argument('--baseline', action='store_true')
    for name in ('report', 'body'):
        command = sub.add_parser(name)
        command.add_argument('--root', required=True, type=Path)
        command.add_argument('--account-activity', choices=('unknown', 'primary_task', 'exclusive'))
        command.add_argument('--calibration', type=Path,
                             help='explicit per-model input/cached_input/output relative weights')
    args = parser.parse_args(argv)
    try:
        if args.action == 'collect':
            baseline = json.loads(args.token_baseline.read_text(encoding='utf-8-sig')) if args.token_baseline else None
            result = collect_usage(args.root, args.rollout, actor=args.actor,
                start=args.start, end=args.end, turn_ids=args.turn_id, token_baseline=baseline,
                model=args.model, effort=args.effort, speed=args.speed, account=args.account,
                limit_ids=args.limit_id)
        elif args.action == 'snapshot':
            supplied = json.loads(args.input.read_text(encoding='utf-8-sig'))
            result = record_rate_limits(args.root, supplied, observed_at=args.at,
                                         account=args.account, baseline=args.baseline)
        else:
            calibration = json.loads(args.calibration.read_text(encoding='utf-8-sig')) if args.calibration else None
            result = build_usage_report(args.root, account_activity=args.account_activity, calibration=calibration)
            if args.action == 'body':
                print(render_usage_markdown(result), end='')
                return 0
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
