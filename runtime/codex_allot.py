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


def _select_legacy(block: Mapping, capabilities: Mapping) -> dict:
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


SOL_MODELS = ('gpt-6.1-sol', 'gpt-6.2-sol')
# Preserve the 0.17 policy fields, which are part of persisted selection hashes.
POLICY = {'profile': 'sol-max-feedback', 'primary_models': list(SOL_MODELS),
          'default_effort': 'max', 'speed': 'standard',
          'downshift': 'only explicitly selected, large, fully specified, non-intellectual controlled repetitive labor',
          'escalation': 'concrete Max capability gap or substantive task failure feedback; no fixed stronger-model seats'}
_PRIMARY_DEFAULT_VERSION = (0, 18, 0)
# Pinned engineering default: logic-first architecture fit and existing Claude
# guidance; local sample token counts do not establish subscription efficiency.
CANDIDATE_DEFAULT_PRIMARY_MODEL = 'gpt-6.2-sol'


def _anchor(lifecycle):
    from .codex_lifecycle import _input_ref
    return _input_ref(lifecycle['current_message'])


def _pin_version(p_run):
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)@', p_run)
    return tuple(map(int, match.groups())) if match else (0, 0, 0)


def _candidate_policy():
    if CANDIDATE_DEFAULT_PRIMARY_MODEL not in SOL_MODELS:
        raise ValueError('the pinned Allot policy needs a supported default_primary_model')
    return {**POLICY, 'primary_models': list(SOL_MODELS),
            'default_primary_model': CANDIDATE_DEFAULT_PRIMARY_MODEL}


def _policy_for_pin(p_run, *, explicit=False):
    version = _pin_version(p_run)
    if version >= _PRIMARY_DEFAULT_VERSION:
        return _candidate_policy()
    if explicit or version >= (0, 17, 0):
        return {**POLICY, 'primary_models': list(SOL_MODELS)}
    return {'profile': 'legacy'}


def current_policy(root: Path) -> dict:
    """Read the immutable task pin or an explicit, source-bound task override."""
    from .codex_session import _session
    root, session = _session(root)
    p_run = session['P_run']
    path = root / 'allot' / 'policy.json'
    if path.exists():
        value = json.loads(path.read_text(encoding='utf-8'))
        if value.get('P_run') != p_run or value.get('policy') != _policy_for_pin(p_run, explicit=True):
            raise ValueError('Allot policy does not match this task or supported policy')
        return value
    return {'format': 'digr-native-allot-policy-1', 'P_run': p_run, 'revision': 0,
            'policy': _policy_for_pin(p_run), 'source': 'PINNED_PROFILE_DEFAULT'}


def _policy_hash(policy):
    return sha256(_json(policy)).hexdigest()


def set_policy(root: Path, value: Mapping) -> dict:
    """Persist the user's actual current choice, never infer it from free text."""
    root, session, lifecycle = _task(root)
    if value.get('profile') != POLICY['profile']:
        raise ValueError('supported explicit policy is sol-max-feedback')
    reason = value.get('reason')
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('record the actual user policy decision and its consequence')
    source = lifecycle['current_message']['source']
    if value.get('source_ref') != source['source_ref']:
        raise ValueError('policy must bind the actual current user source')
    implementation_pin = value.get('implementation_pin')
    implementation_root = Path(__file__).resolve().parents[1]
    implementation_version = (implementation_root / 'codex' / 'VERSION').read_text(encoding='utf-8').strip()
    if implementation_pin is not None and (not isinstance(implementation_pin, str)
            or not re.fullmatch(re.escape(implementation_version) + r'@[a-f0-9]{40}', implementation_pin)):
        raise ValueError('implementation_pin must identify this actual Allot version and immutable commit')
    implementation = {'version': implementation_version, 'pin': implementation_pin,
                      'root': implementation_root.as_posix(),
                      'cli': (implementation_root / 'tools' / 'codex.py').as_posix(),
                      'scope': 'selected implementation locator; an old frozen CLI cannot automatically acquire new behavior'}
    previous = current_policy(root)
    if (previous.get('input_ref') == _anchor(lifecycle) and previous.get('reason') == reason
            and previous.get('implementation') == implementation):
        return previous
    record = {'format': 'digr-native-allot-policy-1', 'P_run': session['P_run'],
              'revision': previous['revision'] + 1, 'policy': _policy_for_pin(session['P_run'], explicit=True),
              'input_ref': _anchor(lifecycle), 'source': source['source_ref'],
              'reason': reason, 'implementation': implementation,
              'created_at': datetime.now(timezone.utc).isoformat()}
    path = root / 'allot' / 'policy.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path.parent / 'policy-history' / (str(record['revision']) + '.json'), record)
    from .codex_session import _write_json
    _write_json(path, record)
    return record


def _controlled_labor(block):
    labor = block.get('controlled_labor')
    if not isinstance(labor, Mapping) or block.get('fully_specified') is not True:
        return False
    # These are operator-supplied work facts, not proof produced by this helper.
    if any(labor.get(key) is not True for key in
           ('large_batch', 'repetitive', 'non_intellectual', 'controlled')):
        return False
    return all(isinstance(labor.get(key), str) and labor[key].strip()
               for key in ('scope_ref', 'validation_ref'))


def _feedback(block):
    feedback = block.get('feedback')
    if feedback is None:
        return None
    if not isinstance(feedback, Mapping) or feedback.get('category') not in {
            'quality', 'capability', 'tool', 'network', 'permission', 'input', 'budget'}:
        raise ValueError('feedback needs a specific intellectual or execution failure category')
    if any(not isinstance(feedback.get(key), str) or not feedback[key].strip()
           for key in ('evidence_ref', 'detail')):
        raise ValueError('feedback needs actual failure evidence and consequence')
    return dict(feedback)


def _escalation(block):
    escalation = block.get('escalation')
    if not isinstance(escalation, Mapping):
        return None
    if escalation.get('trigger') not in {'max_capability_insufficient', 'task_failure_feedback'}:
        raise ValueError('stronger model needs a concrete capability gap or substantive failure trigger')
    if escalation.get('source_model') not in SOL_MODELS or escalation.get('source_effort') != 'max':
        raise ValueError('stronger model escalation must explain the Sol Max capability boundary')
    if any(not isinstance(escalation.get(key), str) or not escalation[key].strip()
           for key in ('evidence_ref', 'reason')):
        raise ValueError('stronger model escalation needs actual source and reason')
    if not isinstance(block.get('unresolved'), list) or not block['unresolved'] or any(
            not isinstance(item, str) or not item.strip() for item in block['unresolved']):
        raise ValueError('escalation needs the concrete unresolved task, not a generic difficult label')
    feedback = _feedback(block)
    if (feedback and feedback['category'] not in {'quality', 'capability'}
            and feedback['evidence_ref'] == escalation['evidence_ref']):
        raise ValueError('the same execution fault cannot also stand as intellectual insufficiency evidence')
    if escalation['trigger'] == 'task_failure_feedback':
        if not feedback or feedback['category'] not in {'quality', 'capability'}:
            raise ValueError('tool, network, permission, input and budget failures do not establish model insufficiency')
    return dict(escalation)


def select(block: Mapping, capabilities: Mapping, *, policy: Mapping | None = None) -> dict:
    """Sol Max is the intellectual baseline; effort is independent of DIGR tier."""
    policy = POLICY if policy is None else policy
    if policy.get('profile') == 'legacy':
        return _select_legacy(block, capabilities)
    if policy != POLICY and policy != _candidate_policy():
        raise ValueError('unsupported Allot selection policy')
    uses_default = 'model' not in block and 'default_primary_model' in policy
    model = block.get('model', policy.get('default_primary_model'))
    supported = catalogue(capabilities).get(model)
    if not supported:
        if uses_default:
            raise ValueError(f'pinned default_primary_model {model!r} is absent from the supplied host catalogue')
        raise ValueError('requested model is absent from the supplied host catalogue')
    kind, evidence = block.get('kind'), block.get('evidence')
    if kind not in {'routine', 'maintenance', 'response', 'architecture', 'breakthrough'}:
        raise ValueError('kind must identify the meaningful work block')
    if not isinstance(evidence, list) or not evidence or any(
            not isinstance(item, str) or not item.strip() for item in evidence):
        raise ValueError('selection needs actual work/evidence, not a bare difficulty label')
    feedback = _feedback(block)
    escalation = _escalation(block)
    if model not in SOL_MODELS and escalation is None:
        raise ValueError('ordinary intellectual work uses 6.1 Sol/max or 6.2 Sol/max; stronger models need actual escalation evidence')
    requested = block.get('requested_effort', 'max')
    if requested not in EFFORTS:
        raise ValueError('unsupported explicitly requested effort')
    desired = requested
    intellectual_failure = bool(feedback and feedback['category'] in {'quality', 'capability'})
    if intellectual_failure and EFFORTS.index(desired) < EFFORTS.index('max'):
        desired = 'max'
    controlled = _controlled_labor(block)
    for field in ('current_effort', 'minimum_effort'):
        value = block.get(field)
        if value is not None and value not in EFFORTS:
            raise ValueError('unsupported ' + field)
    floor = block.get('minimum_effort')
    if floor is not None and EFFORTS.index(desired) < EFFORTS.index(floor):
        desired = floor
    current = block.get('current_effort')
    if current is not None and EFFORTS.index(desired) < EFFORTS.index(current) and block.get('allow_downshift') is not True:
        desired = current
    if EFFORTS.index(desired) < EFFORTS.index('max'):
        if model not in SOL_MODELS or not controlled or block.get('allow_downshift') is not True:
            raise ValueError('every below-Max selection needs explicit controlled large-batch non-intellectual repetitive labor, its scope/validator, and downshift choice')
    if desired == 'ultra' and (requested != 'ultra' or escalation is None):
        raise ValueError('Ultra requires explicit selection and concrete Max insufficiency, not an automatic floor/current promotion')
    if desired not in supported:
        raise ValueError('selected effort is unavailable; no silent substitution or downshift')
    return {'model': model, 'effort': desired,
            'host_payload': {'fork_turns': 'none', 'model': model, 'reasoning_effort': desired},
            'selection_basis': {'kind': kind, 'evidence': evidence, 'policy': policy['profile'],
                                'controlled_labor': dict(block['controlled_labor']) if controlled else None,
                                'labor_scope': _labor_scope(block),
                                'feedback': feedback, 'escalation': escalation,
                                'explicit_effort': block.get('requested_effort'),
                                'restored_to_max': intellectual_failure and desired == 'max'},
            'applied': False,
            'scope': 'native host must apply this payload; policy/selection cannot switch Main or authenticate execution'}


def _labor_scope(block):
    value = block.get('controlled_labor')
    if not isinstance(value, Mapping) or any(not isinstance(value.get(key), str) or not value[key].strip()
                                             for key in ('scope_ref', 'validation_ref')):
        return None
    return {key: value[key] for key in ('scope_ref', 'validation_ref')}


def _failed_attempt(root, selection):
    escalation = selection.get('selection_basis', {}).get('escalation')
    if not escalation or escalation['trigger'] != 'task_failure_feedback':
        return
    block_id = escalation.get('source_block_id', '')
    if not _ID.fullmatch(block_id):
        raise ValueError('failure escalation needs an actual same-task source_block_id')
    previous = json.loads((root / 'allot' / block_id / 'selection.json').read_text(encoding='utf-8'))
    observed = json.loads((root / 'allot' / block_id / 'observation.json').read_text(encoding='utf-8'))
    if (observed.get('actual_model') != escalation['source_model']
            or observed.get('actual_effort') != 'max' or previous.get('block_id') != block_id):
        raise ValueError('the referenced attempt was not actually the declared Sol Max execution')
    from .codex_allot_labor import load_feedback
    feedback = load_feedback(root, escalation.get('feedback_id', ''))
    if (feedback.get('block_id') != block_id or feedback.get('feedback', {}).get('category') not in {'quality', 'capability'}
            or feedback['feedback']['evidence_ref'] != selection['selection_basis']['feedback']['evidence_ref']):
        raise ValueError('escalation feedback does not belong to that real failed attempt')


def plan(root: Path, block: Mapping, capabilities: Mapping, *, catalogue_ref: str) -> dict:
    root, session, lifecycle = _task(root)
    block_id = block.get('block_id', '')
    if not _ID.fullmatch(block_id):
        raise ValueError('a stable safe block_id is required')
    if not isinstance(catalogue_ref, str) or not catalogue_ref.strip():
        raise ValueError('actual capability source reference is required')
    policy = current_policy(root)
    modern = policy['policy']['profile'] != 'legacy'
    effective_block = dict(block)
    hold = None
    if modern:
        from .codex_allot_labor import status as labor_status
        hold = labor_status(root, _labor_scope(block))
        requested = effective_block.get('requested_effort', 'max')
        if hold['blocked'] and requested in EFFORTS and EFFORTS.index(requested) < EFFORTS.index('max'):
            effective_block['requested_effort'] = 'max'
    selection = select(effective_block, capabilities, policy=policy['policy'])
    if modern:
        selection['selection_basis']['explicit_effort'] = block.get('requested_effort')
        selection['selection_basis']['labor_hold'] = hold if hold['blocked'] else None
        selection['selection_basis']['labor_revision'] = hold.get('feedback_revision')
        _failed_attempt(root, selection)
    record = {'format': 'digr-native-allot-2' if modern else 'digr-native-allot-1', 'P_run': session['P_run'],
              'block_id': block_id, 'input_ref': _anchor(lifecycle) if modern else lifecycle['current_message']['source']['sha256'],
              'block_sha256': sha256(_json(block)).hexdigest(),
              'catalogue_sha256': sha256(_json(catalogue(capabilities))).hexdigest(),
              'catalogue_ref': catalogue_ref, 'created_at': datetime.now(timezone.utc).isoformat(),
              **selection}
    if modern:
        record.update(policy_revision=policy['revision'], policy_sha256=_policy_hash(policy))
        record['proposed_host_payload'] = record.pop('host_payload')
        record['requires_ready'] = True
    path = root / 'allot' / block_id / 'selection.json'
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        if any(previous.get(k) != record.get(k) for k in
               ('block_sha256', 'input_ref', 'catalogue_sha256', 'policy_sha256')):
            raise ValueError('block selection changed; use a new block_id for the new decision')
        return previous
    _write(path, record)
    return record


def ready(root: Path, block_id: str, capabilities: Mapping) -> dict:
    """Readiness immediately before native dispatch, not an atomic host gate."""
    root, session, lifecycle = _task(root)
    if not _ID.fullmatch(block_id):
        raise ValueError('invalid block id')
    selected = json.loads((root / 'allot' / block_id / 'selection.json').read_text(encoding='utf-8'))
    if not _selection_current(selected, lifecycle, current_policy(root)):
        raise ValueError('selection was superseded; plan the current affected work instead')
    if (root / 'allot' / block_id / 'observation.json').exists():
        raise ValueError('this block already has an execution observation; a new attempt needs a new block')
    if selected['effort'] not in catalogue(capabilities).get(selected['model'], []):
        raise ValueError('selected model/effort is no longer available in the actual host catalogue')
    if selected.get('format') == 'digr-native-allot-2':
        from .codex_allot_labor import status as labor_status
        scope = selected['selection_basis'].get('labor_scope')
        status = labor_status(root, scope)
        if EFFORTS.index(selected['effort']) < EFFORTS.index('max') and (
                status['blocked'] or selected['selection_basis'].get('labor_revision') != status['feedback_revision']):
            raise ValueError('the controlled batch changed its evidence or eligibility; plan affected remaining work again')
        _failed_attempt(root, selected)
    return {'format': 'digr-native-allot-ready-1', 'block_id': block_id,
            'input_ref': selected['input_ref'], 'policy_sha256': selected.get('policy_sha256'),
            'host_payload': {'fork_turns': 'none', 'model': selected['model'], 'reasoning_effort': selected['effort']},
            'applied': False,
            'scope': 'read-only dispatch readiness; host must still honor input/stop changes before its actual native call'}


def observe(root: Path, block_id: str, observation: Mapping) -> dict:
    # New-policy observations record already performed facts, even if a DO,
    # pause or close has superseded permission to dispatch the old selection.
    from .codex_session import _session
    from .codex_lifecycle import load_lifecycle
    root, session = _session(root)
    lifecycle = load_lifecycle(root)
    if not _ID.fullmatch(block_id):
        raise ValueError('invalid block id')
    selected = json.loads((root / 'allot' / block_id / 'selection.json').read_text(encoding='utf-8'))
    modern = selected.get('format') == 'digr-native-allot-2'
    if modern and set(observation) - {'model', 'effort', 'source_ref', 'feedback'}:
        raise ValueError('unsupported observation fields; record actual failure through the explicit feedback field or operation')
    if not modern:
        _task(root)  # Preserve the old pin's original observation contract.
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
    if modern and path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        if any(previous.get(key) != record[key] for key in ('actual_model', 'actual_effort', 'source_ref')):
            raise ValueError('existing observation differs; preserve the actual fact and use a new block')
        submitted_feedback = _feedback({'feedback': observation.get('feedback')})
        if previous.get('feedback') != submitted_feedback:
            raise ValueError('later feedback needs the explicit feedback operation; do not rewrite an execution observation')
        if submitted_feedback is not None:
            from .codex_allot_labor import record_feedback as save_feedback
            save_feedback(root, selected, submitted_feedback, previous['observed_input_ref'])
        return previous
    if modern:
        record.update(superseded=not _selection_current(selected, lifecycle, current_policy(root)),
                      observed_input_ref=_anchor(lifecycle),
                      execution_authorization=False)
        if observation.get('feedback') is not None:
            record['feedback'] = _feedback({'feedback': observation['feedback']})
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != record:
            raise ValueError('existing observation differs; preserve it and use a new block')
    else:
        _write(path, record)
    if modern and observation.get('feedback') is not None:
        from .codex_allot_labor import record_feedback as save_feedback
        save_feedback(root, selected, record['feedback'], record['observed_input_ref'])
    return record


def record_feedback(root: Path, block_id: str, value: Mapping) -> dict:
    from .codex_session import _session
    from .codex_lifecycle import load_lifecycle
    from .codex_allot_labor import record_feedback as save_feedback
    root, _ = _session(root)
    if not _ID.fullmatch(block_id):
        raise ValueError('invalid source block id')
    selected = json.loads((root / 'allot' / block_id / 'selection.json').read_text(encoding='utf-8'))
    if selected.get('format') != 'digr-native-allot-2':
        raise ValueError('legacy selections retain their original feedback contract')
    feedback = _feedback({'feedback': value})
    if feedback is None:
        raise ValueError('actual feedback is required')
    return save_feedback(root, selected, feedback, _anchor(load_lifecycle(root)))


def resolve_labor(root: Path, value: Mapping) -> dict:
    root, _, lifecycle = _task(root)
    from .codex_allot_labor import resolve
    block_id = value.get('solver_block_id', '')
    if not _ID.fullmatch(block_id):
        raise ValueError('resolution needs its actual solver block')
    selected = json.loads((root / 'allot' / block_id / 'selection.json').read_text(encoding='utf-8'))
    observed = json.loads((root / 'allot' / block_id / 'observation.json').read_text(encoding='utf-8'))
    scope = selected['selection_basis'].get('labor_scope')
    if not scope:
        raise ValueError('solver needs the actual affected labor scope, without claiming it is mechanical')
    if not _selection_current(selected, lifecycle, current_policy(root)) and value.get('current_scope') != scope:
        raise ValueError('reusing an earlier solver needs explicit current adoption of the unchanged scope and validation; this does not authorize redispatch')
    return resolve(root, scope, value, selected, observed, _anchor(lifecycle))


def _selection_current(selected, lifecycle, policy):
    if selected.get('format') == 'digr-native-allot-2':
        same_input = selected['input_ref'] == _anchor(lifecycle)
        same_policy = selected.get('policy_sha256') == _policy_hash(policy)
    else:
        same_input = selected['input_ref'] == lifecycle['current_message']['source']['sha256']
        same_policy = policy['policy']['profile'] == 'legacy'
    return (same_input and same_policy and lifecycle['status'] == 'ACTIVE'
            and lifecycle['handled_message_id'] == lifecycle['message_id'])


def context_summary(root: Path, *, limit: int = 16) -> dict:
    """Read safe common allocation metadata, never another actor's research."""
    from .codex_session import _session
    from .codex_lifecycle import load_lifecycle
    root, _ = _session(root)
    lifecycle = load_lifecycle(root)
    policy = current_policy(root)
    common = None if policy['policy']['profile'] == 'legacy' else {
        **policy['policy'], 'revision': policy['revision']}
    if common is not None and policy.get('implementation'):
        common['implementation'] = policy['implementation']
    if type(limit) is not int or not 1 <= limit <= 256:
        raise ValueError('summary limit must be between 1 and 256')
    rows = []
    for path in sorted((root / 'allot').glob('*/selection.json')):
        selection = json.loads(path.read_text(encoding='utf-8'))
        observed = path.with_name('observation.json')
        observation = json.loads(observed.read_text(encoding='utf-8')) if observed.exists() else None
        now_current = _selection_current(selection, lifecycle, policy)
        observation_summary = ({key: observation.get(key) for key in
                                ('actual_model', 'actual_effort', 'matches_selection', 'superseded')}
                               if observation else None)
        if observation_summary is not None and selection.get('format') == 'digr-native-allot-2':
            observation_summary['superseded_at_observation'] = observation.get('superseded')
            observation_summary['superseded'] = not now_current
        labor = {'scope_key': None, 'blocked': False, 'feedback_ids': [], 'feedback_revision': None}
        if selection.get('format') == 'digr-native-allot-2':
            from .codex_allot_labor import status as labor_status
            labor = labor_status(root, selection.get('selection_basis', {}).get('labor_scope'))
        needs_labor_replan = (EFFORTS.index(selection['effort']) < EFFORTS.index('max')
                              and labor['scope_key'] is not None and (
                                  labor['blocked'] or selection.get('selection_basis', {}).get('labor_revision') != labor['feedback_revision']))
        rows.append({'block_id': selection['block_id'], 'model': selection['model'],
                     'effort': selection['effort'], 'policy_revision': selection.get('policy_revision'),
                     'current': now_current, 'observation': observation_summary,
                     'labor_scope_key': labor['scope_key'], 'labor_blocked': labor['blocked'],
                     'unresolved_labor_feedback_count': len(labor['feedback_ids']),
                     'labor_replan_required': needs_labor_replan})
    rows.sort(key=lambda row: (not (row['observation'] and row['observation'].get('matches_selection') is False),
                              not row['labor_replan_required'], row['observation'] is not None,
                              not row['current'], row['block_id']))
    pending = sum(row['observation'] is None for row in rows)
    total = len(rows)
    return {'format': 'digr-native-allot-context-1', 'policy': common, 'selections': rows[:limit],
            'total_selections': total, 'omitted_selections': max(total - limit, 0),
            'unobserved_selections': pending,
            'mismatched_observations': sum(bool(row['observation'] and row['observation'].get('matches_selection') is False) for row in rows),
            'labor_replan_required_count': sum(row['labor_replan_required'] for row in rows),
            'scope': 'shared policy and execution metadata only; selection is not execution or authorization'}


def inspect(root: Path) -> dict:
    from .codex_session import _session
    root, session = _session(root)
    rows = []
    for path in sorted((root / 'allot').glob('*/selection.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        if row.get('format') == 'digr-native-allot-2':
            if 'host_payload' in row:
                row['proposed_host_payload'] = row.pop('host_payload')
            row['requires_ready'] = True
        observation = path.with_name('observation.json')
        row['observation'] = json.loads(observation.read_text(encoding='utf-8')) if observation.exists() else None
        rows.append(row)
    result = {'selections': rows, 'automatic_model_calls': 0}
    if _pin_version(session['P_run']) >= _PRIMARY_DEFAULT_VERSION:
        result['policy'] = current_policy(root)
    return result
