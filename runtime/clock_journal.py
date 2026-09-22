"""Append-only, hash-chained clock/state journal for DIGR 5.0 Alpha 8.

The journal is the single timing/state audit substrate.  Formal work may cross
host/process boundaries only when an explicit WORK_LEASE_OPEN event was
persisted before the boundary.  Unleased formal work gaps are never silently
discarded: they become CoverageGap records and therefore invalidate hard time
coverage.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable
from .clock_probe import ClockSnapshot, elapsed_ns, observed_elapsed_ns, pair_is_hard_verifiable
from .interval_ledger import WorkState, WorkInterval, CoverageGap
from .validation import require_nonempty_text, require_nonnegative_int


def _canonical_bytes(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


@dataclass(frozen=True)
class ClockJournalEvent:
    seq: int
    run_id: str
    event: str
    snapshot: ClockSnapshot
    state: WorkState | None
    prev_hash: str | None
    record_hash: str

    def __post_init__(self):
        require_nonnegative_int('seq', self.seq)
        require_nonempty_text('run_id', self.run_id)
        require_nonempty_text('event', self.event)
        if not isinstance(self.snapshot, ClockSnapshot):
            raise TypeError('snapshot must be ClockSnapshot')
        if self.state is not None and not isinstance(self.state, WorkState):
            object.__setattr__(self, 'state', WorkState(self.state))
        for name, value in (('prev_hash', self.prev_hash), ('record_hash', self.record_hash)):
            if value is None and name == 'prev_hash':
                continue
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError(f'{name} must be lowercase SHA-256 hex')

    def payload(self) -> dict[str, Any]:
        return {
            'seq': self.seq,
            'run_id': self.run_id,
            'event': self.event,
            'snapshot': self.snapshot.to_dict(),
            'state': self.state.value if self.state else None,
            'prev_hash': self.prev_hash,
        }

    def to_dict(self) -> dict[str, Any]:
        d = self.payload()
        d['record_hash'] = self.record_hash
        return d


@dataclass(frozen=True)
class DerivedWorkTimeline:
    intervals: tuple[WorkInterval, ...]
    gaps: tuple[CoverageGap, ...]
    open_state: WorkState | None
    open_start: ClockSnapshot | None
    open_state_ref: str | None
    lease_open: bool
    finished: bool


def _interval(state: WorkState, start: ClockSnapshot, end: ClockSnapshot) -> WorkInterval:
    observed = observed_elapsed_ns(start, end)
    return WorkInterval(state, start, end, observed, pair_is_hard_verifiable(start, end))


def _gap(state: WorkState, start: ClockSnapshot, end: ClockSnapshot) -> CoverageGap:
    observed = observed_elapsed_ns(start, end)
    return CoverageGap(state, start, end, observed, pair_is_hard_verifiable(start, end))


def derive_work_timeline(events: Iterable[ClockJournalEvent]) -> DerivedWorkTimeline:
    """Re-derive intervals, open work state and unattributed cross-host gaps.

    A WORK_LEASE_OPEN event explicitly authorizes the current semantic work
    state to remain attributable across the next process/host boundary.  A
    RESUME_ANCHOR without such a lease closes whatever part can still be
    attributed and records the boundary as an unattributed gap instead of
    erasing it.
    """
    active_state: WorkState | None = None
    active_start: ClockSnapshot | None = None
    active_ref: str | None = None
    lease_open = False
    out: list[WorkInterval] = []
    gaps: list[CoverageGap] = []
    finished = False
    last_snapshot: ClockSnapshot | None = None

    for item in events:
        if item.event == 'STATE':
            if finished:
                raise ValueError('STATE event after FINISH')
            if item.state is None:
                raise ValueError('STATE journal event requires state')
            if active_state is not None and active_start is not None:
                out.append(_interval(active_state, active_start, item.snapshot))
            active_state = item.state
            active_start = item.snapshot
            active_ref = item.record_hash
            lease_open = False

        elif item.event == 'WORK_LEASE_OPEN':
            if finished:
                raise ValueError('WORK_LEASE_OPEN after FINISH')
            if item.state is None or active_state is None or active_start is None:
                raise ValueError('work lease requires an active work state')
            if item.state is not active_state:
                raise ValueError('work lease state must match active work state')
            lease_open = True
            active_ref = item.record_hash

        elif item.event == 'RESUME_ANCHOR':
            if active_state is not None and active_start is not None:
                if lease_open:
                    # Keep the original interval open through the boundary.  A
                    # resumed STATE event will close/re-anchor it after readiness.
                    lease_open = False
                else:
                    # We can only attribute up to the last persisted clock
                    # event.  The remainder is preserved as an explicit gap.
                    if last_snapshot is not None:
                        if last_snapshot.monotonic_ns > active_start.monotonic_ns:
                            out.append(_interval(active_state, active_start, last_snapshot))
                        if item.snapshot.monotonic_ns > last_snapshot.monotonic_ns:
                            gaps.append(_gap(active_state, last_snapshot, item.snapshot))
                    active_state = None
                    active_start = None
                    active_ref = None
                    lease_open = False

        elif item.event == 'FINISH':
            if finished:
                raise ValueError('duplicate FINISH')
            if active_state is not None and active_start is not None:
                out.append(_interval(active_state, active_start, item.snapshot))
            active_state = None
            active_start = None
            active_ref = None
            lease_open = False
            finished = True

        last_snapshot = item.snapshot

    return DerivedWorkTimeline(tuple(out), tuple(gaps), active_state, active_start, active_ref, lease_open, finished)


def derive_work_intervals(events: Iterable[ClockJournalEvent]) -> tuple[WorkInterval, ...]:
    return derive_work_timeline(events).intervals


class ClockJournal:
    def __init__(self, run_id: str, path: Path | None = None):
        self.run_id = require_nonempty_text('run_id', run_id)
        self.path = Path(path).resolve() if path is not None else None
        self._events: list[ClockJournalEvent] = []
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() and self.path.stat().st_size:
                raise ValueError('clock journal path must be new/empty')

    @property
    def events(self) -> tuple[ClockJournalEvent, ...]:
        return tuple(self._events)

    def append(self, event: str, snapshot: ClockSnapshot, state: WorkState | None = None) -> ClockJournalEvent:
        if not isinstance(snapshot, ClockSnapshot):
            raise TypeError('snapshot must be ClockSnapshot')
        event = require_nonempty_text('event', event)
        if self._events:
            prev = self._events[-1]
            observed_elapsed_ns(prev.snapshot, snapshot)
            prev_hash = prev.record_hash
        else:
            prev_hash = None
        seq = len(self._events)
        payload = {
            'seq': seq,
            'run_id': self.run_id,
            'event': event,
            'snapshot': snapshot.to_dict(),
            'state': state.value if isinstance(state, WorkState) else (str(state) if state is not None else None),
            'prev_hash': prev_hash,
        }
        digest = sha256(_canonical_bytes(payload)).hexdigest()
        item = ClockJournalEvent(seq, self.run_id, event, snapshot, state, prev_hash, digest)
        self._events.append(item)
        if self.path is not None:
            line = _canonical_bytes(item.to_dict()) + b'\n'
            with self.path.open('ab') as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        return item

    def append_genesis(self, samples) -> None:
        samples = tuple(samples)
        if self._events:
            raise RuntimeError('genesis already written')
        if len(samples) < 3:
            raise ValueError('genesis requires at least three clock samples')
        for a, b in zip(samples, samples[1:]):
            elapsed_ns(a, b)
        for i, snap in enumerate(samples):
            event = 'GENESIS_ANCHOR' if i == 0 else ('GENESIS_READY' if i == len(samples) - 1 else 'GENESIS_PROBE')
            self.append(event, snap, WorkState.META)

    def append_resume(self, samples) -> None:
        """Append a hard-verified same-boot cross-process readiness sequence."""
        samples = tuple(samples)
        if len(samples) < 3:
            raise ValueError('resume requires at least three clock samples')
        if not self._events:
            raise ValueError('resume requires an existing journal')
        elapsed_ns(self._events[-1].snapshot, samples[0])
        for a, b in zip(samples, samples[1:]):
            elapsed_ns(a, b)
        for i, snap in enumerate(samples):
            event = 'RESUME_ANCHOR' if i == 0 else ('RESUME_READY' if i == len(samples) - 1 else 'RESUME_PROBE')
            self.append(event, snap, WorkState.META)

    def verify(self, require_hard_continuity: bool = False) -> bool:
        prev_hash: str | None = None
        prev_snap: ClockSnapshot | None = None
        for expected_seq, item in enumerate(self._events):
            if item.seq != expected_seq or item.run_id != self.run_id or item.prev_hash != prev_hash:
                raise ValueError('clock journal sequence/hash chain mismatch')
            digest = sha256(_canonical_bytes(item.payload())).hexdigest()
            if digest != item.record_hash:
                raise ValueError('clock journal record hash mismatch')
            if prev_snap is not None:
                if require_hard_continuity:
                    elapsed_ns(prev_snap, item.snapshot)
                else:
                    observed_elapsed_ns(prev_snap, item.snapshot)
            prev_hash = item.record_hash
            prev_snap = item.snapshot
        return True

    @classmethod
    def load(cls, run_id: str, path: Path) -> 'ClockJournal':
        path = Path(path).resolve()
        obj = cls.__new__(cls)
        obj.run_id = require_nonempty_text('run_id', run_id)
        obj.path = path
        obj._events = []
        if not path.is_file():
            raise FileNotFoundError(path)
        for raw in path.read_text(encoding='utf-8').splitlines():
            d = json.loads(raw)
            s = d['snapshot']
            snap = ClockSnapshot(s['provider'], s['session_id'], s.get('boot_id'), s['monotonic_ns'], s['wall_ns'])
            state = WorkState(d['state']) if d.get('state') else None
            obj._events.append(ClockJournalEvent(d['seq'], d['run_id'], d['event'], snap, state, d.get('prev_hash'), d['record_hash']))
        obj.verify(False)
        return obj
