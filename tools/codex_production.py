#!/usr/bin/env python3
"""Record same-task native dispatch, candidates and application of Claude arbitration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime import codex_production as production


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    start = commands.add_parser('start', help='freeze the shared assignment and actual native dispatch')
    start.add_argument('--scope', type=Path, required=True, help='actual shared UTF-8 assignment file')
    start.add_argument('--actor', required=True, help='assigned independent native actor')
    start.add_argument('--dispatch-ref', required=True, help='actual native host dispatch event reference')
    start.add_argument('--paper-root', type=Path, help='selected registered paper authoring scope')
    submit = commands.add_parser('submit-native', help='seal the actual complete native candidate')
    submit.add_argument('--actor', required=True)
    submit.add_argument('--output', type=Path, required=True, help='usable native candidate in UTF-8')
    submit.add_argument('--return-ref', required=True, help='actual native host return event reference')
    applied = commands.add_parser('record-applied', help='bind actual Claude arbitration to the final artifact')
    applied.add_argument('--arbitration-exchange', required=True)
    applied.add_argument('--peer-arbitration-exchange', action='append',
                         help='a complete coequal arbitration for the same assignment; repeat for multiple peers')
    applied.add_argument('--output', type=Path, required=True)
    applied.add_argument('--effect', required=True, help='what the actual verdict changed in the artifact')
    release = commands.add_parser('release', help='record an actual later user fallback or scope replacement')
    release.add_argument('--disposition', choices=('fallback', 'superseded'), required=True)
    release.add_argument('--source', required=True, help='handled user message source reference')
    release.add_argument('--quote', required=True, help='exact excerpt from that actual decision')
    release.add_argument('--effect', required=True)
    release.add_argument('--replacement-production-id')
    inspect = commands.add_parser('inspect', help='read production history locally without any calls')
    for command in (start, submit, applied, release, inspect):
        command.add_argument('--root', type=Path, required=True)
        command.add_argument('--production-id', required=command is not inspect)
    args = parser.parse_args(argv)
    try:
        if args.command == 'start':
            result = production.start(args.root, args.production_id, scope_path=args.scope,
                                      actor=args.actor, dispatch_ref=args.dispatch_ref, paper_root=args.paper_root)
        elif args.command == 'submit-native':
            result = production.submit_native(args.root, args.production_id, actor=args.actor,
                                              output_path=args.output, return_ref=args.return_ref)
        elif args.command == 'record-applied':
            result = production.record_applied(args.root, args.production_id,
                arbitration_exchange=args.arbitration_exchange, output_path=args.output,
                effect=args.effect, peer_exchange=args.peer_arbitration_exchange)
        elif args.command == 'release':
            result = production.release(args.root, args.production_id, disposition=args.disposition,
                source=args.source, quote=args.quote, effect=args.effect,
                replacement_production_id=args.replacement_production_id)
        else:
            result = production.inspect(args.root, args.production_id)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print('DIGR Production: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
