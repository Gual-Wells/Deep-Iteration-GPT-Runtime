#!/usr/bin/env python3
"""Record a real selected court and retrieve role packets. No model calls."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.codex_court import (
    ROLES, cc_intervene, cc_resume, court_packet, court_receipt, court_status, open_court, record_docket,
    record_verdict, remand, review, submit_statement,
)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', newline='\n')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('open', 'submit', 'verdict', 'record', 'remand', 'review', 'status', 'packet',
                                           'cc-intervene', 'cc-resume'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path, help='actual source-bound public input JSON, required for writes')
    parser.add_argument('--role', choices=ROLES, help='actual role for the read-only packet action')
    parser.add_argument('--full', action='store_true', help='print the complete status; default for pins before 1.6')
    args = parser.parse_args(argv)
    try:
        if args.action == 'packet':
            if args.role is None:
                raise ValueError('--role is required for a role packet')
            result = court_packet(args.root, args.role)
        elif args.action == 'status':
            result = court_status(args.root)
        else:
            if args.input is None:
                raise ValueError('--input actual public-source JSON is required')
            supplied = json.loads(args.input.read_text(encoding='utf-8-sig'))
            if not isinstance(supplied, dict):
                raise ValueError('--input must contain a JSON object')
            functions = {'open': open_court, 'submit': submit_statement, 'verdict': record_verdict,
                         'record': record_docket, 'remand': remand, 'review': review,
                         'cc-intervene': cc_intervene, 'cc-resume': cc_resume}
            result = functions[args.action](args.root, supplied)
        if args.action != 'packet':
            result = court_receipt(args.root, result, full=args.full)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if result['status'] == 'STALE' else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
