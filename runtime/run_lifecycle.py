"""Persisted run lifecycle for DIGR 5.0.0-Berta1.

RunPhase constrains lifecycle ordering only. It is not a workflow planner and
never dictates task strategy.

``FINISHED`` remains readable solely for alpha.4 recovery compatibility.
Stable.1 runs can claim success only after the crash-safe two-phase delivery
commit reaches its persisted ``DELIVERED`` phase; an irrecoverably closed run
whose delivery gates were not met is
``INCOMPLETE`` and can never render a canonical proof.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from .validation import require_nonnegative_int, require_nonempty_text
from .workspace import RunWorkspace


class RunPhase(str, Enum):
    GENESIS='GENESIS'
    PARAMETER_RESOLVED='PARAMETER_RESOLVED'
    U0_FROZEN='U0_FROZEN'
    CONTRACT_FROZEN='CONTRACT_FROZEN'
    EXECUTING='EXECUTING'
    FINALIZING='FINALIZING'
    DELIVERED='DELIVERED'
    INCOMPLETE='INCOMPLETE'
    # Legacy alpha.4 terminal state. New stable.1 code must not create it.
    FINISHED='FINISHED'
    ABORTED='ABORTED'


_ALLOWED = {
    RunPhase.GENESIS: {RunPhase.PARAMETER_RESOLVED, RunPhase.ABORTED},
    RunPhase.PARAMETER_RESOLVED: {RunPhase.U0_FROZEN, RunPhase.ABORTED},
    RunPhase.U0_FROZEN: {RunPhase.CONTRACT_FROZEN, RunPhase.ABORTED},
    RunPhase.CONTRACT_FROZEN: {RunPhase.EXECUTING, RunPhase.ABORTED},
    RunPhase.EXECUTING: {RunPhase.FINALIZING, RunPhase.ABORTED},
    RunPhase.FINALIZING: {
        RunPhase.DELIVERED, RunPhase.INCOMPLETE, RunPhase.ABORTED,
        RunPhase.FINISHED,
    },
    RunPhase.DELIVERED: set(),
    RunPhase.INCOMPLETE: set(),
    RunPhase.FINISHED: set(),
    RunPhase.ABORTED: set(),
}


@dataclass(frozen=True)
class RunPhaseState:
    revision: int
    phase: RunPhase
    previous: RunPhase | None
    reason: str
    def __post_init__(self):
        require_nonnegative_int('revision', self.revision)
        if not isinstance(self.phase, RunPhase): object.__setattr__(self,'phase',RunPhase(self.phase))
        if self.previous is not None and not isinstance(self.previous,RunPhase): object.__setattr__(self,'previous',RunPhase(self.previous))
        object.__setattr__(self,'reason',require_nonempty_text('reason',self.reason))
    def to_dict(self):
        d=asdict(self); d['phase']=self.phase.value; d['previous']=self.previous.value if self.previous else None; return d
    @classmethod
    def from_dict(cls,d): return cls(d['revision'],RunPhase(d['phase']),RunPhase(d['previous']) if d.get('previous') else None,d['reason'])


class RunPhaseStore:
    def __init__(self, workspace: RunWorkspace, initialize: bool=True):
        self.workspace=workspace; self._history:list[RunPhaseState]=[]
        if initialize: self._save(RunPhaseState(0,RunPhase.GENESIS,None,'trusted clock genesis and workspace created'))
    def _save(self,state):
        if state.revision!=len(self._history): raise ValueError('run phase revision drift')
        self._history.append(state)
        self.workspace.write_json(f'state/run-phase-r{state.revision:04d}.json',state.to_dict(),kind='run-phase',revision=state.revision)
        self.workspace.write_json('state/run-phase.json',state.to_dict(),kind='run-phase-latest',revision=state.revision)
        return state
    @property
    def current(self): return self._history[-1]
    @property
    def phase(self): return self.current.phase
    @property
    def history(self): return tuple(self._history)
    def transition(self,phase:RunPhase,reason:str):
        phase=phase if isinstance(phase,RunPhase) else RunPhase(phase)
        cur=self.phase
        if phase not in _ALLOWED[cur]: raise RuntimeError(f'illegal run phase transition {cur.value}->{phase.value}')
        return self._save(RunPhaseState(len(self._history),phase,cur,reason))
    def abort(self,reason:str):
        if self.phase in (
            RunPhase.DELIVERED, RunPhase.INCOMPLETE,
            RunPhase.FINISHED, RunPhase.ABORTED,
        ):
            raise RuntimeError('terminal run cannot be aborted again')
        return self.transition(RunPhase.ABORTED,reason)
    def verify(self)->bool:
        if not self._history:raise ValueError('run phase history missing')
        first=self._history[0]
        if first.revision!=0 or first.phase is not RunPhase.GENESIS or first.previous is not None:
            raise ValueError('run phase history must start at GENESIS')
        for before,after in zip(self._history,self._history[1:]):
            if after.previous is not before.phase or after.phase not in _ALLOWED[before.phase]:
                raise ValueError(f'illegal persisted run phase transition {before.phase.value}->{after.phase.value}')
        return True
    @classmethod
    def load(cls,workspace:RunWorkspace):
        obj=cls.__new__(cls);obj.workspace=workspace;obj._history=[]
        for p in sorted(workspace.path('state').glob('run-phase-r*.json')):
            item=RunPhaseState.from_dict(workspace.read_json(str(p.relative_to(workspace.root))))
            if item.revision!=len(obj._history): raise ValueError('run phase history revision drift')
            if obj._history and item.previous is not obj._history[-1].phase: raise ValueError('run phase previous pointer drift')
            obj._history.append(item)
        if not obj._history: raise ValueError('run phase history missing')
        latest=RunPhaseState.from_dict(workspace.read_json('state/run-phase.json'))
        if latest!=obj._history[-1]: raise ValueError('run phase latest pointer drift')
        obj.verify();return obj
