"""Revisioned, non-authoritative Strategy State for DIGR 5.0 Alpha 2.

A strategy snapshot records the model's current working approach. It never
contains a scheduler field such as next_step/score/priority and never gains the
immutability of U0 or the Effective Contract.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .validation import require_nonempty_text, require_nonnegative_int
from .workspace import RunWorkspace


@dataclass(frozen=True)
class StrategyState:
    revision: int
    current_task_model: str
    current_primary_route: str
    alternative_routes: tuple[str, ...] = ()
    source_strategy: str = 'not-yet-specified'
    validation_strategy: str = 'not-yet-specified'
    tool_strategy: str = 'not-yet-specified'
    current_assumptions: tuple[str, ...] = ()
    current_risks: tuple[str, ...] = ()
    pivot_reason: str = 'strategy genesis'
    triggering_event_refs: tuple[str, ...] = ()

    def __post_init__(self):
        require_nonnegative_int('revision',self.revision)
        for n in ('current_task_model','current_primary_route','source_strategy','validation_strategy','tool_strategy','pivot_reason'):
            object.__setattr__(self,n,require_nonempty_text(n,getattr(self,n)))
        for n in ('alternative_routes','current_assumptions','current_risks','triggering_event_refs'):
            vals=tuple(getattr(self,n));
            for x in vals: require_nonempty_text(n,x)
            object.__setattr__(self,n,vals)

    def to_dict(self)->dict[str,Any]:
        d=asdict(self)
        for k,v in list(d.items()):
            if isinstance(v,tuple): d[k]=list(v)
        return d

    @classmethod
    def from_dict(cls,d:dict[str,Any])->'StrategyState':
        return cls(
            d['revision'],d['current_task_model'],d['current_primary_route'],
            tuple(d.get('alternative_routes',[])),d.get('source_strategy','not-yet-specified'),
            d.get('validation_strategy','not-yet-specified'),d.get('tool_strategy','not-yet-specified'),
            tuple(d.get('current_assumptions',[])),tuple(d.get('current_risks',[])),
            d.get('pivot_reason','restored'),tuple(d.get('triggering_event_refs',[])),
        )


class StrategyStore:
    def __init__(self,workspace:RunWorkspace):
        if not isinstance(workspace,RunWorkspace): raise TypeError('workspace must be RunWorkspace')
        self.workspace=workspace; self._items:list[StrategyState]=[]

    def save(self,state:StrategyState)->StrategyState:
        if not isinstance(state,StrategyState): raise TypeError('state must be StrategyState')
        expected=len(self._items)
        if state.revision!=expected: raise ValueError(f'strategy revision must be {expected}')
        self._items.append(state)
        self.workspace.write_json(f'state/strategy-r{state.revision:04d}.json',state.to_dict(),kind='strategy',revision=state.revision)
        self.workspace.write_json('state/strategy-latest.json',state.to_dict(),kind='strategy-latest',revision=state.revision)
        return state

    @property
    def latest(self)->StrategyState|None: return self._items[-1] if self._items else None
    @property
    def current(self)->StrategyState|None: return self.latest
    @property
    def has_state(self)->bool: return bool(self._items)
    @property
    def items(self)->tuple[StrategyState,...]: return tuple(self._items)

    @classmethod
    def load(cls,workspace:RunWorkspace)->'StrategyStore':
        obj=cls(workspace)
        for p in sorted(workspace.path('state').glob('strategy-r*.json')):
            obj._items.append(StrategyState.from_dict(workspace.read_json(str(p.relative_to(workspace.root)))))
        for i,x in enumerate(obj._items):
            if x.revision!=i: raise ValueError('strategy revision chain is not contiguous')
        latest=workspace.path('state/strategy-latest.json')
        if latest.is_file() and (not obj._items or StrategyState.from_dict(workspace.read_json('state/strategy-latest.json'))!=obj._items[-1]):
            raise ValueError('strategy latest pointer drift')
        return obj
