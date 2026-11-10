#!/usr/bin/env python3
"""Build, inspect and close one source-bound task return. No model/API calls."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime.codex_return import close_return, return_status, seal_return


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('seal', 'status', 'close'))
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--outcome', choices=('CLOSED', 'STOPPED', 'CANCELLED'), default='CLOSED')
    parser.add_argument('--reason')
    args = parser.parse_args(argv)
    try:
        if args.action == 'seal':
            if args.input is None:
                raise ValueError('--input is required for seal')
            result = seal_return(args.root, args.input)
        elif args.action == 'close':
            if not args.reason:
                raise ValueError('--reason is required for close')
            result = close_return(args.root, reason=args.reason, outcome=args.outcome)
        else:
            result = return_status(args.root, refresh_entry=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        stopped = result['lifecycle_status'] in {'STOPPED', 'CANCELLED'}
        return 2 if result['current_receipt'] in {'MISSING', 'STALE'} and not stopped else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
