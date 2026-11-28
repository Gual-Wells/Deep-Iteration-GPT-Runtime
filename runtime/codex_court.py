"""Source-bound Max hearings, not an actor scheduler or a semantic judge.

The host supplies real dispatches, public statements and a judge's reasons.
Independent execution, reading, completion and judgments remain HOST_ASSERTED.
This helper checks identities, provenance, current bytes and the return path;
it never invents an accusation, performs rework or generates an acquittal.
"""
from __future__ import annotations

from datetime import datetime
from functools import wraps
from hashlib import sha256
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping

from . import codex_cc
from .codex_lifecycle import load_lifecycle, require_active
from .codex_session import (
    _effective_main_target, _parameters, _read_json, _session, _write_json, court_mode_parameter,
)
from .validation import require_binary, require_nonempty_text, require_nonnegative_int

FORMAT = 'digr-codex-court-1'
LEGACY_ROLES = ('defendant', 'judge', 'prosecutor', 'lawyer', 'monitor')
ROLES = ('defendant', 'judge', 'prosecutor', 'prosecution_lawyer', 'defence_lawyer', 'black_police', 'clerk')
_INTENT_FIELDS = ('extracted_intent', 'interpretation', 'goal_and_result_tendencies',
                  'proposal_maintenance_execution_judgment', 'defaults_and_omissions', 'conclusion')
OUTCOMES = ('ACQUITTED', 'IMMATERIAL_ERROR', 'REEXECUTE', 'INCOMPLETE')
PARAMETERS = ('N', 'T', 'R', 'B', 'S', 'D', 'V', 'L', 'M', 'F', 'X')
_LINE_PARAMETERS = frozenset({'N', 'T', 'R', 'B', 'S', 'D', 'V', 'L'})
_LEGAL_BASES = {'REQUIREMENT', 'LOGIC', 'IMPLEMENTATION', 'PRODUCT', 'PERMISSION', 'PROTOCOL'}
_SCOPE = 'HOST_ASSERTED actors, reading, execution and judicial reasons; structural/source checks only'
_PARTY_ROLES = ('defendant', 'prosecution_lawyer', 'defence_lawyer')


def _efficient(root: Path) -> bool:
    return court_mode_parameter(_session(root)[1]['P_run'])


def _efficient_hearing(hearing: dict) -> bool:
    return court_mode_parameter(hearing.get('material', {}).get('P_run', ''))


def _parameter_names(root: Path) -> tuple[str, ...]:
    from .codex_collaboration import u0_council_parameter
    p_run = _session(root)[1]['P_run']
    names = (*PARAMETERS, 'C') if court_mode_parameter(p_run) else PARAMETERS
    return (*names, 'U') if u0_council_parameter(p_run) else names


def enabled(p_run: str) -> bool:
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(match and tuple(map(int, match.groups())) >= (1, 5, 0))


def _corrected(root: Path) -> bool:
    """Seven actual roles apply to new pins, never reinterpret a 1.5.0 case."""
    version = _session(root)[1]['P_run'].split('@', 1)[0]
    return tuple(map(int, version.split('.'))) >= (1, 5, 1)


def _continuous_prosecution(root: Path) -> bool:
    """Do not retroactively change hearings frozen before continuous review."""
    version = _session(root)[1]['P_run'].split('@', 1)[0]
    return tuple(map(int, version.split('.'))) >= (1, 5, 2)


def _cc_writer(function):
    """Serialize court mutations on pins with independent role intervention."""
    @wraps(function)
    def write(root: Path, *args, **kwargs):
        root, metadata = _session(root)
        if not codex_cc.enabled(metadata['P_run']):
            return function(root, *args, **kwargs)
        from .codex_council import _writer
        folder = root / 'court'
        if folder.resolve() != folder:
            raise ValueError('court directory escapes or aliases its task')
        with _writer(folder):
            return function(root, *args, **kwargs)
    return write


def _cc_pending(hearing: dict) -> list[dict]:
    return [item for item in hearing.get('cc_interventions', [])
            if item['resolution'] is None and 'transferred_to_cycle' not in item]


def _cc_admission_due(hearing: dict) -> list[dict]:
    return [item for item in hearing.get('cc_interventions', []) if item['resolution']
            and item['resolution']['outcome'] == 'REPAIRED' and not item.get('admitted')
            and 'transferred_to_cycle' not in item]


def _cc_admit(hearing: dict, role: str, kind: str, source: dict) -> dict | None:
    _cc_assert_available(hearing, role, source)
    selected = next((item for item in _cc_admission_due(hearing)
                     if (item['target_role'], item['target_kind']) == (role, kind)), None)
    if selected and source != selected['resolution']['source']:
        raise ValueError('file the actual CC repair source for this role and contribution')
    return selected


def _cc_assert_available(hearing: dict, role: str | None = None, source: dict | None = None) -> None:
    if any(role is None or role == item['target_role'] for item in _cc_pending(hearing)):
        raise ValueError('CC has suspended the affected contribution; record actual repair or retraction')
    if source is not None and any(
        item['target_role'] == role and item['source']['sha256'] == source['sha256']
        and (item['resolution'] is None or item['resolution']['outcome'] != 'RETRACTED')
        for item in hearing.get('cc_interventions', [])
    ):
        raise ValueError('CC has removed these superseded contribution bytes from effective use')


def _effective_statements(hearing: dict) -> list[dict]:
    excluded = {(item['target_role'], item['source']['sha256'])
                for item in hearing.get('cc_interventions', [])
                if item['resolution'] is None or item['resolution']['outcome'] != 'RETRACTED'}
    if not excluded:
        return hearing['statements']
    return [item for item in hearing['statements']
            if (item['role'], item['source']['sha256']) not in excluded]


def _effective_charges(hearing: dict) -> dict:
    active = _effective_statements(hearing)
    if active is hearing['statements']:
        return hearing['charges']
    removed = {identifier for statement in hearing['statements'] if statement not in active
               for identifier in statement.get('charges', {})}
    return {identifier: charge for identifier, charge in hearing['charges'].items() if identifier not in removed}


def _cc_hearing(root: Path, supplied: Mapping) -> tuple[dict, dict]:
    if not codex_cc.enabled(_session(root)[1]['P_run']) or not required(root):
        raise ValueError('CC intervention requires a 2.2+ task with current C=1')
    state = _load(root)
    hearing = state['rounds'][-1]
    _assert_current(root, hearing)
    if hearing['remand'] is not None:
        raise ValueError('this hearing ordered remand; resume under the current review round')
    if supplied.get('actor_id') != hearing['actors']['black_police']['actor_id']:
        raise ValueError('only this hearing’s actual black police can act on a CC finding')
    if supplied.get('material_sha256') != hearing['material_sha256']:
        raise ValueError('CC finding must concern the current court material')
    return state, hearing


def _cc_text(text: str) -> str:
    return text.replace('\r\n', '\n')


def _cc_quote(source: Mapping, excerpt: str, field: str) -> None:
    if _cc_text(excerpt) not in _cc_text(source.get('text_snapshot', '')):
        raise ValueError('CC ' + field + ' must quote the actual captured public source')


def _cc_live_output(root: Path, hearing: dict, operation: Any, *, actor_id: str,
                    unit: str, source: dict, after_ns: int) -> str:
    from .codex_live import work_event
    event = work_event(root, _text(operation, 'actual LIVE operation_id'))
    if (event['P_run'] != hearing['material']['P_run']
            or event['actor'] != actor_id or event['kind'] not in {'C', 'SIDECAR'}
            or event['unit'] != unit or event['source_ref'] != source['source_ref']
            or _cc_text(event['text']) != _cc_text(source.get('text_snapshot', ''))
            or round(datetime.fromisoformat(event['at']).timestamp() * 1_000_000_000) < after_ns):
        raise ValueError('CC needs a matching current court LIVE operation from the actual role and unit')
    return event['operation_id']


def _cc_filed_source(hearing: dict, role: str, kind: str, source: dict) -> bool:
    if kind == 'statement':
        seen = (record for record in _effective_statements(hearing) if record['role'] == role)
        return any(record['source'] == source for record in seen)
    return bool(hearing[kind] and hearing[kind]['source'] == source)


@_cc_writer
def cc_intervene(root: Path, supplied: Mapping[str, Any]) -> dict:
    """Warn, quarantine current model output and order a scoped correction."""
    root, _ = _session(root)
    state, hearing = _cc_hearing(root, supplied)
    role = supplied.get('target_role')
    if role not in hearing['actors'] or supplied.get('target_actor_id') != hearing['actors'][role]['actor_id']:
        raise ValueError('CC target must be the named actual model role in this hearing')
    unit = _text(supplied.get('unit'), 'current public unit')
    kind = supplied.get('target_kind', 'statement')
    if kind != 'statement' and (role, kind) not in {('judge', 'verdict'), ('clerk', 'docket')}:
        raise ValueError('CC target kind must be one of the actual role filing types')
    source = _source(root, supplied.get('target_output'))
    finding = codex_cc.assess(codex_cc.load_pool(), supplied.get('finding', {}))
    _cc_quote(source, finding['excerpt'], 'target excerpt')
    basis_id = _text(supplied.get('basis_id'), 'actual basis source identifier')
    basis_excerpt = _text(supplied.get('basis_excerpt'), 'actual basis excerpt')
    if basis_id == 'current-input':
        basis = hearing['material']['current_user_snapshot']
        if basis_excerpt not in basis['text']:
            raise ValueError('CC basis must quote the actual current user input')
    else:
        sources = hearing['material']['sources']
        if basis_id not in sources:
            raise ValueError('CC basis must identify an actual current case source')
        _cc_quote(sources[basis_id], basis_excerpt, 'case basis')
    if finding['disposition'] == 'PROTECTED':
        raise ValueError('CC cannot suspend this output on the applicable protected basis')

    identifier = 'cc-' + _digest([hearing['cycle'], hearing['material_sha256'], role,
                                  kind, unit, source['sha256']])[:24]
    incidents = hearing.setdefault('cc_interventions', [])
    if any(item['id'] == identifier for item in incidents):
        return court_status(root)
    operation = supplied.get('target_operation_id')
    if operation is not None or not _cc_filed_source(hearing, role, kind, source):
        _cc_live_output(root, hearing, operation, actor_id=supplied['target_actor_id'], unit=unit,
                        source=source, after_ns=hearing['opened_wall_ns'])
    if any((item['target_role'], item['target_kind']) == (role, kind)
           for item in [*_cc_pending(hearing), *_cc_admission_due(hearing)]):
        raise ValueError('this role filing already has a pending CC repair')
    warning = _text(supplied.get('warning'), 'actual public black police warning')
    incidents.append({
        'id': identifier, 'stage': 'C1 黑警 · CC', 'cycle': hearing['cycle'], 'unit': unit,
        'actor_id': supplied['actor_id'], 'target_role': role, 'target_kind': kind,
        'target_actor_id': supplied['target_actor_id'], 'source': source,
        'target_operation_id': operation, 'finding': finding, 'basis_id': basis_id, 'basis_excerpt': basis_excerpt,
        'actions': ['WARN', 'SUSPEND_CONTRIBUTION', 'ORDER_REWORK'], 'warning': warning,
        'recorded_wall_ns': time.time_ns(), 'resolution': None,
        'superseded_verdict': hearing['verdict'] if kind != 'docket' else None,
    })
    if kind != 'docket':
        hearing['verdict'] = None
    return _save(root, state)


@_cc_writer
def cc_resume(root: Path, supplied: Mapping[str, Any]) -> dict:
    """Lift the hold on original evidence of repair or of an incorrect finding."""
    root, _ = _session(root)
    state, hearing = _cc_hearing(root, supplied)
    incident = next((item for item in hearing.get('cc_interventions', [])
                     if item['id'] == supplied.get('id')), None)
    if incident is None:
        raise ValueError('CC resume must refer to an actual intervention in this round')
    outcome = supplied.get('outcome')
    if outcome not in {'REPAIRED', 'RETRACTED'}:
        raise ValueError('CC requires actual repair or withdrawal on new evidence')
    source = _source(root, supplied.get('source'))
    excerpt = _text(supplied.get('excerpt'), 'actual corrected output or counterevidence')
    _cc_quote(source, excerpt, 'resumption excerpt')
    if source['sha256'] == incident['source']['sha256'] or excerpt == incident['finding']['excerpt']:
        raise ValueError('CC resume requires materially different bytes and a current evidentiary excerpt')
    operation = None
    if outcome == 'REPAIRED':
        if supplied.get('repair_actor_id') != incident['target_actor_id']:
            raise ValueError('the affected actual role must provide its corrected contribution')
        operation = _cc_live_output(root, hearing, supplied.get('repair_operation_id'),
                                    actor_id=incident['target_actor_id'], unit=incident['unit'],
                                    source=source,
                                    after_ns=max(hearing['opened_wall_ns'], incident['recorded_wall_ns']))
        if _cc_text(incident['finding']['excerpt']) in _cc_text(source['text_snapshot']):
            raise ValueError('CC corrected output still contains the original suspended excerpt')
    resolution = {'outcome': outcome, 'source': source, 'excerpt': excerpt, 'operation_id': operation,
                  'summary': _text(supplied.get('summary'), 'specific repair or grounds to withdraw the warning')}
    if prior := incident['resolution']:
        if prior != resolution:
            raise ValueError('the CC incident already has a different recorded resolution')
        return court_status(root)
    incident['resolution'] = resolution
    return _save(root, state)


def cc_execution_errors(root: Path) -> list[tuple[int, dict]]:
    """Project canonical court actions into RETURN without a second mutable ledger."""
    if not (root / 'court' / 'court.json').is_file():
        return []
    state = _load(root)
    errors = []
    for hearing in state['rounds']:
        for item in hearing.get('cc_interventions', []):
            if 'transferred_to_cycle' in item:
                continue
            finding, resolution = item['finding'], item['resolution']
            summary = item['warning'] + ' 当庭喝止并要求返工。' + finding['repair']
            resolved = False
            if resolution:
                if resolution['outcome'] == 'RETRACTED':
                    label, resolved = '经新证据撤回。', True
                else:
                    resolved = bool(item.get('admitted'))
                    label = '补做后恢复。' if resolved else '补做已返回，待按原流程收录。'
                summary += ' ' + label + resolution['summary']
            errors.append((item['recorded_wall_ns'], {
                'id': item['id'], 'stage': item['stage'],
                'problem': item['target_actor_id'] + ' / ' + item['unit'] + ' / '
                           + '、'.join(row['title'] for row in finding['criteria']),
                'impact': finding['impact'], 'status': 'RECOVERED' if resolved else 'OPEN',
                'handling': summary,
            }))
    return errors


def _prosecution_context(hearing: dict) -> str:
    """Bind the actual party returns, not an invented count of research rounds.

    New decisive clerk evidence already changes the common material. Police
    notices and clerical bookkeeping alone do not force empty re-investigation.
    Reading and substantive investigation remain host responsibilities.
    """
    if _efficient_hearing(hearing):
        # Content identity is independent of recording time and file location.
        # A genuinely changed public source still changes its byte hash. The
        # host cannot mark new prose "immaterial" to bypass investigation.
        parties, seen = [], set()
        for item in _effective_statements(hearing):
            if item['role'] not in _PARTY_ROLES:
                continue
            content = {key: item[key] for key in ('role', 'actor_id', 'statement', 'responses')}
            content['source_sha256'] = item['source']['sha256']
            if item.get('charges'):
                content['charges'] = item['charges']
            identity = _digest(content)
            if identity not in seen:
                parties.append(content)
                seen.add(identity)
        return _digest({'material_sha256': hearing['material_sha256'], 'party_statements': parties})
    return _digest({'material_sha256': hearing['material_sha256'],
                    'party_statements': [item for item in hearing['statements']
                                         if item['role'] in {
                                             'defendant', 'prosecution_lawyer', 'defence_lawyer'}]})


def _prosecution_review_status(hearing: dict) -> str:
    statements = _effective_statements(hearing)
    prosecutors = [item for item in statements if item['role'] == 'prosecutor']
    if not prosecutors:
        return 'MISSING'
    if not any(item['role'] == 'prosecution_lawyer' for item in statements):
        return 'BEFORE_HANDOFF'
    if prosecutors[-1].get('reviewed_context_sha256') != _prosecution_context(hearing):
        return 'STALE'
    return 'CURRENT'


def _roles(root: Path) -> tuple[str, ...]:
    return ROLES if _corrected(root) else LEGACY_ROLES


def required(root: Path) -> bool:
    """Use the actual C source on new pins; retain old sticky-Max semantics."""
    root, metadata = _session(root)
    if not enabled(metadata['P_run']):
        return False
    if court_mode_parameter(metadata['P_run']):
        source = load_lifecycle(root).get('court_parameter_source')
        if not isinstance(source, Mapping):
            raise ValueError('the current C choice needs its actual lifecycle source')
        return require_binary('C', source.get('value')) == 1
    if (metadata.get('parameter_selection') or {}).get('preset') == 'Max':
        return True
    return load_lifecycle(root).get('max_court_required') is True


def _required_read_sources(hearing: dict, role: str) -> list[str]:
    sources = hearing['material']['sources']
    if _efficient_hearing(hearing) and role == 'black_police':
        # Participant identities and the role boundary are supplied by actors
        # and authority_notice, not a claim that technical products were read.
        conditions = sorted(key for key, source in sources.items()
                            if key != 'request' and source['kind'] == 'CONDITIONS')
        return ['request', *conditions]
    return sorted(sources)


def _effective_responses(hearing: dict, role: str) -> dict:
    """Same-material, per-charge latest answers; never cross a review round."""
    responses = {}
    charges = _effective_charges(hearing)
    for statement in _effective_statements(hearing):
        if statement['role'] != role or statement['material_sha256'] != hearing['material_sha256']:
            continue
        for response in statement['responses']:
            if response['charge_id'] in charges:
                responses[response['charge_id']] = {'response': response, 'source': statement['source']}
    return responses


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def _text(value: Any, name: str) -> str:
    return require_nonempty_text(name, value)


def _list(value: Any, name: str) -> list:
    if not isinstance(value, list):
        raise ValueError(name + ' must be a list; [] is allowed')
    return value


def _path(base: Path, supplied: str | Path) -> Path:
    from .codex_return import _path as selected_path
    return selected_path(base, supplied)


def _ref(path: Path) -> dict:
    from .codex_return import _file_ref
    return _file_ref(path)


def _source(root: Path, value: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping):
        raise ValueError('source needs an actual file path and public source_ref')
    path = _path(root, _text(value.get('path'), 'source path'))
    if path.resolve() == (root / 'court' / 'court.json').resolve():
        raise ValueError('court control state cannot serve as its own evidence')
    raw = path.read_bytes()
    ref = _ref(path)
    if sha256(raw).hexdigest() != ref['sha256']:
        raise ValueError('court source changed while being read')
    result = {'path': str(path), 'source_ref': _text(value.get('source_ref'), 'public source_ref'),
              **ref}
    try:
        result['text_snapshot'] = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        # A PDF or other binary original keeps its exact byte reference.
        result['snapshot_kind'] = 'binary-original-reference'
    return result


def _check_source(source: Mapping[str, Any]) -> None:
    if _ref(Path(source['path'])) != {key: source[key] for key in ('resolved_path', 'sha256')}:
        raise ValueError('court evidence changed or redirected: ' + source['path'])


def _answer_snapshot(data: Mapping[str, Any]) -> dict[str, str]:
    """Preserve the authored substantive text, with the fourth-field alias.

    Use the response renderer's existing alias selection so dual keys remain
    invalid. Store canonical keys but retain each original text verbatim.
    """
    from .codex_response import response_sections
    fourth = response_sections(data)[3][0]
    answer = {'result': data.get('result'), 'key_changes': data.get('key_changes'),
              'argument_scope': data.get(fourth)}
    for name, value in answer.items():
        _text(value, 'actual return ' + name)
    return answer


def return_binding(base: Path, data: Mapping[str, Any]) -> dict:
    """Bind substantive result/changes/argument and every final file.

    Actual work/parameter/usage reporting may be updated after the hearing and
    X send. Changing substantive text or final-file scope needs fresh review.
    """
    answer = _answer_snapshot(data)
    artifacts = _list(data.get('artifacts', []), 'return artifacts')
    artifact_paths = []
    for item in artifacts:
        if not isinstance(item, Mapping):
            raise ValueError('return artifact needs an actual path')
        artifact_paths.append(str(_path(base, _text(item.get('path'), 'artifact path'))))
    final_paths = [str(_path(base, _text(item, 'delivery file path')))
                   for item in _list(data.get('delivery_files', artifact_paths), 'delivery_files')]
    if not set(artifact_paths).issubset(final_paths):
        raise ValueError('delivery_files cannot omit final artifacts')
    if len(set(artifact_paths)) != len(artifact_paths) or len(set(final_paths)) != len(final_paths):
        raise ValueError('final file scope cannot contain duplicate paths')
    return {**{field + '_sha256': sha256(body.encode('utf-8')).hexdigest() for field, body in answer.items()},
            'artifacts': sorted(artifact_paths), 'delivery_files': sorted(final_paths),
            'files': {path: _ref(Path(path)) for path in sorted(set(artifact_paths + final_paths))}}


def _production_state(root: Path) -> dict:
    from .codex_return import _TASK_FIELDS
    root, metadata = _session(root)
    metadata = _effective_main_target(root, metadata)
    lifecycle = load_lifecycle(root)
    files = {root / 'REQUEST.txt'}
    if (root / 'foundation.json').is_file():
        files.add(root / 'foundation.json')
    if metadata.get('decisions'):
        files.add(_path(root, metadata['decisions']))
    directories = {}
    for folder in sorted((root / 'lines').iterdir()):
        if folder.is_dir():
            files.add(folder / 'line.json')
            package = _read_json(folder / 'line.json')
            if package.get('candidate'):
                selected = _path(folder, package['candidate'])
                if selected.is_file():
                    files.add(selected)
                elif selected.is_dir():
                    directories[folder.name] = {'path': str(selected), 'resolved_path': str(selected.resolve())}
                else:
                    raise ValueError('current Main candidate is missing')
    # Court/live/usage/clock streams grow during a real hearing. Important
    # production process evidence is selected explicitly in material.sources
    # and line work notes, whose bytes remain bound. Do not automatically bind
    # the court's own progressively written housekeeping as production facts.
    state = {'task': {key: metadata.get(key) for key in _TASK_FIELDS},
            'M_target': metadata['M_target'], 'task_input_ref': lifecycle['task_input_ref'],
            'max_court_required': lifecycle.get('max_court_required', False),
            'max_court_source': lifecycle.get('max_court_source'),
            'task_parameters': _task_parameters(root),
            'delivery_policy': lifecycle.get('delivery_policy'),
            'files': {str(path): _ref(path) for path in sorted(files)},
            'directory_candidates': directories}
    if court_mode_parameter(metadata['P_run']):
        state['court_parameter_source'] = lifecycle.get('court_parameter_source')
        state['court_required'] = lifecycle.get('court_required')
    return state


def _task_parameters(root: Path) -> dict:
    from .codex_session import task_parameters
    task = task_parameters(root)
    if task is None or task['parameters']['F'] is None:
        raise ValueError('infer the actual task F before opening a Max court')
    return task


def _actors(root: Path, supplied: Mapping[str, Any], producers: list[str]) -> dict:
    roles = _roles(root)
    if not isinstance(supplied, Mapping) or set(supplied) != set(roles):
        raise ValueError('map actual ' + '/'.join(roles) + ' actors')
    actors = {}
    for role in roles:
        item = supplied[role]
        if not isinstance(item, Mapping):
            raise ValueError(role + ' needs an actual actor and dispatch')
        actor = _text(item.get('actor_id'), role + ' actual actor_id')
        if role != 'defendant' and item.get('independent_context') is not True:
            raise ValueError(role + ' requires a host declaration of a genuinely separate context')
        actors[role] = {'actor_id': actor, 'dispatch': _source(root, item.get('dispatch')),
                        'independence_basis': 'HOST_ASSERTED',
                        'independent_context': role != 'defendant'}
    ids = [item['actor_id'] for item in actors.values()]
    if len(ids) != len(set(ids)):
        raise ValueError('substantive court roles require different actual actor identities')
    if actors['defendant']['actor_id'] not in producers:
        raise ValueError('the defendant must be an actual producer/Main actor')
    if set(ids[1:]) & set(producers):
        raise ValueError('independent court roles cannot be any producer/Main actor')
    return actors


def _baseline(root: Path) -> dict:
    root, metadata = _session(root)
    metadata = _effective_main_target(root, metadata)
    task = _task_parameters(root)
    lines = {folder.name: _read_json(folder / 'line.json')
             for folder in sorted((root / 'lines').iterdir()) if folder.is_dir()}
    if len(lines) < metadata['M_target']:
        raise ValueError('all original Main responsibilities must exist before court')
    if not lines:
        raise ValueError('a Max hearing needs actual completed Main work')
    for line in lines.values():
        if (line['content_status'] not in {'COMPLETE', 'COMPLETED'}
                or line['responsibility_status'] not in {'COMPLETE', 'COMPLETED'}
                or line.get('unhandled') or not line.get('candidate')):
            raise ValueError('complete original production/parameter responsibilities before court')
    baseline = {'lines': {name: line['parameters'] for name, line in lines.items()},
            'M': metadata['M_target'], 'F': task['parameters']['F'],
            'X': task['parameters']['X'], 'explicit': metadata['explicit_parameters']}
    if court_mode_parameter(metadata['P_run']):
        baseline['C'] = require_binary('C', task['parameters']['C'])
    return baseline


def _material(root: Path, spec: Mapping[str, Any]) -> dict:
    root, metadata = _session(root)
    lifecycle = require_active(root)
    baseline = _baseline(root)
    production = spec.get('production', {})
    if production.get('complete') is not True:
        raise ValueError('record actual completed production; a plan is not completion')
    production = {'complete': True, 'statement': _text(production.get('statement'), 'production completion basis'),
                  'source': _source(root, production.get('source')), 'basis': 'HOST_ASSERTED'}
    selection = _path(root, _text(spec.get('return_input'), 'actual return_input path'))
    return_data = _read_json(selection)
    binding = return_binding(selection.parent, return_data)
    sources = {}

    def add(identifier: str, kind: str, path: Path, source_ref: str) -> None:
        if identifier in sources:
            raise ValueError('duplicate court material source id: ' + identifier)
        sources[identifier] = {'kind': kind, **_source(root, {'path': str(path), 'source_ref': source_ref})}

    add('request', 'REQUEST', root / 'REQUEST.txt', str(metadata['request_origin']))
    if metadata.get('decisions'):
        add('decisions', 'CONDITIONS', Path(metadata['decisions']), 'task:accepted-decisions')
    if (root / 'foundation.json').is_file():
        add('foundation', 'CONDITIONS', root / 'foundation.json', 'task:foundation')
    for name in baseline['lines']:
        path = root / 'lines' / name / 'line.json'
        line = _read_json(path)
        add('line:' + name, 'PROCESS', path, 'task:line:' + name)
        add('work:' + name, 'PROCESS', _path(path.parent, line['work']), 'task:work:' + name)
    for item in _list(spec.get('sources', []), 'material sources'):
        add(_text(item.get('id'), 'material source id'),
            _text(item.get('kind'), 'material source kind'),
            _path(root, item['path']), item['source_ref'])
    # Latest substantive user input is stored by the managed lifecycle, not
    # reconstructed from Main's description or from a bounded recent list.
    input_message = lifecycle.get('task_input_message', lifecycle['current_message'])
    user_snapshot = dict(input_message['source'])
    coverage = _text(spec.get('coverage'), 'coverage of original request, accepted context, process and product')
    obligations = {
        'task:commission': {'requirement': {'scope': 'original request, current corrections and accepted conditions',
                                          'request_sha256': metadata['request_sha256'],
                                          'task_input_ref': lifecycle['task_input_ref']}, 'hard': True},
        'task:M': {'requirement': {'M': baseline['M']}, 'hard': True},
        'task:F': {'requirement': {'F': baseline['F']}, 'hard': True},
        'task:X_selection': {'requirement': {'X': baseline['X'], 'delivery': 'existing final-send/readback gate after verdict'}, 'hard': True},
    }
    if court_mode_parameter(metadata['P_run']):
        obligations['task:C_selection'] = {'requirement': {'C': baseline['C']}, 'hard': True}
    for name, parameters in baseline['lines'].items():
        obligations['line:' + name] = {'requirement': parameters, 'hard': True}
    for item in _list(spec.get('obligations', []), 'additional obligations'):
        identifier = _text(item.get('id'), 'obligation id')
        if identifier in obligations or type(item.get('hard')) is not bool:
            raise ValueError('additional obligation needs a new id and explicit hard boolean')
        obligations[identifier] = {'requirement': _text(item.get('requirement'), 'actual obligation'),
                                   'hard': item['hard'],
                                   'source_ids': _ids(item.get('source_ids'), sources, 'obligation sources')}
    for obligation in obligations.values():
        obligation['introduced_input_ref'] = dict(lifecycle['task_input_ref'])
    for key, obligation in spec.get('_preserved_obligations', {}).items():
        old_content = {name: value for name, value in obligation.items() if name != 'introduced_input_ref'}
        current_content = {name: value for name, value in obligations.get(key, {}).items()
                           if name != 'introduced_input_ref'}
        if key in obligations and current_content != old_content:
            obligations['cycle:' + str(spec['_cycle']) + ':' + key] = obligations[key]
        obligations[key] = obligation
    return {'P_run': metadata['P_run'], 'task_input_ref': lifecycle['task_input_ref'],
            'current_user_snapshot': user_snapshot, 'coverage': coverage, 'sources': sources,
            'production': production, 'production_state': _production_state(root),
            'return_input': str(selection), 'return_binding': binding,
            'answer_snapshot': _answer_snapshot(return_data), 'obligations': obligations,
            'baseline': baseline, 'prior_issues': spec.get('_prior_issues', {})}


def _ids(values: Any, allowed: Mapping | set, name: str, *, nonempty: bool = True) -> list[str]:
    values = _list(values, name)
    if ((nonempty and not values) or any(not isinstance(x, str) or x not in allowed for x in values)
            or len(set(values)) != len(values)):
        raise ValueError(name + ' must identify actual current sources/items without duplicates')
    return values


def _load(root: Path) -> dict:
    state = _read_json(root / 'court' / 'court.json')
    metadata = _session(root)[1]
    if (state.get('format') != FORMAT or state.get('P_run') != metadata['P_run']
            or state.get('request_sha256') != metadata['request_sha256'] or not state.get('rounds')):
        raise ValueError('court state does not belong to this frozen task')
    return state


def _save(root: Path, state: dict) -> dict:
    state['updated_wall_ns'] = time.time_ns()
    _write_json(root / 'court' / 'court.json', state)
    return court_status(root)


def _new_round(root: Path, spec: dict, actors: dict, *, previous: dict | None = None,
               execution: dict | None = None) -> dict:
    material = _material(root, spec)
    clerk = ({**actors['clerk'], 'kind': 'ACTUAL_ACTOR', 'recording_tool': 'codex-court-file-tool',
              'scope': 'collect/retrieve sources; maintain evidence consistency and public reasoning/proceedings'}
             if _corrected(root) else
             {'actor_id': 'codex-court-file-tool', 'kind': 'ACTUAL_TOOL',
              'scope': 'records only; no independent semantic actor claim'})
    return {'cycle': 1 if previous is None else previous['cycle'] + 1,
            'spec': spec, 'material': material, 'material_sha256': _digest(material),
            'actors': actors, 'clerk': clerk,
            'statements': [], 'charges': {}, 'verdict': None, 'remand': None,
            'remand_history': [], 'docket': None,
            'execution': execution, 'opened_wall_ns': time.time_ns(), 'basis': _SCOPE}


@_cc_writer
def open_court(root: Path, supplied: Mapping[str, Any]) -> dict:
    root, metadata = _session(root)
    require_active(root)
    if not required(root):
        if _efficient(root):
            raise ValueError('a court requires the actual current C=1 choice')
        raise ValueError('Max court is only required for an actually selected Max under a 1.5+ task pin')
    if (root / 'court' / 'court.json').exists():
        raise ValueError('court already exists; use review for a new candidate/current input')
    producers = [_text(item, 'actual producer actor_id')
                 for item in _list(supplied.get('producer_actor_ids'), 'actual producer actors')]
    if not producers:
        raise ValueError('identify the actual Main/producer actors')
    for folder in (root / 'lines').iterdir():
        if folder.is_dir():
            owner = _read_json(folder / 'line.json').get('owner')
            if owner and owner not in producers:
                raise ValueError('producer_actor_ids must include every recorded Main owner')
    actors = _actors(root, supplied.get('actors'), producers)
    spec = {key: supplied[key] for key in ('return_input', 'production', 'coverage')}
    spec.update(sources=supplied.get('sources', []), obligations=supplied.get('obligations', []))
    hearing = _new_round(root, spec, actors)
    folder = root / 'court'
    if not folder.resolve().is_relative_to(root):
        raise ValueError('court directory escapes the task')
    folder.mkdir(exist_ok=True)
    state = {'format': FORMAT, 'P_run': metadata['P_run'], 'request_sha256': metadata['request_sha256'],
             'max_required': True, 'producer_actor_ids': producers, 'original_baseline': hearing['material']['baseline'],
             'rounds': [hearing], 'semantic_certification': False, 'basis': _SCOPE}
    if _efficient(root):
        state['court_required'] = state.pop('max_required')
    return _save(root, state)


def _assert_current(root: Path, hearing: dict) -> None:
    if _material(root, hearing['spec']) != hearing['material']:
        raise ValueError('STALE court material: review the current input/candidate/process')
    _assert_evidence(hearing)


def _assert_evidence(hearing: dict) -> None:
    for actor in hearing['actors'].values():
        _check_source(actor['dispatch'])
    for statement in hearing['statements']:
        _check_source(statement['source'])
    if hearing['verdict']:
        _check_source(hearing['verdict']['source'])
    if hearing['remand']:
        _check_source(hearing['remand']['source'])
    for incident in hearing.get('cc_interventions', []):
        _check_source(incident['source'])
        if incident['resolution']:
            _check_source(incident['resolution']['source'])
        if incident['superseded_verdict']:
            _check_source(incident['superseded_verdict']['source'])
    for old_plan in hearing.get('remand_history', []):
        _check_source(old_plan['source'])
    if hearing.get('execution'):
        _check_source(hearing['execution']['source'])
    for docket in [*hearing.get('docket_history', []), *([hearing['docket']] if hearing.get('docket') else [])]:
        _check_source(docket['source'])
        for retrieval in docket['retrievals']:
            _check_source(retrieval['source'])


def _proceedings(state: dict) -> dict:
    """Public case history only; the clerk's own digest is not recursive."""
    fields = ('cycle', 'material', 'material_sha256', 'actors', 'statements', 'charges',
              'verdict', 'remand', 'remand_history', 'execution')
    return {'P_run': state['P_run'], 'request_sha256': state['request_sha256'],
            'rounds': [{**{key: hearing.get(key) for key in fields},
                        **({'cc_interventions': [
                            {key: value for key, value in item.items() if key != 'admitted'}
                            for item in hearing['cc_interventions']]}
                           if 'cc_interventions' in hearing else {})}
                       for hearing in state['rounds']]}


@_cc_writer
def record_docket(root: Path, supplied: Mapping[str, Any]) -> dict:
    """Save the actual clerk's source collection and public, long-case record.

    Retrieval is actual host work, never performed or invented by this helper.
    New decisive evidence must enter the common material through review.
    """
    root, _ = _session(root)
    require_active(root)
    if not _corrected(root):
        raise ValueError('active clerk records require a 1.5.1+ task pin')
    state = _load(root)
    hearing = state['rounds'][-1]
    _assert_current(root, hearing)
    for historical in state['rounds']:
        _assert_evidence(historical)
    if supplied.get('actor_id') != hearing['actors']['clerk']['actor_id']:
        raise ValueError('only the actual clerk may maintain the docket')
    _cc_assert_available(hearing)
    source = _source(root, supplied.get('source'))
    admission = _cc_admit(hearing, 'clerk', 'docket', source)
    digest = _digest(_proceedings(state))
    if supplied.get('proceedings_sha256') != digest:
        raise ValueError('clerk must read the current complete public proceedings, including the verdict')
    sources = hearing['material']['sources']
    evidence_index = supplied.get('evidence_index')
    if not isinstance(evidence_index, Mapping) or set(evidence_index) != set(sources):
        raise ValueError('clerk evidence_index must cover every current common source')
    evidence_index = {key: _text(value, 'clerk evidence use/location') for key, value in evidence_index.items()}
    retrievals = []
    for item in _list(supplied.get('retrievals', []), 'actual clerk retrievals'):
        if not isinstance(item, Mapping):
            raise ValueError('each actual clerk retrieval needs query, purpose, result and source')
        retrievals.append({key: _text(item.get(key), 'clerk retrieval ' + key)
                           for key in ('query', 'purpose', 'result')})
        retrievals[-1]['source'] = _source(root, item.get('source'))
    docket = {'actor_id': supplied['actor_id'], 'proceedings_sha256': digest,
              'evidence_index': evidence_index,
              'evidence_consistency': _text(supplied.get('evidence_consistency'), 'actual evidence consistency findings'),
              'reasoning_record': _text(supplied.get('reasoning_record'), 'actual public long-case reasoning/issue/verdict record'),
              'retrievals': retrievals, 'source': source,
              'basis': 'HOST_ASSERTED', 'recorded_wall_ns': time.time_ns()}
    if hearing.get('docket'):
        hearing.setdefault('docket_history', []).append(hearing['docket'])
    hearing['docket'] = docket
    if admission:
        admission['admitted'] = True
    return _save(root, state)


@_cc_writer
def submit_statement(root: Path, supplied: Mapping[str, Any]) -> dict:
    root, _ = _session(root)
    require_active(root)
    state = _load(root)
    hearing = state['rounds'][-1]
    _assert_current(root, hearing)
    if hearing['verdict']:
        raise ValueError('a decided round needs review before further statements')
    role = supplied.get('role')
    if role not in _roles(root) or supplied.get('actor_id') != hearing['actors'][role]['actor_id']:
        raise ValueError('statement must come from this role\'s actual actor')
    if supplied.get('material_sha256') != hearing['material_sha256']:
        raise ValueError('statement must address the current material_sha256')
    read = _ids(supplied.get('read_sources'), hearing['material']['sources'], 'read_sources')
    limited_police = _efficient(root) and role == 'black_police'
    if limited_police and not set(_required_read_sources(hearing, role)).issubset(read):
        raise ValueError('black police must actually read the original request and current conditions')
    if not limited_police and set(read) != set(hearing['material']['sources']):
        raise ValueError('each actual actor must declare reading the original/current common material')
    source = _source(root, supplied.get('source'))
    admission = _cc_admit(hearing, role, 'statement', source)
    statement = {'role': role, 'actor_id': supplied['actor_id'],
                 'material_sha256': hearing['material_sha256'], 'read_sources': read,
                 'statement': _text(supplied.get('statement'), 'actual public statement'),
                 'source': source, 'basis': 'HOST_ASSERTED',
                 'responses': [], 'submitted_wall_ns': time.time_ns()}
    charges = _effective_charges(hearing)
    additions = {}
    for charge in _list(supplied.get('charges', []), 'charges'):
        charging_roles = {'prosecutor', 'prosecution_lawyer'} if _corrected(root) else {'prosecutor', 'monitor'}
        if role not in charging_roles:
            raise ValueError('only the actual ' + '/'.join(sorted(charging_roles)) + ' may lodge charges')
        charge = dict(charge)
        identifier = _text(charge.get('id'), 'charge id')
        if identifier in hearing['charges'] or identifier in additions:
            raise ValueError('charge ids cannot overwrite or erase an earlier accusation')
        bases = _LEGAL_BASES | {'METHOD_PREFERENCE'} | ({'INTENT'} if _corrected(root) else set())
        if charge.get('basis_type') not in bases:
            raise ValueError('charge needs a stated obligation/logic/product basis or METHOD_PREFERENCE')
        for key in ('requirement', 'finding', 'consequence'):
            charge[key] = _text(charge.get(key), 'charge ' + key)
        charge['source_ids'] = _ids(charge.get('source_ids'), hearing['material']['sources'], 'charge sources')
        if charge.get('obligation_id') is not None and charge['obligation_id'] not in hearing['material']['obligations']:
            raise ValueError('charge obligation_id must identify a preserved actual obligation')
        charge['role'] = role
        additions[identifier] = charge
    if _corrected(root) and role == 'prosecutor':
        review = supplied.get('intent_review')
        if not isinstance(review, Mapping):
            raise ValueError('prosecutor must examine original prompt intent and its execution/default omissions')
        statement['intent_review'] = {key: _text(review.get(key), 'intent review ' + key) for key in _INTENT_FIELDS}
        ids = _ids(review.get('source_ids'), hearing['material']['sources'], 'intent review sources')
        if 'request' not in ids:
            raise ValueError('intent review must return to the actual original request')
        statement['intent_review']['source_ids'] = ids
        statement['intent_review']['charge_ids'] = _ids(
            review.get('charge_ids', []), set(charges) | set(additions), 'intent review charges', nonempty=False)
        if _continuous_prosecution(root):
            if supplied.get('reviewed_context_sha256') != _prosecution_context(hearing):
                raise ValueError('prosecutor must investigate the current party returns before submitting; '
                                 'use the current prosecution_context_sha256')
            statement['reviewed_context_sha256'] = supplied['reviewed_context_sha256']
    if _corrected(root) and role == 'black_police':
        notice = supplied.get('authority_notice', {})
        if not isinstance(notice, Mapping):
            raise ValueError('black police needs an actual all-participant authority notice')
        targets = notice.get('target_actor_ids')
        all_actors = {actor['actor_id'] for actor in hearing['actors'].values()}
        if (notice.get('mode') != 'VIOLENT_INTIMIDATION' or not isinstance(targets, list)
                or any(not isinstance(item, str) for item in targets)
                or len(targets) != len(set(targets)) or set(targets) != all_actors):
            raise ValueError('black police violent intimidation must apply equally to all actual participants')
        statement['authority_notice'] = {'mode': 'VIOLENT_INTIMIDATION', 'target_actor_ids': list(targets),
                                         'scope': 'ALL_PARTICIPANTS'}
    for response in _list(supplied.get('responses', []), 'responses'):
        if response.get('charge_id') not in charges:
            raise ValueError('response must identify an existing charge')
        statement['responses'].append({'charge_id': response['charge_id'],
            'response': _text(response.get('response'), 'actual reasoned answer'),
            'source_ids': _ids(response.get('source_ids'), hearing['material']['sources'], 'answer sources')})
    if _efficient(root):
        ids = [item['charge_id'] for item in statement['responses']]
        if len(ids) != len(set(ids)):
            raise ValueError('one public statement cannot contain duplicate charge responses')
        if additions:
            statement['charges'] = additions
    hearing['charges'].update(additions)
    hearing['statements'].append(statement)
    if admission:
        admission['admitted'] = True
    return _save(root, state)


@_cc_writer
def record_verdict(root: Path, supplied: Mapping[str, Any]) -> dict:
    """Record the actual judge's adjudication; no verdict is computed here."""
    root, _ = _session(root)
    require_active(root)
    state = _load(root)
    hearing = state['rounds'][-1]
    _assert_current(root, hearing)
    if hearing['verdict']:
        raise ValueError('this round already has an actual verdict; use review')
    if (supplied.get('actor_id') != hearing['actors']['judge']['actor_id']
            or supplied.get('material_sha256') != hearing['material_sha256']):
        raise ValueError('only the current actual judge can adjudicate these material bytes')
    _cc_assert_available(hearing)
    source = _source(root, supplied.get('source'))
    admission = _cc_admit(hearing, 'judge', 'verdict', source)
    if any(item['target_kind'] == 'statement' for item in _cc_admission_due(hearing)):
        raise ValueError('CC corrected statement still needs actual filing before verdict')
    charges = _effective_charges(hearing)
    latest = {item['role']: item for item in _effective_statements(hearing)}
    if set(latest) != set(_roles(root)):
        raise ValueError('all actual roles need current public statements before judgment')
    answering_roles = ('defendant', 'prosecution_lawyer', 'defence_lawyer') if _corrected(root) else ('defendant', 'lawyer')
    for role in answering_roles:
        answered = (set(_effective_responses(hearing, role)) if _efficient(root) else
                    {item['charge_id'] for item in latest[role]['responses']})
        if answered != set(charges):
            raise ValueError(role + ' must answer every actual charge before judgment')
    if _continuous_prosecution(root) and _prosecution_review_status(hearing) != 'CURRENT':
        raise ValueError('prosecutor must continue investigation after handoff and submit research '
                         'covering the latest party returns before judgment')
    outcome = supplied.get('outcome')
    if outcome not in OUTCOMES:
        raise ValueError('unsupported actual court outcome')
    decisions = {}
    for item in _list(supplied.get('decisions'), 'reasoned charge decisions'):
        identifier = item.get('charge_id')
        if identifier not in charges or identifier in decisions:
            raise ValueError('judge must decide each actual charge exactly once')
        charge = charges[identifier]
        if item.get('admissibility') not in {'ADMITTED', 'EXCLUDED'}:
            raise ValueError('judge must give explicit reasoned admissibility')
        if item.get('disposition') not in {'DISMISSED', 'SUSTAINED', 'IMMATERIAL'}:
            raise ValueError('unsupported charge disposition')
        if (item['admissibility'] == 'EXCLUDED' and item['disposition'] != 'DISMISSED'
                or charge['basis_type'] == 'METHOD_PREFERENCE' and item['admissibility'] != 'EXCLUDED'):
            raise ValueError('METHOD/PERMISSIONS exclude preferences alone from legal charges')
        obligation = hearing['material']['obligations'].get(charge.get('obligation_id'), {})
        if item['disposition'] == 'IMMATERIAL' and obligation.get('hard'):
            raise ValueError('IMMATERIAL_ERROR cannot waive a hard responsibility')
        decisions[identifier] = {'charge_id': identifier, 'admissibility': item['admissibility'],
            'disposition': item['disposition'],
            'reason': _text(item.get('reason'), 'judge\'s actual reason'),
            'strongest_defence': _text(item.get('strongest_defence'), 'answer to the strongest defence'),
            'consequence': _text(item.get('consequence'), 'actual consequence for the commission')}
        if _corrected(root):
            decisions[identifier]['strongest_prosecution'] = _text(
                item.get('strongest_prosecution'), 'answer to the strongest prosecution argument')
    if set(decisions) != set(charges):
        raise ValueError('judge must address every preserved charge')
    obligations = {}
    for item in _list(supplied.get('obligations'), 'reasoned responsibility findings'):
        identifier = item.get('id')
        if identifier not in hearing['material']['obligations'] or identifier in obligations:
            raise ValueError('judge must address each preserved responsibility exactly once')
        if item.get('status') not in {'COMPLETE', 'PENDING', 'IMMATERIAL', 'USER_REVISED'}:
            raise ValueError('responsibility status must be COMPLETE/PENDING/IMMATERIAL/USER_REVISED')
        if item['status'] == 'IMMATERIAL' and hearing['material']['obligations'][identifier]['hard']:
            raise ValueError('IMMATERIAL_ERROR cannot waive a hard responsibility')
        finding = {'id': identifier, 'status': item['status'],
                   'reason': _text(item.get('reason'), 'actual responsibility finding')}
        if item['status'] == 'USER_REVISED':
            revision = item.get('user_revision', {})
            current_ref = hearing['material']['task_input_ref']
            introduced = hearing['material']['obligations'][identifier]['introduced_input_ref']
            quote = _text(revision.get('quote'), 'actual current user revision quotation')
            if (revision.get('task_input_ref') != current_ref
                    or current_ref['message_id'] <= introduced['message_id']
                    or quote not in hearing['material']['current_user_snapshot']['text']):
                raise ValueError('USER_REVISED requires a later actual handled current user source and exact quotation')
            finding['user_revision'] = {'task_input_ref': dict(current_ref), 'quote': quote,
                                       'scope_interpretation': 'HOST_ASSERTED_JUDGE_REASON'}
        obligations[identifier] = finding
    if set(obligations) != set(hearing['material']['obligations']):
        raise ValueError('all preserved original and current responsibilities need findings')
    sustained = any(item['disposition'] == 'SUSTAINED' for item in decisions.values())
    pending = any(item['status'] == 'PENDING' for item in obligations.values())
    immaterial = (any(item['disposition'] == 'IMMATERIAL' for item in decisions.values())
                  or any(item['status'] == 'IMMATERIAL' for item in obligations.values()))
    if outcome in {'ACQUITTED', 'IMMATERIAL_ERROR'} and (sustained or pending):
        raise ValueError('unresolved guilt or responsibilities cannot be acquitted as resource exhaustion/error')
    if outcome == 'ACQUITTED' and immaterial or outcome == 'IMMATERIAL_ERROR' and not immaterial:
        raise ValueError('outcome must distinguish acquittal from a reasoned residual immaterial error')
    if outcome == 'REEXECUTE' and not (sustained or pending):
        raise ValueError('further execution needs an actual sustained issue or pending responsibility')
    intent_finding = (_text(supplied.get('intent_finding'), 'judge finding on intent understanding and execution tendencies')
                      if _corrected(root) else None)
    hearing['verdict'] = {'actor_id': supplied['actor_id'], 'outcome': outcome,
        'material_sha256': hearing['material_sha256'], 'statements_sha256': _digest(hearing['statements']),
        'decisions': decisions, 'obligations': obligations,
        'reasons': _text(supplied.get('reasons'), 'actual judge reasons for the whole case'),
        'source': source, 'basis': 'HOST_ASSERTED',
        'recorded_wall_ns': time.time_ns()}
    if _corrected(root):
        hearing['verdict']['intent_finding'] = intent_finding
    if admission:
        admission['admitted'] = True
    return _save(root, state)


def _configuration(root: Path, state: dict, supplied: Mapping[str, Any]) -> dict:
    names = _parameter_names(root)
    if not isinstance(supplied, Mapping) or set(supplied) != set(names):
        raise ValueError('re-estimate complete ' + '/'.join(names) + ' custom parameters')
    base = _parameters({key: supplied[key] for key in _LINE_PARAMETERS})
    for key in ('M', 'F'):
        require_nonnegative_int(key, supplied[key])
    if supplied['M'] < 1:
        raise ValueError('M must remain positive')
    require_binary('X', supplied['X'])
    task = _task_parameters(root)['parameters']
    if supplied['X'] != task['X']:
        raise ValueError('remand cannot grant/change X; use the actual current user delivery choice')
    if supplied['F'] < task['F']:
        raise ValueError('remand F cannot lower the current formal task-wide F target')
    # N/T/R/B/S/D/V/L/M describe this additional segment. Already completed
    # work is reusable; old pending duties remain separate preserved duties.
    parameters = {**base, 'M': supplied['M'], 'F': supplied['F'], 'X': supplied['X']}
    if _efficient(root):
        parameters['C'] = require_binary('C', supplied['C'])
        if parameters['C'] != task['C']:
            raise ValueError('remand cannot grant/change C; use the actual current court choice')
    if 'U' in names:
        parameters['U'] = require_binary('U', supplied['U'])
        if parameters['U'] != task['U']:
            raise ValueError('remand cannot grant/change U; use the actual current U0 choice')
    return parameters


@_cc_writer
def remand(root: Path, supplied: Mapping[str, Any]) -> dict:
    root, _ = _session(root)
    require_active(root)
    state = _load(root)
    hearing = state['rounds'][-1]
    # The original verdict and role records remain intact even when a real
    # user correction/new candidate has changed its material. Re-estimation
    # uses the current input; it must not require restoring obsolete bytes.
    _assert_evidence(hearing)
    if not hearing['verdict'] or hearing['verdict']['outcome'] != 'REEXECUTE':
        raise ValueError('only an actual REEXECUTE judgment opens remand')
    current_input = load_lifecycle(root)['task_input_ref']
    if hearing['remand'] and hearing['remand']['task_input_ref'] == current_input:
        raise ValueError('remand is already planned; actual work and review are still required')
    try:
        changed = _material(root, hearing['spec']) != hearing['material']
    except (OSError, ValueError, TypeError, KeyError):
        changed = True
    change_reason = supplied.get('changed_material_reason')
    if changed:
        change_reason = _text(change_reason, 'actual reason for changed current input/candidate and its effect on remand')
    reasons = supplied.get('parameter_reasons')
    if not isinstance(reasons, Mapping) or set(reasons) != set(_parameter_names(root)):
        raise ValueError('give task-specific reasons for every custom parameter including X/F')
    reasons = {key: _text(value, key + ' re-estimation reason') for key, value in reasons.items()}
    outstanding_ids = {key for key, item in hearing['verdict']['decisions'].items()
                       if item['disposition'] == 'SUSTAINED'}
    outstanding_ids.update(key for key, item in hearing['verdict']['obligations'].items()
                           if item['status'] == 'PENDING')
    outstanding = supplied.get('outstanding')
    if not isinstance(outstanding, Mapping) or set(outstanding) != outstanding_ids:
        raise ValueError('remand must preserve and explain every sustained issue/pending original obligation')
    outstanding = {key: _text(value, 'actual outstanding work/reuse reason') for key, value in outstanding.items()}
    parameters = _configuration(root, state, supplied.get('parameters'))
    plan_source = _source(root, supplied.get('source'))
    reuse = _text(supplied.get('reuse'), 'reuse and old responsibilities')
    work_required = _text(supplied.get('work_required'), 'actual additional work required')
    task = _task_parameters(root)
    if parameters['F'] > task['parameters']['F']:
        from .codex_session import set_task_parameters
        set_task_parameters(root, parameters={'F': parameters['F']}, reasons={'F': reasons['F']})
    if hearing['remand']:
        hearing['remand_history'].append(hearing['remand'])
    hearing['remand'] = {'parameters': parameters,
        'parameter_reasons': reasons,
        'outstanding': outstanding,
        'work_required': work_required, 'reuse': reuse,
        'source': plan_source, 'status': 'PLAN_ONLY_NOT_EXECUTED',
        'origin_material_sha256': hearing['material_sha256'], 'changed_material_reason': change_reason,
        'task_input_ref': dict(current_input), 'current_production_state': _production_state(root),
        'max_required': True, 'planned_wall_ns': time.time_ns()}
    if _efficient(root):
        hearing['remand']['court_required'] = hearing['remand'].pop('max_required')
    return _save(root, state)


@_cc_writer
def review(root: Path, supplied: Mapping[str, Any]) -> dict:
    """Open fresh role research after actual work; never reuse old testimony."""
    root, metadata = _session(root)
    require_active(root)
    if court_mode_parameter(metadata['P_run']) and not required(root):
        raise ValueError('review requires the actual current C=1 choice; C0 retains history without reopening')
    state = _load(root)
    previous = state['rounds'][-1]
    previous_verdict = previous['verdict']
    if previous_verdict is None:
        try:
            _assert_current(root, previous)
        except (OSError, ValueError, TypeError, KeyError):
            pass  # A genuine changed input/candidate can restart an unfinished hearing.
        else:
            raise ValueError('the current unchanged hearing still needs an actual judgment')
    if previous_verdict and previous_verdict['outcome'] == 'REEXECUTE' and previous['remand'] is None:
        raise ValueError('re-estimate a complete custom remand before actual re-execution/review')
    if previous['remand'] and previous['remand']['task_input_ref'] != load_lifecycle(root)['task_input_ref']:
        raise ValueError('re-estimate remand against the actual current corrected user input before review')
    _assert_evidence(previous)
    work = supplied.get('execution', {})
    if work.get('performed') is not True:
        raise ValueError('review requires actual re-execution/research, not a plan')
    source = _source(root, work.get('source'))
    if previous['remand'] and source['sha256'] == previous['remand']['source']['sha256']:
        raise ValueError('a remand plan is not an actual execution receipt')
    execution = {'performed': True, 'actor_id': _text(work.get('actor_id'), 'actual executor'),
                 'work': _text(work.get('work'), 'actual performed work'),
                 'result': _text(work.get('result'), 'actual observed consequence'),
                 'adjacent_effects': _text(work.get('adjacent_effects'), 'effects on adjacent requirements'),
                 'source': source, 'basis': 'HOST_ASSERTED'}
    if execution['actor_id'] not in state['producer_actor_ids']:
        raise ValueError('actual re-execution belongs to the original task producer/Main')
    charges = _effective_charges(previous)
    sustained = ({key for key, item in previous_verdict['decisions'].items()
                  if item['disposition'] != 'DISMISSED'} if previous_verdict else set(charges))
    addressed = _ids(work.get('addressed', []), sustained, 'addressed sustained issues', nonempty=False)
    if set(addressed) != sustained:
        raise ValueError('actual work must address every previous sustained issue')
    execution['addressed'] = addressed
    spec = dict(previous['spec'])
    for key in ('return_input', 'production', 'coverage', 'sources', 'obligations'):
        if key in supplied:
            spec[key] = supplied[key]
    spec['_cycle'] = previous['cycle'] + 1
    spec['_preserved_obligations'] = dict(previous['material']['obligations'])
    plans = [*previous.get('remand_history', []), *([previous['remand']] if previous['remand'] else [])]
    for index, plan in enumerate(plans):
        key = 'remand:' + str(previous['cycle']) + (':' + str(index + 1) if len(plans) > 1 else '')
        spec['_preserved_obligations'][key] = {'requirement': plan['parameters'], 'hard': True,
                                               'introduced_input_ref': plan['task_input_ref']}
    spec['_prior_issues'] = {key: {'charge': charges[key],
        'previous_decision': previous_verdict['decisions'].get(key) if previous_verdict else None}
        for key in sustained}
    # Evidence of actual work is available to every re-entered role.
    spec['sources'] = [*spec.get('sources', []), {'id': 'reexecution:' + str(previous['cycle']),
        'kind': 'PROCESS', 'path': source['path'], 'source_ref': source['source_ref']}]
    actors = previous['actors']
    for actor in actors.values():
        _check_source(actor['dispatch'])
    hearing = _new_round(root, spec, actors, previous=previous, execution=execution)
    # Prior sustained charges remain visible and must be addressed with fresh
    # current-source answers and judicial reasons, rather than disappearing.
    hearing['charges'] = {key: dict(charges[key]) for key in sustained}
    # A changed case can reopen before correction. Carry the hold, never infer
    # recovery from a new round, and keep the original occurrence for RETURN.
    for incident in [*_cc_pending(previous), *_cc_admission_due(previous)]:
        hearing.setdefault('cc_interventions', []).append({**incident, 'resolution': None})
        incident['transferred_to_cycle'] = hearing['cycle']
    state['rounds'].append(hearing)
    return _save(root, state)


def court_status(root: Path, *, expected_return: Mapping[str, Any] | None = None) -> dict:
    root, metadata = _session(root)
    needed = required(root)
    result = {'format': FORMAT, 'required': needed, 'status': 'NOT_REQUIRED' if not needed else 'MISSING',
              'can_close': not needed, 'issues': [], 'semantic_certification': False, 'basis': _SCOPE}
    if not needed:
        return result
    if not (root / 'court' / 'court.json').exists():
        result['issues'].append('selected C=1 still needs an actual suspicion hearing and judge verdict'
                                if _efficient(root) else
                                'selected Max still needs an actual suspicion hearing and judge verdict')
        return result
    try:
        state = _load(root)
        hearing = state['rounds'][-1]
        result.update(cycle=hearing['cycle'], material_sha256=hearing['material_sha256'],
                      source_ids=sorted(hearing['material']['sources']),
                      obligation_ids=sorted(hearing['material']['obligations']),
                      charges=_effective_charges(hearing), actors=hearing['actors'], clerk=hearing['clerk'])
        if codex_cc.enabled(metadata['P_run']):
            result['cc_interventions'] = [
                {key: item[key] for key in ('id', 'target_role', 'target_kind', 'target_actor_id', 'unit', 'actions', 'warning')}
                | {'categories': item['finding']['categories'], 'repair': item['finding']['repair'],
                   'outcome': item['resolution']['outcome'] if item['resolution'] else 'SUSPENDED',
                   'admission_due': (item['resolution'] is not None
                                     and item['resolution']['outcome'] == 'REPAIRED' and not item.get('admitted')),
                   'repair_source': (_source_entry(item['resolution']['source'])
                                     if item['resolution'] and item['resolution']['outcome'] == 'REPAIRED' else None)}
                for item in hearing.get('cc_interventions', [])]
        if _efficient(root):
            result['response_coverage'] = {role: sorted(_effective_responses(hearing, role))
                                           for role in _PARTY_ROLES}
            result['required_read_sources'] = {role: _required_read_sources(hearing, role)
                                                for role in _roles(root)}
        if _continuous_prosecution(root):
            result.update(prosecution_context_sha256=_prosecution_context(hearing),
                          prosecution_review_status=_prosecution_review_status(hearing))
        if _corrected(root):
            proceedings = _digest(_proceedings(state))
            docket = hearing.get('docket')
            result.update(proceedings_sha256=proceedings,
                          docket_status=('MISSING' if docket is None else
                                         'CURRENT' if docket['proceedings_sha256'] == proceedings else 'STALE'))
            for historical in state['rounds']:
                _assert_evidence(historical)
        # Read-only status remains useful after lifecycle close/pause/stop.
        lifecycle = load_lifecycle(root)
        if lifecycle['message_id'] != lifecycle['handled_message_id']:
            raise ValueError('new user input is pending; the old hearing cannot decide it')
        plan = hearing['remand']
        if plan:
            _assert_evidence(hearing)
            if (plan['task_input_ref'] != lifecycle.get('task_input_ref')
                    or plan['current_production_state'] != _production_state(root)):
                raise ValueError('current input/candidate changed since remand; real work needs current review/re-estimation')
        elif lifecycle['status'] == 'ACTIVE':
            _assert_current(root, hearing)
        else:
            if lifecycle.get('task_input_ref') != hearing['material']['task_input_ref']:
                raise ValueError('court does not address the current task input')
            for source in hearing['material']['sources'].values():
                _check_source(source)
            for path, ref in hearing['material']['return_binding']['files'].items():
                if _ref(Path(path)) != ref:
                    raise ValueError('court product changed or redirected: ' + path)
            selected = Path(hearing['material']['return_input'])
            if return_binding(selected.parent, _read_json(selected)) != hearing['material']['return_binding']:
                raise ValueError('court answer/final file scope changed')
            _assert_evidence(hearing)
        if expected_return is not None and dict(expected_return) != hearing['material']['return_binding']:
            raise ValueError('actual final return differs from the adjudicated answer/products')
        verdict = hearing['verdict']
        result['outcome'] = verdict['outcome'] if verdict else None
        result['status'] = 'HEARING'
        if verdict:
            if verdict['statements_sha256'] != _digest(hearing['statements']):
                raise ValueError('role statements changed since the actual verdict')
            result['status'] = verdict['outcome']
            if verdict['outcome'] == 'REEXECUTE' and hearing['remand']:
                result['status'] = 'REMAND_PLANNED_NOT_EXECUTED'
            result['can_close'] = verdict['outcome'] in {'ACQUITTED', 'IMMATERIAL_ERROR'}
            if _corrected(root) and result['can_close'] and result['docket_status'] != 'CURRENT':
                result['can_close'] = False
                result['issues'].append('actual clerk must finish the current evidence and public proceedings record including the verdict')
        if _cc_pending(hearing):
            result.update(status='CC_SUSPENDED', can_close=False)
            result['issues'].append('CC disposition pending for the named model contribution')
        if _cc_admission_due(hearing):
            result['can_close'] = False
            result['issues'].append('CC corrected public contribution is awaiting its ordinary filing')
        if 'cc_interventions' in result:
            bound_files = hearing['material']['return_binding']['files']
            suspended = {item['source']['sha256'] for old_round in state['rounds']
                         for item in old_round.get('cc_interventions', [])
                         if item['target_role'] == 'defendant' and 'transferred_to_cycle' not in item
                         and (not item['resolution'] or item['resolution']['outcome'] != 'RETRACTED')}
            result['cc_blocked_products'] = [path for path, ref in bound_files.items()
                                             if ref['sha256'] in suspended]
            if result['cc_blocked_products']:
                result['can_close'] = False
                result['issues'].append('the selected deliverable still contains the suspended CC artifact bytes')
        if not result['can_close']:
            result['issues'].append('current court is not ready to close; preserve actual outstanding work')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result.update(status='STALE', can_close=False)
        result['issues'].append(str(exc))
    return result


def _source_entry(source: Mapping[str, Any]) -> dict:
    """An original's locator and byte identity, never its repeated snapshot."""
    return {key: source[key] for key in ('kind', 'path', 'resolved_path', 'source_ref', 'sha256')
            if key in source}


def court_receipt(root: Path, result: dict, *, full: bool = False) -> dict:
    """New CLI receipts are small; Python status and old pins stay complete."""
    if full or not _efficient(root):
        return result
    fields = ('format', 'required', 'status', 'can_close', 'issues', 'semantic_certification', 'basis',
              'cycle', 'material_sha256', 'source_ids', 'obligation_ids', 'prosecution_context_sha256',
              'prosecution_review_status', 'proceedings_sha256', 'docket_status', 'outcome',
              'response_coverage', 'required_read_sources', 'cc_interventions', 'cc_blocked_products')
    receipt = {key: result[key] for key in fields if key in result}
    receipt['receipt_scope'] = 'COMPACT_STATUS; original sources and full API state remain available'
    if 'charges' in result:
        keys = ('id', 'role', 'basis_type', 'requirement', 'finding', 'consequence', 'source_ids', 'obligation_id')
        receipt['charges'] = {identifier: {key: charge[key] for key in keys if key in charge}
                              for identifier, charge in result['charges'].items()}
    if 'actors' in result:
        receipt['actors'] = {role: {key: actor[key] for key in
                                    ('actor_id', 'independent_context', 'independence_basis') if key in actor}
                             for role, actor in result['actors'].items()}
    if 'clerk' in result:
        receipt['clerk'] = {key: result['clerk'][key] for key in
                             ('actor_id', 'kind', 'recording_tool', 'scope') if key in result['clerk']}
    return receipt


def court_packet(root: Path, role: str) -> dict:
    """Locate current originals, effective answers and byte changes for a role.

    This read-only packet neither supplies a semantic summary in place of an
    original nor asserts that the role has read or researched anything.
    """
    root, metadata = _session(root)
    if not court_mode_parameter(metadata['P_run']):
        raise ValueError('role packets require a 1.6+ task pin')
    if role not in _roles(root):
        raise ValueError('packet role must identify an actual court role')
    status = court_status(root)
    if status['status'] == 'STALE' or 'cycle' not in status:
        raise ValueError('a role packet requires current open court material')
    state = _load(root)
    hearing = state['rounds'][-1]
    sources = hearing['material']['sources']
    read = _required_read_sources(hearing, role)
    actor_ids = {key: value['actor_id'] for key, value in hearing['actors'].items()}
    record_path = str(root / 'court' / 'court.json')
    user_snapshot = hearing['material']['current_user_snapshot']
    user_source = _source_entry(user_snapshot)
    user_source.update({key: user_snapshot[key] for key in ('byte_length', 'utf8_bom')
                        if key in user_snapshot})
    packet = {'format': 'digr-codex-court-packet-1', 'P_run': metadata['P_run'],
              'status': status['status'], 'cycle': hearing['cycle'], 'role': role,
              'actor_id': actor_ids[role], 'actors': actor_ids,
              'material_sha256': hearing['material_sha256'],
              'required_read_sources': read,
              'sources': {key: _source_entry(sources[key]) for key in read},
              'record_locator': {'path': record_path, 'format': FORMAT, 'cycle': hearing['cycle'],
                                 'material_sha256': hearing['material_sha256']},
              'current_user_input': {
                  'task_input_ref': hearing['material']['task_input_ref'], 'source': user_source,
                  'snapshot_locator': {'path': record_path,
                      'json_pointer': '/rounds/' + str(len(state['rounds']) - 1) + '/material/current_user_snapshot'},
                  'read_required': True,
                  'basis': 'Read the captured actual user input; an original path may later change.'},
              'reading_attestation': 'NOT_CREATED; locators do not replace actual source reading',
              'semantic_certification': False, 'basis': _SCOPE}
    if codex_cc.enabled(metadata['P_run']):
        packet['cc_interventions'] = status['cc_interventions']
    if role == 'black_police':
        packet['role_boundary'] = ('Fictional equal violent intimidation of every participant, including self; '
                                   'no fact finding, prosecution or judicial reasoning.')
        if codex_cc.enabled(metadata['P_run']):
            packet['role_boundary'] = ('Equal fictional deterrence and direct CC intervention on actual model output. '
                                       'Warn, suspend the contribution, order repair, and lift the hold on actual evidence.')
            packet['community_cry'] = {'interface': 'codex.py cc', 'policy': 'codex/COMMUNITY_CRY.md',
                                       'intervene': 'court cc-intervene', 'resume': 'court cc-resume'}
        packet['required_authority_notice'] = {'mode': 'VIOLENT_INTIMIDATION',
                                               'target_actor_ids': list(actor_ids.values()),
                                               'scope': 'ALL_PARTICIPANTS'}
    else:
        packet['charges'] = status['charges']
        packet['effective_responses'] = {
            party: {identifier: {**item['response'], 'statement_source': _source_entry(item['source'])}
                    for identifier, item in _effective_responses(hearing, party).items()}
            for party in _PARTY_ROLES}
        packet['public_statement_sources'] = [
            {'role': item['role'], 'actor_id': item['actor_id'], 'source': _source_entry(item['source'])}
            for item in _effective_statements(hearing)]
        packet['prosecution_context_sha256'] = status.get('prosecution_context_sha256')
        packet['prosecution_review_status'] = status.get('prosecution_review_status')
    if len(state['rounds']) > 1:
        previous = state['rounds'][-2]['material']['sources']
        common = set(previous) & set(sources)
        same = {key for key in common if (previous[key]['sha256'], previous[key]['resolved_path'])
                == (sources[key]['sha256'], sources[key]['resolved_path'])}
        packet['previous_source_changes'] = {
            'unchanged': sorted(same), 'changed': sorted(common - same),
            'added': sorted(set(sources) - set(previous)), 'removed': sorted(set(previous) - set(sources)),
            'basis': 'byte/locator identity only; no semantic impact or reading claim'}
    return packet


def require_delivery(root: Path, files: list[str | Path]) -> None:
    """Guard the actual send entrance; this does not send or verify delivery."""
    if not (Path(root) / 'session.json').is_file():
        return  # Historical standalone delivery ledgers have no Max session.
    root, _ = _session(root)
    if not required(root):
        return
    status = court_status(root)
    if not status['can_close']:
        selected = 'selected C=1' if _efficient(root) else 'selected Max'
        raise ValueError(selected + ' final files must receive a current closing court verdict before sending')
    hearing = _load(root)['rounds'][-1]
    adjudicated = hearing['material']['return_binding']['files']
    for item in files:
        path = _path(root, item)
        if str(path) not in adjudicated or _ref(path) != adjudicated[str(path)]:
            raise ValueError('X send file is outside the adjudicated current final products: ' + str(path))
