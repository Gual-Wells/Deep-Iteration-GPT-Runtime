#!/usr/bin/env python3
"""Append real Begin/End visits or summarize one task group. No running timer."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_visits import append_visit, read_visits, summarize_visits


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('begin', 'end', 'repair', 'report'))
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument('--root', type=Path, help='task with a stored shared-file locator')
    location.add_argument('--file', type=Path, help='shared journal, not a per-agent timer')
    parser.add_argument('--run-id', help='required with --file')
    parser.add_argument('--actor', help='actual participant identity, required for boundaries')
    parser.add_argument('--line', default='M01', help='M01, M02, ... or COMMON')
    parser.add_argument('--phase', choices=('FOUNDATION', 'EXECUTION'), default='EXECUTION')
    parser.add_argument('--category', choices=('WORK', 'SOURCE', 'META', 'IDLE'), default='WORK')
    parser.add_argument('--work', default='', help='short public work purpose')
    parser.add_argument('--begin-id', help='specific missing-End Begin to repair')
    boundary = parser.add_mutually_exclusive_group()
    boundary.add_argument('--at', help='supported effective boundary, ISO8601 with UTC offset')
    boundary.add_argument('--at-ns', type=int, help='supported effective boundary, Unix nanoseconds')
    parser.add_argument('--basis', default='', help='visible evidence for an approximate repair')
    parser.add_argument('--format', choices=('json', 'summary'), default='json',
                        help='report summary is a short readable T/t account')
    args = parser.parse_args(argv)
    try:
        if args.root is not None:
            if args.run_id is not None:
                raise ValueError('--root already identifies the task group; do not override --run-id')
            from runtime.codex_session import _session
            _, metadata = _session(args.root)
            clock = metadata.get('visit_clock')
            if not clock:
                raise ValueError('legacy task: use its pinned owner-clock entry, not shared visits')
            path, run_id = Path(clock['path']), clock['run_id']
        else:
            path, run_id = args.file, args.run_id
            if not run_id:
                raise ValueError('--file needs --run-id')
        if args.action == 'report':
            result = summarize_visits(read_visits(path, run_id=run_id), run_id=run_id, phase=args.phase)
            if args.format == 'summary':
                print(f"T={result['T_seconds'] / 60:.1f}min; t={result['t_seconds'] / 60:.1f}min "
                      f"({args.phase}; all-participant interval unions)")
                print(f"Approximate intervals={result['approximate_interval_count']}; "
                      f"unresolved Begins={result['unresolved_begin_count']}; "
                      f"boundary diagnostics={len(result['gaps'])}; file={result['file_status']}")
                print('Recorded coverage only; repaired intervals included; waiting and open tails excluded.')
                return 0
        else:
            if args.format != 'json':
                raise ValueError('--format summary applies only to report')
            if not args.actor:
                raise ValueError('boundary requires --actor')
            repair = args.action == 'repair'
            if repair and (not args.begin_id or not args.basis or (args.at is None and args.at_ns is None)):
                raise ValueError('repair needs --begin-id, --at/--at-ns and --basis')
            if not repair and (args.begin_id or args.at is not None or args.at_ns is not None or args.basis):
                raise ValueError('historical boundaries require the explicit repair action')
            if args.root is not None and args.action == 'begin':
                from runtime.codex_lifecycle import require_active
                require_active(args.root)
                if args.phase == 'EXECUTION' and args.category in {'WORK', 'SOURCE'}:
                    from runtime.codex_foundation import require_foundation_ready
                    require_foundation_ready(args.root, owner=args.line)
            at_ns = args.at_ns
            if args.at is not None:
                at = datetime.fromisoformat(args.at.replace('Z', '+00:00'))
                if at.tzinfo is None:
                    raise ValueError('--at must include a UTC offset')
                at_ns = int(at.timestamp() * 1_000_000_000)
            extra = {'begin_event_id': args.begin_id} if repair else {}
            result = append_visit(path, run_id=run_id, actor_id=args.actor,
                                  line_id=args.line, phase=args.phase,
                                  category=args.category, event='BEGIN' if args.action == 'begin' else 'END',
                                  work=args.work, at_ns=at_ns, approximate=repair,
                                  basis=args.basis, **extra)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
