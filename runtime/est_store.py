"""Lightweight revisioned Evolution State Tree memory for DIGR 5.0 Alpha 3.

EST is a compact working-memory index, not a search algorithm and not a second
source of truth for Strategy/Candidate.  It references their revisions instead
of duplicating the current plan/result.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any
from .validation import require_nonempty_text, require_nonnegative_int
from .workspace import RunWorkspace


@dataclass(frozen=True)
class ESTSnapshot:
    scope: str
    revision: int
    currently_supported_facts: tuple[str,...]
    current_decisions: tuple[str,...]
    superseded_assumptions: tuple[str,...]
    open_questions: tuple[str,...]
    active_routes: tuple[str,...] = ()
    dormant_reopenable_routes: tuple[str,...] = ()
    last_meaningful_changes: tuple[str,...] = ()
    strategy_revision: int | None = None
    candidate_revision: int | None = None

    def __post_init__(self):
        object.__setattr__(self,'scope',require_nonempty_text('scope',self.scope)); require_nonnegative_int('revision',self.revision)
        for n in ('strategy_revision','candidate_revision'):
            v=getattr(self,n)
            if v is not None: require_nonnegative_int(n,v)
        for n in ('currently_supported_facts','current_decisions','superseded_assumptions','open_questions','active_routes','dormant_reopenable_routes','last_meaningful_changes'):
            vals=tuple(getattr(self,n));
            for x in vals: require_nonempty_text(n,x)
            object.__setattr__(self,n,vals)

    def to_dict(self)->dict[str,Any]:
        d=asdict(self)
        for k,v in list(d.items()):
            if isinstance(v,tuple): d[k]=list(v)
        return d

    @classmethod
    def from_dict(cls,d):
        return cls(d['scope'],d['revision'],tuple(d.get('currently_supported_facts',[])),tuple(d.get('current_decisions',[])),tuple(d.get('superseded_assumptions',[])),tuple(d.get('open_questions',[])),tuple(d.get('active_routes',[])),tuple(d.get('dormant_reopenable_routes',[])),tuple(d.get('last_meaningful_changes',[])),d.get('strategy_revision'),d.get('candidate_revision'))


class ESTStore:
    def __init__(self,workspace:RunWorkspace): self.workspace=workspace; self._latest:dict[str,ESTSnapshot]={}; self._history:dict[str,list[ESTSnapshot]]={}
    def save(self,snapshot:ESTSnapshot)->str:
        if not isinstance(snapshot,ESTSnapshot): raise TypeError('snapshot must be ESTSnapshot')
        prev=self._latest.get(snapshot.scope); expected=0 if prev is None else prev.revision+1
        if snapshot.revision!=expected: raise ValueError(f'EST revision must be {expected}')
        self._latest[snapshot.scope]=snapshot; self._history.setdefault(snapshot.scope,[]).append(snapshot)
        safe=''.join(c if c.isalnum() or c in '._-' else '_' for c in snapshot.scope)[:48]; tag=sha256(snapshot.scope.encode()).hexdigest()[:10]; stem=f'est-{safe}-{tag}'
        self.workspace.write_json(f'state/{stem}-r{snapshot.revision:04d}.json',snapshot.to_dict(),kind='est',revision=snapshot.revision)
        return self.workspace.write_json(f'state/{stem}-latest.json',snapshot.to_dict(),kind='est-latest',revision=snapshot.revision)
    def latest(self,scope:str)->ESTSnapshot|None:return self._latest.get(scope)
    @property
    def scopes(self):return tuple(self._latest)
    @classmethod
    def load(cls,workspace:RunWorkspace)->'ESTStore':
        obj=cls(workspace)
        files=sorted(p for p in workspace.path('state').glob('est-*-r*.json'))
        for p in files:
            item=ESTSnapshot.from_dict(workspace.read_json(str(p.relative_to(workspace.root))))
            prev=obj._latest.get(item.scope); expected=0 if prev is None else prev.revision+1
            if item.revision!=expected: raise ValueError('EST revision chain drift')
            obj._latest[item.scope]=item; obj._history.setdefault(item.scope,[]).append(item)
        # Latest pointers are convenience artifacts, but recovery must still
        # prove they agree with immutable revision history rather than trusting
        # a separately re-indexed stale/edited cache.
        for scope,item in obj._latest.items():
            safe=''.join(c if c.isalnum() or c in '._-' else '_' for c in scope)[:48]
            tag=sha256(scope.encode()).hexdigest()[:10]; rel=f'state/est-{safe}-{tag}-latest.json'
            if not workspace.path(rel).is_file(): raise ValueError('EST latest pointer missing')
            latest=ESTSnapshot.from_dict(workspace.read_json(rel))
            if latest!=item: raise ValueError('EST latest pointer drift')
        return obj
