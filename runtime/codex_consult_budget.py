"""Use task input as authority and the shared ledger as spending evidence."""
from __future__ import annotations

from decimal import Decimal, DecimalException, ROUND_CEILING
from http.client import HTTPException
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request

from . import codex_collaboration, codex_wallet

PREVIEW_FORMAT = 'digr-consult-budget-preview-1'
DECISION_FORMAT = 'digr-consult-budget-decision-1'
ROLES = {'council_member', 'consult_guidance'}
_QUOTE_PLAN = 'Use an explicit --plan with current price and wallet facts.'


def _quote_amount(value: Any) -> Decimal:
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError('A quoted amount must be finite and nonnegative')
    return amount


def _quote_data(opener, resource: str, *, timeout: float, credential: str | None = None) -> Any:
    headers = {'Accept': 'application/json'}
    if credential is not None:
        headers['Authorization'] = 'Bearer ' + credential
    request = Request('https://openrouter.ai/api/v1/' + resource, headers=headers, method='GET')
    try:
        with opener.open(request, timeout=timeout) as response:
            result = json.load(response, parse_float=Decimal)
    except HTTPError as error:
        error.close()
        raise ValueError(f'OpenRouter {resource} read returned HTTP {error.code}. {_QUOTE_PLAN}') from None
    except (OSError, HTTPException, DecimalException, ValueError) as error:
        raise ValueError(f'OpenRouter {resource} read failed ({type(error).__name__}). {_QUOTE_PLAN}') from None
    return result.get('data') if isinstance(result, Mapping) else None


def first_opinion_quote(request: Mapping[str, Any], *, config_path: Path | None = None) -> dict:
    """Quote a prepared text-only exchange in a validated first-opinion line.

    The existing send path checks current authority and reserves against the quoted facts.
    """
    from . import codex_consult as consult

    model, messages, max_tokens = (request.get(key) for key in ('model', 'messages', 'max_tokens'))
    if (not isinstance(model, str) or not isinstance(messages, list) or not messages
            or any(not isinstance(message, Mapping) or not isinstance(message.get('content'), str)
                   for message in messages)
            or type(max_tokens) is not int or max_tokens < 1):
        raise ValueError(f'Automatic pricing requires a prepared text-only first opinion. {_QUOTE_PLAN}')
    try:
        config, credential = consult._config(config_path)
        wallet_id = consult._text('shared wallet_id in the private config', config.get('wallet_id'))
    except (OSError, ValueError, TypeError) as error:
        raise ValueError(f'OpenRouter quote needs the current Consult wallet configuration '
                         f'({type(error).__name__}). {_QUOTE_PLAN}') from None
    endpoint = urlsplit(config['endpoint'])
    if (endpoint.scheme != 'https' or endpoint.netloc.lower() not in {'openrouter.ai', 'openrouter.ai:443'}
            or endpoint.path != '/api/v1/chat/completions' or endpoint.query or endpoint.fragment):
        raise ValueError(f'Automatic pricing requires the official OpenRouter HTTPS chat endpoint. {_QUOTE_PLAN}')
    opener = consult._opener(config)
    timeout = min(config['timeout_seconds'], 15)
    checked_at = consult._now()
    models = _quote_data(opener, 'models', timeout=timeout)
    catalog = models if isinstance(models, list) else []
    matches = [item.get('pricing') for item in catalog if isinstance(item, Mapping) and item.get('id') == model]
    if len(matches) != 1 or not isinstance(matches[0], Mapping):
        raise ValueError(f'OpenRouter did not list one current price for the prepared model. {_QUOTE_PLAN}')
    pricing = matches[0]
    try:
        prompt = _quote_amount(pricing['prompt'])
        completion = max(_quote_amount(pricing['completion']), _quote_amount(pricing.get('internal_reasoning', 0)))
        # The public model listing omits the optional fee when it is absent.
        request_fee = _quote_amount(pricing.get('request', 0))
        prices = {'prompt': float(prompt * 1_000_000), 'completion': float(completion * 1_000_000),
                  'request': float(request_fee)}
        sized_request = {**request, 'provider': {**request['provider'], 'max_price': prices}}
        # The UTF-8 bound covers the entire priced request. The extra tokens
        # allow for provider framing and the roles of every text message.
        input_tokens = len(consult._json_bytes(sized_request)) + 256 + 32 * len(messages)
        cost_bound = prompt * input_tokens + completion * max_tokens + request_fee
    except (KeyError, DecimalException, TypeError, ValueError):
        raise ValueError(f'OpenRouter did not supply usable pricing for the prepared request. {_QUOTE_PLAN}') from None
    if cost_bound > Decimal(str(codex_collaboration.FIRST_OPINION_CEILING_USD)):
        raise ValueError(f'The prepared first opinion exceeds its USD 0.20 ceiling at current prices. {_QUOTE_PLAN}')
    precision = Decimal('0.000001')
    ceiling = float(max(precision, cost_bound.quantize(precision, rounding=ROUND_CEILING)))
    credits = _quote_data(opener, 'credits', timeout=timeout, credential=credential)
    try:
        remaining = max(Decimal(0), _quote_amount(credits['total_credits']) - _quote_amount(credits['total_usage']))
        wallet_remaining = consult._number('remaining OpenRouter credits', float(remaining))
    except (KeyError, DecimalException, TypeError, ValueError):
        raise ValueError(f'OpenRouter did not supply a usable current credit balance. {_QUOTE_PLAN}') from None
    return {'facts': {'model': model, 'checked_at': checked_at, 'pricing_ref': 'OpenRouter GET /api/v1/models',
                      'input_bound_basis': 'Complete text-only UTF-8 request bytes with provider framing allowance',
                      'wallet_id': wallet_id, 'wallet_remaining_usd': wallet_remaining, 'outside_spent_usd': 0,
                      'prompt_usd_per_million': prices['prompt'], 'completion_usd_per_million': prices['completion'],
                      'request_usd': prices['request'], 'input_tokens_upper_bound': input_tokens},
            'ceiling_usd': ceiling}


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


def _production_stage(root: Path, session: Mapping[str, Any], input_ref: Mapping[str, Any], *,
                      production_id: Any, stage: Any, model: str) -> dict:
    from . import codex_production
    from .codex_consult import _text
    if not codex_production.enabled(session['P_run']):
        raise ValueError('Formal production quotes require Stable 1.1 or later')
    if stage not in ('candidate', 'arbitration'):
        raise ValueError('A formal production quote needs the candidate or arbitration stage')
    if not codex_production.claude_model(model):
        raise ValueError('A formal production quote needs a canonical Anthropic Claude model')
    production_id = _text('production_id', production_id)
    record = codex_production.inspect(root, production_id)
    if (record.get('current') is not True or record.get('resolved') is not False
            or record.get('production_id') != production_id or record.get('task_uuid') != session['task_uuid']
            or record.get('P_run') != session['P_run'] or record.get('task_request_sha256') != session['request_sha256']
            or record.get('input_ref') != input_ref):
        raise ValueError('A formal production quote must use a current production scope in this task')
    return {'production_id': production_id, 'stage': stage, 'input_ref': dict(input_ref),
            'scope_sha256': record['scope_sha256']}


def _attempt_production(root: Path, session: Mapping[str, Any], lifecycle: Mapping[str, Any],
                        attempt: Mapping[str, Any], model: str) -> dict | None:
    binding = attempt.get('production')
    if binding is None:
        return None
    from . import codex_production
    from .codex_consult import _input_ref
    if not codex_production.enabled(session['P_run']):
        return None
    if not isinstance(binding, Mapping) or attempt.get('participation_role') != 'consult_guidance':
        raise ValueError('Only formal Consult can use a production budget scope')
    input_ref = _input_ref(lifecycle)
    stage = _production_stage(root, session, input_ref, production_id=binding.get('production_id'),
                              stage=binding.get('stage'), model=model)
    if attempt.get('input_ref') != input_ref or any(binding.get(key) != item for key, item in stage.items()):
        raise ValueError('The prepared formal Consult does not match the current production scope')
    return stage


def preview(root: Path, *, jobs: Sequence[Mapping[str, Any]], task_ceiling_usd: float,
            scope: str, wallet_id: str) -> dict:
    """Price prepared requests and projected Council or formal production work."""
    from . import codex_consult as consult
    root, session, lifecycle = consult._task(root, active=True)
    standing = codex_collaboration.standing_claude_budget_policy(session['P_run'])
    mode = _policy_mode(lifecycle)
    allowed_modes = ('ALLOW', codex_collaboration.COUNCIL_ONLY) if standing else ('ALLOW',)
    if not codex_collaboration.layered_policy(session['P_run']) or mode not in allowed_modes:
        raise ValueError('A budget preview requires a currently allowed Claude layer' if standing else
                         'An approval preview is for a Stable double-colon task')
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
    seen_stages, production_models = set(), {}
    for job in jobs:
        if not isinstance(job, Mapping) or not isinstance(job.get('facts'), Mapping):
            raise ValueError('Every budget preview job needs current pricing and wallet facts')
        production = None
        if 'planned_production' in job:
            planned = job['planned_production']
            if ('exchange_id' in job or 'planned_council_member' in job or not isinstance(planned, Mapping)
                    or set(planned) != {'production_id', 'stage', 'model', 'max_tokens', 'purpose'}):
                raise ValueError('A planned formal production request needs its ID, stage, model, output bound and purpose')
            model = consult._text('planned production model', planned['model'])
            max_tokens = planned['max_tokens']
            if type(max_tokens) is not int or max_tokens < 1:
                raise ValueError('A planned production stage needs a positive output-token bound')
            production = _production_stage(root, session, input_ref, production_id=planned['production_id'],
                                           stage=planned['stage'], model=model)
            request = {'model': model, 'max_tokens': max_tokens}
            role = 'consult_guidance'
            origin = {'request_basis': 'PLANNED_PRODUCTION',
                      'purpose': consult._text('planned production purpose', planned['purpose'])}
        elif 'planned_council_member' in job:
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
            production = _attempt_production(root, session, lifecycle, attempt, request['model'])
        if production is not None:
            production_id, stage = production['production_id'], production['stage']
            if (production_id, stage) in seen_stages:
                raise ValueError('Budget preview counts each formal production stage only once')
            if production_models.setdefault(production_id, request['model']) != request['model']:
                raise ValueError('A production candidate and its arbitration must quote the same Claude model')
            seen_stages.add((production_id, stage))
            origin['production'] = production
        codex_collaboration.require_claude_permission(session['P_run'], request['model'], lifecycle,
            participation_role=role)
        if standing and job['facts'].get('wallet_id', wallet_id) != wallet_id:
            raise ValueError('Budget facts name a different wallet configuration')
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
    # An old approval preview offers a whole affordable envelope. A standing
    # preview tests the requests actually planned against current wallet capacity.
    wallet_check = reserved_upper if standing else remaining
    if reserved_upper > remaining + 1e-12 or wallet_check > safe_available + 1e-12:
        raise ValueError('The combined task envelope exceeds current capacity after known costs and reservations')
    value = {'format': PREVIEW_FORMAT, 'task': _task_binding(session),
             'presented_after_message_id': lifecycle['message_id'], 'input_ref': input_ref,
             'scope_revision_message_id': lifecycle.get('latest_revision_message_id', 0),
             'created_at': consult._now(), 'wallet_id': wallet_id, 'scope': scope,
             'task_ceiling_usd': total, 'remaining_envelope_usd': remaining,
             'available_to_reserve_usd': safe_available, 'prepared_reservation_upper_usd': reserved_upper,
             'requests': rows, 'basis': 'read-only estimate using actual or projected bounded work and supplied provider facts'}
    if codex_collaboration.double_colon_layer_budget_policy(session['P_run']):
        layer_budgets = {}
        # Layer availability comes from the same task rows for the whole preview.
        remaining_by_layer = positions[0]['layer_available_before_usd']
        for layer, ceiling in codex_collaboration.DOUBLE_COLON_LAYER_CEILINGS_USD.items():
            if standing and mode == codex_collaboration.COUNCIL_ONLY and layer != 'COUNCIL':
                continue
            proposed = sum(row['reservation_ceiling_usd'] for row in rows
                           if codex_collaboration.CLAUDE_LAYER_BY_ROLE[row['role']] == layer)
            available = remaining_by_layer[layer]
            if proposed > available + 1e-12:
                raise ValueError(f'The proposed {layer} work exceeds its remaining layer budget (USD {ceiling:.2f} per task)')
            layer_budgets[layer] = {'ceiling_usd': ceiling, 'remaining_usd': available,
                                    'proposed_reservation_usd': proposed}
        value['layer_budgets'] = layer_budgets
    return {**value, 'preview_id': consult._hash(consult._json_bytes(value))}


def _selected_reply(root: Path, *, user_text: str, source: str, quote: str,
                    for_limit: bool = False) -> tuple[dict, dict, dict]:
    from .codex_consult import _task, _text
    from .codex_lifecycle import content_message, require_open_decision
    root, session, lifecycle = _task(root, active=True)
    if not codex_collaboration.layered_policy(session['P_run']):
        raise ValueError('Recorded budget decisions require a frozen Stable task')
    standing = codex_collaboration.standing_claude_budget_policy(session['P_run'])
    if standing and not for_limit:
        raise ValueError('The current choice provides standing layer authority; use budget-limit for an explicit task limit')
    require_open_decision(root, user_text=user_text, source=source)
    current = lifecycle['current_message']
    action = current.get('handling', {}).get('action')
    work_limit = (standing and for_limit and current['id'] == content_message(lifecycle)['id']
                  and action in {'invoke', 'continue', 'revise', 'resume'})
    if action != 'budget' and not work_limit:
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
    session, lifecycle, reply = _selected_reply(root, user_text=user_text, source=source, quote=quote,
                                                for_limit=True)
    return _record(root, session, lifecycle, kind='limit', reply=reply,
                   task_ceiling_usd=_number('explicit task limit', task_ceiling_usd))


def resolve(root: Path, session: Mapping[str, Any], lifecycle: Mapping[str, Any],
            attempt: Mapping[str, Any], facts: Mapping[str, Any], wallet_id: str, *,
            ceiling_usd: float | None = None, max_tokens: int | None = None) -> dict:
    """Derive canonical authority. Caller-supplied facts can only narrow the charge."""
    from .codex_consult import _hash, _input_ref, _json_bytes, _number, _text
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
    standing = codex_collaboration.standing_claude_budget_policy(session['P_run'])
    scope = attempt.get('council_scope')
    purpose = scope.get('purpose') if isinstance(scope, Mapping) else None
    first_opinion = (codex_collaboration.first_opinion_policy(session['P_run'])
                     and purpose == codex_collaboration.FIRST_OPINION_PURPOSE)
    first_return = standing and purpose == codex_collaboration.FIRST_OPINION_NATIVE_WORK_RETURN_PURPOSE
    if first_opinion or first_return:
        codex_collaboration.require_first_opinion_permission(lifecycle)
    approval = None if standing else read_decision(root, session, lifecycle, 'approval')
    limit = read_decision(root, session, lifecycle, 'limit')
    decisions = [item for item in (approval, limit) if item is not None]
    fee_message = lifecycle.get('latest_budget_message_id')
    if fee_message is not None and not any(
        item['reply']['message_id'] == fee_message or (standing and item['reply']['message_id'] > fee_message)
        for item in decisions
    ):
        raise ValueError('The latest fee-only decision is not yet recorded; resolve it before paid work')
    caps = [record['task_ceiling_usd'] for record in decisions]
    if facts.get('budget_total_usd') is not None:
        caps.append(_number('narrower caller-supplied task ceiling', facts['budget_total_usd']))
    if standing:
        codex_collaboration.require_claude_permission(session['P_run'], model, lifecycle, participation_role=role)
        if facts.get('wallet_id', wallet_id) != wallet_id:
            raise ValueError('Budget facts name a different wallet configuration')
        input_ref = _input_ref(lifecycle)
        if attempt.get('input_ref') != input_ref:
            raise ValueError('New user input supersedes this paid Claude scope; prepare a current exchange')
        policy = lifecycle['claude_policy']
        layer = codex_collaboration.CLAUDE_LAYER_BY_ROLE[role]
        authority = {'kind': 'STANDING_CLAUDE_LAYER_LIMIT', 'mode': mode, 'message_id': policy['message_id'],
                     'source_ref': policy['source']['source_ref'], 'source_sha256': policy['source']['sha256'],
                     'input_ref': input_ref, 'layer': layer,
                     'layer_ceiling_usd': codex_collaboration.DOUBLE_COLON_LAYER_CEILINGS_USD[layer]}
        production = _attempt_production(root, session, lifecycle, attempt, model)
        if production is not None:
            authority['production'] = production
        if first_opinion or first_return:
            authority['purpose'] = purpose
        if first_return:
            authority['first_opinion_exchange_id'] = _text('the original first-opinion exchange',
                                                           scope.get('first_opinion_exchange_id'))
    elif mode == 'COUNCIL_ONLY':
        if (role != 'council_member' or not model.startswith('anthropic/')
                or not codex_collaboration.CLAUDE_MODEL.search(model)):
            raise ValueError('Wallet-only authority is for Claude Council members under a single colon')
        policy = lifecycle['claude_policy']
        authority = {'kind': 'SINGLE_COLON_WALLET_ONLY', 'message_id': policy['message_id'],
                     'source_ref': policy['source']['source_ref'], 'source_sha256': policy['source']['sha256']}
        if first_opinion:
            if facts.get('wallet_id', wallet_id) != wallet_id:
                raise ValueError('The first-opinion balance was quoted for a different wallet configuration')
            reservation = _number('first-opinion reservation ceiling', ceiling_usd, positive=True)
            if reservation > codex_collaboration.FIRST_OPINION_CEILING_USD:
                raise ValueError('The first-opinion reservation exceeds its USD 0.20 ceiling')
            if caps and reservation > min(caps) + 1e-12:
                raise ValueError('The first-opinion reservation exceeds the current task budget ceiling')
            authority['purpose'] = codex_collaboration.FIRST_OPINION_PURPOSE
    elif mode == 'ALLOW':
        if (approval is None or approval['reply']['message_id'] <= lifecycle.get('latest_claude_revocation_message_id', -1)):
            raise ValueError('Double-colon use needs a scoped cost preview and recorded user budget approval')
        approved = approval['preview']
        if approved['scope_revision_message_id'] != lifecycle.get('latest_revision_message_id', 0):
            raise ValueError('The material task revision requires a fresh scoped cost preview and user approval')
        production = _attempt_production(root, session, lifecycle, attempt, model)
        covered = [item for item in approved['requests'] if item['role'] == role and item['model'] == model
                   and item.get('production') == production]
        if approved['wallet_id'] != wallet_id or not covered:
            if production is not None:
                raise ValueError('The formal production stage, scope, model or wallet falls outside the approved budget scope')
            raise ValueError('The requested role, model or wallet falls outside the approved budget scope')
        authority = {'kind': 'EXPLICIT_TASK_APPROVAL', 'scope': approved['scope'],
                     'message_id': approval['reply']['message_id'], 'decision_id': approval['decision_id'],
                     'preview_id': approved['preview_id'], 'source_ref': approval['reply']['source']['source_ref'],
                     'source_sha256': approval['reply']['source']['sha256']}
        if production is not None:
            quoted = covered[0]
            actual_ceiling = _number('actual formal production reservation ceiling', ceiling_usd, positive=True)
            if (type(max_tokens) is not int or not 1 <= max_tokens <= quoted['max_output_tokens']
                    or actual_ceiling > quoted['reservation_ceiling_usd'] + 1e-12):
                raise ValueError('The actual output or reservation bound exceeds the approved formal production stage quote')
            authority['production'] = production
    else:
        raise ValueError('Current task has no valid layered Claude choice')
    ceiling = min(caps) if caps else None
    authority.update(task=_task_binding(session), wallet_id=wallet_id, role=role, model=model,
                     task_ceiling_usd=ceiling, limit_decision_id=None if limit is None else limit['decision_id'])
    return {**facts, 'authorization_ref': 'digr-budget-' + _hash(_json_bytes(authority)),
            'authorization_evidence': authority, 'budget_total_usd': ceiling}
