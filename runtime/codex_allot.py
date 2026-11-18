"""Thin native-host effort selection, with observed execution kept separate.

No model calls or config rewrites. The host applies a returned payload through
its native agent interface; only a subsequent observation records what ran.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Mapping

EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max', 'ultra')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(_json(value) + b'\n')


def _task(root):
    from .codex_session import _session
    from .codex_lifecycle import load_lifecycle, require_active
    root, session = _session(root)
    lifecycle = load_lifecycle(root)
    require_active(root)
    if session.get('foundation_required'):
        from .codex_foundation import require_foundation_ready
        require_foundation_ready(root)
    return root, session, lifecycle


def catalogue(value: Mapping) -> dict:
    """Project only capability fields from model/list or native model cache."""
    rows = value.get('models', value.get('data'))
    if not isinstance(rows, list):
        raise ValueError('supply actual model/list data or a native models cache')
    result = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        model = row.get('slug', row.get('model', row.get('id')))
        levels = row.get('supported_reasoning_levels', row.get('supportedReasoningEfforts', []))
        supported = [x.get('effort', x.get('reasoningEffort')) if isinstance(x, Mapping) else x for x in levels]
        supported = [x for x in supported if x in EFFORTS]
        if isinstance(model, str) and supported:
            result[model] = supported
    if not result:
        raise ValueError('no observed usable models/efforts in supplied catalogue')
    return result


def select(block: Mapping, capabilities: Mapping) -> dict:
    """Select by work difficulty, never by DIGR preset or guessed cost ratios."""
    model = block.get('model')
    supported = catalogue(capabilities).get(model)
    if not supported:
        raise ValueError('requested model is absent from the supplied host catalogue')
    kind = block.get('kind')
    if kind not in {'routine', 'maintenance', 'response', 'architecture', 'breakthrough'}:
        raise ValueError('kind must identify routine/maintenance/response/architecture/breakthrough work')
    evidence = block.get('evidence', [])
    if not isinstance(evidence, list) or not evidence or any(not isinstance(x, str) or not x.strip() for x in evidence):
        raise ValueError('selection needs actual work/evidence, not a bare difficulty label')
    if kind == 'routine' and block.get('fully_specified') is not True:
        raise ValueError('Low routine work requires a fully specified bounded operation')
    desired = {'routine': 'low', 'maintenance': 'medium', 'response': 'high',
               'architecture': 'high', 'breakthrough': 'high'}[kind]
    unresolved = block.get('unresolved', [])
    tried = block.get('failed_efforts', [])
    if not isinstance(unresolved, list) or not isinstance(tried, list):
        raise ValueError('unresolved and failed_efforts must be lists')
    if any(x not in EFFORTS for x in tried):
        raise ValueError('unknown failed effort')
    if unresolved and 'high' in tried:
        desired = 'xhigh'
    if unresolved and 'xhigh' in tried and block.get('high_value') is True:
        desired = 'max'
    requested = block.get('requested_effort')
    if requested is not None:
        if requested not in EFFORTS:
            raise ValueError('unsupported explicitly requested effort')
        desired = requested
    floor = block.get('minimum_effort')
    if floor is not None:
        if floor not in EFFORTS:
            raise ValueError('unsupported minimum effort')
        desired = EFFORTS[max(EFFORTS.index(desired), EFFORTS.index(floor))]
    current = block.get('current_effort')
    if current is not None:
        if current not in EFFORTS:
            raise ValueError('unsupported current effort')
        if EFFORTS.index(desired) < EFFORTS.index(current) and block.get('allow_downshift') is not True:
            desired = current
    if desired not in supported:
        raise ValueError('selected effort is unavailable; no silent model substitution or downshift')
    return {'model': model, 'effort': desired,
            'host_payload': {'fork_turns': 'none', 'model': model, 'reasoning_effort': desired},
            'selection_basis': {'kind': kind, 'evidence': evidence, 'unresolved': unresolved,
                                'failed_efforts': tried, 'explicit_effort': requested},
            'applied': False,
            'scope': 'native host must apply this payload; selection is not a model execution receipt'}


def plan(root: Path, block: Mapping, capabilities: Mapping, *, catalogue_ref: str) -> dict:
    root, session, lifecycle = _task(root)
    block_id = block.get('block_id', '')
    if not _ID.fullmatch(block_id):
        raise ValueError('a stable safe block_id is required')
    if not isinstance(catalogue_ref, str) or not catalogue_ref.strip():
        raise ValueError('actual capability source reference is required')
    selection = select(block, capabilities)
    record = {'format': 'digr-native-allot-1', 'P_run': session['P_run'],
              'block_id': block_id, 'input_ref': lifecycle['current_message']['source']['sha256'],
              'block_sha256': sha256(_json(block)).hexdigest(),
              'catalogue_sha256': sha256(_json(catalogue(capabilities))).hexdigest(),
              'catalogue_ref': catalogue_ref, 'created_at': datetime.now(timezone.utc).isoformat(),
              **selection}
    path = root / 'allot' / block_id / 'selection.json'
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        if any(previous.get(k) != record[k] for k in ('block_sha256', 'input_ref', 'catalogue_sha256')):
            raise ValueError('block selection changed; use a new block_id for the new decision')
        return previous
    _write(path, record)
    return record


def observe(root: Path, block_id: str, observation: Mapping) -> dict:
    root, session, lifecycle = _task(root)
    if not _ID.fullmatch(block_id):
        raise ValueError('invalid block id')
    selected = json.loads((root / 'allot' / block_id / 'selection.json').read_text(encoding='utf-8'))
    if selected['input_ref'] != lifecycle['current_message']['source']['sha256']:
        raise ValueError('current user input superseded the selected work block')
    source = observation.get('source_ref')
    if not isinstance(source, str) or not source.strip():
        raise ValueError('actual host observation source_ref is required')
    model, effort = observation.get('model'), observation.get('effort')
    if not isinstance(model, str) or not model or effort not in EFFORTS:
        raise ValueError('observation must contain actual model and effort')
    matched = (model, effort) == (selected['model'], selected['effort'])
    record = {'format': 'digr-native-allot-observation-1', 'block_id': block_id,
              'actual_model': model, 'actual_effort': effort, 'source_ref': source,
              'matches_selection': matched, 'applied': matched,
              'scope': 'caller-supplied actual host fields; not authentication or inference from a plan'}
    path = root / 'allot' / block_id / 'observation.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != record:
            raise ValueError('existing observation differs; preserve it and use a new block')
    else:
        _write(path, record)
    return record


def inspect(root: Path) -> dict:
    from .codex_session import _session
    root, _ = _session(root)
    rows = []
    for path in sorted((root / 'allot').glob('*/selection.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        observation = path.with_name('observation.json')
        row['observation'] = json.loads(observation.read_text(encoding='utf-8')) if observation.exists() else None
        rows.append(row)
    return {'selections': rows, 'automatic_model_calls': 0}
