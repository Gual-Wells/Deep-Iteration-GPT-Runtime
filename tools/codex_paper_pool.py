"""Paper Pool corpus access and work receipts for the current task."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime import codex_paper_pool as catalog
from runtime import codex_paper_pool_index as indexed
from runtime import codex_paper_pool_route as work


def _private_directory() -> Path:
    location = os.environ.get('CODEX_HOME')
    if not location:
        raise ValueError('select the private corpus binding explicitly or use the existing CODEX_HOME')
    return Path(location) / 'digr-codex'


def _binding(value: Path | None) -> Path:
    if value is not None:
        return value
    directory = _private_directory()
    index = directory / indexed.INDEX_NAME
    try:
        index.lstat()
    except FileNotFoundError:
        return directory / 'paper-pool.json'
    return index


def _is_index(path: Path) -> bool:
    return path.suffix.lower() in ('.sqlite3', '.db')


def _legacy_snapshot(binding: Path, requested: str | None) -> None:
    if requested is None:
        return
    _, hashes = catalog._read_binding(catalog._absolute_local(binding))
    if requested != catalog._fingerprint(hashes):
        raise ValueError('selected snapshot is unavailable in this legacy binding')


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    bind = commands.add_parser('bind', help='verify and register a legacy JSONL corpus binding')
    for field in ('out', 'abstracts', 'parents', 'extractions'):
        bind.add_argument('--' + field, type=Path, required=True)
    migrate = commands.add_parser('migrate', help='build the local append-only index from a verified legacy binding')
    migrate.add_argument('--from-binding', type=Path)
    migrate.add_argument('--out', type=Path)
    append = commands.add_parser('append', help='validate and append one new paper batch atomically')
    append.add_argument('--binding', type=Path)
    append.add_argument('--abstracts', type=Path, required=True)
    for role in ('parents', 'extractions'):
        append.add_argument('--' + role, type=Path)
    check = commands.add_parser('check', help='read an indexed snapshot or verify a legacy binding')
    check.add_argument('--binding', type=Path)
    check.add_argument('--snapshot')
    audit = commands.add_parser('audit', help='verify the index and the archived source bytes')
    audit.add_argument('--binding', type=Path)
    search = commands.add_parser('search', help='search source records and their clearly marked derived views')
    search.add_argument('--term', action='append', required=True)
    search.add_argument('--limit', type=int, default=12)
    show = commands.add_parser('show', help='retrieve one paper and its original-text evidence')
    show.add_argument('paper_id')
    for action in (search, show):
        action.add_argument('--binding', type=Path)
        action.add_argument('--snapshot')
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
            if _is_index(args.out):
                raise ValueError('use migrate to create a Paper Pool index')
            value = catalog.bind_catalog(args.out, abstracts=args.abstracts, parents=args.parents,
                                         extractions=args.extractions)
        elif args.action == 'migrate':
            source = args.from_binding if args.from_binding is not None else _private_directory() / 'paper-pool.json'
            output = args.out if args.out is not None else _private_directory() / indexed.INDEX_NAME
            if not _is_index(output):
                raise ValueError('choose a .sqlite3 or .db file for the Paper Pool index')
            value = indexed.migrate(output, source)
        elif args.action == 'append':
            output = args.binding if args.binding is not None else _private_directory() / indexed.INDEX_NAME
            if not _is_index(output):
                raise ValueError('migrate the legacy binding before appending a batch')
            value = indexed.append(output, abstracts=args.abstracts, parents=args.parents, extractions=args.extractions)
        elif args.action in ('check', 'audit'):
            target = _binding(args.binding)
            if _is_index(target):
                value = indexed.audit(target) if args.action == 'audit' else indexed.check(target, args.snapshot)
            else:
                if args.action == 'check':
                    _legacy_snapshot(target, args.snapshot)
                value = catalog.check_catalog(target)
        elif args.action in ('search', 'show'):
            context = work.query_context(args.root) if args.root is not None else None
            terms = args.term if args.action == 'search' else [args.paper_id]
            try:
                current = work.query_snapshot(args.root, context) if context is not None else None
                if current and args.snapshot is not None and args.snapshot != current:
                    raise ValueError('this assignment already uses a different Paper Pool snapshot')
                fingerprint = current or args.snapshot
                binding = _binding(args.binding)
                use_index = _is_index(binding)
                if not use_index:
                    _legacy_snapshot(binding, fingerprint)
                if args.action == 'search':
                    value = (indexed.search(binding, terms, args.limit, fingerprint) if use_index
                             else catalog.search_catalog(binding, terms=terms, limit=args.limit))
                    query = value
                else:
                    value = (indexed.show(binding, args.paper_id, fingerprint) if use_index
                             else catalog.show_paper(binding, args.paper_id))
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
