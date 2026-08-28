"""Append-only, hash-chained clock/state journal for DIGR 5.0.

The journal is an audit substrate, not a scheduler. The model/host decides the
semantic work state. The journal records snapshots, sequence, and state changes
so formal time can be re-derived and truncation/reordering can be detected.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable
from .clock_probe import ClockSnapshot, elapsed_ns, observed_elapsed_ns
from .interval_ledger import WorkState, WorkInterval
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


def derive_work_intervals(events: Iterable[ClockJournalEvent]) -> tuple[WorkInterval, ...]:
    """Re-derive formal foreground intervals from journal STATE/FINISH events."""
    active_state: WorkState | None = None
    active_start: ClockSnapshot | None = None
    out: list[WorkInterval] = []
    finished = False
    for item in events:
        if item.event == 'RESUME_ANCHOR':
            # A process boundary cannot prove that an open semantic state was
            # continuously active while no receipts were being written. Drop
            # the unclosed tail rather than counting inter-call idle time.
            active_state = None
            active_start = None
            finished = False
            continue
        if item.event == 'STATE':
            if finished:
                raise ValueError('STATE event after FINISH')
            if item.state is None:
                raise ValueError('STATE journal event requires state')
            if active_state is not None and active_start is not None:
                observed = observed_elapsed_ns(active_start, item.snapshot)
                hard = True
                try:
                    elapsed_ns(active_start, item.snapshot)
                except ValueError:
                    hard = False
                out.append(WorkInterval(active_state, active_start, item.snapshot, observed, hard))
            active_state = item.state
            active_start = item.snapshot
        elif item.event == 'FINISH':
            if finished:
                raise ValueError('duplicate FINISH')
            if active_state is not None and active_start is not None:
                observed = observed_elapsed_ns(active_start, item.snapshot)
                hard = True
                try:
                    elapsed_ns(active_start, item.snapshot)
                except ValueError:
                    hard = False
                out.append(WorkInterval(active_state, active_start, item.snapshot, observed, hard))
            active_state = None; active_start = None; finished = True
    return tuple(out)


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
            # All recorded events must move monotonically within a provider;
            # hard continuity is checked by callers where required.
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
        if self.path is not None:
            line = _canonical_bytes(item.to_dict()) + b'\n'
            with self.path.open('ab') as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        # Memory becomes authoritative only after durable append succeeds.
        self._events.append(item)
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
            if i == 0:
                event = 'GENESIS_ANCHOR'
            elif i == len(samples) - 1:
                event = 'GENESIS_READY'
            else:
                event = 'GENESIS_PROBE'
            self.append(event, snap, WorkState.META)

    def append_resume(self, samples) -> None:
        """Append a cross-process resume readiness sequence.

        Resume is deliberately stricter than ordinary soft timing: the previous
        journal snapshot and the new anchor must share a provider and a non-
        empty equal boot identity. This prevents a new monotonic epoch from
        being mistaken for continuity. The unclosed semantic state before the
        boundary is not charged across the process gap.
        """
        samples=tuple(samples)
        if len(samples)<3:
            raise ValueError('resume requires at least three clock samples')
        if not self._events:
            raise ValueError('resume requires an existing journal')
        # hard bridge from persisted last snapshot to new process anchor
        elapsed_ns(self._events[-1].snapshot, samples[0])
        for a,b in zip(samples,samples[1:]):
            elapsed_ns(a,b)
        for i,snap in enumerate(samples):
            event='RESUME_ANCHOR' if i==0 else ('RESUME_READY' if i==len(samples)-1 else 'RESUME_PROBE')
            self.append(event,snap,WorkState.META)

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
