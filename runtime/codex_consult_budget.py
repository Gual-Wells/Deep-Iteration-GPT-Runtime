"""Use task input as authority and the shared ledger as spending evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from . import codex_collaboration, codex_wallet

PREVIEW_FORMAT = 'digr-consult-budget-preview-1'
DECISION_FORMAT = 'digr-consult-budget-decision-1'
ROLES = {'council_member', 'consult_guidance'}


def _task_binding(session: Mapping[str, Any]) -> dict:
    return {key: session[key] for key in ('task_uuid', 'P_run', 'request_sha256')}


def _policy_mode(lifecycle: Mapping[str, Any]) -> str | None:
    return lifecycle.get('claude_policy', {}).get('mode')


def _decision_path(root: Path, kind: str) -> Path:
    if kind not in {'approval', 'limit'}:
        raise ValueError('Unknown budget decision kind')
    return root / 'consult' / ('budget-' + kind + '.json')


def read_decision(root: Path, session: Mapping[str, Any], lifecycle: Mapping[str, Any],
                  kind: str) -> dict | None:
    from .codex_consult import _hash, _json_bytes, _number, _read
    from .codex_lifecycle import _validate_snapshot
    path = _decision_path(root, kind)
    if not path.exists():
        return None
    value = _read(path)
    body = {key: item for key, item in value.items() if key != 'decision_id'}
    if (value.get('format') != DECISION_FORMAT or value.get('kind') != kind
            or value.get('task') != _task_binding(session)
            or value.get('decision_id') != _hash(_json_bytes(body))):
        raise ValueError('Consult budget decision does not belong to this task or changed on disk')
    reply = value['reply']
    source = reply['source']
    _validate_snapshot(source)
    actual = lifecycle['seen_source_refs'].get(source['source_ref'])
    if (type(reply['message_id']) is not int or reply['message_id'] > lifecycle['handled_message_id']
            or actual != {'sha256': source['sha256'], 'message_id': reply['message_id']}
            or reply['quote'] not in source['text']):
        raise ValueError('Consult budget decision is detached from its actual handled user source')
    _number('recorded task ceiling', value.get('task_ceiling_usd'))
    return value


def preview(root: Path, *, jobs: Sequence[Mapping[str, Any]], task_ceiling_usd: float,
            scope: str, wallet_id: str) -> dict:
    """Price prepared requests or a projected member before its council starts."""
    from . import codex_consult as consult
    root, session, lifecycle = consult._task(root, active=True)
    if not codex_collaboration.layered_policy(session['P_run']) or _policy_mode(lifecycle) != 'ALLOW':
        raise ValueError('An approval preview is for a Stable double-colon task')
    wallet_id = consult._text('shared wallet alias', wallet_id)
    scope = consult._text('actual budget scope', scope)
    total = consult._number('task_ceiling_usd', task_ceiling_usd, positive=True)
    limit = read_decision(root, session, lifecycle, 'limit')
    if limit is not None and total > limit['task_ceiling_usd'] + 1e-12:
        raise ValueError('Proposed ceiling exceeds the current explicit task limit')
    if not isinstance(jobs, (tuple, list)) or not jobs:
        raise ValueError('Budget preview needs one or more actual prepared requests')

    input_ref = consult._input_ref(lifecycle)
    rows, budgets, seen = [], [], set()
    for job in jobs:
        if not isinstance(job, Mapping) or not isinstance(job.get('facts'), Mapping):
            raise ValueError('Every budget preview job needs current pricing and wallet facts')
        if 'planned_council_member' in job:
            planned = job['planned_council_member']
            if ('exchange_id' in job or not isinstance(planned, Mapping)
                    or set(planned) != {'model', 'max_tokens', 'purpose'}):
                raise ValueError('A planned council member needs its model, output bound and actual purpose')
            model = consult._text('planned member model', planned['model'])
            max_tokens = planned['max_tokens']
            if type(max_tokens) is not int or max_tokens < 1:
                raise ValueError('A planned member needs a positive combined output-token bound')
            request = {'model': model, 'max_tokens': max_tokens}
            role = 'council_member'
            origin = {'request_basis': 'PLANNED_COUNCIL_MEMBER',
                      'purpose': consult._text('planned member research purpose', planned['purpose'])}
        else:
            exchange = consult._text('exchange_id', job.get('exchange_id'))
            if exchange in seen:
                raise ValueError('Budget preview counts each prepared exchange only once')
            seen.add(exchange)
            _, attempt, request = consult._load(root, exchange)
            if attempt['transport_status'] != 'PREPARED' or attempt['input_ref'] != input_ref:
                raise ValueError('Budget preview needs currently prepared exchanges for this task input')
            role = attempt.get('participation_role')
            if role not in ROLES:
                raise ValueError('Budget preview needs a prepared Consult or Council role')
            origin = {'request_basis': 'PREPARED_EXCHANGE', 'exchange_id': exchange,
                      'request_sha256': attempt['request_sha256']}
        codex_collaboration.require_claude_permission(session['P_run'], request['model'], lifecycle,
            participation_role=role)
        facts = {**job['facts'], 'authorization_ref': 'PREVIEW_ONLY', 'budget_total_usd': total}
        budget = consult._budget(facts, request, (), job.get('ceiling_usd'), canonical_wallet=True)
        budgets.append(budget)
        rows.append({**origin,
                     'role': role, 'model': request['model'], 'input_tokens_upper_bound': budget['input_tokens_upper_bound'],
                     'max_output_tokens': request['max_tokens'], 'pricing_ref': budget['pricing_ref'],
                     'checked_at': budget['checked_at'], 'estimated_upper_usd': budget['planned_cost_bound_usd'],
                     'reservation_ceiling_usd': budget['ceiling_usd']})

    positions = codex_wallet.review_capacity(root, session, wallet_id=wallet_id, budgets=budgets)
    remaining = min(position['task_available_before_usd'] for position in positions)
    safe_available = min(position[key] for position in positions
                         for key in ('wallet_available_before_usd', 'account_available_before_usd')
                         if position[key] is not None)
    reserved_upper = sum(job['ceiling_usd'] for job in budgets)
    # Both the prepared batch and the remaining envelope must fit. Per-request
    # fit alone misses consecutive/parallel members spending the same balance.
    if reserved_upper > remaining + 1e-12 or remaining > safe_available + 1e-12:
        raise ValueError('The combined task envelope exceeds current capacity after known costs and reservations')
    value = {'format': PREVIEW_FORMAT, 'task': _task_binding(session),
             'presented_after_message_id': lifecycle['message_id'], 'input_ref': input_ref,
             'scope_revision_message_id': lifecycle.get('latest_revision_message_id', 0),
             'created_at': consult._now(), 'wallet_id': wallet_id, 'scope': scope,
             'task_ceiling_usd': total, 'remaining_envelope_usd': remaining,
             'available_to_reserve_usd': safe_available, 'prepared_reservation_upper_usd': reserved_upper,
             'requests': rows, 'basis': 'read-only estimate using actual or projected bounded work and supplied provider facts'}
    return {**value, 'preview_id': consult._hash(consult._json_bytes(value))}


def _selected_reply(root: Path, *, user_text: str, source: str, quote: str) -> tuple[dict, dict, dict]:
    from .codex_consult import _task, _text
    from .codex_lifecycle import require_open_decision
    root, session, lifecycle = _task(root, active=True)
    if not codex_collaboration.layered_policy(session['P_run']):
        raise ValueError('Recorded budget decisions require a frozen Stable task')
    require_open_decision(root, user_text=user_text, source=source)
    current = lifecycle['current_message']
    if current.get('handling', {}).get('action') != 'budget':
        raise ValueError('Record the actual fee-only user reply with task handle --action budget first')
    quote = _text('exact quote of the user decision', quote)
    if quote not in current['source']['text']:
        raise ValueError('Budget decision quote differs from the actual user reply')
    return session, lifecycle, {'message_id': current['id'], 'source': current['source'], 'quote': quote}


def _record(root: Path, session: Mapping[str, Any], lifecycle: Mapping[str, Any], *,
            kind: str, reply: Mapping[str, Any], task_ceiling_usd: float, **details) -> dict:
    from .codex_consult import _hash, _json_bytes, _now, _writer
    from .codex_lifecycle import require_active
    from .codex_session import _write_json
    with _writer(root):
        current = require_active(root)
        if current['revision'] != lifecycle['revision']:
            raise ValueError('The active user budget decision changed before recording')
        body = {'format': DECISION_FORMAT, 'kind': kind, 'task': _task_binding(session),
                'reply': dict(reply), 'task_ceiling_usd': task_ceiling_usd, **details,
                'basis': 'actual selected user reply and operator interpretation of amount and approved scope'}
        previous = read_decision(root, session, current, kind)
        if previous and previous['reply']['message_id'] == reply['message_id']:
            if any(previous.get(key) != item for key, item in body.items()):
                raise ValueError('One user reply cannot be reused to record a different budget decision')
            return previous
        body['recorded_at'] = _now()
        result = {**body, 'decision_id': _hash(_json_bytes(body))}
        _write_json(_decision_path(root, kind), result)
        return result


def approve(root: Path, *, preview_path: Path, user_text: str, source: str, quote: str,
            task_ceiling_usd: float | None = None) -> dict:
    """Retain the user's fee decision independently of the task's working input."""
    from . import codex_consult as consult
    root = Path(root).resolve()
    session, lifecycle, reply = _selected_reply(root, user_text=user_text, source=source, quote=quote)
    if _policy_mode(lifecycle) != 'ALLOW':
        raise ValueError('Explicit fee approval applies to the current double-colon choice')
    offered = consult._read(Path(preview_path))
    body = {key: value for key, value in offered.items() if key != 'preview_id'}
    if (offered.get('format') != PREVIEW_FORMAT or offered.get('task') != _task_binding(session)
            or offered.get('preview_id') != consult._hash(consult._json_bytes(body))
            or offered.get('input_ref') != consult._input_ref(lifecycle)
            or offered.get('scope_revision_message_id') != lifecycle.get('latest_revision_message_id', 0)
            or type(offered.get('presented_after_message_id')) is not int
            or offered['presented_after_message_id'] >= reply['message_id']):
        raise ValueError('Approval needs the same task’s earlier scoped preview and a later actual fee reply')
    offered_ceiling = consult._number('offered task ceiling', offered.get('task_ceiling_usd'), positive=True)
    total = offered_ceiling if task_ceiling_usd is None else consult._number('approved task ceiling', task_ceiling_usd)
    limit = read_decision(root, session, lifecycle, 'limit')
    if total > offered_ceiling + 1e-12 or (limit is not None and total > limit['task_ceiling_usd'] + 1e-12):
        raise ValueError('Approved ceiling exceeds the offered envelope or current explicit task limit')
    return _record(root, session, lifecycle, kind='approval', reply=reply, task_ceiling_usd=total,
                   preview=offered)


def record_limit(root: Path, *, user_text: str, source: str, quote: str, task_ceiling_usd: float) -> dict:
    """Record an explicit task-wide ceiling, including zero. This grants no calls."""
    from .codex_consult import _number
    root = Path(root).resolve()
    session, lifecycle, reply = _selected_reply(root, user_text=user_text, source=source, quote=quote)
    return _record(root, session, lifecycle, kind='limit', reply=reply,
                   task_ceiling_usd=_number('explicit task limit', task_ceiling_usd))


def resolve(root: Path, session: Mapping[str, Any], lifecycle: Mapping[str, Any],
            attempt: Mapping[str, Any], facts: Mapping[str, Any], wallet_id: str) -> dict:
    """Derive canonical authority. Caller-supplied facts can only narrow the charge."""
    from .codex_consult import _hash, _json_bytes, _number, _text
    if not codex_collaboration.layered_policy(session['P_run']):
        return dict(facts)
    if not isinstance(facts, Mapping):
        raise ValueError('Current budget facts must be an object')
    wallet_id = _text('shared wallet alias', wallet_id)
    mode = _policy_mode(lifecycle)
    role = attempt.get('participation_role')
    model = attempt.get('collaboration_contract', {}).get('requested_model', '')
    if mode == 'DENY' or role not in ROLES:
        raise ValueError('The current task choice does not authorize this paid Claude role')
    approval = read_decision(root, session, lifecycle, 'approval')
    limit = read_decision(root, session, lifecycle, 'limit')
    decisions = [item for item in (approval, limit) if item is not None]
    fee_message = lifecycle.get('latest_budget_message_id')
    if fee_message is not None and all(item['reply']['message_id'] != fee_message for item in decisions):
        raise ValueError('The latest fee-only decision is not yet recorded; resolve it before paid work')
    caps = [record['task_ceiling_usd'] for record in decisions]
    if facts.get('budget_total_usd') is not None:
        caps.append(_number('narrower caller-supplied task ceiling', facts['budget_total_usd']))
    if mode == 'COUNCIL_ONLY':
        if (role != 'council_member' or not model.startswith('anthropic/')
                or not codex_collaboration.CLAUDE_MODEL.search(model)):
            raise ValueError('Wallet-only authority is for Claude Council members under a single colon')
        policy = lifecycle['claude_policy']
        authority = {'kind': 'SINGLE_COLON_WALLET_ONLY', 'message_id': policy['message_id'],
                     'source_ref': policy['source']['source_ref'], 'source_sha256': policy['source']['sha256']}
    elif mode == 'ALLOW':
        if (approval is None or approval['reply']['message_id'] <= lifecycle.get('latest_claude_revocation_message_id', -1)):
            raise ValueError('Double-colon use needs a scoped cost preview and recorded user budget approval')
        approved = approval['preview']
        if approved['scope_revision_message_id'] != lifecycle.get('latest_revision_message_id', 0):
            raise ValueError('The material task revision requires a fresh scoped cost preview and user approval')
        if (approved['wallet_id'] != wallet_id or not any(item['role'] == role and item['model'] == model
                for item in approved['requests'])):
            raise ValueError('The requested role, model or wallet falls outside the approved budget scope')
        authority = {'kind': 'EXPLICIT_TASK_APPROVAL', 'scope': approved['scope'],
                     'message_id': approval['reply']['message_id'], 'decision_id': approval['decision_id'],
                     'preview_id': approved['preview_id'], 'source_ref': approval['reply']['source']['source_ref'],
                     'source_sha256': approval['reply']['source']['sha256']}
    else:
        raise ValueError('Current task has no valid layered Claude choice')
    ceiling = min(caps) if caps else None
    authority.update(task=_task_binding(session), wallet_id=wallet_id, role=role, model=model,
                     task_ceiling_usd=ceiling, limit_decision_id=None if limit is None else limit['decision_id'])
    return {**facts, 'authorization_ref': 'digr-budget-' + _hash(_json_bytes(authority)),
            'authorization_evidence': authority, 'budget_total_usd': ceiling}
