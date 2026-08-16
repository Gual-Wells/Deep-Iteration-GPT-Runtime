"""Formal Active Time ledger for DIGR 4.1.0.

The semantic layer decides work states.  The ledger only records foreground
state intervals and enforces timing truthfulness.

MAIN -> T
SOURCE -> T+t
D_EXCLUSIVE / META / IDLE -> neither

Foreground intervals never overlap by construction, therefore total formal T
and t are sums of per-interval observed durations.  This deliberately avoids
unioning absolute monotonic coordinates across different soft-only clock
identities, which could otherwise under-count intervals whose numeric epochs
happen to overlap.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from .clock_probe import (
    ClockSnapshot,
    elapsed_ns,
    observed_elapsed_ns,
    pair_is_hard_verifiable,
)
from .validation import require_bool

class WorkState(str, Enum):
    MAIN = 'MAIN'
    SOURCE = 'SOURCE'
    D_EXCLUSIVE = 'D_EXCLUSIVE'
    META = 'META'
    IDLE = 'IDLE'

_FORMAL = {WorkState.MAIN, WorkState.SOURCE}

@dataclass(frozen=True)
class WorkInterval:
    state: WorkState
    start: ClockSnapshot
    end: ClockSnapshot
    observed_ns: int
    hard_verified: bool

    def __post_init__(self):
        if not isinstance(self.state, WorkState):
            object.__setattr__(self, 'state', WorkState(self.state))
        if not isinstance(self.start, ClockSnapshot) or not isinstance(self.end, ClockSnapshot):
            raise TypeError('start/end must be ClockSnapshot')
        if observed_elapsed_ns(self.start, self.end) != self.observed_ns:
            raise ValueError('observed_ns does not match snapshots')
        require_bool('hard_verified', self.hard_verified)
        if self.hard_verified and not pair_is_hard_verifiable(self.start, self.end):
            raise ValueError('hard_verified cannot be asserted without continuity proof')

def sum_interval_durations_ns(items: Iterable[WorkInterval]) -> int:
    items = tuple(items)
    if any(not isinstance(item, WorkInterval) for item in items):
        raise TypeError('all items must be WorkInterval')
    return sum(item.observed_ns for item in items)


class FormalTimeLedger:
    def __init__(self, *, hard_T: bool = False, hard_t: bool = False):
        self._hard_T = require_bool('hard_T', hard_T)
        self._hard_t = require_bool('hard_t', hard_t)
        self._hard_required = self._hard_T or self._hard_t
        # Repository Execution Gate requires timing readiness for every DIGR run,
        # not only for hard T/t contracts.
        self._timing_ready = False
        self._readiness_at: ClockSnapshot | None = None
        self._formal_started = False
        self._state: WorkState | None = None
        self._start: ClockSnapshot | None = None
        self._last_event: ClockSnapshot | None = None
        self._intervals: list[WorkInterval] = []
        self._finished = False

    @property
    def timing_ready(self) -> bool:
        return self._timing_ready

    @property
    def formal_started(self) -> bool:
        return self._formal_started

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def intervals(self) -> tuple[WorkInterval, ...]:
        return tuple(self._intervals)

    def _require_open(self) -> None:
        if self._finished:
            raise RuntimeError('ledger is finished')

    def _check_event(self, at: ClockSnapshot) -> None:
        if not isinstance(at, ClockSnapshot):
            raise TypeError('at must be ClockSnapshot')
        anchor = self._last_event or self._readiness_at
        if anchor is not None:
            if self._hard_required:
                elapsed_ns(anchor, at)
            else:
                observed_elapsed_ns(anchor, at)

    def establish_timing_readiness(self, anchor: ClockSnapshot, probe: ClockSnapshot) -> None:
        self._require_open()
        if self._formal_started:
            raise RuntimeError('timing readiness cannot be established retroactively')
        if not isinstance(anchor, ClockSnapshot) or not isinstance(probe, ClockSnapshot):
            raise TypeError('anchor/probe must be ClockSnapshot')
        # Universal startup gate: require a real continuity probe even for soft contracts.
        elapsed_ns(anchor, probe)
        if self._last_event is not None:
            elapsed_ns(self._last_event, anchor)
        self._timing_ready = True
        self._readiness_at = anchor
        self._last_event = probe

    def _close_current(self, at: ClockSnapshot) -> None:
        if self._state is None or self._start is None:
            return
        observed = observed_elapsed_ns(self._start, at)
        hard_verified = pair_is_hard_verifiable(self._start, at)
        if self._hard_required and not hard_verified:
            raise ValueError('hard ledger interval lost clock continuity')
        self._intervals.append(
            WorkInterval(self._state, self._start, at, observed, hard_verified)
        )

    def transition(self, new_state: WorkState, at: ClockSnapshot) -> None:
        self._require_open()
        new_state = WorkState(new_state)
        if new_state in _FORMAL and not self._timing_ready:
            raise RuntimeError('Repository Execution Gate: trusted timing must be ready before MAIN/SOURCE')
        self._check_event(at)
        self._close_current(at)
        if new_state in _FORMAL:
            self._formal_started = True
        self._state = new_state
        self._start = at
        self._last_event = at

    def finish(self, at: ClockSnapshot) -> None:
        self._require_open()
        self._check_event(at)
        self._close_current(at)
        self._state = None
        self._start = None
        self._last_event = at
        self._finished = True

    def _selected(self, states: Iterable[WorkState]) -> tuple[WorkInterval, ...]:
        wanted = set(states)
        return tuple(item for item in self._intervals if item.state in wanted)

    @staticmethod
    def _sum_ns(items: Iterable[WorkInterval]) -> int:
        return sum_interval_durations_ns(items)

    @staticmethod
    def _all_hard_verified(items: tuple[WorkInterval, ...]) -> bool:
        return bool(items) and all(item.hard_verified for item in items)

    def formal_T_ns(self) -> int:
        return self._sum_ns(self._selected((WorkState.MAIN, WorkState.SOURCE)))

    def formal_t_ns(self) -> int:
        return self._sum_ns(self._selected((WorkState.SOURCE,)))

    def formal_T_seconds(self) -> float:
        return self.formal_T_ns() / 1_000_000_000

    def formal_t_seconds(self) -> float:
        return self.formal_t_ns() / 1_000_000_000

    def T_hard_verified(self) -> bool:
        items = self._selected((WorkState.MAIN, WorkState.SOURCE))
        return self._timing_ready and self._all_hard_verified(items)

    def t_hard_verified(self) -> bool:
        items = self._selected((WorkState.SOURCE,))
        return self._timing_ready and self._all_hard_verified(items)

    def to_dict(self) -> dict:
        return {
            'timing_ready': self.timing_ready,
            'formal_started': self.formal_started,
            'finished': self.finished,
            'foreground_state': None if self._state is None else self._state.value,
            'intervals': [
                {
                    'state': item.state.value,
                    'start': item.start.to_dict(),
                    'end': item.end.to_dict(),
                    'observed_ns': item.observed_ns,
                    'hard_verified': item.hard_verified,
                }
                for item in self._intervals
            ],
            'T_actual_ns': self.formal_T_ns(),
            't_actual_ns': self.formal_t_ns(),
            'T_actual_seconds': self.formal_T_seconds(),
            't_actual_seconds': self.formal_t_seconds(),
            'T_hard_verified': self.T_hard_verified(),
            't_hard_verified': self.t_hard_verified(),
        }
