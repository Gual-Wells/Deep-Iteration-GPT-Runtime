"""Managed task continuation, separate from host turns and semantic consent.

The 0.8+ helper checks its own activity/decision entrances. It does not acquire
the repository, authenticate a user, classify free-text approval, or intercept
host tools. One owner writes lifecycle.json; source snapshots and atomic JSON
replacement are local consistency measures, not a multi-writer event platform.
Legacy pinned sessions are readable without being silently upgraded.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import time
from typing import Any, Mapping

from .validation import require_nonempty_text

FORMAT = 'digr-codex-lifecycle-1'
TERMINAL = frozenset({'CLOSED', 'STOPPED', 'CANCELLED'})
STATUSES = frozenset({'ACTIVE', 'PAUSED', 'ORDINARY', *TERMINAL})
MESSAGE_ACTIONS = frozenset({'continue', 'ordinary', 'revise', 'pause', 'resume', 'stop', 'cancel'})
RECENT_LIMIT = 8
_PIN = re.compile(r'[^@\s]+@[0-9a-f]{40}')


def requires_lifecycle(metadata: Mapping[str, Any]) -> bool:
    """Use the frozen run version, never the currently installed tool version."""
    version = str(metadata.get('P_run', '')).split('@', 1)[0]
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)', version)
    return bool(match and tuple(map(int, match.groups())) >= (0, 8, 0))


def _snapshot(source: Path, source_ref: str) -> dict[str, Any]:
    source = Path(source).resolve()
    raw = source.read_bytes()
    text = raw.decode('utf-8-sig')
    if not text.strip():
        raise ValueError('user message source is empty')
    return {'path': source.as_posix(), 'source_ref': require_nonempty_text('message source reference', source_ref),
            'text': text, 'utf8_bom': raw.startswith(b'\xef\xbb\xbf'),
            'byte_length': len(raw), 'sha256': sha256(raw).hexdigest(),
            'basis': 'selected source bytes; does not authenticate author or semantic consent'}


def _validate_snapshot(source: Mapping[str, Any]) -> None:
    text = source['text']
    if not isinstance(text, str) or not text.strip() or type(source['utf8_bom']) is not bool:
        raise ValueError('current user source snapshot is invalid')
    raw = (b'\xef\xbb\xbf' if source['utf8_bom'] else b'') + text.encode('utf-8')
    if len(raw) != source['byte_length'] or sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('current user source snapshot changed')
    require_nonempty_text('message source reference', source['source_ref'])


def _pin_reference(value: str | None) -> str | None:
    if value is not None and (not isinstance(value, str) or not _PIN.fullmatch(value)):
        raise ValueError('upstream route pin reference must be version@full-40-character-SHA')
    return value


def _input_ref(message: Mapping[str, Any]) -> dict[str, Any]:
    """A stable task input anchor; ordinary post-return chat does not replace it."""
    return {'message_id': message['id'], 'source_sha256': message['source']['sha256'],
            'source_ref': message['source']['source_ref'], 'path': message['source']['path']}


def initialize_lifecycle(root: Path, metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Initialize only a newly created 0.8+ session, not a legacy migration."""
    from .codex_profile import classify_invocation
    from .codex_session import _write_json
    if not requires_lifecycle(metadata):
        raise ValueError('legacy pinned sessions are not silently upgraded')
    root = Path(root).resolve()
    source = _snapshot(root / 'REQUEST.txt', str(metadata['request_origin']))
    surface = classify_invocation(source['text'])
    if surface['classification'] != 'EXECUTING':
        raise ValueError('new managed session requires an EXECUTING original request')
    value = {'format': FORMAT, 'P_run': metadata['P_run'],
             'request_sha256': metadata['request_sha256'], 'status': 'ACTIVE',
             'revision': 1, 'message_id': 0, 'handled_message_id': 0,
             'current_message': {'id': 0, 'source': source, 'surface': surface['classification'],
                                 'route_required': True, 'upstream_route_pin_ref': metadata['P_run'],
                                 'route_basis': 'caller-supplied run pin; acquisition is an upstream obligation',
                                 'handling': {'action': 'invoke', 'reason': 'original explicit task; structure only'}},
             'recent_messages': [],
             'seen_source_refs': {source['source_ref']: {'sha256': source['sha256'], 'message_id': 0}},
             'closure': None, 'cleanup_issues': [],
             'updated_wall_ns': time.time_ns(),
             'scope': 'managed continuation only; not host interception or authenticated consent'}
    value['task_input_ref'] = _input_ref(value['current_message'])
    _write_json(root / 'lifecycle.json', value, new=True)
    return value


def load_lifecycle(root: Path) -> dict[str, Any]:
    """Read finite current source/state. Legacy absence is explicitly unmanaged."""
    from .codex_session import _read_json, _session
    root, metadata = _session(root)
    if not requires_lifecycle(metadata):
        return {'managed': False, 'status': 'LEGACY_UNMANAGED', 'P_run': metadata['P_run'],
                'basis': 'frozen pre-0.8 run; no lifecycle or semantic approval inferred'}
    value = _read_json(root / 'lifecycle.json')
    if (value.get('format') != FORMAT or value.get('P_run') != metadata['P_run']
            or value.get('request_sha256') != metadata['request_sha256']):
        raise ValueError('lifecycle is not bound to this frozen run/request')
    if value.get('status') not in STATUSES:
        raise ValueError('unknown managed lifecycle status')
    for key in ('revision', 'message_id', 'handled_message_id'):
        if type(value.get(key)) is not int or value[key] < 0:
            raise ValueError('invalid lifecycle message/revision boundary')
    if value['handled_message_id'] > value['message_id']:
        raise ValueError('handled lifecycle message is in the future')
    current = value['current_message']
    if current['id'] != value['message_id']:
        raise ValueError('current lifecycle message identity mismatch')
    _validate_snapshot(current['source'])
    _pin_reference(current.get('upstream_route_pin_ref'))
    if value['status'] in TERMINAL and not value.get('closure'):
        raise ValueError('terminal lifecycle lacks its actual close record')
    value['managed'] = True
    return value


def _managed(root: Path) -> tuple[Path, dict[str, Any]]:
    value = load_lifecycle(root)
    if value.get('managed') is False:
        raise ValueError('legacy session has no managed lifecycle; use its pinned toolchain')
    return Path(root).resolve(), value


def _save(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    from .codex_session import _write_json
    value['revision'] += 1
    value['updated_wall_ns'] = time.time_ns()
    _write_json(root / 'lifecycle.json', value)
    return value


def require_active(root: Path) -> dict[str, Any]:
    """Check the current disk state; ending/recovering never calls this gate."""
    value = load_lifecycle(root)
    if value.get('managed') is False:
        return value
    if value['status'] != 'ACTIVE':
        raise ValueError('managed task is ' + value['status'] + '; no continued execution')
    if value['handled_message_id'] != value['message_id']:
        raise ValueError('new user message is pending; process it before the next managed action')
    return value


def require_open_decision(root: Path, *, user_text: str | None = None,
                          source: str | None = None) -> dict[str, Any]:
    """Guard foundation work while allowing an actual pending user answer.

    Supplying reply text/source binds them to the currently selected snapshot;
    it does not establish that their meaning is consent. Call this before a
    foundation mutation, then consume_decision_message only after it succeeds.
    """
    value = load_lifecycle(root)
    if value.get('managed') is False:
        return value
    if value['status'] != 'ACTIVE':
        raise ValueError('managed task is ' + value['status'] + '; no open foundation decision')
    message = value['current_message']
    if message['route_required'] and not message['upstream_route_pin_ref']:
        raise ValueError('candidate message still requires its upstream acquired protocol')
    if message['surface'] in {'HELP', 'INVALID', 'ROUTE_PENDING'}:
        raise ValueError('HELP/INVALID/unresolved route cannot be a deep task decision')
    if (user_text is None) != (source is None):
        raise ValueError('reply text and source must identify the same selected user message')
    if user_text is not None:
        if user_text != message['source']['text'] or source != message['source']['source_ref']:
            raise ValueError('decision reply/source does not match the current selected user message')
    return value


def consume_decision_message(root: Path, *, message_id: int, user_text: str,
                             source: str, kind: str, reason: str) -> dict[str, Any]:
    """Consume a matching source after a successful foundation answer/decision.

    No active flag is accepted. A newer pending input or pause stays effective;
    failure between the two files leaves the message fence closed to execution.
    One reply may answer several current questions, so already consumed exact
    sources are readable/idempotent rather than forged into another message.
    """
    value = require_open_decision(root, user_text=user_text, source=source)
    if value.get('managed') is False:
        return value
    if kind not in {'answer', 'confirm', 'revoke'}:
        raise ValueError('unknown foundation decision consequence')
    reason = require_nonempty_text('actual decision consequence', reason)
    if type(message_id) is not int or message_id != value['message_id']:
        raise ValueError('foundation decision cannot consume a different/newer user input')
    if value['handled_message_id'] == message_id:
        return value
    value['current_message']['handling'] = {'action': 'foundation-' + kind, 'reason': reason,
                                           'wall_ns': time.time_ns()}
    value['handled_message_id'] = message_id
    value['task_input_ref'] = _input_ref(value['current_message'])
    root = Path(root).resolve()
    _save(root, value)
    if kind in {'answer', 'revoke'}:
        # A successful answer may itself have invalidated the current brief.
        # Close unknown open tails without guessing the answer's meaning here.
        from .codex_foundation import load_foundation
        foundation = load_foundation(root)
        if foundation['status'] in {'REVISION_REQUIRED', 'REVOKED'}:
            facts = _discard_open_activity(root, reason)
            value['last_cleanup'], value['cleanup_issues'] = facts, facts['issues']
            _save(root, value)
    return value


def ingest_message(root: Path, *, source: Path, source_ref: str,
                   route_pin: str | None = None) -> dict[str, Any]:
    """Snapshot actual selected text and fence stale work until interpretation.

    route_pin only records the upstream pin reference. Supplying it is NOT a
    network call or freshness proof. The router must still actually acquire the
    pinned protocol before interpreting every candidate-prefix message.
    """
    from .codex_profile import classify_invocation
    from .routing import candidate_route_key
    root, value = _managed(root)
    selected = _snapshot(source, source_ref)
    candidate = candidate_route_key(selected['text']) is not None
    route_pin = _pin_reference(route_pin)
    if route_pin is not None and not candidate:
        raise ValueError('route pin reference applies only to an exact-prefix candidate')
    current = value['current_message']
    if value['handled_message_id'] != value['message_id']:
        # A retried real upstream acquisition can attach its pin reference to
        # the same still-pending input, without inventing another user message.
        if (route_pin is not None and candidate and current['source'] == selected):
            current['upstream_route_pin_ref'] = route_pin
            current['surface'] = classify_invocation(selected['text'])['classification']
            return _save(root, value)
        raise ValueError('handle the pending source before ingesting another message')
    if selected['source_ref'] in value['seen_source_refs']:
        raise ValueError('source reference was already observed; an old reply cannot become a new input')
    previous = {key: current.get(key) for key in ('id', 'surface', 'upstream_route_pin_ref', 'handling')}
    previous['source'] = {key: current['source'][key] for key in ('path', 'source_ref', 'sha256', 'byte_length')}
    value['recent_messages'] = [*value['recent_messages'], previous][-RECENT_LIMIT:]
    value['message_id'] += 1
    value['current_message'] = {
        'id': value['message_id'], 'source': selected,
        'surface': classify_invocation(selected['text'])['classification'] if not candidate or route_pin else 'ROUTE_PENDING',
        'route_required': candidate, 'upstream_route_pin_ref': route_pin,
        'route_basis': 'caller-supplied upstream pin reference; acquisition not performed by this helper',
        'handling': None}
    value['seen_source_refs'][selected['source_ref']] = {'sha256': selected['sha256'], 'message_id': value['message_id']}
    return _save(root, value)


def terminate_message(root: Path, *, source: Path, source_ref: str, action: str,
                      reason: str, route_pin: str | None = None) -> dict[str, Any]:
    """Apply a newly selected STOP/CANCEL even when earlier input is pending.

    This path can only terminate. It preserves the real source and prior fence;
    it cannot supersede a correction in order to continue an old plan.
    """
    from .codex_profile import classify_invocation
    from .routing import candidate_route_key
    if action not in {'stop', 'cancel'}:
        raise ValueError('priority message may only stop or cancel')
    root, value = _managed(root)
    reason = require_nonempty_text('actual termination consequence', reason)
    selected = _snapshot(source, source_ref)
    route_pin = _pin_reference(route_pin)
    candidate = candidate_route_key(selected['text']) is not None
    if route_pin is not None and not candidate:
        raise ValueError('route pin reference applies only to an exact-prefix candidate')
    current = value['current_message']
    if selected['source_ref'] in value['seen_source_refs']:
        if current['source'] == selected:
            if value['status'] in TERMINAL:return value
            if value['handled_message_id'] != value['message_id']:
                return handle_message(root, message_id=value['message_id'], action=action, reason=reason)
        raise ValueError('source reference was already observed; do not replay an old termination')
    previous = {key: current.get(key) for key in ('id', 'surface', 'upstream_route_pin_ref', 'handling')}
    previous['source'] = {key: current['source'][key] for key in ('path', 'source_ref', 'sha256', 'byte_length')}
    previous['pending_at_termination'] = value['message_id'] != value['handled_message_id']
    value['recent_messages'] = [*value['recent_messages'], previous][-RECENT_LIMIT:]
    value['message_id'] += 1
    value['current_message'] = {'id': value['message_id'], 'source': selected,
        'surface': classify_invocation(selected['text'])['classification'] if not candidate or route_pin else 'ROUTE_PENDING',
        'route_required': candidate, 'upstream_route_pin_ref': route_pin,
        'route_basis': 'upstream acquisition obligation; termination does not create execution eligibility',
        'handling': None}
    value['seen_source_refs'][selected['source_ref']] = {'sha256': selected['sha256'], 'message_id': value['message_id']}
    _save(root, value)  # New source is pending if interruption occurs here.
    return handle_message(root, message_id=value['message_id'], action=action, reason=reason)


def _discard_open_activity(root: Path, reason: str) -> dict[str, Any]:
    """Apply recover to real open tails; never infer continuity or repair logs."""
    from .codex_session import _read_activity, activity, derive_activity
    folders = [('COMMON', root / 'common')]
    folders.extend((folder.name, folder) for folder in sorted((root / 'lines').iterdir()) if folder.is_dir())
    recovered, issues = [], []
    for owner, folder in folders:
        path = folder / 'activity.jsonl'
        if not path.exists():
            continue
        try:
            active = derive_activity(_read_activity(path), expose_tail=False)['active']
            if active is not None:
                activity(root, owner, 'recover', reason=reason)
                recovered.append(owner)
        except (OSError, ValueError, TypeError, KeyError) as error:
            issues.append({'owner': owner, 'path': path.as_posix(), 'reason': str(error),
                           'effect': 'tail not repaired; continuation remains governed by lifecycle'})
    return {'recovered_owners': recovered, 'issues': issues}


def _revoke_if_present(root: Path, message: Mapping[str, Any], reason: str) -> None:
    if (root / 'foundation.json').exists():
        from .codex_foundation import revoke_foundation
        revoke_foundation(root, user_text=message['source']['text'],
                          source=message['source']['source_ref'], reason=reason)


def handle_message(root: Path, *, message_id: int, action: str, reason: str) -> dict[str, Any]:
    """Apply a model-owned interpretation; this does not judge free-text intent.

    Harmless same-task continuation carries the existing foundation decision.
    A semantic correction needs `revise`, which revokes before more execution.
    Ordinary messages after termination may be recorded without reopening it.
    """
    root, value = _managed(root)
    reason = require_nonempty_text('actual message consequence', reason)
    if action not in MESSAGE_ACTIONS:
        raise ValueError('unknown lifecycle message action')
    if type(message_id) is not int or message_id != value['message_id'] or message_id <= value['handled_message_id']:
        raise ValueError('handle the actual current pending message, not a stale/replayed source')
    message = value['current_message']
    if (message['route_required'] and not message['upstream_route_pin_ref']
            and action not in {'stop', 'cancel'}):
        raise ValueError('candidate message still lacks its upstream route pin reference; actual acquisition remains required')
    if action in {'continue', 'revise', 'resume'} and value['status'] in TERMINAL:
        raise ValueError('ordinary messages cannot reopen a terminated managed task; a new invocation needs a new session')
    if action in {'continue', 'resume', 'revise'} and message['surface'] in {'HELP', 'INVALID', 'ROUTE_PENDING'}:
        raise ValueError('HELP/INVALID/unresolved route does not continue deep execution')
    if action == 'continue' and value['status'] == 'PAUSED':
        raise ValueError('paused task needs an actual resume decision, not implicit continuation')
    if action == 'revise':
        # The input fence is still pending if this fails. Do not consume it
        # before the actual current foundation decision has been invalidated.
        _revoke_if_present(root, message, reason)
    cleanup = action in {'ordinary', 'revise', 'pause', 'stop', 'cancel'}
    if action in {'continue', 'resume'}:
        value['status'] = 'ACTIVE'
    elif action == 'ordinary' and value['status'] not in {*TERMINAL, 'PAUSED'}:
        value['status'] = 'ORDINARY'
    elif action == 'pause' and value['status'] not in TERMINAL:
        value['status'] = 'PAUSED'
    elif action in {'stop', 'cancel'} and value['status'] not in TERMINAL:
        value['status'] = 'STOPPED' if action == 'stop' else 'CANCELLED'
        value['closure'] = {'status': value['status'], 'reason': reason,
                            'message_id': message_id, 'result_ref': None,
                            'task_input_ref': dict(value['task_input_ref']),
                            'wall_ns': time.time_ns(), 'scope': 'lifecycle termination; no quality claim'}
    if action in {'continue', 'resume', 'revise'}:
        value['task_input_ref'] = _input_ref(message)
    message['handling'] = {'action': action, 'reason': reason, 'wall_ns': time.time_ns()}
    value['handled_message_id'] = message_id
    # Persist the fence/terminal status first. Failure in optional cleanup or
    # decision history must never leave STOP as a preview with execution open.
    _save(root, value)
    if action in {'stop', 'cancel'}:
        _revoke_if_present(root, message, reason)
    if cleanup:
        facts = _discard_open_activity(root, reason)
        value['last_cleanup'] = facts
        value['cleanup_issues'] = facts['issues']
    return _save(root, value)


def close_session(root: Path, *, reason: str, result: Path | None = None,
                  status: str = 'CLOSED') -> dict[str, Any]:
    """Consume continuation without changing session.json or attesting quality."""
    from .codex_session import _artifact_ref
    root, value = _managed(root)
    reason = require_nonempty_text('closure reason', reason)
    if status not in TERMINAL:
        raise ValueError('close status must be CLOSED, STOPPED or CANCELLED')
    if value['status'] in TERMINAL:
        return value
    if status == 'CLOSED':
        require_active(root)  # Do not return past a pending correction or pause.
    result_ref = _artifact_ref(Path(result)) if result is not None else None
    value['status'] = status
    value['closure'] = {'status': status, 'reason': reason, 'message_id': value['message_id'],
                        'result_ref': result_ref, 'wall_ns': time.time_ns(),
                        'task_input_ref': dict(value['task_input_ref']),
                        'scope': 'lifecycle termination; no semantic/delivery-quality attestation'}
    _save(root, value)
    if status in {'STOPPED', 'CANCELLED'}:
        # Direct administrative close has no new captured user message. Keep
        # that distinction explicit instead of quoting an earlier go-ahead as
        # though it were the later stop request.
        notice = {'source': {'text': 'Operator closure record (not user quotation): ' + reason,
                             'source_ref': (root / 'lifecycle.json').as_posix() + '#closure'}}
        _revoke_if_present(root, notice, reason)
    facts = _discard_open_activity(root, reason)
    value['last_cleanup'], value['cleanup_issues'] = facts, facts['issues']
    return _save(root, value)


def recover_session(root: Path, *, reason: str) -> dict[str, Any]:
    """Discard open activity after real recovery, preserving pause/terminal state."""
    root, value = _managed(root)
    reason = require_nonempty_text('recovery reason', reason)
    facts = _discard_open_activity(root, reason)
    value['last_cleanup'], value['cleanup_issues'] = facts, facts['issues']
    value['last_recovery'] = {'reason': reason, 'wall_ns': time.time_ns(),
                              'scope': 'open tails only; no implicit invocation, resume or continuous-time claim'}
    return _save(root, value)
