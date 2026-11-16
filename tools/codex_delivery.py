#!/usr/bin/env python3
"""Gmail file-delivery records and validators; transfer uses the native connector."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime import codex_delivery as delivery


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    resolve = commands.add_parser('resolve')
    resolve.add_argument('--input', type=Path, required=True)
    resolve.add_argument('--registry', type=Path)
    verify = commands.add_parser('verify')
    verify.add_argument('--input', type=Path, required=True)
    view = commands.add_parser('inspect', aliases=['check', 'resume'])
    view.add_argument('--root', type=Path, required=True)
    complete = commands.add_parser('completion')
    complete.add_argument('--root', type=Path, required=True)
    complete.add_argument('--input', type=Path, required=True)
    actions = {'prepare': delivery.prepare, 'mark-sending': delivery.mark_sending, 'reconcile': delivery.reconcile}
    for name in actions:
        action = commands.add_parser(name)
        action.add_argument('--root', type=Path, required=True)
        action.add_argument('--input', type=Path, required=True)
        action.add_argument('--operation-id', required=True)
        action.add_argument('--expected-revision', type=int)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    try:
        if args.command == 'resolve':
            result = delivery.resolve_policy(read(args.input), args.registry)
        elif args.command == 'verify':
            value = read(args.input)
            result = delivery.verify_receipt(value['policy'], value['files'], value['receipt'],
                candidate_id=value.get('candidate_id'), attempt_id=value.get('attempt_id'))
        elif args.command in {'inspect', 'check', 'resume'}:
            result = delivery.inspect(args.root)
        elif args.command == 'completion':
            value = read(args.input)
            result = delivery.completion_status(args.root, value['files'], value.get('policy'),
                                                candidate_id=value.get('candidate_id'))
        else:
            result = actions[args.command](args.root, read(args.input), operation_id=args.operation_id,
                                          expected_revision=args.expected_revision)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('DIGR delivery: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
