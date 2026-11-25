"""Source-bound Max hearings, not an actor scheduler or a semantic judge.

The host supplies real dispatches, public statements and a judge's reasons.
Independent execution, reading, completion and judgments remain HOST_ASSERTED.
This helper checks identities, provenance, current bytes and the return path;
it never invents an accusation, performs rework or generates an acquittal.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping

from .codex_lifecycle import load_lifecycle, require_active
from .codex_session import _effective_main_target, _parameters, _read_json, _session, _write_json
from .validation import require_binary, require_nonempty_text, require_nonnegative_int

FORMAT = 'digr-codex-court-1'
ROLES = ('defendant', 'judge', 'prosecutor', 'lawyer', 'monitor')
OUTCOMES = ('ACQUITTED', 'IMMATERIAL_ERROR', 'REEXECUTE', 'INCOMPLETE')
PARAMETERS = ('N', 'T', 'R', 'B', 'S', 'D', 'V', 'L', 'M', 'F', 'X')
_LINE_PARAMETERS = frozenset({'N', 'T', 'R', 'B', 'S', 'D', 'V', 'L'})
_LEGAL_BASES = {'REQUIREMENT', 'LOGIC', 'IMPLEMENTATION', 'PRODUCT', 'PERMISSION', 'PROTOCOL'}
_SCOPE = 'HOST_ASSERTED actors, reading, execution and judicial reasons; structural/source checks only'


def enabled(p_run: str) -> bool:
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', p_run)
    return bool(match and tuple(map(int, match.groups())) >= (1, 5, 0))


def required(root: Path) -> bool:
    """Max is a selected, sticky task preference, never inferred from N."""
    root, metadata = _session(root)
    if not enabled(metadata['P_run']):
        return False
    if (metadata.get('parameter_selection') or {}).get('preset') == 'Max':
        return True
    return load_lifecycle(root).get('max_court_required') is True


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
    return {'task': {key: metadata.get(key) for key in _TASK_FIELDS},
            'M_target': metadata['M_target'], 'task_input_ref': lifecycle['task_input_ref'],
            'max_court_required': lifecycle.get('max_court_required', False),
            'max_court_source': lifecycle.get('max_court_source'),
            'task_parameters': _task_parameters(root),
            'delivery_policy': lifecycle.get('delivery_policy'),
            'files': {str(path): _ref(path) for path in sorted(files)},
            'directory_candidates': directories}


def _task_parameters(root: Path) -> dict:
    from .codex_session import task_parameters
    task = task_parameters(root)
    if task is None or task['parameters']['F'] is None:
        raise ValueError('infer the actual task F before opening a Max court')
    return task


def _actors(root: Path, supplied: Mapping[str, Any], producers: list[str]) -> dict:
    if not isinstance(supplied, Mapping) or set(supplied) != set(ROLES):
        raise ValueError('map actual defendant/judge/prosecutor/lawyer/monitor actors')
    actors = {}
    for role in ROLES:
        item = supplied[role]
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
    return {'lines': {name: line['parameters'] for name, line in lines.items()},
            'M': metadata['M_target'], 'F': task['parameters']['F'],
            'X': task['parameters']['X'], 'explicit': metadata['explicit_parameters']}


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
    return {'cycle': 1 if previous is None else previous['cycle'] + 1,
            'spec': spec, 'material': material, 'material_sha256': _digest(material),
            'actors': actors, 'clerk': {'actor_id': 'codex-court-file-tool', 'kind': 'ACTUAL_TOOL',
                                      'scope': 'records only; no independent semantic actor claim'},
            'statements': [], 'charges': {}, 'verdict': None, 'remand': None,
            'remand_history': [],
            'execution': execution, 'opened_wall_ns': time.time_ns(), 'basis': _SCOPE}


def open_court(root: Path, supplied: Mapping[str, Any]) -> dict:
    root, metadata = _session(root)
    require_active(root)
    if not required(root):
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
    for old_plan in hearing.get('remand_history', []):
        _check_source(old_plan['source'])
    if hearing.get('execution'):
        _check_source(hearing['execution']['source'])


def submit_statement(root: Path, supplied: Mapping[str, Any]) -> dict:
    root, _ = _session(root)
    require_active(root)
    state = _load(root)
    hearing = state['rounds'][-1]
    _assert_current(root, hearing)
    if hearing['verdict']:
        raise ValueError('a decided round needs review before further statements')
    role = supplied.get('role')
    if role not in ROLES or supplied.get('actor_id') != hearing['actors'][role]['actor_id']:
        raise ValueError('statement must come from this role\'s actual actor')
    if supplied.get('material_sha256') != hearing['material_sha256']:
        raise ValueError('statement must address the current material_sha256')
    read = _ids(supplied.get('read_sources'), hearing['material']['sources'], 'read_sources')
    if set(read) != set(hearing['material']['sources']):
        raise ValueError('each actual actor must declare reading the original/current common material')
    statement = {'role': role, 'actor_id': supplied['actor_id'],
                 'material_sha256': hearing['material_sha256'], 'read_sources': read,
                 'statement': _text(supplied.get('statement'), 'actual public statement'),
                 'source': _source(root, supplied.get('source')), 'basis': 'HOST_ASSERTED',
                 'responses': [], 'submitted_wall_ns': time.time_ns()}
    additions = {}
    for charge in _list(supplied.get('charges', []), 'charges'):
        if role not in {'prosecutor', 'monitor'}:
            raise ValueError('only the actual prosecutor/monitor may lodge charges')
        charge = dict(charge)
        identifier = _text(charge.get('id'), 'charge id')
        if identifier in hearing['charges'] or identifier in additions:
            raise ValueError('charge ids cannot overwrite or erase an earlier accusation')
        if charge.get('basis_type') not in _LEGAL_BASES | {'METHOD_PREFERENCE'}:
            raise ValueError('charge needs a stated obligation/logic/product basis or METHOD_PREFERENCE')
        for key in ('requirement', 'finding', 'consequence'):
            charge[key] = _text(charge.get(key), 'charge ' + key)
        charge['source_ids'] = _ids(charge.get('source_ids'), hearing['material']['sources'], 'charge sources')
        if charge.get('obligation_id') is not None and charge['obligation_id'] not in hearing['material']['obligations']:
            raise ValueError('charge obligation_id must identify a preserved actual obligation')
        charge['role'] = role
        additions[identifier] = charge
    for response in _list(supplied.get('responses', []), 'responses'):
        if response.get('charge_id') not in hearing['charges']:
            raise ValueError('response must identify an existing charge')
        statement['responses'].append({'charge_id': response['charge_id'],
            'response': _text(response.get('response'), 'actual reasoned answer'),
            'source_ids': _ids(response.get('source_ids'), hearing['material']['sources'], 'answer sources')})
    hearing['charges'].update(additions)
    hearing['statements'].append(statement)
    return _save(root, state)


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
    latest = {item['role']: item for item in hearing['statements']}
    if set(latest) != set(ROLES):
        raise ValueError('all actual roles need current public statements before judgment')
    for role in ('defendant', 'lawyer'):
        if {item['charge_id'] for item in latest[role]['responses']} != set(hearing['charges']):
            raise ValueError(role + ' must answer every actual charge before judgment')
    outcome = supplied.get('outcome')
    if outcome not in OUTCOMES:
        raise ValueError('unsupported actual court outcome')
    decisions = {}
    for item in _list(supplied.get('decisions'), 'reasoned charge decisions'):
        identifier = item.get('charge_id')
        if identifier not in hearing['charges'] or identifier in decisions:
            raise ValueError('judge must decide each actual charge exactly once')
        charge = hearing['charges'][identifier]
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
    if set(decisions) != set(hearing['charges']):
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
    hearing['verdict'] = {'actor_id': supplied['actor_id'], 'outcome': outcome,
        'material_sha256': hearing['material_sha256'], 'statements_sha256': _digest(hearing['statements']),
        'decisions': decisions, 'obligations': obligations,
        'reasons': _text(supplied.get('reasons'), 'actual judge reasons for the whole case'),
        'source': _source(root, supplied.get('source')), 'basis': 'HOST_ASSERTED',
        'recorded_wall_ns': time.time_ns()}
    return _save(root, state)


def _configuration(root: Path, state: dict, supplied: Mapping[str, Any]) -> dict:
    if not isinstance(supplied, Mapping) or set(supplied) != set(PARAMETERS):
        raise ValueError('re-estimate complete N/T/R/B/S/D/V/L/M/F/X custom parameters')
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
    return {**base, 'M': supplied['M'], 'F': supplied['F'], 'X': supplied['X']}


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
    if not isinstance(reasons, Mapping) or set(reasons) != set(PARAMETERS):
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
    return _save(root, state)


def review(root: Path, supplied: Mapping[str, Any]) -> dict:
    """Open fresh role research after actual work; never reuse old testimony."""
    root, _ = _session(root)
    require_active(root)
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
    sustained = ({key for key, item in previous_verdict['decisions'].items()
                  if item['disposition'] != 'DISMISSED'} if previous_verdict else set(previous['charges']))
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
    spec['_prior_issues'] = {key: {'charge': previous['charges'][key],
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
    hearing['charges'] = {key: dict(previous['charges'][key]) for key in sustained}
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
        result['issues'].append('selected Max still needs an actual suspicion hearing and judge verdict')
        return result
    try:
        state = _load(root)
        hearing = state['rounds'][-1]
        result.update(cycle=hearing['cycle'], material_sha256=hearing['material_sha256'],
                      source_ids=sorted(hearing['material']['sources']),
                      obligation_ids=sorted(hearing['material']['obligations']),
                      charges=hearing['charges'], actors=hearing['actors'], clerk=hearing['clerk'])
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
        if not result['can_close']:
            result['issues'].append('current court has no closing verdict; preserve actual outstanding work')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result.update(status='STALE', can_close=False)
        result['issues'].append(str(exc))
    return result


def require_delivery(root: Path, files: list[str | Path]) -> None:
    """Guard the actual send entrance; this does not send or verify delivery."""
    if not (Path(root) / 'session.json').is_file():
        return  # Historical standalone delivery ledgers have no Max session.
    root, _ = _session(root)
    if not required(root):
        return
    status = court_status(root)
    if not status['can_close']:
        raise ValueError('selected Max final files must receive a current closing court verdict before sending')
    hearing = _load(root)['rounds'][-1]
    adjudicated = hearing['material']['return_binding']['files']
    for item in files:
        path = _path(root, item)
        if str(path) not in adjudicated or _ref(path) != adjudicated[str(path)]:
            raise ValueError('X send file is outside the adjudicated current final products: ' + str(path))
