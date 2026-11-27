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

from .codex_collaboration import u0_council_parameter
from .validation import require_binary, require_nonempty_text

FORMAT = 'digr-codex-lifecycle-1'
TERMINAL = frozenset({'CLOSED', 'STOPPED', 'CANCELLED'})
STATUSES = frozenset({'ACTIVE', 'PAUSED', 'ORDINARY', *TERMINAL})
MESSAGE_ACTIONS = frozenset({'continue', 'ordinary', 'revise', 'pause', 'resume', 'stop', 'cancel', 'budget'})
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


def _apply_claude_selection(value: dict, metadata: Mapping[str, Any], message: Mapping[str, Any],
                            selection: str | None = None) -> None:
    """Retain the actual current source; interpret prose only at the host.

    A complete prefix supplies its structural choice. An optional prose choice
    is a caller's interpretation of this selected user message, not a grant
    inferred from credentials, task materials or another model's response.
    """
    from .codex_collaboration import allowed_selections, delimiter_policy, layered_policy
    from .codex_profile import classify_invocation
    if not delimiter_policy(metadata['P_run']):
        if selection is not None:
            raise ValueError('Claude delimiter selection requires a 0.15+ task; old pins retain their rules')
        return
    if selection is not None and selection not in allowed_selections(metadata['P_run']):
        raise ValueError('Claude selection is unavailable under this frozen task pin')
    surface = classify_invocation(message['source']['text'], p_run=metadata['P_run'])
    if surface['classification'] in {'HELP', 'INVALID'} and selection is not None:
        raise ValueError('help/malformed source cannot change Claude selection')
    incoming = surface.get('claude_selection')
    if incoming is not None:
        if selection is not None and selection != incoming:
            raise ValueError('Claude choice conflicts with the current user separator')
        selection = incoming
    if selection is not None:
        layered = layered_policy(metadata['P_run'])
        previous_mode = value.get('claude_policy', {}).get('mode')
        value['claude_policy'] = {'mode': selection, 'message_id': message['id'],
            'source': dict(message['source']),
            'basis': 'INVOCATION_SEPARATOR' if incoming is not None else 'CURRENT_USER_DECISION',
            'scope': 'current selected user choice; not authentication or fee authorization'}
        if not layered:
            value['claude_policy']['work_profile'] = 'CLAUDE_GUIDED' if selection == 'ALLOW' else 'EXECUTION'
        if layered and (selection == 'DENY' or previous_mode == 'ALLOW' and selection != 'ALLOW'):
            value['latest_claude_revocation_message_id'] = message['id']
        if layered and selection == 'COUNCIL_ONLY':
            value['claude_policy']['scope'] = 'Claude council roles within the existing wallet and effective limits'


def _input_ref(message: Mapping[str, Any]) -> dict[str, Any]:
    """A stable task input anchor; ordinary post-return chat does not replace it."""
    return {'message_id': message['id'], 'source_sha256': message['source']['sha256'],
            'source_ref': message['source']['source_ref'], 'path': message['source']['path']}


def content_message(lifecycle: Mapping[str, Any]) -> Mapping[str, Any]:
    """Read the substantive work input separately from status and fee replies."""
    from .codex_collaboration import layered_policy
    if layered_policy(lifecycle['P_run']):
        return lifecycle['task_input_message']
    return lifecycle['current_message']


def _set_task_input(value: dict) -> None:
    from .codex_collaboration import layered_policy
    current = value['current_message']
    value['task_input_ref'] = _input_ref(current)
    if layered_policy(value['P_run']):
        value['task_input_message'] = {'id': current['id'], 'source': dict(current['source'])}


def _message_surface(text: str, lifecycle: Mapping[str, Any], *, route_pending: bool) -> dict[str, Any]:
    from .codex_profile import classify_invocation
    if route_pending:
        return {'surface': 'ROUTE_PENDING'}
    invocation = classify_invocation(text, p_run=lifecycle['P_run'])
    surface = {'surface': invocation['classification']}
    if 'supplement' in invocation:
        if lifecycle['status'] not in {'ACTIVE', 'PAUSED'}:
            raise ValueError('DO supplement requires an unfinished DIGR task; specify the target or start a new DIGR invocation')
        surface['supplement'] = invocation['supplement']
    return surface


def _recent_message(message: Mapping[str, Any]) -> dict[str, Any]:
    previous = {key: message.get(key) for key in ('id', 'surface', 'upstream_route_pin_ref', 'handling')}
    previous['source'] = {key: message['source'][key] for key in ('path', 'source_ref', 'sha256', 'byte_length')}
    if 'supplement' in message:
        previous['supplement'] = {key: message['supplement'][key] for key in ('kind', 'prefix')}
    return previous


def initialize_lifecycle(root: Path, metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Initialize only a newly created 0.8+ session, not a legacy migration."""
    from .codex_profile import classify_invocation
    from .codex_session import _write_json
    if not requires_lifecycle(metadata):
        raise ValueError('legacy pinned sessions are not silently upgraded')
    root = Path(root).resolve()
    source = _snapshot(root / 'REQUEST.txt', str(metadata['request_origin']))
    surface = classify_invocation(source['text'], p_run=metadata['P_run'])
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
    value['current_message'].update({key: surface[key] for key in
        ('invocation_key', 'addon_hint', 'addon_selection') if key in surface})
    _set_task_input(value)
    _apply_claude_selection(value, metadata, value['current_message'])
    if metadata.get('delivery_contract') == 'x-files-v1':
        value['delivery_selection'] = metadata['delivery_selection']
        value['delivery_policy'] = metadata['initial_delivery_policy']
        value['delivery_history'] = []
    from .codex_session import formal_task_parameters, court_mode_parameter
    if formal_task_parameters(metadata['P_run']):
        value['x_parameter_source'] = {
            'value': int(metadata['initial_delivery_policy']['mode'] == 'external'),
            'input_explicit': bool(surface.get('delivery_explicit')),
            'message_id': 0, 'source_ref': source['source_ref'],
            'basis': 'INVOCATION_HEADER' if surface.get('delivery_explicit') else 'NEW_TASK_DEFAULT'}
        if court_mode_parameter(metadata['P_run']):
            _apply_court_selection(value, metadata, value['current_message'])
        elif (surface.get('depth_preferences') or {}).get('preset') == 'Max':
            value['max_court_required'] = True
            value['max_court_source'] = _input_ref(value['current_message'])
    _apply_u0_selection(value, metadata, value['current_message'])
    _write_json(root / 'lifecycle.json', value, new=True)
    return value


def _apply_court_selection(value: dict, metadata: Mapping[str, Any],
                           message: Mapping[str, Any], selection: int | None = None) -> None:
    """C is an independent user-source choice, not a production-depth estimate."""
    from .codex_session import court_mode_parameter
    if not court_mode_parameter(metadata['P_run']):
        if selection is not None:
            raise ValueError('C requires a 1.6+ pin; older court rules remain unchanged')
        return
    if selection is not None:
        require_binary('C', selection)
    from .codex_profile import classify_invocation
    surface = classify_invocation(message['source']['text'], p_run=metadata['P_run'])
    if surface['classification'] in {'HELP', 'INVALID', 'ROUTE_PENDING'}:
        if selection is not None:
            raise ValueError('help/malformed/unresolved source cannot change C')
        return
    depth = surface.get('depth_preferences') or {}
    declared = depth.get('explicit_overrides', {})
    header = declared.get('C')
    if header is not None:
        if selection is not None and selection != header:
            raise ValueError('C choice conflicts with the current user header')
        selection = header
    previous = value.get('court_parameter_source')
    if selection is None and previous is not None:
        return  # Later tiers and ordinary messages inherit the actual task C.
    explicit = selection is not None
    if selection is None:
        selection = depth['preference_baseline']['C']
    require_binary('C', selection)
    source = {'value': selection, 'input_explicit': explicit,
              'message_id': message['id'], 'source_ref': message['source']['source_ref'],
              'source_sha256': message['source']['sha256'],
              'basis': ('INVOCATION_HEADER' if header is not None else
                        'CURRENT_USER_DECISION' if explicit else 'NEW_TASK_PRESET_DEFAULT')}
    if previous is not None and previous != source:
        value.setdefault('court_selection_history', []).append(previous)
    value['court_parameter_source'] = source
    value['court_required'] = bool(selection)


def _apply_u0_selection(value: dict, metadata: Mapping[str, Any],
                        message: Mapping[str, Any], selection: int | None = None) -> None:
    if not u0_council_parameter(metadata['P_run']):
        if selection is not None:
            raise ValueError('U requires a frozen Codex 1.8.0+ task')
        return
    from .codex_profile import classify_invocation
    surface = classify_invocation(message['source']['text'], p_run=metadata['P_run'])
    if surface['classification'] in {'HELP', 'INVALID', 'ROUTE_PENDING'}:
        if selection is not None:
            raise ValueError('help/malformed/unresolved source cannot change U')
        return
    depth = surface.get('depth_preferences') or {}
    header = depth.get('explicit_overrides', {}).get('U')
    if selection is not None:
        require_binary('U', selection)
        if header is not None and selection != header:
            raise ValueError('U choice conflicts with the current user header')
    if header is not None:
        selection = header
    previous = value.get('u0_parameter_source')
    if selection is None and previous is not None:
        return
    source = {'value': 0 if selection is None else selection, 'input_explicit': selection is not None,
              'message_id': message['id'], 'source_ref': message['source']['source_ref'],
              'source_sha256': message['source']['sha256'],
              'basis': ('INVOCATION_HEADER' if header is not None else
                        'CURRENT_USER_DECISION' if selection is not None else 'NEW_TASK_DEFAULT')}
    if previous is not None and previous != source:
        value.setdefault('u0_selection_history', []).append(previous)
    value['u0_parameter_source'] = source


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
    from .codex_session import court_mode_parameter
    if court_mode_parameter(metadata['P_run']):
        choice = value.get('court_parameter_source', {})
        require_binary('C', choice.get('value'))
        if type(value.get('court_required')) is not bool or value['court_required'] != bool(choice['value']):
            raise ValueError('C and court_required differ')
        observed = value['seen_source_refs'].get(choice.get('source_ref'))
        if (type(choice.get('message_id')) is not int or choice['message_id'] > value['handled_message_id']
                or observed != {'sha256': choice.get('source_sha256'), 'message_id': choice['message_id']}):
            raise ValueError('C is not bound to a handled actual user source')
    if u0_council_parameter(metadata['P_run']):
        choice = value.get('u0_parameter_source', {})
        require_binary('U', choice.get('value'))
        observed = value['seen_source_refs'].get(choice.get('source_ref'))
        if (type(choice.get('message_id')) is not int or choice['message_id'] > value['handled_message_id']
                or observed != {'sha256': choice.get('source_sha256'), 'message_id': choice['message_id']}):
            raise ValueError('U is not bound to a handled actual user source')
    _validate_snapshot(current['source'])
    _pin_reference(current.get('upstream_route_pin_ref'))
    from .codex_profile import parse_do_supplement
    supplement = parse_do_supplement(current['source']['text'], p_run=metadata['P_run'])
    if current.get('supplement') != supplement:
        raise ValueError('DO supplement does not match the selected user source')
    from .codex_collaboration import allowed_selections, delimiter_policy, layered_policy
    if delimiter_policy(metadata['P_run']):
        policy = value.get('claude_policy', {})
        if policy.get('mode') not in allowed_selections(metadata['P_run']) or policy.get('basis') not in {
                'INVOCATION_SEPARATOR', 'CURRENT_USER_DECISION'}:
            raise ValueError('missing/invalid current Claude choice')
        if (not layered_policy(metadata['P_run'])
                and policy.get('work_profile') != ('CLAUDE_GUIDED' if policy['mode'] == 'ALLOW' else 'EXECUTION')):
            raise ValueError('Claude work profile differs from its current choice')
        _validate_snapshot(policy['source'])
        observed = value['seen_source_refs'].get(policy['source']['source_ref'], {})
        if (type(policy.get('message_id')) is not int or policy['message_id'] > value['handled_message_id']
                or observed != {'sha256': policy['source']['sha256'], 'message_id': policy['message_id']}):
            raise ValueError('Claude choice is not bound to a handled user source')
        if policy['basis'] == 'INVOCATION_SEPARATOR':
            from .codex_profile import classify_invocation
            selected = classify_invocation(policy['source']['text'], p_run=metadata['P_run'])
            if selected.get('claude_selection') != policy['mode']:
                raise ValueError('Claude choice differs from its user separator')
    if layered_policy(metadata['P_run']):
        work = content_message(value)
        _validate_snapshot(work['source'])
        observed = value['seen_source_refs'].get(work['source']['source_ref'], {})
        if (type(work['id']) is not int or work['id'] > value['handled_message_id']
                or observed != {'sha256': work['source']['sha256'], 'message_id': work['id']}
                or value['task_input_ref'] != _input_ref(work)):
            raise ValueError('current work input is not bound to an actual handled user source')
        for key in ('latest_budget_message_id', 'latest_claude_revocation_message_id', 'latest_revision_message_id'):
            decision = value.get(key)
            if decision is not None and (type(decision) is not int or not 0 < decision <= value['handled_message_id']):
                raise ValueError('decision references must identify a handled user input')
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


def _bind_task_parameter_input(root: Path, *, source: Mapping[str, Any]) -> dict[str, Any]:
    """Anchor an actual handled parameter revision, never Main's inference."""
    from .codex_session import formal_task_parameters
    value = require_active(root)
    if not formal_task_parameters(value['P_run']):
        raise ValueError('task parameter source binding requires the new pinned parameter contract')
    current = value['current_message']
    actual = _input_ref(current)
    if any(source.get(key) != actual[key] for key in ('message_id', 'source_ref', 'source_sha256')):
        raise ValueError('task parameter revision must bind the current handled actual user source')
    if value['task_input_ref'] != actual:
        _set_task_input(value)
        return _save(Path(root), value)
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
    from .codex_session import _session
    _apply_claude_selection(value, _session(root)[1], value['current_message'])
    value['handled_message_id'] = message_id
    _set_task_input(value)
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
            current['surface'] = classify_invocation(selected['text'], p_run=value['P_run'])['classification']
            return _save(root, value)
        raise ValueError('handle the pending source before ingesting another message')
    if selected['source_ref'] in value['seen_source_refs']:
        raise ValueError('source reference was already observed; an old reply cannot become a new input')
    surface = _message_surface(selected['text'], value, route_pending=candidate and route_pin is None)
    value['recent_messages'] = [*value['recent_messages'], _recent_message(current)][-RECENT_LIMIT:]
    value['message_id'] += 1
    value['current_message'] = {
        'id': value['message_id'], 'source': selected,
        **surface,
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
    surface = _message_surface(selected['text'], value, route_pending=candidate and route_pin is None)
    previous = _recent_message(current)
    previous['pending_at_termination'] = value['message_id'] != value['handled_message_id']
    value['recent_messages'] = [*value['recent_messages'], previous][-RECENT_LIMIT:]
    value['message_id'] += 1
    value['current_message'] = {'id': value['message_id'], 'source': selected,
        **surface,
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


def handle_message(root: Path, *, message_id: int, action: str, reason: str,
                   delivery_selection: dict | None = None, destinations: Path | None = None,
                   claude_selection: str | None = None, court_mode: int | None = None,
                   u0_council: int | None = None) -> dict[str, Any]:
    """Serialize a real policy change with pre-send reservation, not STOP.

    The message itself is already pending before this call; an external host
    must also honor later user input after it receives a one-time send grant.
    """
    if delivery_selection is None and action not in {'stop', 'cancel', 'pause'}:
        from .codex_session import _session, formal_task_parameters
        metadata = _session(Path(root))[1]
        if formal_task_parameters(metadata['P_run']):
            from .codex_profile import classify_invocation
            selected = load_lifecycle(Path(root))['current_message']['source']['text']
            surface = classify_invocation(selected, p_run=metadata['P_run'])
            if surface['classification'] == 'EXECUTING' and surface.get('delivery_explicit'):
                delivery_selection = surface['delivery_selection']
    if delivery_selection is not None and action not in {'stop','cancel','pause'}:
        from .codex_delivery import policy_lock
        with policy_lock(Path(root).resolve()):
            return _handle_message(root,message_id=message_id,action=action,reason=reason,
                delivery_selection=delivery_selection,destinations=destinations,claude_selection=claude_selection,
                court_mode=court_mode, u0_council=u0_council)
    return _handle_message(root,message_id=message_id,action=action,reason=reason,
        delivery_selection=delivery_selection,destinations=destinations,claude_selection=claude_selection,
        court_mode=court_mode, u0_council=u0_council)


def _handle_message(root: Path, *, message_id: int, action: str, reason: str,
                    delivery_selection: dict | None = None, destinations: Path | None = None,
                    claude_selection: str | None = None, court_mode: int | None = None,
                   u0_council: int | None = None) -> dict[str, Any]:
    """Apply a model-owned interpretation; this does not judge free-text intent.

    Message disposition is not task termination. Ordinary input to ACTIVE is
    a supplement and carries its foundation/activity; PAUSED stays paused.
    Only a material replacement of the accepted object needs `revise`.
    Terminal tasks never reopen through ordinary discussion.
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
    if action in {'continue', 'resume', 'revise'} and message['surface'] == 'ROUTE_PENDING':
        raise ValueError('unresolved route does not continue deep execution')
    if action == 'continue' and value['status'] == 'PAUSED':
        raise ValueError('paused task needs an actual resume decision, not implicit continuation')
    from .codex_session import _session, read_delivery_registry, formal_task_parameters, court_mode_parameter
    from .codex_collaboration import layered_policy
    metadata = _session(root)[1]
    formal = formal_task_parameters(metadata['P_run'])
    binary_court = court_mode_parameter(metadata['P_run'])
    prior_c = value.get('court_parameter_source', {}).get('value')
    prior_x = int(value.get('delivery_policy', {}).get('mode') == 'external')
    prior_max = (value.get('max_court_required') is True
                 or (metadata.get('parameter_selection') or {}).get('preset') == 'Max')
    if formal and delivery_selection is not None and delivery_selection not in (
            {'mode': 'local', 'target': None, 'explicit': False},
            {'mode': 'external', 'target': 'gmail', 'explicit': True}):
        raise ValueError('1.5+ X selects local files or the frozen Gmail mailbox; use binary X=0/1')
    layered = layered_policy(metadata['P_run'])
    if action == 'budget':
        if (not layered or value['status'] != 'ACTIVE'
                or message['surface'] != 'NATIVE' or message['route_required']
                or claude_selection is not None or delivery_selection is not None or destinations is not None
                or court_mode is not None or u0_council is not None):
            raise ValueError('Budget handling is for a standalone fee-only reply on an active Stable task')
        value['latest_budget_message_id'] = message_id
    if action not in {'stop', 'cancel'} and value['status'] not in TERMINAL:
        _apply_claude_selection(value, metadata, message, claude_selection)
    elif claude_selection is not None:
        raise ValueError('a terminal task/source cannot change Claude selection')
    if action not in {'stop', 'cancel'} and value['status'] not in TERMINAL:
        _apply_court_selection(value, metadata, message, court_mode)
        _apply_u0_selection(value, metadata, message, u0_council)
    elif u0_council is not None:
        raise ValueError('a terminal task/source cannot change U')
    elif court_mode is not None:
        raise ValueError('a terminal task/source cannot change C')
    if metadata.get('delivery_contract') == 'x-files-v1' and action not in {'stop','cancel','pause'}:
        from .codex_profile import classify_invocation
        surface = classify_invocation(message['source']['text'], p_run=metadata['P_run'])
        incoming = surface.get('delivery_selection', {})
        current = value.get('delivery_selection', metadata['delivery_selection'])
        if delivery_selection is not None and surface['classification'] in {'HELP','INVALID','ROUTE_PENDING'}:
            raise ValueError('malformed/help/unresolved source cannot authorize an X delivery change')
        if (formal and delivery_selection is not None and surface['classification'] == 'EXECUTING'
                and surface.get('delivery_explicit') and incoming != delivery_selection):
            raise ValueError('delivery change differs from the current source X header')
        if delivery_selection is None and incoming.get('explicit') and incoming != current:
            from .codex_delivery import resolve_policy
            registry, _ = read_delivery_registry(destinations)
            resolved = resolve_policy(incoming, registry)
            endpoint = ('channel','account','recipient','transport','target_kind','evidence_adapter','account_kind')
            if any(resolved.get(field) != value['delivery_policy'].get(field) for field in endpoint):
                raise ValueError('this source changes X; handle its actual choice with --delivery-selection before continuing')
            # An equivalent alias does not rebind the saved endpoint or adopt
            # newly edited registry capability/identity observations.
            value['delivery_selection'] = incoming
        if delivery_selection is not None and delivery_selection != current:
            header_choice = surface.get('delivery_explicit') if formal else incoming.get('explicit')
            if surface['classification'] == 'EXECUTING' and header_choice and incoming != delivery_selection:
                raise ValueError('delivery change differs from the current source X header')
            from .codex_delivery import inspect as inspect_delivery, resolve_policy
            deliveries = inspect_delivery(root)['deliveries']
            if not formal and delivery_selection.get('mode') != 'local' and any(
                    item['unresolved'] or item['recorded_status'] == 'SENT_VERIFIED' for item in deliveries):
                raise ValueError('external retarget after a send is not automatic; reconcile uncertain sends and use a new explicitly scoped task')
            previous_external = next((entry for entry in reversed(value.get('delivery_history', []))
                                      if entry['policy'].get('mode') == 'external'), None)
            if formal and delivery_selection.get('mode') == 'external' and previous_external is not None:
                # A fresh explicit X=1 can resume the same frozen mailbox. It
                # never rebinds to an edited registry or clears prior effects.
                from .codex_delivery import validate_policy
                policy = validate_policy(previous_external['policy'])
                origin = previous_external.get('registry_origin', metadata.get('delivery_registry_origin'))
            else:
                registry, origin = (read_delivery_registry(destinations)
                                    if delivery_selection.get('mode') == 'external' else (None,None))
                policy = resolve_policy(delivery_selection, registry)
            value.setdefault('delivery_history', []).append({
                'selection':current,'policy':value['delivery_policy'],
                **({'registry_origin': value.get('delivery_registry_origin')} if formal else {}),
                'changed_by_message_id':message_id,'source_ref':message['source']['source_ref'],
                'reason':reason,'recorded_wall_ns':time.time_ns()})
            value.update(delivery_selection=delivery_selection,delivery_policy=policy,
                         delivery_registry_origin=origin)
        if formal and (surface.get('delivery_explicit') or delivery_selection is not None):
            value['x_parameter_source'] = {
                'value': int(value['delivery_policy']['mode'] == 'external'),
                'input_explicit': True, 'message_id': message_id,
                'source_ref': message['source']['source_ref'],
                'basis': 'INVOCATION_HEADER' if surface.get('delivery_explicit') else 'USER_MESSAGE_INTERPRETATION'}
    elif delivery_selection is not None or destinations is not None:
        raise ValueError('delivery changes require an active 0.9+ task source and an applicable message action')
    if formal and action not in {'stop', 'cancel'}:
        from .codex_profile import classify_invocation
        selected_surface = classify_invocation(message['source']['text'], p_run=metadata['P_run'])
        if (not binary_court and selected_surface['classification'] == 'EXECUTING'
                and (selected_surface.get('depth_preferences') or {}).get('preset') == 'Max'
                and not value.get('max_court_required')):
            value['max_court_required'] = True
            value['max_court_source'] = _input_ref(message)
    if action == 'revise':
        # Keep the input fence closed until the stale decision is invalidated.
        if layered and (root / 'foundation.json').exists():
            from .codex_foundation import revise_foundation
            revise_foundation(root, user_text=message['source']['text'],
                              source=message['source']['source_ref'], reason=reason)
        elif not layered:
            _revoke_if_present(root, message, reason)
        if layered:
            value['latest_revision_message_id'] = message_id
    cleanup = action in {'revise', 'pause', 'stop', 'cancel'}
    if action in {'continue', 'resume'}:
        value['status'] = 'ACTIVE'
    elif action == 'pause' and value['status'] not in TERMINAL:
        value['status'] = 'PAUSED'
    elif action in {'stop', 'cancel'} and value['status'] not in TERMINAL:
        value['status'] = 'STOPPED' if action == 'stop' else 'CANCELLED'
        value['closure'] = {'status': value['status'], 'reason': reason,
                            'message_id': message_id, 'result_ref': None,
                            'task_input_ref': dict(value['task_input_ref']),
                            'wall_ns': time.time_ns(), 'scope': 'lifecycle termination; no quality claim'}
    changed_user_parameter = False
    if formal and action == 'ordinary' and value['status'] == 'ACTIVE':
        changed_user_parameter = (prior_x != int(value['delivery_policy']['mode'] == 'external')
                                  or (prior_c != value['court_parameter_source']['value'] if binary_court else
                                      not prior_max and value.get('max_court_required') is True))
        declared = (selected_surface.get('depth_preferences') or {}).get('explicit_overrides', {})
        if selected_surface['classification'] == 'EXECUTING' and 'F' in declared:
            from .codex_session import task_parameters
            changed_user_parameter = (changed_user_parameter
                                      or declared['F'] != task_parameters(root)['parameters']['F'])
    if (action in {'continue', 'resume', 'revise'} or changed_user_parameter
            or action == 'ordinary' and not layered and value['status'] not in TERMINAL):
        _set_task_input(value)
    message['handling'] = {'action': action, 'reason': reason, 'wall_ns': time.time_ns()}
    value['handled_message_id'] = message_id
    # Persist the fence/terminal status first. Failure in optional cleanup or
    # decision history must never leave STOP as a preview with execution open.
    _save(root, value)
    if formal and value['status'] == 'ACTIVE' and action not in {'stop', 'cancel', 'pause'}:
        selected_surface = classify_invocation(message['source']['text'], p_run=metadata['P_run'])
        declared = (selected_surface.get('depth_preferences') or {}).get('explicit_overrides', {})
        if selected_surface['classification'] == 'EXECUTING' and 'F' in declared:
            from .codex_session import set_task_parameters
            set_task_parameters(root, parameters={'F': declared['F']},
                                reasons={'F': 'Current selected user header explicitly sets F'},
                                user_revision=message['source']['source_ref'])
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
        from .codex_return import return_status
        current = return_status(root)
        if (not current['can_close'] or result is None
                or Path(result).resolve() != Path(current['receipt']).resolve()):
            raise ValueError('normal closure requires the current sealed return; use return close')
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
