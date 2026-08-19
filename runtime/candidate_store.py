"""Revisioned candidate-result snapshots for DIGR 5.0 Alpha 3.

Candidate snapshots provide an external anchor for whole-process R re-entry
without storing hidden chain-of-thought.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any
from .validation import require_nonempty_text, require_nonnegative_int
from .workspace import RunWorkspace


@dataclass(frozen=True)
class CandidateSnapshot:
    revision: int
    summary: str
    artifact_refs: tuple[str,...] = ()
    evidence_refs: tuple[str,...] = ()
    produced_by: str = 'MAIN'
    digest: str | None = None

    def __post_init__(self):
        require_nonnegative_int('revision',self.revision)
        object.__setattr__(self,'summary',require_nonempty_text('summary',self.summary))
        object.__setattr__(self,'produced_by',require_nonempty_text('produced_by',self.produced_by))
        for n in ('artifact_refs','evidence_refs'):
            vals=tuple(getattr(self,n));
            for x in vals: require_nonempty_text(n,x)
            object.__setattr__(self,n,vals)
        payload={'revision':self.revision,'summary':self.summary,'artifact_refs':list(self.artifact_refs),'evidence_refs':list(self.evidence_refs),'produced_by':self.produced_by}
        calc=sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if self.digest is not None and self.digest!=calc: raise ValueError('candidate digest mismatch')
        object.__setattr__(self,'digest',calc)

    def to_dict(self)->dict[str,Any]:
        d=asdict(self); d['artifact_refs']=list(self.artifact_refs); d['evidence_refs']=list(self.evidence_refs); return d

    @classmethod
    def from_dict(cls,d):
        return cls(d['revision'],d['summary'],tuple(d.get('artifact_refs',[])),tuple(d.get('evidence_refs',[])),d.get('produced_by','MAIN'),d.get('digest'))


class CandidateStore:
    def __init__(self,workspace:RunWorkspace): self.workspace=workspace; self._items:list[CandidateSnapshot]=[]
    def save(self,item:CandidateSnapshot)->CandidateSnapshot:
        if not isinstance(item,CandidateSnapshot): raise TypeError('item must be CandidateSnapshot')
        if item.revision!=len(self._items): raise ValueError(f'candidate revision must be {len(self._items)}')
        self._items.append(item)
        self.workspace.write_json(f'state/candidate-r{item.revision:04d}.json',item.to_dict(),kind='candidate',revision=item.revision)
        self.workspace.write_json('state/candidate-latest.json',item.to_dict(),kind='candidate-latest',revision=item.revision)
        return item
    @property
    def latest(self): return self._items[-1] if self._items else None
    @property
    def current(self): return self.latest
    @property
    def has_state(self)->bool: return bool(self._items)
    @property
    def items(self): return tuple(self._items)
    def get(self,revision:int)->CandidateSnapshot:
        require_nonnegative_int('revision',revision); return self._items[revision]
    @classmethod
    def load(cls,workspace:RunWorkspace)->'CandidateStore':
        obj=cls(workspace)
        for p in sorted(workspace.path('state').glob('candidate-r*.json')):
            obj._items.append(CandidateSnapshot.from_dict(workspace.read_json(str(p.relative_to(workspace.root)))))
        for i,x in enumerate(obj._items):
            if x.revision!=i: raise ValueError('candidate revision chain is not contiguous')
        latest=workspace.path('state/candidate-latest.json')
        if latest.is_file() and (not obj._items or CandidateSnapshot.from_dict(workspace.read_json('state/candidate-latest.json'))!=obj._items[-1]): raise ValueError('candidate latest pointer drift')
        return obj
