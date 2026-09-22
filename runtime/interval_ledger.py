"""Formal Active Time ledger for DIGR 5.0 Alpha 7.

MAIN, SOURCE and D_EXCLUSIVE all contribute to T.  SOURCE additionally
contributes to t.  Cross-host attribution gaps are preserved explicitly; hard
verification requires both clock continuity and complete semantic-time coverage.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from .clock_probe import ClockSnapshot, elapsed_ns, observed_elapsed_ns, pair_is_hard_verifiable
from .task_startup import TaskStartupReceipt
from .validation import require_bool


class WorkState(str, Enum):
    MAIN='MAIN'; SOURCE='SOURCE'; D_EXCLUSIVE='D_EXCLUSIVE'; META='META'; IDLE='IDLE'


_FORMAL_T={WorkState.MAIN,WorkState.SOURCE,WorkState.D_EXCLUSIVE}
_FORMAL_t={WorkState.SOURCE}


@dataclass(frozen=True)
class WorkInterval:
    state:WorkState
    start:ClockSnapshot
    end:ClockSnapshot
    observed_ns:int
    hard_verified:bool
    def __post_init__(self):
        if not isinstance(self.state,WorkState): object.__setattr__(self,'state',WorkState(self.state))
        if not isinstance(self.start,ClockSnapshot) or not isinstance(self.end,ClockSnapshot): raise TypeError('start/end must be ClockSnapshot')
        if observed_elapsed_ns(self.start,self.end)!=self.observed_ns: raise ValueError('observed_ns does not match snapshots')
        require_bool('hard_verified',self.hard_verified)
        if self.hard_verified and not pair_is_hard_verifiable(self.start,self.end): raise ValueError('false hard-verification fact')


@dataclass(frozen=True)
class CoverageGap:
    state:WorkState
    start:ClockSnapshot
    end:ClockSnapshot
    observed_ns:int
    hard_verified:bool
    def __post_init__(self):
        if not isinstance(self.state,WorkState): object.__setattr__(self,'state',WorkState(self.state))
        if not isinstance(self.start,ClockSnapshot) or not isinstance(self.end,ClockSnapshot): raise TypeError('start/end must be ClockSnapshot')
        if observed_elapsed_ns(self.start,self.end)!=self.observed_ns: raise ValueError('observed_ns does not match snapshots')
        require_bool('hard_verified',self.hard_verified)


def sum_interval_durations_ns(items:Iterable[WorkInterval])->int:
    items=tuple(items)
    if any(not isinstance(x,WorkInterval) for x in items): raise TypeError('all items must be WorkInterval')
    return sum(x.observed_ns for x in items)


class FormalTimeLedger:
    def __init__(self,startup:TaskStartupReceipt,*,hard_T:bool=False,hard_t:bool=False):
        if not isinstance(startup,TaskStartupReceipt): raise TypeError('startup must be TaskStartupReceipt')
        self._startup=startup
        self._hard_T=require_bool('hard_T',hard_T); self._hard_t=require_bool('hard_t',hard_t)
        self._hard_required=self._hard_T or self._hard_t
        self._state:WorkState|None=None; self._start:ClockSnapshot|None=None
        self._last_event=startup.clock.probe; self._intervals:list[WorkInterval]=[]; self._gaps:list[CoverageGap]=[]; self._finished=False

    @classmethod
    def resume_from_timeline(cls,startup:TaskStartupReceipt,intervals,gaps,last_snapshot:ClockSnapshot,*,open_state=None,open_start=None,finished:bool=False,hard_T:bool=False,hard_t:bool=False):
        obj=cls(startup,hard_T=hard_T,hard_t=hard_t)
        vals=list(intervals); gap_vals=list(gaps)
        if any(not isinstance(x,WorkInterval) for x in vals): raise TypeError('all resumed intervals must be WorkInterval')
        if any(not isinstance(x,CoverageGap) for x in gap_vals): raise TypeError('all resumed gaps must be CoverageGap')
        if not isinstance(last_snapshot,ClockSnapshot): raise TypeError('last_snapshot must be ClockSnapshot')
        if open_state is not None and not isinstance(open_state,WorkState): open_state=WorkState(open_state)
        if (open_state is None)!=(open_start is None): raise ValueError('open_state/open_start must be paired')
        if open_start is not None and not isinstance(open_start,ClockSnapshot): raise TypeError('open_start must be ClockSnapshot')
        require_bool('finished',finished)
        if finished and (open_state is not None or open_start is not None): raise ValueError('finished ledger cannot restore an open work state')
        obj._intervals=vals; obj._gaps=gap_vals; obj._state=open_state; obj._start=open_start; obj._last_event=last_snapshot; obj._finished=finished
        return obj

    @property
    def timing_ready(self)->bool: return True
    @property
    def formal_started(self)->bool: return bool(self._intervals or (self._state in _FORMAL_T))
    @property
    def finished(self)->bool: return self._finished
    @property
    def foreground_state(self)->WorkState|None: return self._state
    @property
    def intervals(self)->tuple[WorkInterval,...]: return tuple(self._intervals)
    @property
    def coverage_gaps(self)->tuple[CoverageGap,...]: return tuple(self._gaps)

    def _require_open(self):
        if self._finished: raise RuntimeError('ledger is finished')

    def _check_event(self,at:ClockSnapshot):
        if not isinstance(at,ClockSnapshot): raise TypeError('at must be ClockSnapshot')
        if self._hard_required: elapsed_ns(self._last_event,at)
        else: observed_elapsed_ns(self._last_event,at)

    def mark(self,at:ClockSnapshot)->None:
        """Advance the trusted event frontier without changing work state."""
        self._require_open(); self._check_event(at); self._last_event=at

    def transition(self,state:WorkState,at:ClockSnapshot)->None:
        self._require_open(); state=state if isinstance(state,WorkState) else WorkState(state); self._check_event(at)
        if self._state is not None and self._start is not None:
            self._close_interval(at)
        self._state=state; self._start=at; self._last_event=at

    def _close_interval(self,end:ClockSnapshot)->None:
        assert self._state is not None and self._start is not None
        observed=observed_elapsed_ns(self._start,end)
        hard=pair_is_hard_verifiable(self._start,end)
        if self._hard_required and not hard: raise ValueError('hard-required interval lacks continuity verification')
        self._intervals.append(WorkInterval(self._state,self._start,end,observed,hard))

    def _clone_open(self):
        obj=FormalTimeLedger(self._startup,hard_T=self._hard_T,hard_t=self._hard_t)
        obj._state=self._state; obj._start=self._start; obj._last_event=self._last_event
        obj._intervals=list(self._intervals); obj._gaps=list(self._gaps); obj._finished=self._finished
        return obj

    def preview_finish(self,at:ClockSnapshot)->'FormalTimeLedger':
        obj=self._clone_open(); obj.finish(at); return obj

    def finish(self,at:ClockSnapshot)->None:
        self._require_open(); self._check_event(at)
        if self._state is not None and self._start is not None: self._close_interval(at)
        self._state=None; self._start=None; self._last_event=at; self._finished=True

    def formal_T_ns(self)->int: return sum(x.observed_ns for x in self._intervals if x.state in _FORMAL_T)
    def formal_t_ns(self)->int: return sum(x.observed_ns for x in self._intervals if x.state in _FORMAL_t)
    def unattributed_T_ns(self)->int: return sum(x.observed_ns for x in self._gaps if x.state in _FORMAL_T)
    def unattributed_t_ns(self)->int: return sum(x.observed_ns for x in self._gaps if x.state in _FORMAL_t)
    def T_coverage_complete(self)->bool: return self.unattributed_T_ns()==0
    def t_coverage_complete(self)->bool: return self.unattributed_t_ns()==0
    def T_hard_verified(self)->bool:
        rel=[x for x in self._intervals if x.state in _FORMAL_T]
        return bool(rel) and self.T_coverage_complete() and all(x.hard_verified for x in rel)
    def t_hard_verified(self)->bool:
        rel=[x for x in self._intervals if x.state in _FORMAL_t]
        return bool(rel) and self.t_coverage_complete() and all(x.hard_verified for x in rel)

    def to_dict(self)->dict:
        return {
            'timing_ready':True,'formal_started':self.formal_started,'finished':self.finished,
            'foreground_state':self._state.value if self._state else None,
            'intervals':[{'state':x.state.value,'start':x.start.to_dict(),'end':x.end.to_dict(),'observed_ns':x.observed_ns,'hard_verified':x.hard_verified} for x in self._intervals],
            'coverage_gaps':[{'state':x.state.value,'start':x.start.to_dict(),'end':x.end.to_dict(),'observed_ns':x.observed_ns,'hard_verified':x.hard_verified} for x in self._gaps],
            'T_actual_seconds':self.formal_T_ns()/1e9,'t_actual_seconds':self.formal_t_ns()/1e9,
            'T_actual_ns':self.formal_T_ns(),'t_actual_ns':self.formal_t_ns(),
            'unattributed_T_ns':self.unattributed_T_ns(),'unattributed_t_ns':self.unattributed_t_ns(),
            'T_coverage_complete':self.T_coverage_complete(),'t_coverage_complete':self.t_coverage_complete(),
            'T_hard_verified':self.T_hard_verified(),'t_hard_verified':self.t_hard_verified(),
        }
