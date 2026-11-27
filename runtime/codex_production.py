"""Bind a native and a Claude candidate to one current task assignment."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from . import codex_collaboration, codex_consult as consult, codex_io
from .codex_lifecycle import content_message, load_lifecycle, require_active, _validate_snapshot
from .codex_session import _session

FORMAT = 'digr-codex-production-1'
SCOPE_LABEL = 'SHARED PRODUCTION ASSIGNMENT'
NATIVE_LABEL = 'NATIVE CANDIDATE'
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')
_IDENTITY = ('task_uuid', 'P_run', 'task_request_sha256')
_OPEN = {'DISPATCHED', 'NATIVE_RETURNED'}
_RELEASED = {'FALLBACK_ACCEPTED', 'SUPERSEDED'}


def enabled(p_run: str) -> bool:
    return codex_collaboration._since(p_run, (1, 1, 0))


def production_model(p_run: str, model: Any) -> bool:
    return isinstance(model, str) and codex_collaboration.authorized_model(p_run, model)


def _task(root: Path, *, active: bool = False) -> tuple[Path, dict, dict]:
    root, session = _session(root)
    if not enabled(session['P_run']):
        raise ValueError('Dual production requires a Stable 1.1+ task pin')
    lifecycle = require_active(root) if active else load_lifecycle(root)
    return root, session, lifecycle


def _identity(session: Mapping[str, Any]) -> dict:
    task_binding = consult._task_binding(session, 'consult_guidance')
    return {key: task_binding[key] for key in _IDENTITY}


def _base(root: Path) -> Path:
    base = (root / 'productions').resolve()
    if base.parent != root or base.name.casefold() != 'productions':
        raise ValueError('Production collection escapes or aliases its task')
    return base


def _writer(root: Path):
    from .codex_council import _writer as state_writer
    return state_writer(_base(root))


def _directory(root: Path, production_id: str) -> Path:
    if not isinstance(production_id, str) or not _ID.fullmatch(production_id):
        raise ValueError('Production id must be a simple local identifier')
    base = _base(root)
    directory = (base / production_id).resolve()
    if directory.parent != base or directory.name.casefold() != production_id.casefold():
        raise ValueError('Production path escapes its task or aliases another assignment')
    return directory


def _seal(directory: Path, path: Path, name: str, *, text: bool) -> dict:
    info, raw = consult._source(path, name)
    if text:
        consult._text(name, raw.decode('utf-8-sig'))
    elif not raw:
        raise ValueError('Applied production output cannot be empty')
    target = directory / (name if text else _final_name(info['sha256']))
    output = {'path': info['path'], 'snapshot_path': target.as_posix(),
              'sha256': info['sha256'], 'byte_length': info['byte_length']}
    if not text and target.exists():
        _snapshot_path(directory, output, target.name)
    else:
        consult._write_bytes(target, raw)
    return output


def _final_name(digest: str) -> str:
    if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Invalid applied output fingerprint')
    return f'final-{digest}.artifact'


def _snapshot_path(directory: Path, record: Mapping[str, Any], name: str) -> Path:
    path = (directory / name).resolve()
    if path.parent != directory or record['snapshot_path'] != path.as_posix():
        raise ValueError('Production artifact snapshot path changed')
    raw = codex_io.read_bytes(path)
    if len(raw) != record['byte_length'] or consult._hash(raw) != record['sha256']:
        raise ValueError('Sealed production artifact changed: ' + name)
    return path


def _state(root: Path, session: Mapping[str, Any], production_id: str) -> tuple[Path, dict]:
    directory = _directory(root, production_id)
    state = consult._read(directory / 'production.json')
    if (state.get('format') != FORMAT or state.get('production_id') != production_id
            or any(state.get(key) != value for key, value in _identity(session).items())
            or state.get('status') not in _OPEN | _RELEASED | {'APPLIED'}):
        raise ValueError('Production identity or status differs from its frozen task')
    source = state['input_source']
    _validate_snapshot(source)
    if (state['input_ref']['source_ref'] != source['source_ref']
            or state['input_ref']['sha256'] != source['sha256']
            or state['scope_sha256'] != state['scope']['sha256']):
        raise ValueError('Production input or scope fingerprint changed')
    status = state['status']
    if ((status == 'DISPATCHED' and state['native'] is not None)
            or (status in {'NATIVE_RETURNED', 'APPLIED'} and state['native'] is None)
            or (status in _RELEASED) != (state['release'] is not None)
            or (status == 'APPLIED' and state['applied'] is None)
            or (state['applied'] is not None and status not in {'APPLIED', 'SUPERSEDED'})):
        raise ValueError('Production disposition has inconsistent evidence')
    return directory, state


def _current(state: Mapping[str, Any], lifecycle: Mapping[str, Any]) -> bool:
    return (lifecycle['status'] == 'ACTIVE'
            and lifecycle['handled_message_id'] == lifecycle['message_id']
            and lifecycle['claude_policy']['mode'] == 'ALLOW'
            and (lifecycle.get('latest_claude_revocation_message_id') or 0) <= state['admitted_message_id']
            and consult._input_ref(lifecycle) == state['input_ref'])


def _require_current_state(state: Mapping[str, Any], lifecycle: Mapping[str, Any]) -> None:
    if state['status'] not in _OPEN:
        raise ValueError('Production assignment already has a recorded disposition')
    if not _current(state, lifecycle):
        raise ValueError('Production assignment no longer matches the current content input or Claude choice')


def start(root: Path, production_id: str, *, scope_path: Path, actor: str, dispatch_ref: str,
          paper_root: Path | None = None) -> dict:
    """Record the actual native dispatch and freeze its shared UTF-8 assignment."""
    root, session, _ = _task(root, active=True)
    actor = consult._text('native actor', actor)
    if actor.strip().casefold() == 'main':
        raise ValueError('Use the actual independent native actor, separate from Main')
    dispatch_ref = consult._text('actual native dispatch reference', dispatch_ref)
    directory = _directory(root, production_id)
    with _writer(root):
        lifecycle = require_active(root)
        codex_collaboration.require_claude_permission(session['P_run'], consult.DEFAULT_MODEL, lifecycle)
        if (directory / 'production.json').exists():
            raise ValueError('Production assignment already exists; inspect its actual state')
        authoring_scope = (consult._selected_paper(root, session, paper_root)[0]
                           if paper_root is not None else None)
        directory.mkdir(exist_ok=True)
        scope = _seal(directory, scope_path, 'scope.md', text=True)
        state = {'format': FORMAT, **_identity(session), 'production_id': production_id,
                 'input_ref': consult._input_ref(lifecycle), 'admitted_message_id': lifecycle['handled_message_id'],
                 'input_source': dict(content_message(lifecycle)['source']),
                 'lifecycle_revision': lifecycle['revision'], 'scope': scope, 'scope_sha256': scope['sha256'],
                 'native_actor': actor, 'dispatch_ref': dispatch_ref, 'created_at': consult._now(),
                 'authoring_scope': authoring_scope, 'status': 'DISPATCHED', 'native': None,
                 'applied': None, 'release': None}
        consult._write(directory / 'production.json', state)
    return inspect(root, production_id)


def submit_native(root: Path, production_id: str, *, actor: str, output_path: Path, return_ref: str) -> dict:
    """Seal the actual assigned native actor's usable candidate."""
    root, session, _ = _task(root, active=True)
    return_ref = consult._text('actual native return reference', return_ref)
    with _writer(root):
        lifecycle = require_active(root)
        directory, state = _state(root, session, production_id)
        _require_current_state(state, lifecycle)
        if actor != state['native_actor'] or state['status'] != 'DISPATCHED':
            raise ValueError('Only the assigned native actor can seal its first complete candidate')
        _snapshot_path(directory, state['scope'], 'scope.md')
        output = _seal(directory, output_path, 'native.md', text=True)
        state.update(status='NATIVE_RETURNED',
                     native={'return_ref': return_ref, 'output': output, 'returned_at': consult._now()})
        consult._write(directory / 'production.json', state)
    return inspect(root, production_id)


def _candidate_binding(state: Mapping[str, Any]) -> dict:
    fields = (*_IDENTITY, 'production_id', 'input_ref', 'scope_sha256',
              'native_actor', 'dispatch_ref', 'authoring_scope')
    return {**{key: state[key] for key in fields}, 'stage': 'candidate'}


def _verify_request(binding: Mapping[str, Any], paths: list[Path], request: Mapping[str, Any]) -> None:
    model = request.get('model')
    if not production_model(binding['P_run'], model) or (binding['stage'] == 'arbitration' and model != binding['model']):
        raise ValueError('Production requires the same supported collaborator across candidate and arbitration')
    messages = request.get('messages', [])
    latest = messages[-1] if isinstance(messages, list) and messages else None
    if not isinstance(latest, Mapping) or latest.get('role') != 'user':
        raise ValueError('Production request lacks its actual current user materials')
    content = latest.get('content')
    parts = []
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = [item['text'] for item in content if isinstance(item, Mapping)
                 and item.get('type') == 'text' and isinstance(item.get('text'), str)]
    for path, digest, label in [(paths[0], binding['scope_sha256'], SCOPE_LABEL)] + (
            [(paths[1], binding['native_sha256'], NATIVE_LABEL)] if binding['stage'] == 'arbitration' else []):
        info, raw = consult._source(path, label)
        block = consult._source_text(info, raw.decode('utf-8-sig'), label=label)
        if info['sha256'] != digest or not any(block in part for part in parts):
            raise ValueError('Production request omits or changes the actual ' + label.lower())
    if binding['stage'] == 'arbitration':
        raw = codex_io.read_bytes(paths[2])
        expected = {'role': 'assistant', 'content': raw.decode('utf-8')}
        if len(messages) < 2 or messages[-2] != expected or consult._hash(raw) != binding['candidate_public_sha256']:
            raise ValueError('Arbitration must replay the actual complete Claude candidate')


def _receipt(directory: Path, attempt: Mapping[str, Any], request: Mapping[str, Any],
             binding: Mapping[str, Any], paths: list[Path]) -> dict:
    if (attempt.get('production') != binding or attempt.get('input_ref') != binding['input_ref']
            or attempt.get('participation_role') != 'consult_guidance'
            or attempt.get('authoring_scope') != binding['authoring_scope']
            or not codex_collaboration.observed_model_matches(
                binding['P_run'], request.get('model'), attempt.get('response_model'))
            or attempt.get('transport_status') != 'RESPONDED' or attempt.get('public_status') != 'COMPLETE'
            or attempt.get('finish_reason') != 'stop' or attempt.get('http_status') != 200):
        raise ValueError('Production requires a complete actual Claude return in the same task and scope')
    if binding['stage'] == 'arbitration' and (
            attempt.get('parent_exchange') != binding['candidate_exchange']
            or attempt.get('parent_request_sha256') != binding['candidate_request_sha256']):
        raise ValueError('Arbitration is not a continuation of the selected Claude candidate')
    _verify_request(binding, paths, request)
    path = directory / 'public.md'
    raw = codex_io.read_bytes(path)
    digest = consult._hash(raw)
    if not raw.decode('utf-8').strip() or attempt.get('public_sha256') != digest:
        raise ValueError('Production requires the actual complete Claude public body')
    return {'exchange_id': attempt['exchange_id'], 'request_sha256': attempt['request_sha256'],
            'public_sha256': digest, 'public_path': path.as_posix(), 'model': attempt['response_model'],
            'generation_id': attempt.get('generation_id')}


def _binding(root: Path, directory: Path, state: Mapping[str, Any], stage: str,
             candidate_exchange: str | None) -> tuple[dict, list[Path]]:
    binding = _candidate_binding(state)
    scope_path = _snapshot_path(directory, state['scope'], 'scope.md')
    if stage == 'candidate' and candidate_exchange is None:
        return binding, [scope_path]
    if stage != 'arbitration' or candidate_exchange is None:
        raise ValueError('Production requires candidate stage or arbitration with its candidate exchange')
    if state['native'] is None:
        raise ValueError('Arbitration requires the actual assigned native candidate first')
    native = state['native']['output']
    native_path = _snapshot_path(directory, native, 'native.md')
    candidate_dir, candidate_attempt, candidate_request = consult._load(root, candidate_exchange)
    candidate = _receipt(candidate_dir, candidate_attempt, candidate_request, binding, [scope_path])
    binding.update(stage=stage, candidate_exchange=candidate['exchange_id'],
                   candidate_request_sha256=candidate['request_sha256'],
                   candidate_public_sha256=candidate['public_sha256'], model=candidate_request['model'],
                   native_sha256=native['sha256'], native_return_ref=state['native']['return_ref'])
    return binding, [scope_path, native_path, Path(candidate['public_path'])]


def bind_exchange(root: Path, production_id: str, *, stage: str,
                  candidate_exchange: str | None = None) -> tuple[dict, list[Path]]:
    """Read only. Arbitration requires both actual candidates before preparation."""
    root, session, lifecycle = _task(root, active=True)
    directory, state = _state(root, session, production_id)
    _require_current_state(state, lifecycle)
    if state['authoring_scope'] is not None:
        actual, _, _ = consult._selected_paper(root, session, Path(state['authoring_scope']['paper_root']))
        if actual != state['authoring_scope']:
            raise ValueError('Selected production paper scope changed')
    return _binding(root, directory, state, stage, candidate_exchange)


def require_current(root: Path, binding: Mapping[str, Any], *, request: Mapping[str, Any] | None = None) -> dict:
    """Fence preparation and dispatch against the exact current scope and bytes."""
    if not isinstance(binding, Mapping):
        raise ValueError('Missing production binding')
    expected, paths = bind_exchange(root, binding.get('production_id'), stage=binding.get('stage'),
                                    candidate_exchange=binding.get('candidate_exchange'))
    if expected != binding:
        raise ValueError('Production binding differs from its current sealed sources')
    if request is not None:
        _verify_request(expected, paths, request)
    return expected


def _arbitration(root: Path, directory: Path, state: Mapping[str, Any], exchange_id: str) -> tuple[dict, dict]:
    returned, attempt, request = consult._load(root, exchange_id)
    recorded = attempt.get('production')
    if not isinstance(recorded, Mapping) or recorded.get('stage') != 'arbitration':
        raise ValueError('Applying production requires an actual scoped Claude arbitration')
    binding, paths = _binding(root, directory, state, 'arbitration', recorded.get('candidate_exchange'))
    return _receipt(returned, attempt, request, binding, paths), binding


def _peer_arbitrations(root: Path, directory: Path, state: Mapping[str, Any],
                       model: str, exchanges: Sequence[str]) -> list[dict]:
    if not exchanges:
        return []
    p_run = state['P_run']
    if not codex_collaboration.parallel_external_policy(p_run):
        raise ValueError('Paired production requires Codex 1.7.0+')
    peers = []
    models = {model}
    roster = set(codex_collaboration.external_models(p_run).values())
    if len(exchanges) >= len(roster):
        raise ValueError('Each collaborator can contribute at most one arbitration')
    for exchange in exchanges:
        receipt, binding = _arbitration(root, directory, state, exchange)
        if binding['model'] in models:
            raise ValueError('Peer arbitrations must come from distinct external collaborators')
        models.add(binding['model'])
        peers.append({'arbitration': receipt, 'binding': binding})
    if not models <= roster:
        raise ValueError('Peer arbitrations must use the collaborators of the frozen task pin')
    return peers


def record_applied(root: Path, production_id: str, *, arbitration_exchange: str,
                   output_path: Path, effect: str, peer_exchange: str | Sequence[str] | None = None) -> dict:
    """Record how the actual Claude arbitration was implemented in the final bytes."""
    root, session, _ = _task(root, active=True)
    effect = consult._text('actual effect of arbitration on the final output', effect)
    with _writer(root):
        lifecycle = require_active(root)
        directory, state = _state(root, session, production_id)
        previous = state['applied']
        if state['status'] == 'APPLIED':
            if (state['input_ref'] != consult._input_ref(lifecycle)
                    or previous['arbitration']['exchange_id'] != arbitration_exchange):
                raise ValueError('Reapplying requires the same current assignment and arbitration')
            _snapshot_path(directory, previous['output'], _final_name(previous['output']['sha256']))
        else:
            _require_current_state(state, lifecycle)
        receipt, binding = _arbitration(root, directory, state, arbitration_exchange)
        peer_ids = [peer_exchange] if isinstance(peer_exchange, str) else list(peer_exchange or ())
        peers = _peer_arbitrations(root, directory, state, binding['model'], peer_ids)
        if previous is not None and (receipt != previous['arbitration'] or binding != previous['binding']
                                     or peers != _saved_peers(previous)):
            raise ValueError('Applied production arbitration provenance changed')
        output = _seal(directory, output_path, 'final', text=False)
        history = list(previous['previous_outputs']) if previous is not None else []
        if previous is not None and output != previous['output']:
            history.append({key: previous[key] for key in ('output', 'effect', 'applied_at', 'message_id')})
        state.update(status='APPLIED', applied={'arbitration': receipt, 'binding': binding,
            'output': output, 'effect': effect, 'applied_at': consult._now(),
            'message_id': lifecycle['handled_message_id'], 'previous_outputs': history})
        if peers:
            if codex_collaboration.flex_collaboration_policy(session['P_run']):
                state['applied']['peers'] = peers
            else:
                state['applied']['peer'] = peers[0]
        consult._write(directory / 'production.json', state)
    return inspect(root, production_id)


def release(root: Path, production_id: str, *, disposition: str, source: str, quote: str, effect: str,
            replacement_production_id: str | None = None) -> dict:
    """Record an actual later user choice to accept fallback or replace the scope."""
    root, session, _ = _task(root, active=True)
    quote = consult._text('exact user quotation', quote)
    effect = consult._text('actual consequence of the user choice', effect)
    with _writer(root):
        lifecycle = require_active(root)
        directory, state = _state(root, session, production_id)
        message = lifecycle['current_message']
        snapshot = message['source']
        since = state['admitted_message_id']
        if state['status'] == 'APPLIED' and disposition == 'superseded':
            since = state['applied']['message_id']
        elif state['status'] not in _OPEN:
            raise ValueError('Production already has a recorded disposition')
        if (message['id'] <= since
                or source != snapshot['source_ref'] or quote not in snapshot['text']
                or message.get('handling', {}).get('action') == 'budget'
                or message['surface'] in {'HELP', 'INVALID', 'ROUTE_PENDING'}):
            raise ValueError('Release requires a later handled user source for this production assignment')
        replacement_digest = None
        if disposition == 'superseded' and replacement_production_id not in {None, production_id}:
            _, replacement = _state(root, session, replacement_production_id)
            if (not _current(replacement, lifecycle)
                    or replacement['status'] in _RELEASED
                    or replacement['authoring_scope'] != state['authoring_scope']
                    or (replacement['input_ref'] == state['input_ref']
                        and replacement['scope_sha256'] == state['scope_sha256'])):
                raise ValueError('Supersession requires a different current assignment in the same production scope')
            status = 'SUPERSEDED'
            replacement_digest = consult._hash(consult._json_bytes(_candidate_binding(replacement)))
        elif disposition == 'fallback' and replacement_production_id is None:
            status = 'FALLBACK_ACCEPTED'
        else:
            raise ValueError('Use fallback, or superseded with an actual replacement production id')
        state.update(status=status, release={'message_id': message['id'], 'user_source': dict(snapshot),
            'quote': quote, 'replacement_production_id': replacement_production_id,
            'replacement_sha256': replacement_digest, 'effect': effect, 'released_at': consult._now()})
        consult._write(directory / 'production.json', state)
    return inspect(root, production_id)


def _saved_peers(applied: Mapping[str, Any]) -> list[dict]:
    return [applied['peer']] if applied.get('peer') is not None else applied.get('peers', [])


def _original_matches(output: Mapping[str, Any]) -> bool:
    try:
        raw = codex_io.read_bytes(Path(output['path']))
    except OSError:
        return False
    return consult._hash(raw) == output['sha256']


def _inspect(root: Path, session: Mapping[str, Any], lifecycle: Mapping[str, Any],
             production_id: str) -> dict:
    directory, state = _state(root, session, production_id)
    _snapshot_path(directory, state['scope'], 'scope.md')
    if state['native'] is not None:
        _snapshot_path(directory, state['native']['output'], 'native.md')
    output_matches = None
    if state['applied'] is not None:
        applied = state['applied']
        output = applied['output']
        _snapshot_path(directory, output, _final_name(output['sha256']))
        receipt, binding = _arbitration(root, directory, state, applied['arbitration']['exchange_id'])
        if receipt != applied['arbitration'] or binding != applied['binding']:
            raise ValueError('Applied production arbitration provenance changed')
        peers = _saved_peers(applied)
        peer_ids = [peer['arbitration']['exchange_id'] for peer in peers]
        if _peer_arbitrations(root, directory, state, binding['model'], peer_ids) != peers:
            raise ValueError('Applied peer arbitration provenance changed')
        if state['status'] == 'APPLIED' and state['input_ref'] == consult._input_ref(lifecycle):
            output_matches = _original_matches(output)
    view = {**state, 'input_source': {key: value for key, value in state['input_source'].items() if key != 'text'}}
    if state['status'] in _RELEASED:
        choice = state['release']
        source = choice['user_source']
        _validate_snapshot(source)
        seen = lifecycle['seen_source_refs'].get(source['source_ref'])
        since = state['applied']['message_id'] if state['applied'] is not None else state['admitted_message_id']
        if (choice['message_id'] <= since or not choice['quote']
                or choice['quote'] not in source['text']
                or seen != {'message_id': choice['message_id'], 'sha256': source['sha256']}):
            raise ValueError('Production release is not bound to a later actual user source')
        if state['status'] == 'SUPERSEDED':
            _, replacement = _state(root, session, choice['replacement_production_id'])
            if choice['replacement_sha256'] != consult._hash(consult._json_bytes(_candidate_binding(replacement))):
                raise ValueError('Production supersession no longer matches its actual replacement')
        view['release'] = {**choice, 'user_source': {key: value for key, value in source.items() if key != 'text'}}
    complete = state['status'] == 'APPLIED' and output_matches is not False
    return {**view, 'current': _current(state, lifecycle), 'complete': complete,
            'resolved': complete or state['status'] in _RELEASED, 'current_output_matches': output_matches}


def inspect(root: Path, production_id: str | None = None) -> dict:
    """Read production history locally, including after task closure."""
    if production_id is None:
        return completion_status(root)
    root, session, lifecycle = _task(root)
    return _inspect(root, session, lifecycle, production_id)


def require_applied(root: Path, production_id: str, *, arbitration_exchange: str | None = None) -> dict:
    """Verify actual applied bytes for a current task delivery or paper artifact."""
    root, session, lifecycle = _task(root, active=True)
    item = _inspect(root, session, lifecycle, production_id)
    applied = item['applied']
    if item['status'] != 'APPLIED' or item['input_ref'] != consult._input_ref(lifecycle):
        raise ValueError('Delivery requires a current applied production arbitration')
    exchanges = {applied['arbitration']['exchange_id']}
    exchanges.update(peer['arbitration']['exchange_id'] for peer in _saved_peers(applied))
    if arbitration_exchange is not None and arbitration_exchange not in exchanges:
        raise ValueError('Delivery requires a current applied production arbitration')
    if item['current_output_matches'] is not True:
        raise ValueError('Current final artifact differs from the applied production output')
    return applied


def completion_status(root: Path) -> dict:
    root, session = _session(root)
    productions = []
    if enabled(session['P_run']):
        lifecycle = load_lifecycle(root)
        productions = [_inspect(root, session, lifecycle, record.parent.name)
                       for record in sorted(_base(root).glob('*/production.json'))]
    unresolved = [item['production_id'] for item in productions if not item['resolved']]
    return {'complete': not unresolved, 'unresolved_productions': unresolved, 'productions': productions}
