#!/usr/bin/env python3
"""Capture or view explicitly selected, source-bound history candidates."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_experience import capture_candidate, write_candidate, render_candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('capture', help='save a freely written local candidate beside selected source excerpts')
    capture.add_argument('--note', type=Path, required=True, help='existing free-form note, not a required preference template')
    capture.add_argument('--source', action='append', required=True, help='text file or line range; relative to note directory unless --base is supplied')
    capture.add_argument('--base', type=Path)
    capture.add_argument('--out', type=Path, required=True)
    show = sub.add_parser('show', help='view selected candidates, saved evidence and current source-location status')
    show.add_argument('candidates', nargs='+', type=Path)
    show.add_argument('--max-chars', type=int, default=24000)
    args = parser.parse_args(argv)
    try:
        if args.command == 'capture':
            note = args.note.resolve()
            candidate = capture_candidate(
                note.read_text(encoding='utf-8-sig'), sources=args.source,
                base=args.base.resolve() if args.base is not None else note.parent,
            )
            write_candidate(args.out, candidate)
            print(args.out.resolve().as_posix())
        else:
            print(render_candidates(args.candidates, max_chars=args.max_chars), end='')
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(f'历史候选：{error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
