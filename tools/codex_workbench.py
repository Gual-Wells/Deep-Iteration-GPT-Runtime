#!/usr/bin/env python3
"""Assemble focused research/production context from one editable workbench."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_workbench import create_workbench, context_packet, topic_index, record_work


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='create an editable workbench from the actual request')
    init.add_argument('--request', type=Path, required=True)
    init.add_argument('--work', type=Path, required=True)
    topics = sub.add_parser('topics', help='locate substantive research sections')
    topics.add_argument('--work', type=Path, required=True)
    record = sub.add_parser('record', help='append a useful public summary to an existing work topic')
    record.add_argument('--work', type=Path, required=True)
    record.add_argument('--topic', default='研究、竞争解释与方案')
    record.add_argument('--kind', default='发现与后果', help='free-form label, not a workflow state')
    record.add_argument('--text-file', type=Path, required=True)
    record.add_argument('--ref', action='append', default=[])
    for command in ('focus', 'challenge'):
        item = sub.add_parser(command)
        item.add_argument('--work', type=Path, required=True)
        item.add_argument('--request', type=Path, help='reuse any existing work document with a separate actual request')
        item.add_argument('--goal-topic', help='use the exact title of an existing original-goal section')
        item.add_argument('--corrections-topic', action='append', default=[], help='also retain this exact existing correction section')
        item.add_argument('--question', help='optional research entry point; D/V may first scout a problem or develop a field')
        item.add_argument('--material', action='append', default=[])
        item.add_argument('--candidate', action='append', default=[])
        item.add_argument('--experience', action='append', default=[], help='explicitly select an optional source-bound history candidate')
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
        elif args.command == 'record':
            print(record_work(
                args.work, args.text_file.read_text(encoding='utf-8-sig'),
                topic=args.topic, kind=args.kind, refs=args.ref,
            ))
        else:
            print(context_packet(
                args.work, question=args.question, topic=getattr(args, 'topic', None),
                materials=args.material, candidates=args.candidate,
                kind=getattr(args, 'kind', 'focus'), max_chars=args.max_chars,
                request=args.request,
                goal_topic=args.goal_topic, corrections_topics=args.corrections_topic,
                experiences=args.experience,
            ), end='')
        return 0
    except (ValueError, OSError) as error:
        print(f'工作上下文：{error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
