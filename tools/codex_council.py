#!/usr/bin/env python3
"""Operate a native council with run-round as the Stable member dispatch entry.

Native identities are host assertions. Shared-disk records are not OS secrecy.
Every paid job still needs its own actual Split and current shared-wallet facts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime import codex_council as council, codex_council_work


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)

    def command(name, help):
        item = commands.add_parser(name, help=help)
        item.add_argument('--root', type=Path, required=True)
        item.add_argument('--council-id', required=True)
        return item

    create = command('create', 'create a native council or open the task first-opinion opportunity')
    create.add_argument('--native-actor', action='append', required=True)
    create.add_argument('--facts', type=Path)
    create.add_argument('--material', type=Path, action='append', default=[])
    create.add_argument('--claude', action='store_true')
    create.add_argument('--first-opinion', metavar='OPEN_DECISION',
                        help='open one independent Claude opinion before this still-open decision')
    create.add_argument('--member-count', type=int)
    create.add_argument('--deadline-seconds', type=int, default=300)
    command('inspect', 'read statuses and identity metadata without opinion bodies')
    packet = command('packet', 'read complete actor-controlled initial or post-barrier packets')
    packet.add_argument('--actor', required=True)
    packet.add_argument('--stage', choices=['INITIAL', 'REDELIBERATION'], default='INITIAL')
    packet.add_argument('--chunk-chars', type=int, default=16000)
    initial = command('native-return', 'seal an actual native initial artifact')
    initial.add_argument('--actor', required=True)
    initial.add_argument('--input', type=Path)
    initial.add_argument('--status', choices=sorted(council.TERMINAL), default='COMPLETE')
    initial.add_argument('--input-version', type=int, required=True)
    work = command('native-work', 'read current work requests from actual public Claude responses')
    work.add_argument('--actor', default='Main', help='actual local Codex worker')
    work_return = command('native-work-return', 'record actual local work for its requesting member without sending')
    work_return.add_argument('--actor', default='Main', help='actual local Codex worker')
    work_return.add_argument('--work-id', required=True)
    work_return.add_argument('--input', type=Path, required=True, help='UTF-8 work output or explanation of unavailability')
    work_return.add_argument('--source', action='append', type=Path, default=[], help='selected UTF-8 evidence window')
    work_return.add_argument('--outcome', choices=sorted(codex_council_work.OUTCOMES), default='COMPLETE')
    prepare = command('prepare-round', 'prepare member requests without sending; bind actual Split per exchange next')
    prepare.add_argument('--kind', choices=sorted(council.ROUND_KINDS), default='INDEPENDENT')
    prepare.add_argument('--member', action='append')
    prepare.add_argument('--model')
    prepare.add_argument('--effort')
    prepare.add_argument('--max-tokens', type=int)
    run = command('run-round', 'send one explicitly prepared batch concurrently, never retry automatically')
    run.add_argument('--round-id', type=int, required=True)
    run.add_argument('--raw-events', action='store_true', help='diagnostic raw token deltas instead of readable source-labelled paragraphs')
    plan_options = run.add_mutually_exclusive_group(required=True)
    plan_options.add_argument('--plan', type=Path,
        help='JSON members object: each member has facts (object or file), ceiling_usd, split_path, optional config_path')
    plan_options.add_argument('--split-plan', type=Path,
        help='first opinion and its native work returns: read price and wallet facts using OpenRouter')
    run.add_argument('--config', type=Path, help='private billing configuration for --split-plan')
    seal = command('seal-member', 'seal actual existing member work without a further paid synthesis')
    seal.add_argument('--member', required=True)
    seal.add_argument('--status', choices=sorted(council.TERMINAL), required=True)
    seal.add_argument('--research', type=Path)
    command('barrier', 'release a phase after explicit terminal states or its recorded deadline')
    result = command('redeliberation-return', 'record an actual native actor redeliberation')
    result.add_argument('--actor', required=True)
    result.add_argument('--input', type=Path, required=True)
    result.add_argument('--input-version', type=int, required=True)
    event = command('event', 'publish actual relevant new material and reopen the same research lines')
    event.add_argument('--input', type=Path, required=True)
    event.add_argument('--kind', required=True)
    event.add_argument('--member', action='append')
    event.add_argument('--native-actor', action='append')
    late = command('reenter-late', 'queue an actual late public result in a later research cycle')
    late.add_argument('--exchange-id', required=True)
    close = command('close', 'close a council while preserving unfinished obligations and public work')
    close.add_argument('--reason', required=True)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(Path(path).read_text(encoding='utf-8-sig'))
    try:
        if args.command == 'create':
            result = council.create_council(args.root, council_id=args.council_id,
                native_actors=args.native_actor, facts_path=args.facts, materials=args.material,
                enable_claude=args.claude, member_count=args.member_count, deadline_seconds=args.deadline_seconds,
                first_opinion=args.first_opinion)
        elif args.command == 'inspect':
            result = council.inspect_council(args.root, args.council_id)
        elif args.command == 'packet':
            result = council.read_packet(args.root, args.council_id, actor=args.actor,
                stage=args.stage, chunk_chars=args.chunk_chars)
        elif args.command == 'native-return':
            result = council.submit_native_initial(args.root, args.council_id, actor=args.actor,
                output_path=args.input, status=args.status, input_version=args.input_version)
        elif args.command == 'native-work':
            result = council.read_native_work(args.root, args.council_id, actor=args.actor)
        elif args.command == 'native-work-return':
            result = council.submit_native_work(args.root, args.council_id, actor=args.actor,
                work_id=args.work_id, output_path=args.input, sources=args.source, outcome=args.outcome)
        elif args.command == 'prepare-round':
            result = council.prepare_round(args.root, args.council_id, kind=args.kind,
                members=args.member, model=args.model, effort=args.effort, max_tokens=args.max_tokens)
        elif args.command == 'run-round':
            if args.split_plan is not None:
                jobs = council.first_opinion_plan(args.root, args.council_id, round_id=args.round_id,
                    split_path=args.split_plan, config_path=args.config)
                quote = next(iter(jobs.values()))
                print(json.dumps({'event': 'first_opinion_quote', 'ceiling_usd': quote['ceiling_usd'],
                                  'model': quote['facts']['model']}, allow_nan=False), flush=True)
            else:
                if args.config is not None:
                    raise ValueError('--config applies to --split-plan; put config_path in an explicit plan')
                jobs = read(args.plan)['members']
                base = args.plan.resolve().parent
                for job in jobs.values():
                    if isinstance(job['facts'], str):
                        path = Path(job['facts'])
                        job['facts'] = read(path if path.is_absolute() else base / path)
                    for key in ('split_path', 'config_path'):
                        if job.get(key):
                            path = Path(job[key])
                            job[key] = str(path if path.is_absolute() else base / path)
            emit = lambda event: print(json.dumps(event, ensure_ascii=False, allow_nan=False), flush=True)
            relay = None
            if not args.raw_events:
                from runtime.codex_live import ParagraphRelay, stable_live
                stable = stable_live(read(args.root / 'session.json')['P_run'])
                relay = ParagraphRelay(emit, stable=stable)
                def source_event(event):
                    exchange = event.get('exchange_id')
                    path = args.root / 'consult/exchanges' / str(exchange) / 'request.json'
                    requested = read(path).get('model') if exchange and path.is_file() else None
                    relay.feed({**event, 'requested_model': requested})
                emit = source_event
            result = council.run_round(args.root, args.council_id, round_id=args.round_id,
                                       jobs=jobs, on_public_event=emit)
            if relay is not None:
                relay.flush()
                print(json.dumps({'event': 'result', 'council_id': args.council_id,
                    'phase': result.get('phase'), 'cycle_id': result.get('cycle_id'),
                    'round_id': args.round_id, 'local_path': result.get('local_path'),
                    'visibility': 'public_text is ready for host commentary, not proof it was displayed',
                    'recovery': 'live read --reader commentary --exchange-id ACTUAL_EXCHANGE'
                                + (' --format commentary' if stable else '')},
                    ensure_ascii=False, allow_nan=False), flush=True)
                return 0
        elif args.command == 'seal-member':
            result = council.seal_member(args.root, args.council_id, member_id=args.member,
                                         status=args.status, research_path=args.research)
        elif args.command == 'barrier':
            result = council.advance_barrier(args.root, args.council_id)
        elif args.command == 'redeliberation-return':
            result = council.submit_redeliberation(args.root, args.council_id, actor=args.actor,
                output_path=args.input, input_version=args.input_version)
        elif args.command == 'event':
            result = council.publish_event(args.root, args.council_id, input_path=args.input,
                kind=args.kind, members=args.member, native_actors=args.native_actor)
        elif args.command == 'reenter-late':
            result = council.reenter_late_result(args.root, args.council_id, exchange_id=args.exchange_id)
        else:
            result = council.close_council(args.root, args.council_id, reason=args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), flush=True)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('DIGR council: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
