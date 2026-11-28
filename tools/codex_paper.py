#!/usr/bin/env python3
"""Source-bound DIGRP work packages; native host teaching and Gmail stay native."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

if __name__ == '__main__':
    print('DIGRP retired in DIGR Codex 2.0. Use the original DIGR Codex 1.x distribution for the task.',
          file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime import codex_paper as paper


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--out', type=Path, required=True)
    init.add_argument('--p-run', required=True); init.add_argument('--authorization', type=Path, required=True)
    init.add_argument('--source-ref', required=True)
    init.add_argument('--recipient', help='legacy pre-X batches only')
    init.add_argument('--task-root', type=Path, help='parent 0.9+ DIGR session with frozen X policy')
    acquire = sub.add_parser('acquire')
    acquire.add_argument('--continue-from', type=Path, required=True)
    acquire.add_argument('--out', type=Path, required=True)
    refresh = sub.add_parser('refresh'); refresh.add_argument('--root', type=Path, default=ROOT)
    add = sub.add_parser('add'); add.add_argument('--batch', type=Path, required=True)
    for name in ('id', 'title', 'line', 'owner'):
        add.add_argument('--' + name, required=True)
    add.add_argument('--parameters', type=Path, required=True)
    actions = {'source': paper.register_source, 'map': paper.map_paper,
        'candidate': paper.prepare_candidate, 'delivery': paper.record_delivery,
        'return': paper.return_paper, 'checkpoint': paper.checkpoint}
    for name in actions:
        action = sub.add_parser(name); action.add_argument('--root', type=Path, required=True)
        action.add_argument('--input', type=Path, required=True)
        action.add_argument('--expected-revision', type=int, required=True)
        action.add_argument('--operation-id', required=True)
    for name in ('check', 'resume'):
        view = sub.add_parser(name); view.add_argument('--root', type=Path, required=True)
    status = sub.add_parser('summary'); status.add_argument('--batch', type=Path, required=True)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    try:
        if args.command == 'init':
            result = paper.initialize(args.out, p_run=args.p_run,
                authorization=args.authorization, source_ref=args.source_ref, recipient=args.recipient,
                task_root=args.task_root)
        elif args.command == 'acquire':
            from runtime.codex_transport import load_acquisition
            result = paper.acquire_addon(load_acquisition(args.continue_from), output=args.out)
        elif args.command == 'refresh':
            result = paper.refresh_addon(args.root)
        elif args.command == 'add':
            result = paper.add_paper(args.batch, paper_id=args.id, title=args.title,
                line=args.line, owner=args.owner, parameters=read(args.parameters))
        elif args.command == 'summary':
            result = paper.summarize(args.batch)
        elif args.command in ('check', 'resume'):
            result = paper.inspect(args.root)
        else:
            result = actions[args.command](args.root, read(args.input),
                expected_revision=args.expected_revision, operation_id=args.operation_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get('status') == 'STALE_OR_UNAVAILABLE' else 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('DIGRP: ' + str(error), file=sys.stderr)
        return 2
