"""Bind the Paper Pool work to one confirmed, versioned task scope."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping

from .codex_collaboration import _since
from .codex_session import _read_json, _session, _write_json
from .validation import require_nonempty_text

PLAN_FIELD = 'paper_pool_routing'
BASELINE_FIELDS = ('environment', 'routes', 'access', 'search', 'research')
SOURCE_FIELDS = ('access', 'search', 'research')
TARGET = 'Paper Pool'


def enabled(p_run: str) -> bool:
    return _since(p_run, (2, 0, 0))


def normalize_plan(value: Any) -> dict:
    """Validate the model's semantic decision, keeping the baseline in order."""
    if not isinstance(value, Mapping) or type(value.get('academic')) is not bool:
        raise ValueError('provide paper_pool_routing with a semantic academic decision')
    baseline = value.get('baseline')
    if not isinstance(baseline, Mapping) or set(baseline) != set(BASELINE_FIELDS):
        raise ValueError('supply the original environment, routes, access, search and research targets')
    original = {}
    for field in BASELINE_FIELDS:
        items = baseline[field]
        if not isinstance(items, list):
            raise ValueError(f'baseline {field} must be an ordered list')
        original[field] = [require_nonempty_text(field, item) for item in items]
        if len(items) != len(set(items)):
            raise ValueError(f'baseline {field} contains duplicate targets')
    if not original['environment'] or not original['routes']:
        raise ValueError('identify the actual original environment and routing')
    plan = {'academic': value['academic'], 'reason': require_nonempty_text('classification basis', value.get('reason')),
            'baseline': original}
    if not value['academic']:
        if value.get('assignment') is not None:
            raise ValueError('a nonacademic plan has no Paper Pool assignment')
        return plan
    assignment = value.get('assignment')
    if not isinstance(assignment, Mapping):
        raise ValueError('an academic task requires a substantive Paper Pool assignment')
    plan['assignment'] = {name: require_nonempty_text(f'Paper Pool {name}', assignment.get(name))
                          for name in ('question', 'work', 'deliverable', 'acceptance')}
    plan['assignment']['source_scope'] = scope = assignment.get('source_scope', 'pool-and-task')
    if scope not in ('pool-and-task', 'task-only'):
        raise ValueError('Paper Pool source_scope must be pool-and-task or task-only')
    if scope == 'task-only':
        plan['assignment']['scope_basis'] = require_nonempty_text(
            'actual constraint limiting the task to its own materials', assignment.get('scope_basis'))
    return plan


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')).hexdigest()


def _context(root: Path) -> tuple[Path, dict | None]:
    from .codex_foundation import load_foundation

    root, session = _session(root)
    if not enabled(session['P_run']) or not (root / 'foundation.json').is_file():
        return root, None
    foundation = load_foundation(root)
    if foundation['status'] != 'CONFIRMED':
        return root, None
    plan = normalize_plan(foundation['brief'].get(PLAN_FIELD))
    return root, {'task_uuid': session['task_uuid'], 'P_run': session['P_run'],
                  'revision': foundation['brief']['paper_pool_revision'], 'plan': plan}


def route(root: Path) -> dict:
    """Read the original task plan and its separate added target."""
    _, context = _context(root)
    if context is None:
        raise ValueError('Paper Pool routing needs a current confirmed 2.0+ task brief')
    plan = context['plan']
    return {**context, 'baseline': plan['baseline'],
            'target': {'name': TARGET, 'assignment': plan['assignment']} if plan['academic'] else None}


def _record_path(root: Path, context: Mapping[str, Any]) -> Path:
    location = root / 'paper-pool' / f"u0-{context['revision']}"
    if not location.resolve().is_relative_to(root):
        raise ValueError('Paper Pool work directory is redirected outside the task')
    return location / 'work.json'


def _read_record(path: Path, context: Mapping[str, Any]) -> dict:
    binding = _digest(context)
    if not path.exists():
        return {'binding': binding, 'worker': None, 'queries': {}, 'query_failures': {},
                'baseline_results': {}, 'result': None, 'disposition': None}
    record = _read_json(path)
    if record.get('binding') != binding:
        raise ValueError('Paper Pool work belongs to a different task scope')
    return record


@contextmanager
def _edit(root: Path):
    from .codex_foundation import require_foundation_ready

    root = Path(root).resolve()
    require_foundation_ready(root)
    root, context = _context(root)
    if context is None or not context['plan']['academic']:
        raise ValueError('there is no current Paper Pool work for this task')
    path = _record_path(root, context)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    try:
        with lock.open('x', encoding='utf-8') as stream:
            stream.write(str(os.getpid()))
    except FileExistsError as exc:
        raise ValueError('Paper Pool work record has a writer; retry after it finishes') from exc
    try:
        record = _read_record(path, context)
        yield context, record
        require_foundation_ready(root)
        if _context(root)[1] != context:
            raise ValueError('current task scope changed while recording Paper Pool work')
        _write_json(path, record)
    finally:
        lock.unlink()


def _artifact(path: Path, *, allow_empty: bool = False) -> dict:
    selected = Path(os.path.abspath(path))
    for component in [*reversed(selected.parents), selected]:
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError('select the known, direct path of a result or source file')
    if not stat.S_ISREG(info.st_mode) or (not allow_empty and not info.st_size):
        raise ValueError('select an actual nonempty result or source file')
    digest = sha256()
    length = 0
    with selected.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            length += len(chunk)
    return {'path': str(selected), 'sha256': digest.hexdigest(), 'bytes': length}


def _current(ref: Mapping[str, Any]) -> bool:
    try:
        return _artifact(Path(ref['path'])) == ref
    except (OSError, ValueError):
        return False


def dispatch(root: Path, *, actor: str, source: str) -> dict:
    """Record a real handoff made by the host to the named Paper Pool worker."""
    handoff = {'actor': require_nonempty_text('Paper Pool worker identity', actor),
               'source': require_nonempty_text('actual handoff reference', source)}
    with _edit(root) as (_, record):
        if record['worker'] not in (None, handoff):
            raise ValueError('this work already has a bound worker and dispatch reference')
        record['worker'] = handoff
    return handoff


def record_query(root: Path, *, context: Mapping[str, Any], query: Mapping[str, Any],
                 response: Mapping[str, Any]) -> str:
    """Register the actual search result returned by the catalog tool."""
    hits = [item['paper_id'] for item in query['results']]
    receipt = {'catalog': query['corpus_fingerprint'], 'terms': query['query'],
               'paper_ids': hits, 'response_sha256': _digest(response)}
    query_id = _digest(receipt)
    with _edit(root) as (current, record):
        if (current != context or not record['worker']
                or current['plan']['assignment']['source_scope'] != 'pool-and-task'):
            raise ValueError('query requires a current dispatched assignment with pool access')
        if record['queries'] and any(item['catalog'] != receipt['catalog'] for item in record['queries'].values()):
            raise ValueError('catalog changed within this work scope')
        record['queries'][query_id] = receipt
    return query_id


def record_query_failure(root: Path, *, context: Mapping[str, Any], terms: list[str], problem: str) -> None:
    failure = {'terms': terms, 'problem': require_nonempty_text('actual catalog error', problem)}
    with _edit(root) as (current, record):
        if context != current or not record['worker']:
            raise ValueError('current Paper Pool work changed during the catalog attempt')
        record['query_failures'][_digest(failure)] = failure


def query_context(root: Path) -> dict:
    """Check the task-local source boundary before any catalog access."""
    root, context = _context(root)
    if (context is None or not context['plan']['academic']
            or context['plan']['assignment']['source_scope'] != 'pool-and-task'):
        raise ValueError('current Paper Pool assignment does not select catalog access')
    from .codex_foundation import require_foundation_ready
    require_foundation_ready(root)
    if not _read_record(_record_path(root, context), context)['worker']:
        raise ValueError('dispatch the Paper Pool assignment before researching it')
    return context


def baseline_result(root: Path, *, kind: str, target: str, disposition: str, reason: str,
                    attempt: str, evidence_anchor: str, artifact: Path) -> dict:
    """Keep an original route result or an evidenced attempt and its disposition."""
    if kind not in SOURCE_FIELDS or disposition not in ('used', 'excluded', 'unavailable'):
        raise ValueError('record an access/search/research result as used, excluded or unavailable')
    reference = _artifact(artifact)
    anchor = require_nonempty_text('observed evidence or outcome in the original route log', evidence_anchor)
    attempt = require_nonempty_text('actual original-route attempt reference', attempt)
    trace = Path(reference['path']).read_text(encoding='utf-8-sig')
    if anchor not in trace or attempt not in trace or not _current(reference):
        raise ValueError('the original-route attempt or its exact evidence anchor is missing or changed')
    result = {'kind': kind, 'target': require_nonempty_text('baseline target', target),
              'attempt': attempt,
              'evidence_anchor': anchor, 'disposition': disposition,
              'reason': require_nonempty_text('actual use or limitation', reason), 'artifact': reference}
    with _edit(root) as (context, record):
        if target not in context['plan']['baseline'][kind]:
            raise ValueError('record the result against its original planned target')
        if record['result'] and result['artifact']['path'] == record['result']['artifact']['path']:
            raise ValueError('record the result of the original route, separately from the Paper Pool product')
        key = _digest([kind, target])
        if any(saved_key != key and saved['attempt'] == attempt and saved['evidence_anchor'] == anchor
               for saved_key, saved in record['baseline_results'].items()):
            raise ValueError('each original target needs its own observation within a shared attempt')
        record['baseline_results'][key] = result
    return result


def result(root: Path, *, artifact: Path, contribution: str, citations: list[str],
           sources: list[Path], pool_issue: str | None = None) -> dict:
    """Record a real scoped work product; a lookup alone cannot be returned."""
    product = _artifact(artifact)
    if not sources:
        raise ValueError('bind the actual evidence reviewed by the Paper Pool worker')
    evidence = [_artifact(path) for path in sources]
    if product['path'] in {item['path'] for item in evidence}:
        raise ValueError('select the produced work separately from its evidence')
    summary = require_nonempty_text('substantive contribution to the assignment', contribution)
    with _edit(root) as (context, record):
        if not record['worker']:
            raise ValueError('record the actual Paper Pool dispatch first')
        full_pool = context['plan']['assignment']['source_scope'] == 'pool-and-task'
        supported = set()
        for reference in evidence:
            path = Path(reference['path'])
            if path.suffix.lower() != '.json':
                continue
            evidence_record = _read_json(path)
            query_id = evidence_record.pop('task_query_receipt', None)
            if query_id is None:
                continue
            receipt = record['queries'].get(query_id)
            if (not receipt or receipt['response_sha256'] != _digest(evidence_record)
                    or not _current(reference)):
                raise ValueError('selected catalog evidence is changed or comes from another assignment')
            supported.update(receipt['paper_ids'])
        if set(citations) - supported:
            raise ValueError('bind the actual catalog JSON response for every cited paper')
        if full_pool and not citations:
            require_nonempty_text('actual pool coverage gap or source failure', pool_issue)
        if full_pool and not (record['queries'] or record['query_failures']):
            raise ValueError('perform an actual in-task catalog query or record its tool error before returning')
        if any(item['artifact']['path'] == product['path'] for item in record['baseline_results'].values()):
            raise ValueError('give the Paper Pool work its own artifact, distinct from original-route results')
        work = {'artifact': product, 'contribution': summary, 'citations': sorted(set(citations)),
                'evidence': evidence, 'pool_issue': pool_issue}
        if record['result'] != work:
            record['result'] = work
            record['disposition'] = None
    return work


def selection_digest(data: Mapping[str, Any]) -> str:
    """Bind the actual returned prose and selected files, separately from background sources."""
    return _digest({'result': data['result'], 'key_changes': data['key_changes'],
                    'argument_scope': data.get('argument_scope', data.get('verification_limits')),
                    'artifacts': [{'label': item['label'], 'file': _artifact(Path(item['path']), allow_empty=True)}
                                  for item in data.get('artifacts', [])],
                    'delivery_files': [_artifact(Path(path), allow_empty=True)
                                       for path in data.get('delivery_files', [])]})


def consider(root: Path, *, disposition: str, effect: str, artifact: Path, return_input: Path) -> dict:
    """Bind Main's actual use, verification or evidenced rejection to the candidate."""
    if disposition not in ('applied', 'verified', 'excluded'):
        raise ValueError('use applied, verified or excluded with the actual consequence')
    from .codex_return import _input
    data, _, _ = _input(Path(root).resolve(), Path(return_input).absolute(), verify_delivery=False)
    decision = {'kind': disposition, 'effect': require_nonempty_text('effect on current product', effect),
                'artifact': _artifact(artifact), 'selection_sha256': selection_digest(data)}
    with _edit(root) as (_, record):
        work = record['result']
        if not work or not _current(work['artifact']):
            raise ValueError('there is no current Paper Pool work product to consider')
        if work['artifact']['path'] == decision['artifact']['path']:
            raise ValueError('bind the primary candidate or review, separate from the Paper Pool product')
        record['disposition'] = decision
    return decision


def completion(root: Path) -> dict:
    """Return bounded, on-disk completion facts without reading the private pool."""
    root, context = _context(root)
    if context is None:
        return {'state': 'AWAITING_ROUTE', 'can_close': False}
    plan = context['plan']
    if not plan['academic']:
        return {'state': 'NOT_APPLICABLE', 'can_close': True, 'revision': context['revision']}
    path = _record_path(root, context)
    record = _read_record(path, context)
    missing = [f'{kind} · {target}' for kind in SOURCE_FIELDS for target in plan['baseline'][kind]
               if not (item := record['baseline_results'].get(_digest([kind, target])))
               or not _current(item['artifact'])]
    work = record['result']
    decision = record['disposition']
    product_current = bool(work and _current(work['artifact']) and all(map(_current, work['evidence'])))
    main_current = bool(decision and _current(decision['artifact']))
    complete = product_current and main_current and not missing
    state = ('COMPLETE' if complete else 'PENDING')
    return {'state': state, 'can_close': complete, 'revision': context['revision'],
            'worker': record['worker']['actor'] if record['worker'] else None,
            'question': plan['assignment']['question'], 'catalog_queries': len(record['queries']),
            'missing_baseline_results': missing, 'product_current': product_current,
            'main_disposition_current': main_current,
            'selection_sha256': decision['selection_sha256'] if main_current else None,
            'catalog_failures': len(record['query_failures']),
            'record_sha256': _digest(record) if path.exists() else None}
