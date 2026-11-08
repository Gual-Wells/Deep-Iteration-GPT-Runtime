"""Resumable Codex work lines and explicitly bounded activity facts.

This is a file utility, not an agent executor, scheduler, semantic approval gate
or attestation service. Each line owns its work, candidate and activity file.
The model initializes complete parameters and judges N/R/D/V responsibilities;
the helper preserves those declarations and merges observed clock intervals.

A Windows live-process anchor establishes a common monotonic clock domain. It
does not establish continuous task activity. Only an explicit end/checkpoint
with caller-declared continuity closes an activity interval. Recovery discards
the open tail, preserving earlier closed intervals and the gap itself.
"""
from __future__ import annotations

from collections import defaultdict
import ctypes
from ctypes import wintypes
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import socket
import sys
import time
from typing import Any, Iterable, Mapping
import uuid

from .codex_workbench import context_packet, create_workbench
from .duration import parse_canonical_duration_seconds
from .validation import require_binary, require_nonempty_text, require_nonnegative_int

FORMAT = 'digr-codex-session-1'
ACTIVITY_STATES = frozenset({'MAIN', 'SOURCE', 'D_EXCLUSIVE', 'V_EXCLUSIVE', 'META', 'IDLE'})
_LINE_ID = re.compile(r'M[0-9]{2,}')
_PROCESS_SESSION = uuid.uuid4().hex
_PARAMETER_KEYS = frozenset({'N', 'T', 'R', 'B', 'S', 'D', 'V', 'L'})


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError(f'expected a JSON object: {path}')
    return value


def _write_json(path: Path, value: Mapping[str, Any], *, new: bool = False) -> None:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
    if new:
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(raw)
    else:
        # One owner per file. Replacement prevents readers from seeing a
        # half-written status; this is not a multi-writer compare-and-swap.
        replacement = path.with_name(path.name + '.new-' + uuid.uuid4().hex)
        with replacement.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(raw)
        replacement.replace(path)


def _session(root: Path) -> tuple[Path, dict[str, Any]]:
    root = Path(root).resolve()
    metadata = _read_json(root / 'session.json')
    if metadata.get('format') != FORMAT:
        raise ValueError('unsupported Codex session format')
    raw = (root / 'REQUEST.txt').read_bytes()
    if sha256(raw).hexdigest() != metadata.get('request_sha256'):
        raise ValueError('frozen original request changed')
    return root, metadata


def _line_dir(root: Path, line_id: str) -> Path:
    if not isinstance(line_id, str) or not _LINE_ID.fullmatch(line_id):
        raise ValueError('line id must be M01, M02, ...')
    root = Path(root).resolve()
    path = (root / 'lines' / line_id).resolve()
    if not path.is_relative_to(root / 'lines'):
        raise ValueError('line path escapes the session')
    return path


def _duration(value: object, name: str) -> None:
    # Numeric API values have the explicit unit seconds. This is not parsing a
    # bare-number DIGR invocation; strings must carry duration semantics.
    if type(value) in (int, float):
        if not math.isfinite(value) or value < 0:
            raise ValueError(f'{name} seconds must be finite and non-negative')
    else:
        seconds = parse_canonical_duration_seconds(value)
        if not math.isfinite(seconds):
            raise ValueError(f'{name} duration must be finite')


def _parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(parameters, Mapping) or set(parameters) != _PARAMETER_KEYS:
        raise ValueError('provide complete N/T/R/B/S(n,t,r,b)/D/V/L for this line')
    nested = parameters['S']
    if not isinstance(nested, Mapping) or set(nested) != {'n', 't', 'r', 'b'}:
        raise ValueError('S must contain exactly n/t/r/b')
    for key in ('N', 'R', 'D', 'V', 'L'):
        require_nonnegative_int(key, parameters[key])
    for key in ('n', 'r'):
        require_nonnegative_int('S.' + key, nested[key])
    require_binary('B', parameters['B'])
    require_binary('S.b', nested['b'])
    _duration(parameters['T'], 'T')
    _duration(nested['t'], 'S.t')
    if parameters['L'] != 3:
        raise ValueError('Codex D/V require L3; a declared value is not execution evidence')
    return json.loads(json.dumps(parameters, ensure_ascii=False, allow_nan=False))


def _differences(explicit: Mapping[str, Any], actual: Mapping[str, Any],
                 reasons: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    reasons = dict(reasons or {})
    result = []
    for key, expected in explicit.items():
        if key == 'M':
            continue
        supplied = actual.get(key)
        if key == 'S' and isinstance(expected, Mapping):
            for nested, value in expected.items():
                current = supplied.get(nested) if isinstance(supplied, Mapping) else None
                if current != value:
                    name = 'S.' + nested
                    result.append({'parameter': name, 'explicit': value, 'effective': current,
                                   'reason': reasons.get(name)})
        elif supplied != expected:
            result.append({'parameter': key, 'explicit': expected, 'effective': supplied,
                           'reason': reasons.get(key)})
    # Preserve explicit values and expose differences. Their permissibility is
    # determined by P_run and the user's actual steering, not by this record.
    return result


def windows_process_anchor(pid: int) -> dict[str, Any]:
    """Verify one explicit live PID and creation identity; never scan for hosts."""
    if sys.platform != 'win32':
        raise OSError('Windows process anchors are unavailable on this platform')
    require_nonnegative_int('anchor_pid', pid)
    if pid == 0:
        raise ValueError('anchor_pid must be positive')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if kernel.WaitForSingleObject(handle, 0) != 0x102:
            raise OSError('anchor process is no longer alive')
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                      ctypes.byref(kernel_time), ctypes.byref(user_time)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'kind': 'windows-live-process', 'host': socket.gethostname(), 'pid': pid,
                'creation_100ns': (created.dwHighDateTime << 32) | created.dwLowDateTime,
                'selection_basis': 'explicit-pid; caller identifies the appropriate host'}
    finally:
        kernel.CloseHandle(handle)


def capture_clock(anchor: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Read real boundaries; missing clock identity stays unknown and nonfatal."""
    wall = time.time_ns()
    try:
        if sys.platform == 'win32' and anchor is not None:
            identity = windows_process_anchor(anchor['pid'])
            if identity != dict(anchor):
                raise OSError('live host anchor identity changed')
        elif sys.platform.startswith('linux'):
            boot_id = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='utf-8').strip()
            if not boot_id:
                raise OSError('Linux boot identity is empty')
            identity = {'kind': 'linux-boot', 'host': socket.gethostname(), 'boot_id': boot_id}
        else:
            identity = {'kind': 'same-process-only', 'session': _PROCESS_SESSION}
        domain = sha256(json.dumps({'provider': 'python-monotonic-ns', 'identity': identity},
                                  sort_keys=True).encode('utf-8')).hexdigest()
        return {'provider': 'python-monotonic-ns', 'domain': domain, 'identity': identity,
                'monotonic_ns': time.monotonic_ns(), 'wall_ns': time.time_ns(),
                'clock_basis': 'tool-observed/' + identity['kind']}
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return {'provider': 'python-monotonic-ns', 'domain': None, 'monotonic_ns': None,
                'wall_ns': wall, 'clock_basis': 'unavailable', 'reason': str(exc)}


def create_session(root: Path, *, request: Path, p_run: str,
                   decisions: Path | None = None, explicit_parameters: Mapping[str, Any] | None = None,
                   anchor_pid: int | None = None, m_target: int | None = None) -> dict[str, Any]:
    """Prepare storage from an already-acquired P_run; do not start execution."""
    if not isinstance(p_run, str) or not re.fullmatch(r'[^@\s]+@[0-9a-f]{40}', p_run):
        raise ValueError('P_run must be version@full-40-character-SHA')
    root, request = Path(root).resolve(), Path(request).resolve()
    raw = request.read_bytes()
    if not raw.decode('utf-8-sig').strip():
        raise ValueError('original request is empty')
    explicit = dict(explicit_parameters or {})
    explicit = json.loads(json.dumps(explicit, ensure_ascii=False, allow_nan=False))
    target = explicit.get('M', 1) if m_target is None else m_target
    require_nonnegative_int('M target', target)
    if target < 1:
        raise ValueError('M target must be at least 1')
    decisions = Path(decisions).resolve() if decisions is not None else None
    if decisions is not None and not decisions.is_file():
        raise ValueError('decisions must reference an existing shared text file')
    anchor, clock_issue = None, None
    if anchor_pid is not None:
        try:
            anchor = windows_process_anchor(anchor_pid)
        except (ValueError, TypeError, OSError) as exc:
            clock_issue = str(exc)
    metadata = {'format': FORMAT, 'P_run': p_run, 'M_target': target,
                'request_origin': request.as_posix(), 'request_sha256': sha256(raw).hexdigest(),
                'decisions': decisions.as_posix() if decisions is not None else None,
                'explicit_parameters': explicit, 'clock_anchor': anchor, 'clock_issue': clock_issue,
                'created_wall_ns': time.time_ns(), 'execution_started_by_helper': False}
    root.mkdir(parents=True, exist_ok=False)
    (root / 'lines').mkdir()
    (root / 'common').mkdir()
    (root / 'REQUEST.txt').write_bytes(raw)
    _write_json(root / 'session.json', metadata, new=True)
    return metadata


def create_line(root: Path, line_id: str, *, parameters: Mapping[str, Any], owner: str | None = None,
                work: Path | None = None, parameter_reasons: Mapping[str, str] | None = None,
                corrections_topics: Iterable[str] = (), experiences: Iterable[str | Path] = ()) -> dict[str, Any]:
    """Accept this owner's complete initialization; do not clone another line."""
    root, session = _session(root)
    values = _parameters(parameters)
    if owner is not None:
        owner = require_nonempty_text('owner', owner)
    line = _line_dir(root, line_id)
    work = Path(work).resolve() if work is not None else line / 'WORK.md'
    if work.exists() and not work.is_file():
        raise ValueError('work must be an ordinary text file')
    if isinstance(corrections_topics, str) or isinstance(experiences, (str, Path)):
        raise TypeError('context selections must be explicit lists/iterables')
    topics = list(dict.fromkeys(require_nonempty_text('corrections topic', item) for item in corrections_topics))
    cases = list(dict.fromkeys(Path(item).as_posix() for item in experiences))
    package = {'line_id': line_id, 'owner': owner, 'parameters': values,
               'explicit_parameter_differences': _differences(session['explicit_parameters'], values, parameter_reasons),
               'work': work.as_posix(), 'candidate': None, 'candidate_ref': None,
               'content_status': 'PREPARED', 'responsibility_status': 'UNVERIFIED',
               'status_basis': 'owner-declared; not verified by the helper', 'unhandled': [],
               'next_action': '本线自行选择实际问题、方法与生产路线。', 'parameter_changes': [],
               'context_selection': {'corrections_topics': topics, 'experiences': cases},
               'updated_wall_ns': time.time_ns()}
    line.mkdir(exist_ok=False)
    if not work.exists():
        work.parent.mkdir(parents=True, exist_ok=True)
        with work.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(create_workbench((root / 'REQUEST.txt').read_text(encoding='utf-8-sig')))
    _write_json(line / 'line.json', package, new=True)
    return package


def _artifact_ref(path: Path) -> dict[str, Any]:
    path = Path(path).resolve()
    if path.is_dir():
        return {'path': path.as_posix(), 'kind': 'directory', 'sha256': None,
                'scope': 'entrypoint only; no recursive content certification'}
    if not path.is_file():
        raise ValueError(f'candidate does not exist: {path}')
    digest = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': path.as_posix(), 'kind': 'file', 'sha256': digest.hexdigest()}


def update_line(root: Path, line_id: str, *, candidate: Path | None,
                content_status: str, responsibility_status: str, next_action: str,
                unhandled: list[str] | tuple[str, ...] = (), owner: str | None = None) -> dict[str, Any]:
    """Save a current artifact and the author's states; no automatic completion."""
    root, _ = _session(root)
    path = _line_dir(root, line_id) / 'line.json'
    package = _read_json(path)
    content_status = require_nonempty_text('content_status', content_status)
    responsibility_status = require_nonempty_text('responsibility_status', responsibility_status)
    next_action = require_nonempty_text('next_action', next_action)
    if not isinstance(unhandled, (list, tuple)):
        raise TypeError('unhandled must be a list or tuple of public pending matters')
    pending = [require_nonempty_text('unhandled item', item) for item in unhandled]
    reference = _artifact_ref(candidate) if candidate is not None else None
    package.update(candidate=reference['path'] if reference else None, candidate_ref=reference,
                   content_status=content_status, responsibility_status=responsibility_status,
                   next_action=next_action, unhandled=pending, updated_wall_ns=time.time_ns())
    if owner is not None:
        package['owner'] = require_nonempty_text('owner', owner)
    _write_json(path, package)
    return package


def set_line_parameters(root: Path, line_id: str, *, parameters: Mapping[str, Any],
                        reasons: Mapping[str, str], user_revision: str | None = None) -> dict[str, Any]:
    """Preserve a real target adjustment without counting it as progress."""
    root, session = _session(root)
    path = _line_dir(root, line_id) / 'line.json'
    package = _read_json(path)
    values = _parameters(parameters)
    if user_revision is not None:
        user_revision = require_nonempty_text('user_revision', user_revision)
    for key in ('N', 'R', 'D', 'V'):
        if values[key] < package['parameters'][key] and user_revision is None:
            raise ValueError(f'{key} cannot be silently reduced in this profile')
    if not isinstance(reasons, Mapping):
        raise TypeError('parameter adjustment reasons must be a mapping')
    changes = _differences(package['parameters'], values, reasons)
    if not changes:
        return package
    package['parameter_changes'].append({'changes': changes, 'user_revision': user_revision,
                                         'recorded_wall_ns': time.time_ns()})
    package['parameters'] = values
    package['explicit_parameter_differences'] = _differences(session['explicit_parameters'], values, reasons)
    package['updated_wall_ns'] = time.time_ns()
    _write_json(path, package)
    return package


def set_clock_anchor(root: Path, *, anchor_pid: int, reason: str) -> dict[str, Any]:
    """Explicitly re-anchor future boundaries; never repair or extend old work."""
    root, metadata = _session(root)
    reason = require_nonempty_text('clock anchor reason', reason)
    anchor = windows_process_anchor(anchor_pid)
    metadata.update(clock_anchor=anchor, clock_issue=None, clock_anchor_note=reason)
    _write_json(root / 'session.json', metadata)
    return anchor


def union_ns(spans: list[tuple[int, int]]) -> int:
    total, end = 0, None
    for start, stop in sorted(spans):
        if start > stop:
            raise ValueError('interval ends before it starts')
        total += max(0, stop - max(start, end if end is not None else start))
        end = max(stop, end if end is not None else stop)
    return total


def derive_activity(events: list[dict[str, Any]], *, expose_tail: bool = True) -> dict[str, Any]:
    """Reconstruct explicitly closed intervals; recovery never closes a tail."""
    active = None
    spans, gaps = [], []
    for event in events:
        action, at = event['action'], event['at']
        if action == 'begin':
            if active is not None:
                raise ValueError('open activity requires end or recover before another begin')
            if event.get('state') not in ACTIVITY_STATES:
                raise ValueError('unknown activity state')
            active = {'state': event['state'], 'start': at}
        elif action == 'recover':
            if active is not None:
                gaps.append({'reason': event.get('reason') or 'recovery-discarded-open-tail',
                             'start': active['start'], 'end': at})
            active = None
        elif action in {'end', 'checkpoint'}:
            if active is None:
                raise ValueError(f'{action} requires open activity')
            if event.get('declared_continuity') is not True:
                raise ValueError('closing activity needs explicit caller-declared continuity')
            start = active['start']
            comparable = (start.get('domain') is not None and start['domain'] == at.get('domain')
                          and start['provider'] == at['provider']
                          and type(start.get('monotonic_ns')) is int and type(at.get('monotonic_ns')) is int
                          and 0 <= start['monotonic_ns'] <= at['monotonic_ns'])
            if comparable:
                spans.append({'state': active['state'], 'start': start, 'end': at,
                              'activity_basis': 'caller-declared-at-explicit-boundary'})
            else:
                gaps.append({'reason': 'clock-domain-or-boundary-unverifiable', 'start': start, 'end': at})
            active = {'state': active['state'], 'start': at} if action == 'checkpoint' else None
        else:
            raise ValueError(f'unknown activity action: {action}')
    if expose_tail and active is not None:
        gaps.append({'reason': 'unclosed-tail-not-counted', 'start': active['start'], 'end': None})
    return {'spans': spans, 'gaps': gaps, 'active': active}


def _read_activity(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []

    def invalid_constant(token: str) -> None:
        raise ValueError(f'non-finite JSON number is not a clock fact: {token}')

    for number, row in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        try:
            value = json.loads(row, parse_constant=invalid_constant)
            if not isinstance(value, dict):
                raise ValueError('event is not an object')
            if not isinstance(value.get('at'), dict):
                raise ValueError('event clock boundary is not an object')
            events.append(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(f'activity record is unreadable at {path}:{number}: {exc}') from exc
    return events


def activity(root: Path, owner: str, action: str, *, state: str | None = None,
             continued: bool = False, reason: str | None = None) -> dict[str, Any]:
    """Append a genuine current boundary to this one owner's activity file."""
    root, metadata = _session(root)
    if owner == 'COMMON':
        folder = root / 'common'
    else:
        folder = _line_dir(root, owner)
        _read_json(folder / 'line.json')
    if type(continued) is not bool:
        raise TypeError('continued must be bool')
    if action == 'begin' and state not in ACTIVITY_STATES:
        raise ValueError('begin requires a known activity state')
    if action != 'begin' and state is not None:
        raise ValueError('state applies only to begin')
    event = {'action': action, 'at': capture_clock(metadata.get('clock_anchor'))}
    if state is not None:
        event['state'] = state
    if continued:
        event['declared_continuity'] = True
    if reason is not None:
        event['reason'] = require_nonempty_text('activity reason', reason)
    path = folder / 'activity.jsonl'
    events = _read_activity(path)
    derive_activity(events + [event])
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')
    return event


def summarize_activity(streams: Mapping[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Merge per-domain spans; incomparable domains are never added as union."""
    lines, by_domain = {}, defaultdict(lambda: {'T': [], 't': []})
    all_gaps = []
    for owner, events in streams.items():
        facts = derive_activity(events)
        own = defaultdict(lambda: {'T': [], 't': []})
        for span in facts['spans']:
            if span['state'] not in {'MAIN', 'SOURCE'}:
                continue
            start, stop = span['start'], span['end']
            pair = (start['monotonic_ns'], stop['monotonic_ns'])
            own[start['domain']]['T'].append(pair)
            by_domain[start['domain']]['T'].append(pair)
            if span['state'] == 'SOURCE':
                own[start['domain']]['t'].append(pair)
                by_domain[start['domain']]['t'].append(pair)
        totals = {domain: {key + '_ns': union_ns(pairs) for key, pairs in group.items()}
                  for domain, group in own.items()}
        only = next(iter(totals.values())) if len(totals) == 1 else None
        clock_bases = sorted({event['at'].get('clock_basis', 'unspecified') for event in events})
        lines[owner] = {'known_by_clock_domain': totals, 'known_union_ns': only,
                        'gaps': facts['gaps'], 'closed_interval_count': len(facts['spans']),
                        'active': facts['active'], 'scope': 'recorded-activity-only',
                        'clock_basis': clock_bases[0] if len(clock_bases) == 1 else 'mixed-or-unknown',
                        'clock_bases': clock_bases,
                        'activity_basis': 'caller-declared-at-explicit-boundary',
                        'recording_status': 'NO_RECORDS' if not events else 'HAS_RECORDS'}
        all_gaps.extend({'owner': owner, **gap} for gap in facts['gaps'])
    totals = {domain: {key + '_ns': union_ns(pairs) for key, pairs in group.items()}
              for domain, group in by_domain.items()}
    only = next(iter(totals.values())) if len(totals) == 1 else None
    return {'lines': lines, 'global_known_by_clock_domain': totals, 'global_known_union_ns': only,
            'single_comparable_domain': len(totals) == 1, 'has_recorded_gaps': bool(all_gaps),
            'gaps': all_gaps, 'COMMON_scope': 'global union only; never credited to an M line',
            'scope': 'recorded activity only; not whole-task completeness or semantic attestation'}


def session_report(root: Path) -> dict[str, Any]:
    """Read packages and available activity without hiding an unreadable owner.

    Task/U0 and registered package identity remain strict. An independently
    unreadable activity log is excluded in full, never treated as zero or
    repaired. Readable subset timing remains available, while the whole-task
    union and whole-task domain comparability stay unknown.
    """
    root, metadata = _session(root)
    streams, packages, issues = {}, {}, []
    unavailable = {}

    def read_activity(owner: str, path: Path) -> None:
        try:
            events = _read_activity(path)
            summarize_activity({owner: events})  # Validate this independent log before global merge.
        except (OSError, ValueError, TypeError, KeyError) as exc:
            issue = {'owner': owner, 'component': 'activity', 'path': path.as_posix(),
                     'reason': str(exc), 'effect': 'owner activity excluded in full; unknown, not zero; no repair'}
            issues.append(issue)
            unavailable[owner] = {
                'known_by_clock_domain': {}, 'known_union_ns': None,
                'gaps': [], 'gaps_status': 'UNKNOWN', 'closed_interval_count': None,
                'active': None, 'active_status': 'UNKNOWN', 'recording_status': 'UNREADABLE',
                'clock_basis': 'UNKNOWN', 'clock_bases': [], 'activity_basis': 'UNKNOWN',
                'scope': 'unreadable owner activity; no zero or completion inferred', 'issue': issue,
            }
        else:
            streams[owner] = events

    for folder in sorted((root / 'lines').iterdir()):
        if not folder.is_dir():
            continue
        _line_dir(root, folder.name)
        package_path = folder / 'line.json'
        try:
            package = _read_json(package_path)
        except (OSError, ValueError) as exc:
            raise ValueError(f'line package is unreadable: {package_path}: {exc}') from exc
        if package.get('line_id') != folder.name:
            raise ValueError(f'line package identity mismatch: {folder / "line.json"}')
        packages[folder.name] = package
        read_activity(folder.name, folder / 'activity.jsonl')
    path = root / 'common' / 'activity.jsonl'
    if path.exists():
        read_activity('COMMON', path)
    timing = summarize_activity(streams)
    timing['available_global_known_union_ns'] = timing['global_known_union_ns']
    timing['available_single_comparable_domain'] = timing['single_comparable_domain']
    timing['unreadable_activity_owners'] = sorted(unavailable)
    timing['lines'].update(unavailable)
    if issues:
        # An omitted owner might contain overlapping work or another clock
        # domain. One domain left in the readable subset proves neither a
        # whole-task union nor whole-task clock comparability.
        timing['global_known_union_ns'] = None
        timing['single_comparable_domain'] = None
        timing['scope'] = 'readable activity subset only; unreadable owners are unknown, not zero'
    return {'session': metadata, 'line_packages': packages, 'timing': timing,
            'registered_line_count': len(packages), 'effective_M_count': None,
            'report_status': 'PARTIAL_READ' if issues else 'READABLE', 'issues': issues,
            'report_scope': 'registered packages and readable activity only; not whole-task completeness',
            'count_scope': 'registered packages do not prove effective independent main lines'}


def line_packet(root: Path, line_id: str, *, topic: str | None = None,
                max_chars: int = 24000, corrections_topics: Iterable[str] = (),
                experiences: Iterable[str | Path] = ()) -> str:
    """Retrieve U0, live shared corrections, own work and actual artifact entry."""
    root, metadata = _session(root)
    package = _read_json(_line_dir(root, line_id) / 'line.json')
    parts = [f'# {line_id} 可继续工作包', f"P_run={metadata['P_run']}",
             '本线完整参数与作者记录如下。旧计划、下一步和状态可因新要求失效；'
             '文件准备与状态声明不证明原生代理已启动或责任完成。',
             json.dumps(package, ensure_ascii=False, indent=2, allow_nan=False)]
    shared_text, shared_path = None, None
    if metadata['decisions'] is not None:
        decisions = Path(metadata['decisions'])
        shared_path = decisions.as_posix()
        shared_text = decisions.read_text(encoding='utf-8-sig')
        parts += ['## 本次共享材料入口', shared_path,
                  '本次读取的共同材料原文放在本包末尾，供看完旧本线记录后校正下一步。'
                  '用户原话、已确认决定、事实记录和模型提议仍按各自原身份理解。']
    selection = package.get('context_selection', {})
    parts.append(context_packet(Path(package['work']), request=root / 'REQUEST.txt',
        topic=topic, max_chars=max_chars,
        corrections_topics=[*selection.get('corrections_topics', []), *corrections_topics],
        experiences=[*selection.get('experiences', []), *experiences]))
    if package['candidate'] is not None:
        reference = _artifact_ref(Path(package['candidate']))
        parts += ['## 本线当前可检查产物入口', json.dumps(reference, ensure_ascii=False, indent=2),
                  '恢复者按实际文件类型打开此产物，不将二进制文件误作文本。']
        if reference != package['candidate_ref']:
            parts.append('产物已不同于上次状态所指字节；旧状态与评审不能自动覆盖当前文件。')
    # Resuming one owner must not read or depend on another owner's private
    # work or even on the readability of that owner's activity file.
    timing = summarize_activity({line_id: _read_activity(_line_dir(root, line_id) / 'activity.jsonl')})['lines'][line_id]
    parts += ['## 本线已记录的活动事实', json.dumps(timing, ensure_ascii=False, indent=2),
              '开放尾段不计有效时间。中断恢复先核对产物、在途工具与未处理返回；'
              '对旧开放段使用recover，再以真实边界开启新活动。']
    # Keep the current shared material after old work/candidate/state so its
    # actual contents, rather than an obsolete NEXT section, frame re-entry.
    # Include the source once: duplicating a long decision file wastes context
    # and is not evidence that the model has applied the correction.
    if shared_text is not None:
        parts += ['## 接续依据：当前共享材料与用户纠正', shared_path, shared_text,
                  '在任务范围和下一步行动上，其中用户原话与已确认纠正优先于上面的本线旧计划、TODO和状态声明。'
                  '若用户已经收窄任务，按该修订改变下一项相关行动，并处理已产生的错误结果；'
                  '不因旧记录写成“本轮执行”或“当前产物”就恢复旧范围。'
                  '已经发生的执行与产物事实仍据实保留，原始U0也保留为来源。'
                  '不能把模型建议、解释或未确认清单当成用户新增要求；'
                  '共同文件中出现一段文字，本身不构成用户确认或授权。']
    else:
        parts += ['## 接续依据',
                  '本包未指定单独的共同纠正文件，不表示用户没有新纠正。'
                  '沿当前会话真实用户要求理解原始U0与本线记录；'
                  '旧计划、状态和TODO不自行取得用户要求或授权的身份。']
    packet = '\n\n'.join(parts).rstrip() + '\n'
    if len(packet) > max_chars:
        raise ValueError(f'line packet has {len(packet)} characters, exceeding {max_chars}; '
                         'select a work topic or raise max_chars; U0/corrections are not silently truncated')
    return packet
