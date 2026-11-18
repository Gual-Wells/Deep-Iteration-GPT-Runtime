"""Select native-host effort per meaningful work block; never calls a model."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime import codex_allot as allot


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'ready', 'observe', 'inspect', 'set-policy', 'feedback', 'resolve-labor'):
        p = sub.add_parser(name)
        p.add_argument('--root', type=Path, required=True)
        if name not in {'inspect', 'ready'}:
            p.add_argument('--input', type=Path, required=True)
        if name in {'plan', 'ready'}:
            p.add_argument('--catalogue', type=Path, required=True)
        if name in {'observe', 'ready', 'feedback'}:
            p.add_argument('--block-id', required=True)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    try:
        if args.command == 'plan':
            result = allot.plan(args.root, read(args.input), read(args.catalogue), catalogue_ref=str(args.catalogue.resolve()))
        elif args.command == 'set-policy':
            result = allot.set_policy(args.root, read(args.input))
        elif args.command == 'ready':
            result = allot.ready(args.root, args.block_id, read(args.catalogue))
        elif args.command == 'feedback':
            result = allot.record_feedback(args.root, args.block_id, read(args.input))
        elif args.command == 'resolve-labor':
            result = allot.resolve_labor(args.root, read(args.input))
        elif args.command == 'observe':
            result = allot.observe(args.root, args.block_id, read(args.input))
        else:
            result = allot.inspect(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('DIGR Allot: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
