#!/usr/bin/env python3
"""Inspect/export the candidate profile, with no network, model calls or install."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_profile import (
    ActiveContext, capability_report, decide_boundary,
    instruction_text, verify_distribution, depth_preferences, refresh_distribution,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('check', help='verify local instruction identity and bytes')
    sub.add_parser('refresh', help='explicitly regenerate local bundle and profile hashes')
    sub.add_parser('depth', help='show user-selected depth and unit-responsibility references')
    ins = sub.add_parser('instructions', help='print a layer; never install it')
    ins.add_argument('layer', choices=('light', 'experimental-router', 'codex-agents'))
    export = sub.add_parser('export', help='create a new instruction file; never overwrite or install global AGENTS')
    export.add_argument('layer', choices=('light', 'experimental-router', 'codex-agents'))
    export.add_argument('--out', required=True, type=Path)
    boundary = sub.add_parser('boundary', help='preview an explicitly supplied host event')
    boundary.add_argument('--input', required=True, type=Path, help='UTF-8 JSON input')
    caps = sub.add_parser('capabilities', help='report declared availability, not run proof')
    caps.add_argument('--input', required=True, type=Path, help='UTF-8 JSON availability map')
    args = ap.parse_args(argv)
    try:
        if args.command == 'check':
            result = verify_distribution(ROOT)
        elif args.command == 'refresh':
            result = refresh_distribution(ROOT)
        elif args.command == 'depth':
            result = depth_preferences(ROOT)
        elif args.command == 'instructions':
            print(instruction_text(ROOT, args.layer), end='')
            return 0
        elif args.command == 'export':
            content = instruction_text(ROOT, args.layer)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(content)
            result = {'exported': args.out.resolve().as_posix(), 'layer': args.layer,
                      'global_install_performed': False, 'run_started': False}
        else:
            data = json.loads(args.input.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('input must be a JSON object')
            if args.command == 'capabilities':
                result = capability_report(data)
            else:
                allowed = {'event', 'message', 'active', 'expected_turn_id', 'goal_changed'}
                if set(data) - allowed:
                    raise ValueError('unknown boundary input keys')
                active = data.get('active')
                result = decide_boundary(
                    data['event'], data.get('message', ''),
                    active=ActiveContext(**active) if active is not None else None,
                    expected_turn_id=data.get('expected_turn_id'),
                    goal_changed=data.get('goal_changed', False),
                ).to_dict()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f'Codex profile error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
