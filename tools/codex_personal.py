#!/usr/bin/env python3
"""Private Personal Context: selected material, scoped statements and role views."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime import codex_personal as p


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--out', required=True, type=Path)
    init.add_argument('--name', default='Personal Context'); init.add_argument('--binding', type=Path)
    index = sub.add_parser('source'); index.add_argument('--root', required=True, type=Path)
    index.add_argument('--file', required=True, type=Path); index.add_argument('--origin', required=True, choices=sorted(p.ORIGINS))
    index.add_argument('--selectors', help='comma-separated exact JSON dotted paths; default $ means the selected file')
    index.add_argument('--pages', help='comma-separated one-based PDF page numbers; omit for metadata only')
    index.add_argument('--items', help='comma-separated EPUB manifest item IDs; omit for metadata/inventory only')
    index.add_argument('--lineage', help='explicit logical document identity, e.g. resume')
    index.add_argument('--current', action='store_true', help='explicitly select this version as the current logical source')
    entry = sub.add_parser('admit'); entry.add_argument('--root', required=True, type=Path); entry.add_argument('--input', required=True, type=Path)
    move = sub.add_parser('relocate-source'); move.add_argument('--root', required=True, type=Path)
    move.add_argument('--source-id', required=True); move.add_argument('--file', required=True, type=Path)
    withdraw = sub.add_parser('withdraw-source'); withdraw.add_argument('--root', required=True, type=Path)
    withdraw.add_argument('--source-id', required=True); withdraw.add_argument('--reason', required=True)
    for command in (index, entry, move, withdraw):
        command.add_argument('--expected-revision', required=True, type=int)
        command.add_argument('--operation-id', required=True)
    view = sub.add_parser('view'); view.add_argument('--root', required=True, type=Path)
    view.add_argument('--entries', required=True); view.add_argument('--purpose', required=True)
    view.add_argument('--audience', choices=sorted(p.AUDIENCES), default='scene_author')
    view.add_argument('--include-resources', action='store_true'); view.add_argument('--out', type=Path)
    view.add_argument('--book'); view.add_argument('--role')
    check = sub.add_parser('check-view'); check.add_argument('--root', required=True, type=Path); check.add_argument('--input', required=True, type=Path)
    check.add_argument('--book'); check.add_argument('--role')
    inspect = sub.add_parser('inspect'); inspect.add_argument('--root', required=True, type=Path)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    try:
        if args.command == 'init':
            result = p.initialize(args.out, name=args.name, binding=read(args.binding) if args.binding else None)
        elif args.command == 'source':
            result = p.register_source(args.root, args.file, origin=args.origin,
                selectors=args.selectors.split(',') if args.selectors else None,
                pages=[int(x) for x in args.pages.split(',')] if args.pages else None,
                items=args.items.split(',') if args.items else None,
                lineage=args.lineage, make_current=args.current,
                expected_revision=args.expected_revision, operation_id=args.operation_id)
        elif args.command == 'admit':
            result = p.admit(args.root, read(args.input), expected_revision=args.expected_revision, operation_id=args.operation_id)
        elif args.command == 'relocate-source':
            result = p.relocate_source(args.root, args.source_id, args.file,
                                      expected_revision=args.expected_revision, operation_id=args.operation_id)
        elif args.command == 'withdraw-source':
            result = p.withdraw_source(args.root, args.source_id, reason=args.reason,
                                        expected_revision=args.expected_revision, operation_id=args.operation_id)
        elif args.command == 'view':
            result = p.make_view(args.root, entry_ids=args.entries.split(','), purpose=args.purpose,
                                 audience=args.audience, include_resources=args.include_resources,
                                 book_id=args.book, role_id=args.role)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                with args.out.open('x', encoding='utf-8', newline='\n') as f:
                    f.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
                result['saved_to'] = args.out.resolve().as_posix()
        elif args.command == 'check-view':
            result = p.check_view(args.root, read(args.input), book_id=args.book, role_id=args.role)
        else:
            result = p.inspect(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get('status') == 'STALE_OR_UNAVAILABLE' else 0
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        print('Personal Context: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
