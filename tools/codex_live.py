"""Record real work stages and read bounded, lossless public commentary batches."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime import codex_live as live


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    work = sub.add_parser('work')
    work.add_argument('--root', type=Path, required=True)
    work.add_argument('--input', type=Path, required=True)
    read = sub.add_parser('read')
    read.add_argument('--root', type=Path, required=True)
    read.add_argument('--reader', required=True)
    read.add_argument('--exchange-id')
    read.add_argument('--max-chars', type=int, default=8000)
    ack = sub.add_parser('ack')
    ack.add_argument('--root', type=Path, required=True)
    ack.add_argument('--delivery-id', required=True)
    ack.add_argument('--evidence-ref', required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'work':
            value = json.loads(args.input.read_text('utf-8-sig'))
            result = live.emit_work(args.root, **value)
        elif args.action == 'read':
            result = live.pending(args.root, reader=args.reader, exchange_id=args.exchange_id, max_chars=args.max_chars)
        else:
            result = live.acknowledge(args.root, args.delivery_id, evidence_ref=args.evidence_ref)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('DIGR live: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
