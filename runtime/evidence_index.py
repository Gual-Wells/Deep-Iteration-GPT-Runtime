"""Minimal evidence locator index for DIGR 5.0 Alpha 3 run workspaces."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any
from .validation import require_nonempty_text
from .workspace import RunWorkspace

@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id:str
    kind:str
    locator:str
    summary:str
    source_scope:str|None=None
    def __post_init__(self):
        for n in ('evidence_id','kind','locator','summary'): object.__setattr__(self,n,require_nonempty_text(n,getattr(self,n)))
        if self.source_scope is not None: object.__setattr__(self,'source_scope',require_nonempty_text('source_scope',self.source_scope))
    def to_dict(self)->dict[str,Any]: return asdict(self)
    @classmethod
    def from_dict(cls,d):return cls(d['evidence_id'],d['kind'],d['locator'],d['summary'],d.get('source_scope'))

class EvidenceIndex:
    def __init__(self,workspace:RunWorkspace): self.workspace=workspace; self._items:dict[str,EvidenceRecord]={}
    def add(self,record:EvidenceRecord)->None:
        if not isinstance(record,EvidenceRecord):raise TypeError('record must be EvidenceRecord')
        if record.evidence_id in self._items: raise ValueError('duplicate evidence_id')
        self._items[record.evidence_id]=record; self._persist()
    def get(self,evidence_id:str)->EvidenceRecord: return self._items[evidence_id]
    @property
    def items(self)->tuple[EvidenceRecord,...]: return tuple(self._items[k] for k in sorted(self._items))
    def _persist(self)->None:self.workspace.write_json('evidence/index.json',{'items':[x.to_dict() for x in self.items]},kind='evidence-index',revision=len(self._items))
    @classmethod
    def load(cls,workspace:RunWorkspace)->'EvidenceIndex':
        obj=cls(workspace);p=workspace.path('evidence/index.json')
        if p.is_file():
            for d in workspace.read_json('evidence/index.json').get('items',[]):
                r=EvidenceRecord.from_dict(d)
                if r.evidence_id in obj._items:raise ValueError('duplicate evidence in persisted index')
                obj._items[r.evidence_id]=r
        return obj
