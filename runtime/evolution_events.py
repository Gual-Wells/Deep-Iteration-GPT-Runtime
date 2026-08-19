"""Hash-chained semantic event receipts for DIGR 5.0 Alpha 3.

Event receipts are deliberately thin: they bind meaningful work to the current
run/journal/strategy/candidate/source state, but do not judge whether the idea
was good.  LiveDIGRRun exposes semantic wrappers; callers should not append raw
receipts directly.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json,os
from pathlib import Path
from typing import Any,Iterable
from .validation import require_nonempty_text,require_nonnegative_int,require_bool

class EvolutionKind(str,Enum):
    MAIN_EVOLUTION='MAIN_EVOLUTION';MAIN_REENTRY='MAIN_REENTRY';SOURCE_EVOLUTION='SOURCE_EVOLUTION';SOURCE_REENTRY='SOURCE_REENTRY'

@dataclass(frozen=True)
class EvolutionEvent:
    seq:int;event_id:str;kind:EvolutionKind;scope:str;summary:str;action:str;result:str
    evidence_refs:tuple[str,...]=();clock_event_ref:str|None=None;strategy_revision:int|None=None;candidate_revision:int|None=None;candidate_after_revision:int|None=None;source_id:str|None=None;source_revision:int|None=None;source_after_revision:int|None=None;retained:bool|None=None;prev_hash:str|None=None;record_hash:str|None=None
    def __post_init__(self):
        require_nonnegative_int('seq',self.seq)
        for n in ('event_id','scope','summary','action','result'):object.__setattr__(self,n,require_nonempty_text(n,getattr(self,n)))
        if not isinstance(self.kind,EvolutionKind):object.__setattr__(self,'kind',EvolutionKind(self.kind))
        object.__setattr__(self,'evidence_refs',tuple(require_nonempty_text('evidence_ref',x) for x in self.evidence_refs))
        if self.clock_event_ref is not None:object.__setattr__(self,'clock_event_ref',require_nonempty_text('clock_event_ref',self.clock_event_ref))
        if self.source_id is not None:object.__setattr__(self,'source_id',require_nonempty_text('source_id',self.source_id))
        for n in ('strategy_revision','candidate_revision','candidate_after_revision','source_revision','source_after_revision'):
            if getattr(self,n) is not None:require_nonnegative_int(n,getattr(self,n))
        if self.retained is not None:require_bool('retained',self.retained)
        # Receipt-v2 structural invariants.  The session wrapper proves that
        # referenced revisions/IDs exist; the receipt itself still refuses
        # context-free or internally contradictory event shapes.
        if self.clock_event_ref is None or self.strategy_revision is None:
            raise ValueError('event v2 requires clock_event_ref and strategy_revision')
        is_source=self.kind in (EvolutionKind.SOURCE_EVOLUTION,EvolutionKind.SOURCE_REENTRY)
        is_reentry=self.kind in (EvolutionKind.MAIN_REENTRY,EvolutionKind.SOURCE_REENTRY)
        if is_source:
            if self.source_id is None or self.scope != f'S:{self.source_id}' or self.source_revision is None:
                raise ValueError('SOURCE event must bind source_id, source_revision and matching S scope')
        elif self.source_id is not None or self.source_revision is not None or self.source_after_revision is not None or self.scope != 'MAIN':
            raise ValueError('MAIN event must use MAIN scope and no source fields')
        if self.kind is EvolutionKind.MAIN_REENTRY:
            if self.candidate_revision is None or self.retained is None:
                raise ValueError('MAIN re-entry requires candidate_before and retained fact')
            if self.retained and self.candidate_after_revision is not None:
                raise ValueError('retained MAIN re-entry cannot name candidate_after_revision')
            if not self.retained and self.candidate_after_revision is None:
                raise ValueError('non-retained MAIN re-entry requires candidate_after_revision')
        elif self.kind is EvolutionKind.SOURCE_REENTRY:
            if self.retained is None:
                raise ValueError('SOURCE re-entry requires retained fact')
            if self.retained and self.source_after_revision is not None:
                raise ValueError('retained SOURCE re-entry cannot name source_after_revision')
            if not self.retained and self.source_after_revision is None:
                raise ValueError('non-retained SOURCE re-entry requires source_after_revision')
            if self.candidate_after_revision is not None:
                raise ValueError('SOURCE re-entry uses source revisions, not candidate_after_revision')
        elif self.retained is not None or self.candidate_after_revision is not None or self.source_after_revision is not None:
            raise ValueError('evolution event cannot carry re-entry outcome fields')
    def payload(self)->dict[str,Any]:
        return {'seq':self.seq,'event_id':self.event_id,'kind':self.kind.value,'scope':self.scope,'summary':self.summary,'action':self.action,'result':self.result,'evidence_refs':list(self.evidence_refs),'clock_event_ref':self.clock_event_ref,'strategy_revision':self.strategy_revision,'candidate_revision':self.candidate_revision,'candidate_after_revision':self.candidate_after_revision,'source_id':self.source_id,'source_revision':self.source_revision,'source_after_revision':self.source_after_revision,'retained':self.retained,'prev_hash':self.prev_hash}
    def to_dict(self):d=self.payload();d['record_hash']=self.record_hash;return d

class EvolutionEventLog:
    def __init__(self,path:Path|None=None):
        self.path=Path(path).resolve() if path is not None else None;self._events:list[EvolutionEvent]=[]
        if self.path is not None:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            if self.path.exists() and self.path.stat().st_size:raise ValueError('event log must be new/empty')
    @property
    def events(self):return tuple(self._events)
    def append(self,*args,**kwargs):raise RuntimeError('raw event append is disabled in Alpha2; use LiveDIGRRun record_* wrappers')
    def _append(self,kind:EvolutionKind,scope:str,summary:str,action:str,result:str,*,evidence_refs:Iterable[str]=(),clock_event_ref:str|None=None,strategy_revision:int|None=None,candidate_revision:int|None=None,candidate_after_revision:int|None=None,source_id:str|None=None,source_revision:int|None=None,source_after_revision:int|None=None,retained:bool|None=None)->EvolutionEvent:
        if not isinstance(kind,EvolutionKind):kind=EvolutionKind(kind)
        seq=len(self._events);prev=self._events[-1].record_hash if self._events else None;eid=f'E{seq:06d}'
        temp=EvolutionEvent(seq,eid,kind,scope,summary,action,result,tuple(evidence_refs),clock_event_ref,strategy_revision,candidate_revision,candidate_after_revision,source_id,source_revision,source_after_revision,retained,prev,None)
        digest=sha256(json.dumps(temp.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        item=EvolutionEvent(seq,eid,kind,scope,summary,action,result,tuple(evidence_refs),clock_event_ref,strategy_revision,candidate_revision,candidate_after_revision,source_id,source_revision,source_after_revision,retained,prev,digest);self._events.append(item)
        if self.path is not None:
            with self.path.open('ab') as f:f.write((json.dumps(item.to_dict(),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode());f.flush();os.fsync(f.fileno())
        return item
    def count(self,kind:EvolutionKind,scope:str|None=None)->int:return sum(1 for e in self._events if e.kind is kind and (scope is None or e.scope==scope))
    @classmethod
    def load(cls,path:Path)->'EvolutionEventLog':
        path=Path(path).resolve();obj=cls.__new__(cls);obj.path=path;obj._events=[]
        if not path.is_file():return obj
        for raw in path.read_text(encoding='utf-8').splitlines():
            d=json.loads(raw);obj._events.append(EvolutionEvent(d['seq'],d['event_id'],EvolutionKind(d['kind']),d['scope'],d['summary'],d['action'],d['result'],tuple(d.get('evidence_refs',[])),d.get('clock_event_ref'),d.get('strategy_revision'),d.get('candidate_revision'),d.get('candidate_after_revision'),d.get('source_id'),d.get('source_revision'),d.get('source_after_revision'),d.get('retained'),d.get('prev_hash'),d.get('record_hash')))
        obj.verify();return obj
    def verify(self)->bool:
        prev=None
        for i,e in enumerate(self._events):
            if e.seq!=i or e.prev_hash!=prev or e.event_id!=f'E{i:06d}':raise ValueError('event chain mismatch')
            digest=sha256(json.dumps(e.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            if digest!=e.record_hash:raise ValueError('event hash mismatch')
            prev=e.record_hash
        return True
