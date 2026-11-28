"""Show the pinned Community Cry pool, query original sources and prepare a finding."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_cc import assess, load_pool, search_pool


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', newline='\n')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('inspect')
    search = commands.add_parser('search')
    search.add_argument('--category')
    search.add_argument('--query')
    search.add_argument('--kind', choices=('community', 'digr_research', 'community_method', 'calibration'))
    assessment = commands.add_parser('assess')
    assessment.add_argument('--input', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        pool = load_pool()
        if args.command == 'inspect':
            result = pool
        elif args.command == 'search':
            result = search_pool(pool, category=args.category, query=args.query, kind=args.kind)
        else:
            supplied = json.loads(args.input.read_text(encoding='utf-8-sig'))
            if not isinstance(supplied, dict):
                raise ValueError('CC finding input must be a JSON object')
            result = assess(pool, supplied)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print('DIGR CC: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
