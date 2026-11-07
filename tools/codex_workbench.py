#!/usr/bin/env python3
"""Assemble focused research/production context from one editable workbench."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_workbench import create_workbench, context_packet, topic_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='create an editable workbench from the actual request')
    init.add_argument('--request', type=Path, required=True)
    init.add_argument('--work', type=Path, required=True)
    topics = sub.add_parser('topics', help='locate substantive research sections')
    topics.add_argument('--work', type=Path, required=True)
    for command in ('focus', 'challenge'):
        item = sub.add_parser(command)
        item.add_argument('--work', type=Path, required=True)
        item.add_argument('--request', type=Path, help='reuse any existing work document with a separate actual request')
        item.add_argument('--question')
        item.add_argument('--material', action='append', default=[])
        item.add_argument('--candidate', action='append', default=[])
        item.add_argument('--max-chars', type=int, default=24000)
        if command == 'focus':
            item.add_argument('--topic')
        else:
            item.add_argument('--kind', choices=('D', 'V'), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            request = args.request.read_text(encoding='utf-8-sig')
            args.work.parent.mkdir(parents=True, exist_ok=True)
            with args.work.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(create_workbench(request))
            print(args.work.resolve().as_posix())
        elif args.command == 'topics':
            print(topic_index(args.work), end='')
        else:
            print(context_packet(
                args.work, question=args.question, topic=getattr(args, 'topic', None),
                materials=args.material, candidates=args.candidate,
                kind=getattr(args, 'kind', 'focus'), max_chars=args.max_chars,
                request=args.request,
            ), end='')
        return 0
    except (ValueError, OSError) as error:
        print(f'工作上下文：{error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
