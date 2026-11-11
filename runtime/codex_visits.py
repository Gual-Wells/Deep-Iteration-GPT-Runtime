"""Shared, append-only Begin/End visits; no running timer or resident service.

The log is caller-declared activity evidence, not proof of continuous work or
whole-task completeness. Only closed visits are counted. Missing boundaries,
conflicting event identities and file damage remain visible. A later repair
needs a particular Begin, an approximate boundary and its visible basis.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable, Mapping
import uuid

FORMAT = 'digr-codex-visits-1'
_CATEGORIES = {'WORK', 'SOURCE', 'META', 'IDLE'}
_ALIASES = {'MAIN': 'WORK', 'D_EXCLUSIVE': 'WORK', 'V_EXCLUSIVE': 'WORK'}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' must be nonempty text')
    return value


def _event(value: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(value)
    if type(item.get('schema_version')) is not int or item['schema_version'] != 1:
        raise ValueError('unsupported visit schema_version')
    for field in ('event_id', 'run_id', 'actor_id', 'line_id'):
        _text(item.get(field), field)
    if item.get('event') not in {'BEGIN', 'END'}:
        raise ValueError('visit event must be BEGIN or END')
    if type(item.get('at_ns')) is not int or item['at_ns'] < 0:
        raise ValueError('at_ns must be nonnegative integer Unix nanoseconds')
    if 'recorded_at_ns' in item and (type(item['recorded_at_ns']) is not int or item['recorded_at_ns'] < 0):
        raise ValueError('recorded_at_ns must be nonnegative integer Unix nanoseconds')
    item['phase'] = item.get('phase', 'EXECUTION')
    if item['phase'] not in {'FOUNDATION', 'EXECUTION'}:
        raise ValueError('visit phase must be FOUNDATION or EXECUTION')
    item['category'] = _ALIASES.get(item.get('category'), item.get('category'))
    if item['category'] not in _CATEGORIES:
        raise ValueError('unknown visit category')
    item.setdefault('work', '')
    item.setdefault('approximate', False)
    item.setdefault('basis', '')
    if not isinstance(item['work'], str) or not isinstance(item['basis'], str):
        raise ValueError('work and basis must be text')
    if type(item['approximate']) is not bool:
        raise ValueError('approximate must be bool')
    if item['approximate'] and not item['basis'].strip():
        raise ValueError('an approximate boundary needs its visible basis')
    if item.get('begin_event_id') is not None:
        _text(item['begin_event_id'], 'begin_event_id')
        if item['event'] != 'END' or not item['approximate']:
            raise ValueError('a targeted repair must be an approximate END with basis')
    return item


@contextmanager
def _locked(path: Path, *, create: bool):
    """Use the pilot's byte-zero lock, also while taking a read snapshot.

    Windows byte locks are mandatory for readers, so an unlocked read can fail
    while an otherwise healthy writer holds byte zero. Retry only contention;
    process exit releases the OS lock. This is a local regular-file protocol.
    """
    flags = (os.O_RDWR | os.O_CREAT | os.O_APPEND) if create else os.O_RDONLY
    flags |= getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags, 0o600)
    locked = False
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError('shared visit file lock remained busy') from exc
                time.sleep(.01)
        yield fd
    finally:
        if locked:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def append_visit(path: Path, *, run_id: str, actor_id: str, event: str,
                 category: str = 'WORK', line_id: str = 'M01', phase: str = 'EXECUTION',
                 work: str = '', at_ns: int | None = None, approximate: bool = False,
                 basis: str = '', event_id: str | None = None,
                 begin_event_id: str | None = None) -> dict[str, Any]:
    """Append one actual observation; explicit effective times are repairs.

    ``recorded_at_ns`` always comes from the current tool clock. ``at_ns`` may
    locate an evidenced historical boundary only with approximate+basis. An
    END with begin_event_id repairs that Begin without closing a newer visit.
    """
    recorded = time.time_ns()
    if at_ns is not None and (not approximate or not isinstance(basis, str) or not basis.strip()):
        raise ValueError('explicit at_ns needs approximate=True and a visible basis')
    item = {'schema_version': 1, 'event_id': uuid.uuid4().hex if event_id is None else event_id,
            'run_id': run_id, 'actor_id': actor_id, 'line_id': line_id,
            'event': event, 'at_ns': recorded if at_ns is None else at_ns,
            'recorded_at_ns': recorded, 'phase': phase, 'category': category,
            'work': work, 'approximate': approximate, 'basis': basis}
    if begin_event_id is not None:
        item['begin_event_id'] = begin_event_id
    item = _event(item)
    raw = json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8') + b'\n'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _locked(path, create=True) as fd:
        # Preserve an interrupted writer's partial bytes as their own bad row;
        # never merge this complete record into a malformed tail or delete it.
        end = os.lseek(fd, 0, os.SEEK_END)
        if end:
            os.lseek(fd, -1, os.SEEK_END)
            if os.read(fd, 1) != b'\n':
                raw = b'\n' + raw
        os.lseek(fd, 0, os.SEEK_END)
        remaining = memoryview(raw)
        while remaining:
            written = os.write(fd, remaining)
            if not written:
                raise OSError('visit append made no progress')
            remaining = remaining[written:]
        os.fsync(fd)
    return item


def _no_constant(token: str) -> None:
    raise ValueError('non-finite JSON number: ' + token)


def read_visits(path: Path, *, run_id: str | None = None) -> dict[str, Any]:
    """Snapshot readable rows. Missing files are explicit, empty first-use logs.

    Run-attributable invalid events remain in ``issues`` at their position in
    the selected stream. Unattributable bytes remain file diagnostics; they
    cannot invalidate a particular run's immutable projection by themselves.
    """
    if run_id is not None:
        _text(run_id, 'run_id')
    try:
        with _locked(Path(path), create=False) as fd:
            with os.fdopen(os.dup(fd), 'rb') as stream:
                raw = stream.read()
    except FileNotFoundError:
        return {'events': [], 'issues': [], 'file_issues': [], 'run_id': run_id, 'file_status': 'MISSING'}
    events, issues, file_issues = [], [], []
    for number, row in enumerate(raw.splitlines(), 1):
        if not row.strip():
            continue
        try:
            value = json.loads(row.decode('utf-8-sig'), parse_constant=_no_constant)
            if not isinstance(value, dict):
                raise ValueError('visit row is not an object')
        except (UnicodeError, ValueError) as exc:
            file_issues.append({'line': number, 'reason': 'unreadable-row', 'detail': str(exc)})
            continue
        if run_id is not None and value.get('run_id') != run_id:
            continue
        try:
            events.append(_event(value))
        except (TypeError, ValueError) as exc:
            issue = {'reason': 'invalid-event', 'detail': str(exc), 'record': value,
                     'before_event_index': len(events)}
            for field in ('run_id', 'actor_id', 'line_id', 'event_id'):
                if isinstance(value.get(field), str) and value[field]:
                    issue[field] = value[field]
            if 'run_id' in issue:
                issues.append(issue)
            else:
                file_issues.append({'line': number, **issue})
    return {'events': events, 'issues': issues, 'file_issues': file_issues, 'run_id': run_id,
            'file_status': 'PARTIAL_READ' if issues or file_issues else 'READABLE'}


def _canonical(item: Any) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _prepare(data: Mapping[str, Any] | Iterable[Mapping[str, Any]], run_id: str):
    _text(run_id, 'run_id')
    if isinstance(data, Mapping):
        events, issues = data['events'], list(data.get('issues', []))
        file_issues = list(data.get('file_issues', []))
        status = data.get('file_status', 'READABLE')
    else:
        events, issues, file_issues, status = list(data), [], [], 'READABLE'
    selected, invalid_selected = [], []
    # Preserve scoped invalid-row barriers while filtering a multi-run read.
    selected_before = [0]
    for item in events:
        if item.get('run_id') == run_id:
            try:
                selected.append(_event(item))
            except (TypeError, ValueError) as exc:
                invalid_selected.append({'reason': 'invalid-event', 'detail': str(exc), 'run_id': run_id,
                                         'actor_id': item.get('actor_id'), 'line_id': item.get('line_id'),
                                         'record': dict(item), 'before_event_index': len(selected)})
        selected_before.append(len(selected))
    scoped = list(invalid_selected)
    for issue in issues:
        if issue.get('run_id') == run_id:
            copy = dict(issue)
            index = copy.get('before_event_index', 0)
            copy['before_event_index'] = selected_before[min(index, len(selected_before) - 1)]
            scoped.append(copy)
    identities = defaultdict(set)
    for item in selected:
        identities[item['event_id']].add(_canonical(item))
    conflicts = {key for key, versions in identities.items() if len(versions) > 1}
    seen, unique, duplicates = set(), [], 0
    for index, item in enumerate(selected):
        signature = _canonical(item)
        if signature in seen:
            duplicates += 1
            continue
        seen.add(signature)
        unique.append(item)
        if item['event_id'] in conflicts:
            scoped.append({'reason': 'conflicting-event-id', 'event_id': item['event_id'],
                           'run_id': run_id, 'actor_id': item['actor_id'], 'line_id': item['line_id'],
                           'before_event_index': index})
    return selected, unique, scoped, file_issues, status, duplicates, conflicts


def _union(pairs: Iterable[tuple[int, int]]) -> int:
    stop = None
    total = 0
    for left, right in sorted(pairs):
        if stop is None or left > stop:
            total += right - left
        elif right > stop:
            total += right - stop
        stop = max(stop, right) if stop is not None else right
    return total


def _totals(spans: list[dict[str, Any]]) -> dict[str, Any]:
    def measure(source: bool, closed_only: bool):
        return _union((s['start_ns'], s['end_ns']) for s in spans
                      if s['category'] in ({'SOURCE'} if source else {'WORK', 'SOURCE'})
                      and (not closed_only or not s['approximate']))
    values = {'T_ns': measure(False, False), 't_ns': measure(True, False),
              'T_closed_ns': measure(False, True), 't_closed_ns': measure(True, True)}
    values.update({key[:-3] + '_seconds': value / 1_000_000_000 for key, value in list(values.items())})
    values['closed_interval_count'] = len(spans)
    values['approximate_interval_count'] = sum(s['approximate'] for s in spans)
    return values


def summarize_visits(data: Mapping[str, Any] | Iterable[Mapping[str, Any]], *, run_id: str,
                     phase: str = 'EXECUTION') -> dict[str, Any]:
    """Pair visits in append order and union all participants' recorded work.

    An END's descriptive work/category need not repeat its Begin (pilot
    compatibility). Phase and actor/line identity must match. A new BEGIN
    leaves the old tail missing, with no implied stop at now or at the switch.
    """
    if phase not in {'FOUNDATION', 'EXECUTION'}:
        raise ValueError('unknown visit summary phase')
    events, unique, issues, file_issues, status, duplicates, conflicts = _prepare(data, run_id)
    active, pending, spans, gaps = {}, {}, [], []
    barriers = defaultdict(list)
    for issue in issues:
        barriers[issue['before_event_index']].append(issue)

    def key(item):
        return item['line_id'], item['actor_id']

    def detach(begin):
        owner = key(begin)
        if active.get(owner, {}).get('event_id') == begin['event_id']:
            active.pop(owner)

    def gap(reason, begin=None, end=None, **extra):
        item = begin or end or {}
        if item.get('phase', phase) == phase:
            gaps.append({'reason': reason, 'actor_id': item.get('actor_id'),
                         'line_id': item.get('line_id'), 'phase': item.get('phase', phase),
                         'begin_event_id': begin.get('event_id') if begin else None,
                         'end_event_id': end.get('event_id') if end else None,
                         'start_ns': begin.get('at_ns') if begin else None,
                         'end_ns': end.get('at_ns') if end else None, **extra})

    seen = set()
    for index in range(len(events) + 1):
        for issue in barriers[index]:
            for owner, begin in list(active.items()):
                if ((not issue.get('actor_id') or owner[1] == issue['actor_id']) and
                    (not issue.get('line_id') or owner[0] == issue['line_id'])):
                    gap('invalid-record-interrupted-open-visit', begin)
                    active.pop(owner)
        if index == len(events):
            break
        item = events[index]
        eid = item['event_id']
        if eid in conflicts or eid in seen:
            continue
        seen.add(eid)
        owner = key(item)
        if item['event'] == 'BEGIN':
            pending[eid] = item
            active[owner] = item
            continue
        target = item.get('begin_event_id')
        begin = pending.get(target) if target else active.get(owner)
        if begin is None:
            gap('repair-target-unavailable' if target else 'end-without-begin', end=item)
            continue
        if key(begin) != owner or begin['phase'] != item['phase']:
            gap('boundary-identity-or-phase-mismatch', begin, item)
            if key(begin) == owner:
                detach(begin)
            continue
        if item['at_ns'] < begin['at_ns']:
            older = [candidate['event_id'] for candidate in pending.values()
                     if not target and key(candidate) == owner and candidate['phase'] == item['phase']
                     and candidate['at_ns'] <= item['at_ns'] < begin['at_ns']]
            if older:
                # An out-of-order observation may concern an abandoned older
                # visit. Do not guess that binding or erase the newer visit.
                gap('late-unbound-end', end=item, candidate_begin_event_ids=older)
                continue
            gap('end-before-begin', begin, item)
            detach(begin)
            continue
        if begin['phase'] == phase:
            spans.append({'run_id': run_id, 'actor_id': begin['actor_id'], 'line_id': begin['line_id'],
                          'phase': phase, 'category': begin['category'], 'work': begin['work'],
                          'start_ns': begin['at_ns'], 'end_ns': item['at_ns'],
                          'begin_event_id': begin['event_id'], 'end_event_id': eid,
                          'approximate': begin['approximate'] or item['approximate'],
                          'basis': [event['basis'] for event in (begin, item) if event['basis']]})
        pending.pop(begin['event_id'], None)
        detach(begin)
    for begin in pending.values():
        gap('missing-end-not-counted', begin)
    by_line = {}
    for line in sorted({e['line_id'] for e in unique}):
        own_spans = [s for s in spans if s['line_id'] == line]
        own_gaps = [g for g in gaps if g['line_id'] == line]
        unresolved = sum(b['phase'] == phase and b['line_id'] == line for b in pending.values())
        by_line[line] = {**_totals(own_spans), 'spans': own_spans, 'gaps': own_gaps,
                         'unresolved_begin_count': unresolved}
    return {'format': FORMAT, 'run_id': run_id, 'phase': phase, **_totals(spans),
            'spans': spans, 'gaps': gaps, 'by_line': by_line, 'issues': issues,
            'file_issues': file_issues, 'file_status': status, 'duplicate_event_count': duplicates,
            'unresolved_begin_count': sum(b['phase'] == phase for b in pending.values()),
            'has_recorded_gaps': bool(gaps or issues or file_issues),
            'clock_basis': 'Unix wall boundaries; recorded visits, not monotonic attestation',
            'scope': 'closed recorded visits only; no whole-task completeness inferred',
            'COMMON_scope': 'COMMON included globally; never assigned to a main line'}


def run_projection(path: Path, run_id: str) -> dict[str, Any]:
    """Stable facts for this run; unrelated runs, file mtime/lines are absent.

    Identical event replays do not change the projection. Conflicting versions
    and attributable invalid events do. Unattributable file damage is reported
    separately by read_visits/summarize_visits, never assigned to another run.
    """
    data = read_visits(path, run_id=run_id)
    events, unique, issues, _, _, _, _ = _prepare(data, run_id)
    seen, before = set(), [0]
    for item in events:
        seen.add(_canonical(item))
        before.append(len(seen))
    # Diagnostic positions refer to unique selected events, not physical rows
    # or replay counts. Identical replays are harmless to a return snapshot.
    normalized = []
    for issue in issues:
        item = dict(issue)
        item['before_event_index'] = before[min(item['before_event_index'], len(before) - 1)]
        if item not in normalized:
            normalized.append(item)
    return {'format': FORMAT, 'run_id': run_id, 'events': unique, 'issues': normalized}
