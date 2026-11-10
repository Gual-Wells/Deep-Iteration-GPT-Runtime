#!/usr/bin/env python3
"""One source-checkout CLI for the experimental Codex profile and work tools.

No model calls, agent scheduler or permission escalation. Existing standalone
profile/workbench/experience commands remain supported.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_permissions import assess_operation
from runtime.codex_foundation import (
    answer_foundation, confirm_foundation, foundation_packet, propose_foundation, revoke_foundation,
)
from runtime.codex_session import (
    ACTIVITY_STATES, activity, create_line, create_session, line_packet,
    session_report, set_clock_anchor, set_line_parameters, update_line,
)
from runtime.codex_transport import CodexRepositoryTransport, load_acquisition
from runtime.codex_lifecycle import (
    MESSAGE_ACTIONS, ingest_message, handle_message, load_lifecycle, close_session, recover_session, terminate_message,
)


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError(f'expected a JSON object: {path}')
    return value


def read_message(path: Path) -> str:
    # Match the lifecycle's byte snapshot. Text-mode newline translation would
    # turn a genuine Windows CRLF reply into different confirmation text.
    return path.read_bytes().decode('utf-8-sig')


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    # Pass through argument parsing rather than duplicate mature CLI surfaces.
    if argv and argv[0] in ('profile', 'workbench', 'experience', 'knowledge', 'timeline', 'voice', 'return'):
        from tools import codex_experience, codex_profile, codex_workbench, codex_knowledge, codex_timeline, codex_voice
        if argv[0] == 'return':
            from tools.codex_return import main as return_main
            return return_main(argv[1:])
        return {'profile': codex_profile.main, 'workbench': codex_workbench.main,
                'experience': codex_experience.main,
                'knowledge': codex_knowledge.main,
                'timeline': codex_timeline.main,
                'voice': codex_voice.main}[argv[0]](argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('profile', 'workbench', 'experience', 'knowledge', 'timeline', 'voice', 'return'):
        sub.add_parser(name, help=f'{name} commands; append --help for details')
    acquire = sub.add_parser('acquire', help='actually acquire a live, immutable Codex profile')
    acquire.add_argument('--stage', choices=('startup', 'help', 'execution'), default='startup')
    acquire.add_argument('--out', type=Path, help='new directory for acquired bytes and observations')
    acquire.add_argument('--continue-from', type=Path,
                         help='continue this already-acquired pin; never substitutes for live routing a new message')
    task = sub.add_parser('task', help='prepare an independently resumable task')
    ts = task.add_subparsers(dest='action', required=True)
    create = ts.add_parser('create')
    create.add_argument('--out', required=True, type=Path)
    create.add_argument('--request', required=True, type=Path)
    create.add_argument('--p-run', required=True)
    create.add_argument('--decisions', type=Path)
    create.add_argument('--explicit', type=Path, help='original explicit parameter declarations, if any')
    create.add_argument('--anchor-pid', type=int)
    create.add_argument('--m', type=int)
    create.add_argument('--require-foundation', action='store_true', default=None,
                        help='prepare research first; managed execution waits for the current user decision')
    report = ts.add_parser('report')
    report.add_argument('--root', required=True, type=Path)
    message = ts.add_parser('message', help='snapshot an actual user input; fence managed execution until handled')
    message.add_argument('--root', required=True, type=Path)
    message.add_argument('--source-file', required=True, type=Path)
    message.add_argument('--source-ref', required=True)
    message.add_argument('--route-pin', help='reference to the actually acquired upstream pin; not an acquisition itself')
    handle = ts.add_parser('handle', help='apply the actual consequence of the selected current input')
    handle.add_argument('--root', required=True, type=Path)
    handle.add_argument('--message-id', required=True, type=int)
    handle.add_argument('--action', dest='message_action', required=True, choices=sorted(MESSAGE_ACTIONS))
    handle.add_argument('--reason', required=True)
    lifecycle = ts.add_parser('lifecycle', help='read managed continuation state or explicit legacy status')
    lifecycle.add_argument('--root', required=True, type=Path)
    stop = ts.add_parser('terminate', help='stop/cancel a task; completed delivery uses return close')
    stop.add_argument('--root', required=True, type=Path)
    stop.add_argument('--status', required=True, choices=('STOPPED', 'CANCELLED'))
    stop.add_argument('--reason', required=True)
    stop.add_argument('--source-file', type=Path, help='actual stop/cancel source; takes priority over older pending input')
    stop.add_argument('--source-ref', help='actual unique message source reference')
    stop.add_argument('--route-pin', help='actually acquired pin reference for a prefixed termination message')
    recover = ts.add_parser('recover', help='discard interrupted open tails; does not reactivate a terminated task')
    recover.add_argument('--root', required=True, type=Path)
    recover.add_argument('--reason', required=True)
    foundation = sub.add_parser('foundation', help='research-authored task brief, dialogue and execution decision')
    fs = foundation.add_subparsers(dest='action', required=True)
    for action in ('propose', 'show', 'answer', 'confirm', 'revoke'):
        command = fs.add_parser(action)
        command.add_argument('--root', required=True, type=Path)
        if action == 'propose':
            command.add_argument('--input', required=True, type=Path)
            command.add_argument('--reason', required=True)
            command.add_argument('--change-kind', choices=('material', 'non_material'), default='material')
        elif action in ('answer', 'confirm', 'revoke'):
            command.add_argument('--reply-file', required=True, type=Path, help='actual user words; no secret confirmation keyword')
            command.add_argument('--source', required=True, help='actual message or decision reference')
            if action == 'answer':
                command.add_argument('--id', required=True)
                command.add_argument('--revision', required=True, type=int)
                command.add_argument('--effect', required=True, help='actual consequence; interpretation is model-owned')
                command.add_argument('--change-kind', choices=('material', 'non_material'), default='material')
            elif action == 'confirm':
                command.add_argument('--revision', required=True, type=int)
            else:
                command.add_argument('--reason', required=True)
    line = sub.add_parser('line', help='create, resume or update one complete work line')
    ls = line.add_subparsers(dest='action', required=True)
    for action in ('create', 'packet', 'update', 'parameters'):
        command = ls.add_parser(action)
        command.add_argument('--root', required=True, type=Path)
        command.add_argument('--id', required=True, help='M01, M02, ...')
        if action in ('create', 'parameters'):
            command.add_argument('--parameters', required=True, type=Path)
            command.add_argument('--reasons', type=Path, help='optional parameter reason map')
        if action in ('create', 'update'):
            command.add_argument('--owner')
        if action == 'create':
            command.add_argument('--work', type=Path, help='reuse an existing ordinary work note')
        if action in ('create', 'packet'):
            command.add_argument('--corrections-topic', action='append', default=[],
                                 help='explicit user-correction section in the existing work note')
            command.add_argument('--experience', action='append', default=[], type=Path,
                                 help='explicit optional history candidate; relative to work note')
        if action == 'packet':
            command.add_argument('--topic')
            command.add_argument('--max-chars', type=int, default=24000)
        elif action == 'update':
            command.add_argument('--input', required=True, type=Path,
                                 help='candidate, content_status, responsibility_status, next_action, unhandled')
        elif action == 'parameters':
            command.add_argument('--user-revision', help='actual user revision reference; not inferred by helper')
    clock = sub.add_parser('clock', help='explicit real boundaries; no automatic continuity inference')
    cs = clock.add_subparsers(dest='action', required=True)
    for action in ('begin', 'checkpoint', 'end', 'recover'):
        command = cs.add_parser(action)
        command.add_argument('--root', required=True, type=Path)
        command.add_argument('--owner', required=True, help='M01, M02, ... or COMMON')
        if action == 'begin':
            command.add_argument('--state', choices=sorted(ACTIVITY_STATES), required=True)
            command.add_argument('--scope', choices=('FOUNDATION', 'EXECUTION'), default='EXECUTION')
        if action in ('checkpoint', 'end'):
            command.add_argument('--continued', action='store_true',
                                 help='declare genuine continuous activity since the previous boundary')
        command.add_argument('--reason')
    cr = cs.add_parser('report')
    cr.add_argument('--root', required=True, type=Path)
    anchor = cs.add_parser('anchor')
    anchor.add_argument('--root', required=True, type=Path)
    anchor.add_argument('--pid', type=int, required=True)
    anchor.add_argument('--reason', required=True)
    permissions = sub.add_parser('permissions', help='advice from supplied task authorization; executes nothing')
    permissions.add_argument('--input', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'acquire':
            previous = load_acquisition(args.continue_from) if args.continue_from else None
            acquired = CodexRepositoryTransport().acquire(args.stage, startup=previous)
            result = acquired.summary()
            if args.out is not None:
                result['receipt'] = acquired.export(args.out).as_posix()
        elif args.command == 'permissions':
            supplied = read_object(args.input)
            result = assess_operation(supplied['context'], supplied['operation'],
                within_task=supplied['within_task'], capability=supplied.get('capability', 'UNKNOWN'),
                estimated_cost=supplied.get('estimated_cost'))
        elif args.command == 'task':
            if args.action == 'create':
                result = create_session(args.out, request=args.request, p_run=args.p_run,
                    decisions=args.decisions,
                    explicit_parameters=read_object(args.explicit) if args.explicit else None,
                    anchor_pid=args.anchor_pid, m_target=args.m, require_foundation=args.require_foundation)
            elif args.action == 'message':
                result = ingest_message(args.root, source=args.source_file,
                    source_ref=args.source_ref, route_pin=args.route_pin)
            elif args.action == 'handle':
                result = handle_message(args.root, message_id=args.message_id,
                    action=args.message_action, reason=args.reason)
            elif args.action == 'lifecycle':
                result = load_lifecycle(args.root)
            elif args.action == 'terminate':
                if (args.source_file is None) != (args.source_ref is None):
                    raise ValueError('termination source file and source reference must be supplied together')
                if args.source_file is not None:
                    result = terminate_message(args.root, source=args.source_file, source_ref=args.source_ref,
                        action='stop' if args.status == 'STOPPED' else 'cancel', reason=args.reason,
                        route_pin=args.route_pin)
                else:
                    if args.route_pin is not None:raise ValueError('route pin requires the actual termination source')
                    result = close_session(args.root, status=args.status, reason=args.reason)
            elif args.action == 'recover':
                result = recover_session(args.root, reason=args.reason)
            else:
                result = session_report(args.root)
        elif args.command == 'foundation':
            if args.action == 'show':
                print(foundation_packet(args.root), end='')
                return 0
            if args.action == 'propose':
                result = propose_foundation(args.root, read_object(args.input),
                    reason=args.reason, change_kind=args.change_kind)
            elif args.action == 'answer':
                result = answer_foundation(args.root, args.id,
                    revision=args.revision, user_text=read_message(args.reply_file),
                    source=args.source, effect=args.effect, change_kind=args.change_kind)
            elif args.action == 'revoke':
                result = revoke_foundation(args.root,
                    user_text=read_message(args.reply_file),
                    source=args.source, reason=args.reason)
            else:
                result = confirm_foundation(args.root, revision=args.revision,
                    user_text=read_message(args.reply_file), source=args.source)
        elif args.command == 'line':
            if args.action == 'create':
                result = create_line(args.root, args.id, parameters=read_object(args.parameters),
                    owner=args.owner, work=args.work,
                    parameter_reasons=read_object(args.reasons) if args.reasons else None,
                    corrections_topics=args.corrections_topic, experiences=args.experience)
            elif args.action == 'packet':
                print(line_packet(args.root, args.id, topic=args.topic, max_chars=args.max_chars,
                    corrections_topics=args.corrections_topic, experiences=args.experience), end='')
                return 0
            elif args.action == 'parameters':
                result = set_line_parameters(args.root, args.id,
                    parameters=read_object(args.parameters),
                    reasons=read_object(args.reasons) if args.reasons else {},
                    user_revision=args.user_revision)
            else:
                data = read_object(args.input)
                candidate = Path(data['candidate']) if data.get('candidate') else None
                if candidate is not None and not candidate.is_absolute():
                    candidate = args.input.resolve().parent / candidate
                result = update_line(args.root, args.id, candidate=candidate,
                    content_status=data['content_status'], responsibility_status=data['responsibility_status'],
                    next_action=data['next_action'], unhandled=data.get('unhandled', []), owner=args.owner)
        elif args.action == 'report':
            result = session_report(args.root)
        elif args.action == 'anchor':
            result = set_clock_anchor(args.root, anchor_pid=args.pid, reason=args.reason)
        else:
            result = activity(args.root, args.owner, args.action,
                state=getattr(args, 'state', None), continued=getattr(args, 'continued', False),
                reason=args.reason, scope=getattr(args, 'scope', None))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError, OSError, KeyError, RuntimeError) as error:
        print(f'Codex: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
