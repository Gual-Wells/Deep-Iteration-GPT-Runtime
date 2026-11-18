"""Scoped labor feedback facts, without model calls or dispatch authority.

The Allot caller validates current policy, lifecycle and actual solver records.
This module preserves only declared public facts. An explicit resolution clears
its listed feedback, never an entire scope's future history.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Mapping
from uuid import uuid4


_FEEDBACK_FORMAT = 'digr-native-allot-feedback-1'
_RESOLUTION_FORMAT = 'digr-native-allot-labor-resolution-1'
_FEEDBACK_ID = re.compile(r'fb-[0-9a-f]{64}')
_RESOLUTION_ID = re.compile(r'lr-[0-9a-f]{64}')
_BLOCK_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')
_CATEGORIES = frozenset({'quality', 'capability', 'tool', 'network',
                         'permission', 'input', 'budget'})
_BLOCKING = frozenset({'quality', 'capability'})


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      allow_nan=False).encode('utf-8')


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ' must reference an actual nonempty fact')
    return value


def _mapping(value, name):
    if not isinstance(value, Mapping) or not value:
        raise ValueError(name + ' must be a nonempty mapping')
    return json.loads(_json(dict(value)))


def _scope(value):
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError('labor scope must contain scope_ref and validation_ref')
    return {key: _text(value.get(key), key)
            for key in ('scope_ref', 'validation_ref')}


def scope_key(scope: Mapping | None) -> str | None:
    """Identify the declared scope; changing validators cannot erase a hold."""
    value = _scope(scope)
    return sha256(_json({'scope_ref': value['scope_ref']})).hexdigest() if value is not None else None


def _task(root):
    from .codex_session import _session
    root, session = _session(root)
    identity = {'P_run': session['P_run'], 'request_sha256': session['request_sha256']}
    if session.get('task_uuid'):
        identity['task_uuid'] = session['task_uuid']
    else:
        # Older tasks may explicitly adopt the policy without being migrated.
        identity['created_wall_ns'] = session['created_wall_ns']
    return root, identity


def _containment_path(path):
    # On Windows, non-strict resolve can retain the extended prefix if a
    # directory is created between its missing-path probes. Compare equivalent
    # DOS/UNC spellings in one namespace; keep the resolved spelling for I/O.
    # Other device namespaces are deliberately not rewritten.
    if os.name == 'nt':
        value = str(path)
        if value[:8].upper() == '\\\\?\\UNC\\':
            return Path('\\\\' + value[8:])
        if (value.startswith('\\\\?\\') and len(value) >= 7
                and value[4].isascii() and value[4].isalpha()
                and value[5:7] == ':\\'):
            return Path(value[4:])
    return path


def _directory(root, name):
    path = (root / 'allot' / '_labor' / name).resolve()
    if not _containment_path(path).is_relative_to(_containment_path(root)):
        raise ValueError('labor facts must remain within the current task')
    return path


def _event_id(record, key, prefix):
    # A retry can arrive after DO. Its reporting anchor changes, the actual
    # referenced failure/resolution does not become a second event.
    return prefix + sha256(_json({k: v for k, v in record.items()
                                 if k not in {key, 'input_ref', 'record_sha256'}})).hexdigest()


def _content_digest(record):
    return sha256(_json({k: v for k, v in record.items() if k != 'record_sha256'})).hexdigest()


def _same_fact(left, right):
    return ({k: v for k, v in left.items() if k not in {'input_ref', 'record_sha256'}}
            == {k: v for k, v in right.items() if k not in {'input_ref', 'record_sha256'}})


def _load(path, task_ref, *, key, pattern, prefix, format):
    from .codex_io import read_bytes
    record = json.loads(read_bytes(path))
    if not isinstance(record, dict) or record.get('format') != format:
        raise ValueError('unsupported Allot labor fact')
    identity = record.get(key)
    if (not isinstance(identity, str) or not pattern.fullmatch(identity)
            or path.stem != identity or _event_id(record, key, prefix) != identity
            or record.get('record_sha256') != _content_digest(record)):
        raise ValueError('Allot labor fact identity or contents changed')
    if record.get('task_ref') != task_ref:
        raise ValueError('Allot labor fact belongs to a different task')
    return record


def _publish(path, record, task_ref, **schema):
    """Publish complete immutable bytes; concurrent identical retries converge."""
    record['record_sha256'] = _content_digest(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.pending-' + uuid4().hex)
    try:
        with temporary.open('xb') as stream:
            stream.write(_json(record) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # A hard link publishes the fully written local file without ever
            # replacing an event already published by another caller.
            os.link(temporary, path)
        except FileExistsError:
            previous = _load(path, task_ref, **schema)
            if not _same_fact(previous, record):
                raise ValueError('immutable Allot labor event differs')
            return previous
    finally:
        temporary.unlink(missing_ok=True)
    return record


_FEEDBACK_SCHEMA = {'key': 'feedback_id', 'pattern': _FEEDBACK_ID,
                    'prefix': 'fb-', 'format': _FEEDBACK_FORMAT}
_RESOLUTION_SCHEMA = {'key': 'resolution_id', 'pattern': _RESOLUTION_ID,
                      'prefix': 'lr-', 'format': _RESOLUTION_FORMAT}


def _feedback(root, task_ref, feedback_id):
    if not isinstance(feedback_id, str) or not _FEEDBACK_ID.fullmatch(feedback_id):
        raise ValueError('invalid Allot feedback id')
    return _load(_directory(root, 'feedback') / (feedback_id + '.json'),
                 task_ref, **_FEEDBACK_SCHEMA)


def load_feedback(root: Path, feedback_id: str) -> dict:
    """Read a same-task public fact, excluding private selection evidence."""
    root, task_ref = _task(root)
    return _feedback(root, task_ref, feedback_id)


def record_feedback(root: Path, selected: Mapping, feedback: Mapping,
                    input_ref: Mapping) -> dict:
    """Record actual supplied failure facts; do not infer a failure from a plan."""
    root, task_ref = _task(root)
    if not isinstance(selected, Mapping):
        raise ValueError('feedback needs the actual selected work block')
    block_id = selected.get('block_id')
    if not isinstance(block_id, str) or not _BLOCK_ID.fullmatch(block_id):
        raise ValueError('feedback needs an actual safe block_id')
    if selected.get('P_run', task_ref['P_run']) != task_ref['P_run']:
        raise ValueError('selected work belongs to a different task pin')
    basis = selected.get('selection_basis', {})
    if not isinstance(basis, Mapping):
        raise ValueError('selection_basis must be a mapping')
    scope = _scope(basis.get('labor_scope'))
    if not isinstance(feedback, Mapping) or feedback.get('category') not in _CATEGORIES:
        raise ValueError('feedback needs a specific supported failure category')
    actual = {'category': feedback['category'],
              **{key: _text(feedback.get(key), key)
                 for key in ('evidence_ref', 'detail')}}
    record = {'format': _FEEDBACK_FORMAT, 'task_ref': task_ref,
              'block_id': block_id,
              'model': _text(selected.get('model'), 'selected model'),
              'effort': _text(selected.get('effort'), 'selected effort'),
              'selection_input_ref': _mapping(selected.get('input_ref'), 'selection input_ref'),
              'input_ref': _mapping(input_ref, 'current input_ref'),
              'labor_scope': scope, 'scope_key': scope_key(scope), 'feedback': actual}
    record['feedback_id'] = _event_id(record, 'feedback_id', 'fb-')
    path = _directory(root, 'feedback') / (record['feedback_id'] + '.json')
    return _publish(path, record, task_ref, **_FEEDBACK_SCHEMA)


def _status(root, task_ref, scope):
    key = scope_key(scope)
    if key is None:
        return {'scope_key': None, 'blocked': False, 'feedback_ids': [], 'feedback_revision': None}
    blocking = set()
    for path in sorted(_directory(root, 'feedback').glob('fb-*.json')):
        record = _load(path, task_ref, **_FEEDBACK_SCHEMA)
        if record['scope_key'] == key and record['feedback']['category'] in _BLOCKING:
            blocking.add(record['feedback_id'])
    resolved = set()
    for path in sorted(_directory(root, 'resolutions').glob('lr-*.json')):
        record = _load(path, task_ref, **_RESOLUTION_SCHEMA)
        if record['scope_key'] == key:
            resolved.update(record['feedback_ids'])
    pending = sorted(blocking - resolved)
    return {'scope_key': key, 'blocked': bool(pending), 'feedback_ids': pending,
            'feedback_revision': sha256(_json(sorted(blocking))).hexdigest()}


def status(root: Path, scope: Mapping | None) -> dict:
    """Project unresolved quality/capability facts for exactly one labor scope."""
    root, task_ref = _task(root)
    return _status(root, task_ref, scope)


def resolve(root: Path, scope: Mapping, value: Mapping,
            solver_selection: Mapping, solver_observation: Mapping,
            input_ref: Mapping) -> dict:
    """Preserve one explicit disposition backed by observed high-effort work.

    Allot validates current solver/input/policy eligibility before calling.
    Matching declared execution fields do not authenticate the host or certify
    the quality of the supplied diagnosis and acceptance evidence.
    """
    root, task_ref = _task(root)
    normalized = _scope(scope)
    if normalized is None:
        raise ValueError('labor resolution needs a specific labor scope')
    key = scope_key(normalized)
    if not isinstance(value, Mapping):
        raise ValueError('labor resolution needs an explicit disposition')
    ids = value.get('feedback_ids')
    if (not isinstance(ids, list) or not ids
            or any(not isinstance(item, str) or not _FEEDBACK_ID.fullmatch(item) for item in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError('list the specific distinct feedback_ids being resolved')
    disposition = {name: _text(value.get(name), name)
                   for name in ('evidence_ref', 'detail', 'validation_ref')}
    if not isinstance(solver_selection, Mapping) or not isinstance(solver_observation, Mapping):
        raise ValueError('resolution needs actual selected and observed solver facts')
    solver_id = solver_selection.get('block_id')
    if not isinstance(solver_id, str) or not _BLOCK_ID.fullmatch(solver_id):
        raise ValueError('resolution needs an actual solver block')
    effort = solver_selection.get('effort')
    model = _text(solver_selection.get('model'), 'solver model')
    if effort not in {'max', 'ultra'}:
        raise ValueError('labor requalification needs actual high-effort work')
    if (solver_observation.get('block_id') != solver_id
            or solver_observation.get('actual_model') != model
            or solver_observation.get('actual_effort') != effort
            or solver_observation.get('matches_selection') is not True):
        raise ValueError('solver observation must match the selected actual high-effort work')
    if solver_selection.get('P_run', task_ref['P_run']) != task_ref['P_run']:
        raise ValueError('solver belongs to a different task pin')
    record = {'format': _RESOLUTION_FORMAT, 'task_ref': task_ref,
              'labor_scope': normalized, 'scope_key': key,
              'feedback_ids': sorted(ids), **disposition,
              'input_ref': _mapping(input_ref, 'current input_ref'),
              'solver_block_id': solver_id, 'solver_model': model, 'solver_effort': effort,
              'solver_selection_input_ref': _mapping(solver_selection.get('input_ref'), 'solver input_ref'),
              'solver_observation_source_ref': _text(solver_observation.get('source_ref'), 'solver observation source_ref')}
    record['resolution_id'] = _event_id(record, 'resolution_id', 'lr-')
    path = _directory(root, 'resolutions') / (record['resolution_id'] + '.json')
    if path.exists():
        # A retry of an already committed resolution must not fail merely
        # because its listed feedback is no longer pending.
        previous = _load(path, task_ref, **_RESOLUTION_SCHEMA)
        if not _same_fact(previous, record):
            raise ValueError('immutable labor resolution differs')
        return previous
    pending = set(_status(root, task_ref, normalized)['feedback_ids'])
    for identity in ids:
        feedback = _feedback(root, task_ref, identity)
        if feedback['scope_key'] != key or feedback['feedback']['category'] not in _BLOCKING:
            raise ValueError('resolution may clear only relevant same-scope quality/capability feedback')
        if identity not in pending:
            raise ValueError('feedback already resolved; replay the original resolution')
    return _publish(path, record, task_ref, **_RESOLUTION_SCHEMA)
