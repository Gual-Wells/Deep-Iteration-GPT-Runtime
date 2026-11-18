"""One native council, with a bounded Claude subcouncil and honest reentry.

This is a host-level context gate, not an OS access-control system or a proof of
independent thought. Native actor IDs are supplied by the actual host. The host
still relays public model output to the user and performs native research.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Sequence
import uuid

from . import codex_io

FORMAT = 'digr-native-council-1'
TERMINAL = frozenset({'COMPLETE', 'PARTIAL', 'FAILED', 'BUDGET_STOPPED', 'TIMEOUT',
                      'CANCELLED', 'OUTCOME_UNKNOWN'})
ROUND_KINDS = frozenset({'INDEPENDENT', 'CROSS', 'FINAL', 'REENTRY'})
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')
_SCOPE_KEYS = frozenset({'council_id', 'member_id', 'line_id', 'cycle_id',
                          'input_version', 'packet_sha256', 'round_id', 'round_kind'})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def _hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _read(path: Path) -> dict:
    value = json.loads(codex_io.read_bytes(path).decode('utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Council record must be an object')
    return value


def _write(path: Path, value: Any, *, new: bool = False) -> None:
    raw = _bytes(value)
    if new:
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return
    replacement = path.with_name(path.name + '.new-' + uuid.uuid4().hex)
    try:
        _write(replacement, value, new=True)
        codex_io.replace(replacement, path)
    finally:
        replacement.unlink(missing_ok=True)


def _id(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value) or value in {'.', '..'}:
        raise ValueError(name + ' must be a simple local identifier of 1 to 64 characters')
    return value


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ' must be nonempty text')
    return value


def _task(root: Path, *, active: bool = False) -> tuple[Path, dict, dict]:
    from .codex_session import _session
    from .codex_lifecycle import load_lifecycle, require_active
    root, session = _session(Path(root))
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)@[0-9a-f]{40}', session['P_run'])
    if not version or tuple(map(int, version.groups())) < (0, 16, 0):
        raise ValueError('Council requires a 0.16+ frozen Codex profile; old pins retain their semantics')
    lifecycle = require_active(root) if active else load_lifecycle(root)
    return root, session, lifecycle


def _input_ref(lifecycle: Mapping[str, Any]) -> dict:
    message = lifecycle['current_message']
    return {'message_id': message['id'], 'sha256': message['source']['sha256'],
            'source_ref': message['source']['source_ref']}


def _directory(root: Path, council_id: str) -> Path:
    _id('council_id', council_id)
    base = (Path(root).resolve() / 'councils').resolve()
    directory = (base / council_id).resolve()
    if not directory.is_relative_to(base):
        raise ValueError('Council path escapes the task')
    return directory


@contextmanager
def _writer(directory: Path):
    """A short, OS-released lock; no model/network work is done inside it."""
    directory.mkdir(parents=True, exist_ok=True)
    stream = (directory / '.writer.lock').open('a+b')
    stream.seek(0, 2)
    if not stream.tell():
        stream.write(b'0')
        stream.flush()
    stream.seek(0)
    try:
        until = time.monotonic() + 5
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= until:
                    raise ValueError('Another council state writer is active; retry the local operation') from None
                time.sleep(.01)
        yield
    finally:
        stream.close()


def _load(root: Path, council_id: str, *, active: bool = False) -> tuple[Path, dict, dict]:
    root, session, lifecycle = _task(root, active=active)
    directory = _directory(root, council_id)
    state = _read(directory / 'council.json')
    if (state.get('format') != FORMAT or state.get('council_id') != council_id
            or state.get('P_run') != session['P_run']
            or state.get('task_request_sha256') != session['request_sha256']):
        raise ValueError('Council identity differs from the frozen task')
    if active and state['phase'] == 'CLOSED':
        raise ValueError('Council is closed')
    _packet(directory, state, state['input_version'])
    return directory, state, lifecycle


def _snapshot(path: Path, kind: str) -> dict:
    path = Path(path).resolve()
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    _text('actual source', text)
    return {'kind': kind, 'name': path.name, 'path': path.as_posix(),
            'sha256': _hash(raw), 'byte_length': len(raw), 'text': text}


def _packet(directory: Path, state: Mapping[str, Any], version: int) -> dict:
    if type(version) is not int or version < 1 or version > len(state['packets']):
        raise ValueError('Unknown council input version')
    record = state['packets'][version - 1]
    raw = (directory / record['path']).read_bytes()
    if _hash(raw) != record['sha256']:
        raise ValueError('Frozen council packet changed')
    packet = json.loads(raw)
    if packet['input_version'] != version or packet['council_id'] != state['council_id']:
        raise ValueError('Frozen council packet identity changed')
    return packet


def _save_packet(directory: Path, state: dict, sources: list[dict], lifecycle: dict) -> None:
    version = len(state['packets']) + 1
    packet = {'format': 'digr-council-common-input-1', 'council_id': state['council_id'],
              'input_version': version, 'input_ref': _input_ref(lifecycle), 'sources': sources,
              'scope': 'exact shared facts and constraints; host must exclude initial-side opinions'}
    name = 'packet-' + str(version) + '.json'
    _write(directory / name, packet, new=True)
    state['packets'].append({'path': name, 'sha256': _hash(_bytes(packet)),
                             'input_ref': packet['input_ref']})
    state['input_version'] = version


def _allow(lifecycle: Mapping[str, Any]) -> None:
    if lifecycle.get('claude_policy', {}).get('mode') != 'ALLOW':
        raise ValueError('Claude council members are disabled by the current task choice; native council remains usable')


def _cycle(state: dict) -> dict:
    return state['cycles'][state['cycle_id'] - 1]


def _obligations(cycle: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    """Each native actor owes its own reconsideration, even before initial ends."""
    native = set(cycle['native']) - set(cycle['redeliberation'])
    members = {member for member, side in cycle['members'].items() if side['status'] not in TERMINAL}
    return native, members


def _valid_migration(state: Mapping[str, Any], cycle: Mapping[str, Any]) -> bool:
    resolution = cycle.get('resolution') or {}
    destination = resolution.get('to_cycle_id')
    if (resolution.get('status') != 'MIGRATED' or type(destination) is not int
            or destination <= cycle['cycle_id'] or destination > len(state['cycles'])):
        return False
    native, members = _obligations(cycle)
    target = state['cycles'][destination - 1]
    return (set(resolution.get('native_actors', [])) == native
            and set(resolution.get('members', [])) == members
            and native <= set(target['native']) and members <= set(target['members']))


def _new_cycle(state: dict, *, native_actors: Sequence[str], members: Sequence[str], deadline_seconds: int,
               event_ids: Sequence[int] = ()) -> None:
    cycle_id = len(state['cycles']) + 1
    state['cycle_id'] = cycle_id
    state['phase'] = 'INITIAL'
    state['cycles'].append({'cycle_id': cycle_id, 'input_version': state['input_version'],
        'started_at': _now(), 'deadline_at': (datetime.now(timezone.utc) + timedelta(seconds=deadline_seconds)).isoformat(),
        'native': {actor: {'status': 'PENDING', 'output': None} for actor in native_actors},
        'members': {member: {'status': 'PENDING', 'exchange_id': None} for member in members},
        'barrier': None, 'redeliberation': {}, 'event_ids': list(event_ids)})


def create_council(root: Path, *, council_id: str, native_actors: Sequence[str],
                   facts_path: Path | None = None, materials: Sequence[Path] = (),
                   enable_claude: bool = False, member_count: int = 2,
                   deadline_seconds: int = 300) -> dict:
    """Create a real native work object. A single colon never enables Claude."""
    root, session, lifecycle = _task(root, active=True)
    _id('council_id', council_id)
    actors = list(native_actors)
    if not actors or len(actors) != len(set(actors)):
        raise ValueError('Supply distinct actual native actor IDs')
    for actor in actors:
        _id('native actor', actor)
    if type(member_count) is not int or member_count < 1 or member_count > 16:
        raise ValueError('member_count must be 1 to 16; this is a resource bound, not a native V count')
    if type(deadline_seconds) is not int or deadline_seconds < 1:
        raise ValueError('deadline_seconds must be a positive integer')
    if enable_claude:
        _allow(lifecycle)
    directory = _directory(root, council_id)
    with _writer(directory):
        if (directory / 'council.json').exists():
            raise ValueError('Council already exists; resume its research line or choose a new identity')
        sources = [_snapshot(root / 'REQUEST.txt', 'HISTORICAL_TASK_ORIGIN'),
                   {'kind': 'CURRENT_USER_INPUT', **dict(lifecycle['current_message']['source'])}]
        if facts_path is not None:
            sources.append(_snapshot(facts_path, 'ACCEPTED_FACTS_AND_CONSTRAINTS'))
        sources.extend(_snapshot(path, 'SOURCE_MATERIAL') for path in materials)
        members = {f'member-{index + 1}': {'line_id': council_id + '/member-' + str(index + 1),
            'exchanges': [], 'research_state': None, 'last_researched_input_version': None}
            for index in range(member_count)} if enable_claude else {}
        state = {'format': FORMAT, 'council_id': council_id, 'P_run': session['P_run'],
            'task_request_sha256': session['request_sha256'], 'created_at': _now(),
            'isolation': 'HOST_LEVEL', 'actor_authority': 'HOST_ASSERTED_NOT_OS_AUTHENTICATED',
            'native_actors': actors, 'members': members, 'claude_enabled': enable_claude,
            'deadline_seconds': deadline_seconds, 'packets': [], 'cycles': [], 'rounds': [],
            'events': [], 'late_results': [], 'native_responsibility_credit': False}
        _save_packet(directory, state, sources, lifecycle)
        _new_cycle(state, native_actors=actors, members=list(members), deadline_seconds=deadline_seconds)
        _write(directory / 'council.json', state, new=True)
    return inspect_council(root, council_id)


def inspect_council(root: Path, council_id: str) -> dict:
    """Metadata and statuses only; no cross-side opinion bodies leak here."""
    directory, state, lifecycle = _load(root, council_id)
    return {'council_id': council_id, 'P_run': state['P_run'], 'phase': state['phase'],
            'cycle_id': state['cycle_id'], 'input_version': state['input_version'],
            'packet_sha256': state['packets'][-1]['sha256'], 'isolation': state['isolation'],
            'actor_authority': state['actor_authority'], 'native_actors': state['native_actors'],
            'members': {key: {'line_id': value['line_id'], 'exchanges': value['exchanges'],
                             'last_researched_input_version': value['last_researched_input_version']}
                        for key, value in state['members'].items()},
            'cycle': _cycle(state), 'rounds': state['rounds'],
            'cycle_history': [{'cycle_id': cycle['cycle_id'], 'input_version': cycle['input_version'],
                'resolution': cycle.get('resolution'), 'unreturned_native_actors': sorted(_obligations(cycle)[0]),
                'unsealed_members': sorted(_obligations(cycle)[1])} for cycle in state['cycles']],
            'pending_events': [event for event in state['events'] if event['status'] != 'PROCESSED'],
            'late_results': state['late_results'],
            'current_input_changed': state['packets'][-1]['input_ref'] != _input_ref(lifecycle),
            'local_path': directory.as_posix(), 'native_responsibility_credit': False}


def _artifact(directory: Path, path: Path, *, name: str, kind: str) -> dict:
    raw = Path(path).read_bytes()
    text = raw.decode('utf-8-sig')
    _text(kind, text)
    destination = directory / name
    with destination.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'kind': kind, 'path': name, 'sha256': _hash(raw), 'byte_length': len(raw)}


def _artifact_text(directory: Path, record: Mapping[str, Any]) -> str:
    path = (directory / record['path']).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError('Council artifact path escapes its directory')
    raw = path.read_bytes()
    if _hash(raw) != record['sha256']:
        raise ValueError('Sealed council public artifact changed')
    return raw.decode('utf-8-sig')


def submit_native_initial(root: Path, council_id: str, *, actor: str, output_path: Path | None = None,
                          status: str = 'COMPLETE', input_version: int | None = None) -> dict:
    advance_barrier(root, council_id)
    directory, _, _ = _load(root, council_id, active=True)
    with _writer(directory):
        _, state, lifecycle = _load(root, council_id, active=True)
        cycle = _cycle(state)
        if state['phase'] != 'INITIAL' or actor not in cycle['native']:
            raise ValueError('Only an assigned native initial actor can seal its current initial work')
        if input_version != state['input_version']:
            raise ValueError('Native return must name the exact current input_version')
        if state['packets'][-1]['input_ref'] != _input_ref(lifecycle):
            raise ValueError('Publish the relevant new user input before returning current native work')
        if status not in TERMINAL or cycle['native'][actor]['status'] != 'PENDING':
            raise ValueError('Native initial work is already sealed or status is not terminal')
        if status == 'COMPLETE' and output_path is None:
            raise ValueError('Complete native work needs its actual public artifact')
        output = (_artifact(directory, output_path, name=f'native-{state["cycle_id"]}-{actor}.txt',
                            kind='NATIVE_INITIAL_PUBLIC') if output_path is not None else None)
        cycle['native'][actor] = {'status': status, 'output': output, 'sealed_at': _now(),
                                   'input_version': state['input_version']}
        for event in state['events']:
            if event['id'] in cycle['event_ids'] and actor in event['native_actors']:
                event.setdefault('native_reentries', {})[actor] = {'status': status,
                    'cycle_id': state['cycle_id'], 'input_version': state['input_version']}
        _write(directory / 'council.json', state)
    return advance_barrier(root, council_id)


def require_member_scope(root: Path, scope: Mapping[str, Any], *, active: bool = True,
                         exchange_id: str | None = None) -> dict:
    """Validate an exact member/line/cycle/packet/round binding for Consult."""
    if not isinstance(scope, Mapping) or set(scope) != _SCOPE_KEYS:
        raise ValueError('Council member scope has an invalid schema')
    directory, state, lifecycle = _load(root, scope['council_id'], active=active)
    member = state['members'].get(scope['member_id'])
    if member is None or member['line_id'] != scope['line_id']:
        raise ValueError('Unknown council member research line')
    for key in ('cycle_id', 'input_version', 'round_id'):
        if type(scope[key]) is not int or scope[key] < 1:
            raise ValueError('Council scope ' + key + ' must be a positive integer')
    if (scope['cycle_id'] > len(state['cycles']) or scope['round_id'] > len(state['rounds'])
            or scope['input_version'] > len(state['packets'])):
        raise ValueError('Unknown council cycle or round')
    round_record = state['rounds'][scope['round_id'] - 1]
    if (scope['round_kind'] not in ROUND_KINDS or scope['round_kind'] != round_record['kind']
            or scope['cycle_id'] != round_record['cycle_id']
            or scope['input_version'] != round_record['input_version']
            or scope['member_id'] not in round_record['jobs']
            or scope['packet_sha256'] != state['packets'][scope['input_version'] - 1]['sha256']):
        raise ValueError('Council member scope differs from its frozen round')
    if (exchange_id is not None
            and round_record['jobs'][scope['member_id']]['exchange_id'] != exchange_id):
        raise ValueError('Council member exchange is not the one registered for this round')
    _packet(directory, state, scope['input_version'])
    if active:
        _allow(lifecycle)
        if (state['cycle_id'] != scope['cycle_id'] or state['input_version'] != scope['input_version']
                or state['phase'] != 'INITIAL' or round_record['status'] not in {'PREPARING', 'PREPARED', 'RUNNING'}
                or state['packets'][-1]['input_ref'] != _input_ref(lifecycle)):
            raise ValueError('Council member request is stale, sealed or needs a current-input reentry')
        if datetime.now(timezone.utc) >= datetime.fromisoformat(_cycle(state)['deadline_at']):
            raise ValueError('Council deadline reached; seal known work without starting another paid request')
    return dict(scope)


def member_deadline(root: Path, scope: Mapping[str, Any]) -> str:
    require_member_scope(root, scope, active=False)
    _, state, _ = _load(root, scope['council_id'])
    return state['cycles'][scope['cycle_id'] - 1]['deadline_at']


_MEMBER_PROMPT = (
    'Work as one research member inside the native council. First explore the '
    'actual sources and choose a worthwhile problem; do not adopt a generic '
    'review role. You may discover a dominating premise or a strong alternative '
    'that competes for the whole route. Develop the alternative with actual '
    'research, comparison, argument or supplied trial evidence, stating what '
    'it replaces and under what conditions. A contrary slogan is insufficient. '
    'After independent exploration, negotiate a domain with real semantic '
    'distance, select its materials/questions/methods, and develop substantive '
    'work. Keep unresolved questions, source identities, objections and relevant '
    'reentry triggers. Continue that same line when relevant new material arrives; '
    'saving this conversation alone is not evidence of continuous research. '
    'Request missing evidence naturally; the host obtains it and must actually '
    'supply it. Never claim to have read local paths or run tools. Only supplied '
    'public messages are shared. Your own proposal is not a formal Consult '
    'instruction and carries no guidance priority. Do not manage native counters '
    'or engineering bookkeeping. Return useful public work, with your own '
    'compression when a final synthesis is requested; preserve the decisive '
    'conditions and objections. Do not expose hidden reasoning.'
)


def _exchange_public(root: Path, exchange_id: str) -> tuple[dict, str | None]:
    from . import codex_consult as consult
    directory, attempt, _ = consult._load(Path(root).resolve(), exchange_id)
    body = (directory / 'public.md').read_text(encoding='utf-8') if attempt.get('public_sha256') else None
    return attempt, body


def prepare_round(root: Path, council_id: str, *, kind: str = 'INDEPENDENT',
                  members: Sequence[str] | None = None, model: str | None = None,
                  effort: str | None = None, max_tokens: int | None = None) -> dict:
    """Prepare explicit member requests; no credentials, Split invention or send.

    The host performs and binds an actual Split separately for every exchange.
    Other members' complete public replies are passed verbatim, without a Main
    summary. No native initial opinion is passed to the subcouncil.
    """
    from . import codex_consult as consult
    advance_barrier(root, council_id)
    directory, _, _ = _load(root, council_id, active=True)
    kind = str(kind).upper()
    if kind not in ROUND_KINDS:
        raise ValueError('Unknown council round kind')
    with _writer(directory):
        _, state, lifecycle = _load(root, council_id, active=True)
        _allow(lifecycle)
        cycle = _cycle(state)
        if not state['claude_enabled'] or state['phase'] != 'INITIAL':
            raise ValueError('This council has no active Claude member work')
        if state['packets'][-1]['input_ref'] != _input_ref(lifecycle):
            raise ValueError('Publish the relevant new input before preparing member reentry')
        if any(record['status'] in {'PREPARING', 'PREPARED', 'RUNNING'}
               and record['cycle_id'] == state['cycle_id'] for record in state['rounds']):
            raise ValueError('A council round is already pending; run or seal it before another round')
        selected = list(members) if members is not None else list(cycle['members'])
        if not selected or len(selected) != len(set(selected)) or any(mid not in cycle['members'] for mid in selected):
            raise ValueError('Select distinct active member IDs from this cycle')
        previous = [record for record in state['rounds'] if record['cycle_id'] == state['cycle_id']]
        if not previous and kind != ('INDEPENDENT' if state['cycle_id'] == 1 else 'REENTRY'):
            raise ValueError('Start with independent exploration, or same-line reentry in a later cycle')
        if previous and kind in {'INDEPENDENT', 'REENTRY'}:
            raise ValueError('Later rounds must exchange public work or request a final synthesis')
        if any(cycle['members'][mid]['status'] in TERMINAL for mid in selected):
            raise ValueError('Member is sealed for this cycle; publish a relevant event for reentry')
        round_id = len(state['rounds']) + 1
        jobs = {}
        for member_id in selected:
            scope = {'council_id': council_id, 'member_id': member_id,
                'line_id': state['members'][member_id]['line_id'], 'cycle_id': state['cycle_id'],
                'input_version': state['input_version'], 'packet_sha256': state['packets'][-1]['sha256'],
                'round_id': round_id, 'round_kind': kind}
            exchange_id = 'c-' + _hash(_bytes(scope))[:32]
            jobs[member_id] = {'scope': scope, 'exchange_id': exchange_id, 'status': 'PREPARING'}
        record = {'round_id': round_id, 'kind': kind, 'cycle_id': state['cycle_id'],
            'input_version': state['input_version'], 'status': 'PREPARING', 'created_at': _now(), 'jobs': jobs}
        state['rounds'].append(record)
        _write(directory / 'council.json', state)
    failures = {}
    for member_id, job in jobs.items():
        try:
            _, current, _ = _load(root, council_id, active=True)
            packet = _packet(directory, current, job['scope']['input_version'])
            parts = [_MEMBER_PROMPT, '\nROUND: ' + kind,
                     '\nEXACT COMMON INPUT PACKET:\n' + json.dumps(packet, ensure_ascii=False, indent=2)]
            if kind in {'CROSS', 'FINAL', 'REENTRY'}:
                parts.append('\nSOURCE-IDENTIFIED PUBLIC RESEARCH; absent replies are not positions:')
                for peer_id, member in current['members'].items():
                    for exchange in member['exchanges']:
                        attempt, body = _exchange_public(root, exchange)
                        if body is not None:
                            parts.append('\n--- PUBLIC MEMBER ' + peer_id + ' / ' + exchange
                                         + ' status=' + attempt['public_status'] + ' ---\n' + body
                                         + '\n--- END PUBLIC MEMBER ---')
            if kind == 'FINAL':
                parts.append('\nProduce your own public synthesis. Preserve the decisive reasons, '
                    'strong alternatives, domain, unresolved objections and specific reentry triggers.')
            input_path = directory / f'round-{round_id}-{member_id}-input.txt'
            with input_path.open('x', encoding='utf-8', newline='') as stream:
                stream.write('\n'.join(parts))
            previous_exchange = current['members'][member_id]['exchanges'][-1:] or [None]
            kwargs = {'participation_role': 'council_member', 'council_scope': job['scope'],
                      'continue_from': previous_exchange[0], 'exchange_id': job['exchange_id']}
            if model is not None:
                kwargs['model'] = model
            if effort is not None:
                kwargs['effort'] = effort
            if max_tokens is not None:
                kwargs['max_tokens'] = max_tokens
            consult.prepare_request(root, input_path=input_path, **kwargs)
            job['status'] = 'PREPARED'
        except (OSError, ValueError, KeyError, TypeError) as error:
            job['status'] = 'PREPARE_FAILED'
            failures[member_id] = str(error)
    with _writer(directory):
        _, state, _ = _load(root, council_id)
        record = state['rounds'][round_id - 1]
        record['jobs'] = jobs
        record['prepare_errors'] = failures
        record['status'] = 'PREPARED' if any(job['status'] == 'PREPARED' for job in jobs.values()) else 'FAILED'
        for member_id, job in jobs.items():
            if job['status'] == 'PREPARE_FAILED':
                _cycle(state)['members'][member_id]['status'] = 'FAILED'
        _write(directory / 'council.json', state)
    return inspect_council(root, council_id)


def run_round(root: Path, council_id: str, *, round_id: int,
              jobs: Mapping[str, Mapping[str, Any]],
              on_public_event: Callable[[dict], None] | None = None) -> dict:
    """Run one prepared batch with actual parallel bounded Consult requests.

    Each member job supplies its own actual facts, ceiling_usd and bound
    split_path. Shared-account reservations and per-exchange claims remain in
    Consult. A local error is recorded, never automatically retried.
    """
    from . import codex_consult as consult
    directory, _, _ = _load(root, council_id, active=True)
    with _writer(directory):
        _, state, _ = _load(root, council_id, active=True)
        if type(round_id) is not int or round_id < 1 or round_id > len(state['rounds']):
            raise ValueError('Unknown council round')
        record = state['rounds'][round_id - 1]
        ready = {mid for mid, job in record['jobs'].items() if job['status'] == 'PREPARED'}
        if record['status'] != 'PREPARED' or set(jobs) != ready:
            raise ValueError('Supply exactly the prepared member jobs; an attempted batch cannot be replayed')
        for member_id in ready:
            require_member_scope(root, record['jobs'][member_id]['scope'])
            if not isinstance(jobs[member_id], Mapping) or not {'facts', 'ceiling_usd', 'split_path'} <= set(jobs[member_id]):
                raise ValueError('Every member needs current facts, ceiling_usd and its actual Split plan')
        record['status'] = 'RUNNING'
        record['started_at'] = _now()
        _write(directory / 'council.json', state)

    def invoke(member_id: str) -> tuple[str, dict]:
        job = jobs[member_id]
        exchange_id = record['jobs'][member_id]['exchange_id']
        emit = ((lambda event: on_public_event({'source': 'claude_subcouncil', 'member_id': member_id,
                    'council_id': council_id, 'round_id': round_id, **event})) if on_public_event else None)
        try:
            consult.call_once(root, exchange_id, facts=job['facts'], ceiling_usd=job['ceiling_usd'],
                split_path=Path(job['split_path']),
                config_path=Path(job['config_path']) if job.get('config_path') else None,
                on_public_event=emit)
            attempt, _ = _exchange_public(root, exchange_id)
            status = ('COMPLETE' if attempt['public_status'] == 'COMPLETE' else
                      'PARTIAL' if attempt['public_status'] == 'PARTIAL' else
                      'OUTCOME_UNKNOWN' if attempt['transport_status'] == 'OUTCOME_UNKNOWN' else 'FAILED')
            return member_id, {'status': status, 'transport_status': attempt['transport_status'],
                'public_status': attempt['public_status'], 'billing_status': attempt['billing_status'],
                'known_cost_usd': attempt.get('known_cost_usd'), 'reserved_usd': attempt.get('reserved_usd'),
                'exchange_id': exchange_id}
        except (OSError, ValueError, KeyError, TypeError) as error:
            return member_id, {'status': 'FAILED', 'error': str(error), 'error_class': type(error).__name__,
                               'exchange_id': exchange_id,
                               'billing_status': 'INSPECT_EXCHANGE_BEFORE_RETRY'}

    def record_outcome(member_id: str, outcome: dict) -> None:
        with _writer(directory):
            _, current, _ = _load(root, council_id)
            round_record = current['rounds'][round_id - 1]
            round_record['jobs'][member_id].update(outcome)
            member = current['members'][member_id]
            attempt, body = _exchange_public(root, outcome['exchange_id'])
            # Expire before committing late work, even if the caller has not
            # reached its timeout wakeup yet.
            _expire_cycle(current, datetime.now(timezone.utc))
            if body is not None and outcome['exchange_id'] not in member['exchanges']:
                member['exchanges'].append(outcome['exchange_id'])
                member['last_researched_input_version'] = round_record['input_version']
            if (round_record['cycle_id'] == current['cycle_id']
                    and _cycle(current)['barrier'] is None and current['phase'] == 'INITIAL'):
                side = _cycle(current)['members'][member_id]
                side['exchange_id'] = outcome['exchange_id']
                # A first complete response is not a completed research line.
                if round_record['kind'] == 'FINAL' or outcome['status'] != 'COMPLETE':
                    side['status'] = outcome['status']
                for event in current['events']:
                    if event['id'] in _cycle(current)['event_ids'] and member_id in event['members'] and body is not None:
                        event.setdefault('member_reentries', {})[member_id] = {
                            'exchange_id': outcome['exchange_id'], 'public_status': attempt['public_status'],
                            'input_version': round_record['input_version']}
                        event['research_reentry_performed'] = True
            elif body is not None:
                current['late_results'].append({'member_id': member_id, 'exchange_id': outcome['exchange_id'],
                    'cycle_id': round_record['cycle_id'], 'input_version': round_record['input_version'],
                    'at': _now(), 'status': 'PENDING_REENTRY',
                    'scope': 'late public work; old barrier and redeliberation unchanged'})
            if all(job['status'] not in {'PREPARING', 'PREPARED'} for job in round_record['jobs'].values()):
                round_record['status'] = 'FINISHED'
                round_record['finished_at'] = _now()
            _write(directory / 'council.json', current)

    def worker(member_id: str) -> None:
        identity, outcome = invoke(member_id)
        record_outcome(identity, outcome)

    pool = ThreadPoolExecutor(max_workers=len(ready), thread_name_prefix='digr-council')
    futures = [pool.submit(worker, member_id) for member_id in sorted(ready)]
    remaining = max(0.0, (datetime.fromisoformat(_cycle(state)['deadline_at'])
                          - datetime.now(timezone.utc)).total_seconds())
    completed, pending = wait(futures, timeout=remaining)
    # No context-manager shutdown(wait=True): the phase can end while transport
    # remains unknown. Callbacks preserve the original cycle when it arrives.
    pool.shutdown(wait=False)
    for future in completed:
        future.result()
    if pending:
        with _writer(directory):
            _, current, _ = _load(root, council_id)
            record = current['rounds'][round_id - 1]
            if record['status'] == 'RUNNING':
                record['status'] = 'OUTCOME_PENDING'
            _write(directory / 'council.json', current)
    return advance_barrier(root, council_id)


def seal_member(root: Path, council_id: str, *, member_id: str, status: str,
                research_path: Path | None = None) -> dict:
    """Seal actual existing work without buying an assumed-free final answer."""
    advance_barrier(root, council_id)
    directory, _, _ = _load(root, council_id, active=True)
    with _writer(directory):
        _, state, _ = _load(root, council_id, active=True)
        cycle = _cycle(state)
        if state['phase'] != 'INITIAL' or member_id not in cycle['members'] or status not in TERMINAL:
            raise ValueError('Only a current member can be sealed with a known terminal status')
        side = cycle['members'][member_id]
        if side['status'] in TERMINAL:
            raise ValueError('Member is already sealed')
        if status == 'COMPLETE' and not side['exchange_id']:
            raise ValueError('Complete member research needs an actual observed public exchange')
        side['status'] = status
        side['sealed_at'] = _now()
        if research_path is not None:
            # A host-selected public research record is resumable evidence, not
            # a claim that the member authored a host summary.
            state['members'][member_id]['research_state'] = _artifact(directory, research_path,
                name=f'research-{state["cycle_id"]}-{member_id}.txt', kind='HOST_RESEARCH_HANDOFF')
        _write(directory / 'council.json', state)
    return advance_barrier(root, council_id)


def _expire_cycle(state: dict, instant: datetime) -> None:
    cycle = _cycle(state)
    if state['phase'] != 'INITIAL':
        return
    if instant >= datetime.fromisoformat(cycle['deadline_at']):
        for side in (*cycle['native'].values(), *cycle['members'].values()):
            if side['status'] not in TERMINAL:
                side['status'] = 'TIMEOUT'
                side['sealed_at'] = instant.isoformat()
    sides = [*cycle['native'].values(), *cycle['members'].values()]
    if all(side['status'] in TERMINAL for side in sides):
        cycle['barrier'] = {'released_at': instant.isoformat(),
            'reason': 'ALL_COMPLETE' if all(side['status'] == 'COMPLETE' for side in sides) else 'EXPLICIT_ABNORMAL_TERMINALS',
            'research_complete': all(side['status'] == 'COMPLETE' for side in sides),
            'absence_is_position': False,
            'member_exchanges': {mid: list(member['exchanges']) for mid, member in state['members'].items()}}
        state['phase'] = 'REDELIBERATION'


def advance_barrier(root: Path, council_id: str, *, now: datetime | None = None) -> dict:
    """Release only the relevant phase; abnormal absence is never a vote."""
    directory, _, _ = _load(root, council_id)
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError('Barrier time needs a UTC offset')
    with _writer(directory):
        _, state, _ = _load(root, council_id)
        _expire_cycle(state, instant)
        _write(directory / 'council.json', state)
    return inspect_council(root, council_id)


def _chunks(text: str, size: int) -> list[dict]:
    if type(size) is not int or size < 1:
        raise ValueError('chunk_chars must be a positive integer')
    return [{'offset': offset, 'text': text[offset:offset + size]}
            for offset in range(0, len(text), size)]


def read_packet(root: Path, council_id: str, *, actor: str, stage: str = 'INITIAL',
                chunk_chars: int = 16000) -> dict:
    """Supply actual text under an actor gate. Chunking omits no characters."""
    directory, state, lifecycle = _load(root, council_id)
    cycle = _cycle(state)
    stage = stage.upper()
    if actor not in state['native_actors'] and actor not in state['members']:
        raise ValueError('Packet reader is not an assigned council actor')
    if stage not in {'INITIAL', 'REDELIBERATION'}:
        raise ValueError('Unknown packet stage')
    if stage == 'REDELIBERATION' and (actor not in cycle['native'] or cycle['barrier'] is None):
        raise ValueError('Only native actors may read cross-side work after the barrier releases')
    if state['packets'][-1]['input_ref'] != _input_ref(lifecycle):
        raise ValueError('Publish current user input before reading a current council packet')
    packet = _packet(directory, state, state['input_version'])
    result = {'council_id': council_id, 'actor': actor, 'stage': stage, 'cycle_id': state['cycle_id'],
        'input_version': state['input_version'], 'packet_sha256': state['packets'][-1]['sha256'],
        'isolation': state['isolation'], 'common_input': packet, 'public_work': [],
        'scope': 'host asserted actor; shared disk is not OS isolation'}
    if stage == 'REDELIBERATION':
        result['barrier'] = cycle['barrier']
        result['native_statuses'] = cycle['native']
        result['member_statuses'] = cycle['members']
        for native_id, side in cycle['native'].items():
            if side['output']:
                text = _artifact_text(directory, side['output'])
                result['public_work'].append({'source': 'native_initial', 'actor': native_id,
                    'status': side['status'], 'sha256': side['output']['sha256'], 'chunks': _chunks(text, chunk_chars)})
        for member_id, exchanges in cycle['barrier']['member_exchanges'].items():
            for exchange_id in exchanges:
                attempt, body = _exchange_public(root, exchange_id)
                if body is not None:
                    result['public_work'].append({'source': 'claude_subcouncil', 'actor': member_id,
                        'exchange_id': exchange_id, 'public_status': attempt['public_status'],
                        'transport_status': attempt['transport_status'], 'billing_status': attempt['billing_status'],
                        'known_cost_usd': attempt.get('known_cost_usd'), 'reserved_usd': attempt.get('reserved_usd'),
                        'sha256': attempt['public_sha256'], 'chunks': _chunks(body, chunk_chars)})
        result['native_duty'] = ('Independently reconsider domains and conclusions from the actual complete '
            'public work. Address substantive and strong alternative claims with reasons. '
            'Do not treat missing or partial work as support/opposition. Main relays, not selects positions.')
    return result


def submit_redeliberation(root: Path, council_id: str, *, actor: str, output_path: Path,
                          input_version: int) -> dict:
    directory, _, _ = _load(root, council_id, active=True)
    with _writer(directory):
        _, state, lifecycle = _load(root, council_id, active=True)
        cycle = _cycle(state)
        if (state['phase'] != 'REDELIBERATION' or actor not in cycle['native']
                or actor in cycle['redeliberation'] or input_version != state['input_version']):
            raise ValueError('A current assigned native actor must return its own redeliberation once')
        if state['packets'][-1]['input_ref'] != _input_ref(lifecycle):
            raise ValueError('Publish relevant current user input before redeliberation')
        output = _artifact(directory, output_path, name=f'redeliberation-{state["cycle_id"]}-{actor}.txt',
                           kind='NATIVE_REDELIBERATION_PUBLIC')
        cycle['redeliberation'][actor] = {'output': output, 'at': _now(), 'input_version': input_version}
        if set(cycle['redeliberation']) == set(cycle['native']):
            state['phase'] = 'COMPLETE'
            cycle['resolution'] = {'status': 'COMPLETE', 'at': _now(),
                                   'scope': 'actual assigned native redeliberations returned'}
            for event in state['events']:
                if event['id'] in cycle['event_ids']:
                    event['status'] = 'PROCESSED'
                    event['processed_cycle_id'] = state['cycle_id']
        _write(directory / 'council.json', state)
    return inspect_council(root, council_id)


def reenter_late_result(root: Path, council_id: str, *, exchange_id: str) -> dict:
    """Actually queue a late public result in a later cycle, without resending it."""
    from . import codex_consult as consult
    directory, state, _ = _load(root, council_id, active=True)
    if state['phase'] not in {'COMPLETE', 'REDELIBERATION'}:
        raise ValueError('Late-result reentry follows the released council phase')
    late = next((item for item in state['late_results'] if item['exchange_id'] == exchange_id
                 and item['status'] == 'PENDING_REENTRY'), None)
    if late is None:
        raise ValueError('No pending late public result with this exchange identity')
    exchange_dir, _, _ = consult._load(Path(root).resolve(), exchange_id)
    result = publish_event(root, council_id, input_path=exchange_dir / 'public.md',
                           kind='LATE_MEMBER_RESULT', members=[late['member_id']])
    with _writer(directory):
        _, state, _ = _load(root, council_id)
        for item in state['late_results']:
            if item['exchange_id'] == exchange_id:
                item['status'] = 'QUEUED'
                item['reentry_cycle_id'] = state['cycle_id']
        _write(directory / 'council.json', state)
    return inspect_council(root, council_id)


def publish_event(root: Path, council_id: str, *, input_path: Path, kind: str,
                  members: Sequence[str] | None = None, native_actors: Sequence[str] | None = None) -> dict:
    """Queue actual relevant new material and reopen the same research lines.

    This creates work to do; it does not claim reentry has already occurred or
    send a request. Old results and redeliberations keep their old identities.
    """
    directory, _, _ = _load(root, council_id, active=True)
    _text('event kind', kind)
    source = _snapshot(input_path, 'RELEVANT_EVENT_' + kind)
    with _writer(directory):
        _, state, lifecycle = _load(root, council_id, active=True)
        selected = list(members) if members is not None else list(state['members'])
        actors = list(native_actors) if native_actors is not None else list(state['native_actors'])
        if not actors or len(actors) != len(set(actors)) or any(actor not in state['native_actors'] for actor in actors):
            raise ValueError('Select actual affected native actors')
        if len(selected) != len(set(selected)) or any(mid not in state['members'] for mid in selected):
            raise ValueError('Select actual affected member lines')
        prior = _packet(directory, state, state['input_version'])
        sources = [item for item in prior['sources'] if item['kind'] != 'CURRENT_USER_INPUT']
        sources += [{'kind': 'CURRENT_USER_INPUT', **dict(lifecycle['current_message']['source'])}, source]
        _save_packet(directory, state, sources, lifecycle)
        event_id = len(state['events']) + 1
        state['events'].append({'id': event_id, 'kind': kind, 'source_sha256': source['sha256'],
            'input_version': state['input_version'], 'at': _now(), 'members': selected,
            'native_actors': actors, 'status': 'PENDING', 'research_reentry_performed': False})
        pending = [event['id'] for event in state['events'] if event['status'] != 'PROCESSED']
        # Preserve every pending obligation when successive facts arrive before
        # research can resume. A newer packet must not silently lose an actor.
        selected = sorted(set(selected).union(*(set(event['members']) for event in state['events']
                                                 if event['status'] != 'PROCESSED')))
        actors = sorted(set(actors).union(*(set(event['native_actors']) for event in state['events']
                                             if event['status'] != 'PROCESSED')))
        migrations = []
        for prior_cycle in state['cycles']:
            pending_native, pending_members = _obligations(prior_cycle)
            if (pending_native or pending_members) and not _valid_migration(state, prior_cycle):
                # Selecting only the newly affected actor must not erase an old
                # participant who has not returned its own initial/reconsidered
                # work. Move that duty to the corrected facts, not to a stale
                # packet that the actor can no longer legitimately submit.
                actors = sorted(set(actors) | pending_native)
                selected = sorted(set(selected) | pending_members)
                migrations.append((prior_cycle, pending_native, pending_members))
        _new_cycle(state, native_actors=actors, members=selected,
                   deadline_seconds=state['deadline_seconds'], event_ids=pending)
        for prior_cycle, pending_native, pending_members in migrations:
            prior_cycle['resolution'] = {'status': 'MIGRATED', 'at': _now(),
                'to_cycle_id': state['cycle_id'], 'native_actors': sorted(pending_native),
                'members': sorted(pending_members),
                'reason': 'new shared input; every unfinished initial/reconsideration duty continues in the newer cycle'}
        for record in state['rounds']:
            if record['cycle_id'] != state['cycle_id'] and record['status'] in {'PREPARING', 'PREPARED'}:
                record['status'] = 'SUPERSEDED_NOT_SENT'
                record['superseded_by_cycle_id'] = state['cycle_id']
        _write(directory / 'council.json', state)
    return inspect_council(root, council_id)


def close_council(root: Path, council_id: str, *, reason: str) -> dict:
    directory, _, _ = _load(root, council_id)
    with _writer(directory):
        _, state, _ = _load(root, council_id)
        state['closed_from_phase'] = state['phase']
        state['phase'] = 'CLOSED'
        state['closure'] = {'at': _now(), 'reason': _text('closure reason', reason),
                            'pending_work_completed': False}
        for record in state['rounds']:
            if record['status'] in {'PREPARING', 'PREPARED'}:
                record['status'] = 'CANCELLED_NOT_SENT'
            elif record['status'] in {'RUNNING', 'OUTCOME_PENDING'}:
                record['status'] = 'CLOSED_OUTCOME_UNKNOWN'
                record['transport_resolution_pending'] = True
        for cycle in state['cycles']:
            if any(_obligations(cycle)) and not _valid_migration(state, cycle):
                native, members = _obligations(cycle)
                cycle['resolution'] = {'status': 'CLOSED_WITH_UNFINISHED_WORK', 'at': _now(),
                    'reason': reason, 'native_actors': sorted(native), 'members': sorted(members)}
        _write(directory / 'council.json', state)
    return inspect_council(root, council_id)


def completion_status(root: Path) -> dict:
    """Return-adapter dependency, never infer completion from API termination."""
    root = Path(root).resolve()
    summaries = []
    for path in sorted((root / 'councils').glob('*/council.json')):
        _, state, _ = _load(root, path.parent.name)
        running = [record['round_id'] for record in state['rounds']
                   if record['status'] in {'PREPARING', 'PREPARED', 'RUNNING', 'OUTCOME_PENDING'}]
        pending_events = [event['id'] for event in state['events'] if event['status'] != 'PROCESSED']
        pending_late = [item['exchange_id'] for item in state['late_results']
                        if item['status'] == 'PENDING_REENTRY']
        cycle_obligations = []
        for cycle in state['cycles']:
            native, members = _obligations(cycle)
            if (native or members) and not _valid_migration(state, cycle):
                cycle_obligations.append({'cycle_id': cycle['cycle_id'], 'input_version': cycle['input_version'],
                    'native_actors': sorted(native), 'members': sorted(members),
                    'resolution': cycle.get('resolution')})
        explicitly_closed = state['phase'] == 'CLOSED'
        summaries.append({'council_id': state['council_id'], 'phase': state['phase'],
            'complete': state['phase'] == 'COMPLETE' and not running and not pending_events and not pending_late and not cycle_obligations,
            'closed_with_declared_scope': explicitly_closed,
            'closure': state.get('closure'), 'active_rounds': running,
            'pending_transport_rounds': [record['round_id'] for record in state['rounds']
                                          if record['status'] == 'CLOSED_OUTCOME_UNKNOWN'],
            'pending_events': pending_events, 'pending_late_results': pending_late,
            'unresolved_cycle_obligations': cycle_obligations,
            'native_redeliberations': sorted(_cycle(state)['redeliberation']),
            'required_native_actors': sorted(_cycle(state)['native']),
            'input_version': state['input_version'], 'cycle_id': state['cycle_id']})
    unresolved = [item['council_id'] for item in summaries
                  if not item['complete'] and not item['closed_with_declared_scope']]
    active = [item['council_id'] for item in summaries if item['active_rounds']]
    return {'complete': not unresolved and not active, 'active_councils': active,
            'unresolved_councils': unresolved, 'councils': summaries,
            'scope': 'helper-managed council state; CLOSED preserves stated unfinished work; no native counter certification'}
