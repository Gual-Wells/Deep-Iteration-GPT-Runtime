#!/usr/bin/env python3
"""Prepare public Consult conversations, call once, inspect and reconcile cost.

Credentials come only from a private config locator or environment variable.
Locator: --config, DIGR_CONSULT_CONFIG, then CODEX_HOME/digr-codex/consult.json.
Config supports api_key_env or an existing api_key_file + api_key_field.
New 0.16+ submissions also require the stable nonsecret wallet_id alias;
all managed tasks share the CODEX_HOME/digr-codex SQLite reservation ledger.
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
    prepare.add_argument('--participation-role', choices=('consult_guidance', 'council_member'), default='consult_guidance')
    prepare.add_argument('--council-scope', type=Path, help='actual registered council member scope; not a role authorization')
    call = commands.add_parser('call', help='one physical inference POST with task-wide budget reservations')
    call.add_argument('--root', type=Path, required=True)
    call.add_argument('--exchange-id', required=True)
    call.add_argument('--facts', type=Path, required=True, help='actual current authorization, prices, input bound and wallet/budget facts')
    call.add_argument('--ceiling-usd', type=float, required=True, help='positive conservative call reservation; not a provider invoice guarantee')
    call.add_argument('--config', type=Path, help='explicit private provider/credential config; never copied into the task')
    call.add_argument('--split-plan', type=Path,
                      help='native Codex Split result bound to this request; required for new 0.13+ submissions')
    call.add_argument('--raw-events', action='store_true', help='diagnostic raw token events; default new pins relay readable public paragraphs')
    split = commands.add_parser('split', help='read the current local Split binding; native Codex performs the research')
    split.add_argument('--root', type=Path, required=True)
    split.add_argument('--exchange-id', required=True)
    split.add_argument('--input', type=Path, help='actual unbound native decision; no generated research text')
    split.add_argument('--out', type=Path, help='write a new bound plan; use together with --input')
    preview = commands.add_parser('budget-preview', help='calculate a safe task fee proposal from current prepared requests')
    preview.add_argument('--root', type=Path, required=True)
    preview.add_argument('--input', type=Path, required=True,
                         help='jobs, task_ceiling_usd, scope and configured wallet_id')
    preview.add_argument('--out', type=Path, required=True, help='write a new proposal before asking the user')
    approve = commands.add_parser('budget-approve', help='record the actual handled fee approval for a shown proposal')
    approve.add_argument('--root', type=Path, required=True)
    approve.add_argument('--preview', type=Path, required=True)
    limit = commands.add_parser('budget-limit', help='record an actual narrower task spending limit, even across layer changes')
    limit.add_argument('--root', type=Path, required=True)
    for command in (approve, limit):
        command.add_argument('--reply-file', type=Path, required=True)
        command.add_argument('--source', required=True)
        command.add_argument('--quote', required=True)
    approve.add_argument('--task-ceiling-usd', type=float, help='actual lower amount selected by the user, if any')
    limit.add_argument('--task-ceiling-usd', type=float, required=True)
    view = commands.add_parser('inspect', help='read public source/output facts and all task exchange costs; no network or credentials')
    view.add_argument('--root', type=Path, required=True)
    view.add_argument('--exchange-id')
    reconcile = commands.add_parser('reconcile-cost', help='one metadata GET or actual supplied read-back; never infer or regenerate content')
    reconcile.add_argument('--root', type=Path, required=True)
    reconcile.add_argument('--exchange-id', required=True)
    source = reconcile.add_mutually_exclusive_group()
    source.add_argument('--metadata', type=Path, help='actual generation metadata read-back for offline composition')
    source.add_argument('--config', type=Path, help='explicit private config for the metadata GET')
    recovery = commands.add_parser('recover-preflight', help='release a proven unsent pre-intent reservation without inference or replay')
    recovery.add_argument('--root', type=Path, required=True)
    recovery.add_argument('--exchange-id', required=True)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    try:
        if args.command == 'prepare':
            result = consult.prepare_request(args.root, input_path=args.input, materials=args.material,
                images=args.image, continue_from=args.continue_from, exchange_id=args.exchange_id,
                model=args.model, effort=args.effort, max_tokens=args.max_tokens, input_revision=args.input_revision,
                paper_root=args.paper_root, participation_role=args.participation_role,
                council_scope=read(args.council_scope) if args.council_scope else None)
        elif args.command == 'call':
            session = read(args.root / 'session.json')
            live = consult.streams_public(session['P_run'])
            emit = (lambda event: print(json.dumps(event, ensure_ascii=False, allow_nan=False), flush=True)) if live else None
            compact = tuple(map(int, session['P_run'].split('@')[0].split('.'))) >= (0, 16, 0) and not args.raw_events
            relay = None
            if live and compact:
                from runtime.codex_live import ParagraphRelay, stable_live
                stable = stable_live(session['P_run'])
                relay = ParagraphRelay(emit, stable=stable)
                requested_model = read(args.root / 'consult/exchanges' / args.exchange_id / 'request.json')['model']
                emit = lambda event: relay.feed({**event, 'requested_model': requested_model})
            result = consult.call_once(args.root, args.exchange_id, facts=read(args.facts),
                                       ceiling_usd=args.ceiling_usd, config_path=args.config,
                                       split_path=args.split_plan, on_public_event=emit)
            if relay is not None:
                relay.flush()
            if live:
                if compact:
                    attempt = result.get('exchange', {})
                    print(json.dumps({'event': 'result', 'exchange_id': args.exchange_id,
                        'public_path': result.get('public_path'), 'public_status': attempt.get('public_status'),
                        'billing_status': attempt.get('billing_status'), 'known_cost_usd': attempt.get('known_cost_usd'),
                        'identity': result.get('sonnet_model_identity'),
                        'recovery': 'live read --reader commentary --exchange-id ' + args.exchange_id
                                    + (' --format commentary' if stable else ''),
                        'visibility': 'stdout is not user-visible commentary; host must relay actual text'},
                        ensure_ascii=False, allow_nan=False), flush=True)
                else:
                    print(json.dumps({'event': 'result', 'result': result}, ensure_ascii=False, allow_nan=False), flush=True)
                return 0
        elif args.command == 'split':
            if (args.input is None) != (args.out is None):
                raise ValueError('split --input and --out must be used together')
            result = (consult.bind_split_decision(args.root, args.exchange_id,
                input_path=args.input, output=args.out) if args.input else consult.split_brief(args.root, args.exchange_id))
        elif args.command in {'budget-preview', 'budget-approve', 'budget-limit'}:
            from runtime import codex_consult_budget
            if args.command == 'budget-preview':
                supplied = read(args.input)
                result = codex_consult_budget.preview(args.root, jobs=supplied['jobs'],
                    task_ceiling_usd=supplied['task_ceiling_usd'], scope=supplied['scope'], wallet_id=supplied['wallet_id'])
                consult._write(args.out, result, new=True)
            else:
                text = args.reply_file.read_bytes().decode('utf-8-sig')
                decide = {'user_text': text, 'source': args.source, 'quote': args.quote,
                          'task_ceiling_usd': args.task_ceiling_usd}
                result = (codex_consult_budget.approve(args.root, preview_path=args.preview, **decide)
                          if args.command == 'budget-approve' else codex_consult_budget.record_limit(args.root, **decide))
        elif args.command == 'inspect':
            result = consult.inspect_exchange(args.root, args.exchange_id)
        elif args.command == 'recover-preflight':
            result = consult.recover_preflight(args.root, args.exchange_id)
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
