#!/usr/bin/env python3
"""Prepare public Consult conversations, call once, inspect and reconcile cost.

Credentials come only from a private config locator or environment variable.
Locator: --config, DIGR_CONSULT_CONFIG, then CODEX_HOME/digr-codex/consult.json.
Config supports api_key_env or an existing api_key_file + api_key_field.
Without a locator the environment default is OPENROUTER_API_KEY. No retry.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime import codex_consult as consult


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help='expand selected real sources and public conversation without sending')
    prepare.add_argument('--root', type=Path, required=True)
    prepare.add_argument('--input', type=Path, required=True, help='current natural task, corrections and content question')
    prepare.add_argument('--material', type=Path, action='append', default=[], help='actual UTF-8 source to include; repeatable')
    prepare.add_argument('--image', type=Path, action='append', default=[], help='actual PNG/JPEG/WebP bytes to include; repeatable')
    prepare.add_argument('--continue-from', help='same-task exchange whose exact public messages and reply are replayed')
    prepare.add_argument('--paper-root', type=Path,
                         help='select one registered paper 0.5 for native Sonnet authoring; inherited on continuation')
    prepare.add_argument('--exchange-id', help='optional simple local identifier')
    prepare.add_argument('--model', default=consult.DEFAULT_MODEL)
    prepare.add_argument('--effort', default=consult.DEFAULT_EFFORT)
    prepare.add_argument('--max-tokens', type=int, default=consult.DEFAULT_MAX_TOKENS,
                         help='combined hidden/public output ceiling, independent of native depth')
    prepare.add_argument('--input-revision', help='optional public source/handoff revision label')
    call = commands.add_parser('call', help='one physical inference POST with task-wide budget reservations')
    call.add_argument('--root', type=Path, required=True)
    call.add_argument('--exchange-id', required=True)
    call.add_argument('--facts', type=Path, required=True, help='actual current authorization, prices, input bound and wallet/budget facts')
    call.add_argument('--ceiling-usd', type=float, required=True, help='positive conservative call reservation; not a provider invoice guarantee')
    call.add_argument('--config', type=Path, help='explicit private provider/credential config; never copied into the task')
    view = commands.add_parser('inspect', help='read public source/output facts and all task exchange costs; no network or credentials')
    view.add_argument('--root', type=Path, required=True)
    view.add_argument('--exchange-id')
    reconcile = commands.add_parser('reconcile-cost', help='one metadata GET or actual supplied read-back; never infer or regenerate content')
    reconcile.add_argument('--root', type=Path, required=True)
    reconcile.add_argument('--exchange-id', required=True)
    source = reconcile.add_mutually_exclusive_group()
    source.add_argument('--metadata', type=Path, help='actual generation metadata read-back for offline composition')
    source.add_argument('--config', type=Path, help='explicit private config for the metadata GET')
    args = parser.parse_args(argv)
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    try:
        if args.command == 'prepare':
            result = consult.prepare_request(args.root, input_path=args.input, materials=args.material,
                images=args.image, continue_from=args.continue_from, exchange_id=args.exchange_id,
                model=args.model, effort=args.effort, max_tokens=args.max_tokens, input_revision=args.input_revision,
                paper_root=args.paper_root)
        elif args.command == 'call':
            session = read(args.root / 'session.json')
            live = consult.streams_public(session['P_run'])
            emit = (lambda event: print(json.dumps(event, ensure_ascii=False, allow_nan=False), flush=True)) if live else None
            result = consult.call_once(args.root, args.exchange_id, facts=read(args.facts),
                                       ceiling_usd=args.ceiling_usd, config_path=args.config,
                                       on_public_event=emit)
            if live:
                print(json.dumps({'event': 'result', 'result': result}, ensure_ascii=False, allow_nan=False), flush=True)
                return 0
        elif args.command == 'inspect':
            result = consult.inspect_exchange(args.root, args.exchange_id)
        else:
            result = consult.reconcile_cost(args.root, args.exchange_id,
                metadata=read(args.metadata) if args.metadata else None, config_path=args.config)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Network errors are sanitized inside runtime; no credential values,
        # arbitrary raw response bodies or hidden reasoning enter CLI errors.
        print('DIGR Consult: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
