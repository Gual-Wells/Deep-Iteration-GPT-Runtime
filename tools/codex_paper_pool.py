"""Paper Pool corpus access and work receipts for the current task."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime import codex_paper_pool as catalog, codex_paper_pool_route as work


def _binding(value: Path | None) -> Path:
    if value is not None:
        return value
    location = os.environ.get('CODEX_HOME')
    if not location:
        raise ValueError('select the private corpus binding with --binding or the existing CODEX_HOME')
    return Path(location) / 'digr-codex' / 'paper-pool.json'


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    bind = commands.add_parser('bind', help='verify and register the fixed corpus on this machine')
    for field in ('out', 'abstracts', 'parents', 'extractions'):
        bind.add_argument('--' + field, type=Path, required=True)
    check = commands.add_parser('check', help='verify the private binding')
    check.add_argument('--binding', type=Path)
    search = commands.add_parser('search', help='search source records and their clearly marked derived views')
    search.add_argument('--term', action='append', required=True)
    search.add_argument('--limit', type=int, default=12)
    show = commands.add_parser('show', help='retrieve one paper and its original-text evidence')
    show.add_argument('paper_id')
    for action in (search, show):
        action.add_argument('--binding', type=Path)
        action.add_argument('--root', type=Path, help='bind this retrieval to the current Paper Pool assignment')
    task_commands = {}
    for name, description in (
        ('route', 'read the original plan and separate Paper Pool target'),
        ('dispatch', 'record an actual assignment to the Paper Pool worker'),
        ('baseline-result', 'record an original route result and disposition'),
        ('result', 'register the work product and actual evidence'),
        ('consider', 'bind use or considered exclusion to the current candidate'),
        ('status', 'show completion facts for the current task scope'),
    ):
        task_commands[name] = action = commands.add_parser(name, help=description)
        action.add_argument('--root', type=Path, required=True)
    dispatch = task_commands['dispatch']
    dispatch.add_argument('--actor', required=True)
    dispatch.add_argument('--source', required=True)
    baseline = task_commands['baseline-result']
    baseline.add_argument('--kind', choices=work.SOURCE_FIELDS, required=True)
    baseline.add_argument('--target', required=True)
    baseline.add_argument('--disposition', choices=('used', 'excluded', 'unavailable'), required=True)
    baseline.add_argument('--reason', required=True)
    baseline.add_argument('--attempt', required=True)
    baseline.add_argument('--evidence-anchor', required=True)
    baseline.add_argument('--artifact', type=Path, required=True)
    result = task_commands['result']
    result.add_argument('--artifact', type=Path, required=True)
    result.add_argument('--contribution', required=True)
    result.add_argument('--cite', action='append', default=[])
    result.add_argument('--source', action='append', type=Path, required=True)
    result.add_argument('--pool-issue')
    consider = task_commands['consider']
    consider.add_argument('--disposition', choices=('applied', 'verified', 'excluded'), required=True)
    consider.add_argument('--effect', required=True)
    consider.add_argument('--artifact', type=Path, required=True)
    consider.add_argument('--return-input', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'bind':
            value = catalog.bind_catalog(args.out, abstracts=args.abstracts, parents=args.parents,
                                         extractions=args.extractions)
        elif args.action == 'check':
            value = catalog.check_catalog(_binding(args.binding))
        elif args.action in ('search', 'show'):
            context = work.query_context(args.root) if args.root is not None else None
            terms = args.term if args.action == 'search' else [args.paper_id]
            try:
                binding = _binding(args.binding)
                if args.action == 'search':
                    value = catalog.search_catalog(binding, terms=terms, limit=args.limit)
                    query = value
                else:
                    value = catalog.show_paper(binding, args.paper_id)
                    query = {'corpus_fingerprint': value['corpus_fingerprint'], 'query': terms,
                             'results': [value['paper']]}
            except (OSError, ValueError) as exc:
                if context is not None:
                    work.record_query_failure(args.root, context=context, terms=terms, problem=str(exc))
                raise
            if context is not None:
                value['task_query_receipt'] = work.record_query(args.root, context=context, query=query, response=value)
        elif args.action == 'route':
            value = work.route(args.root)
        elif args.action == 'dispatch':
            value = work.dispatch(args.root, actor=args.actor, source=args.source)
        elif args.action == 'baseline-result':
            value = work.baseline_result(args.root, kind=args.kind, target=args.target, reason=args.reason,
                                         disposition=args.disposition, artifact=args.artifact,
                                         attempt=args.attempt, evidence_anchor=args.evidence_anchor)
        elif args.action == 'result':
            value = work.result(args.root, artifact=args.artifact, contribution=args.contribution,
                                citations=args.cite, sources=args.source, pool_issue=args.pool_issue)
        elif args.action == 'consider':
            value = work.consider(args.root, disposition=args.disposition, effect=args.effect,
                                  artifact=args.artifact, return_input=args.return_input)
        else:
            value = work.completion(args.root)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f'DIGR Paper Pool: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
