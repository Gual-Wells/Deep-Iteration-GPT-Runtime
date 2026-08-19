"""Revisioned source-research workspaces and source-activity binding for Alpha 2."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json, os
from pathlib import Path
from typing import Any, Iterable
from .validation import require_nonempty_text, require_nonnegative_int
from .workspace import RunWorkspace, validate_component_id


@dataclass(frozen=True)
class SourceWorkspaceState:
    source_id: str
    revision: int
    objective: str
    current_direction: str
    status: str='OPEN'
    finding_summary: str|None=None
    contradictions: tuple[str,...]=()
    evidence_refs: tuple[str,...]=()
    pivot_reason: str|None=None

    def __post_init__(self):
        object.__setattr__(self,'source_id',validate_component_id('source_id',self.source_id)); require_nonnegative_int('revision',self.revision)
        object.__setattr__(self,'objective',require_nonempty_text('objective',self.objective)); object.__setattr__(self,'current_direction',require_nonempty_text('current_direction',self.current_direction))
        if self.status not in ('OPEN','CLOSED'): raise ValueError('status must be OPEN/CLOSED')
        if self.finding_summary is not None: object.__setattr__(self,'finding_summary',require_nonempty_text('finding_summary',self.finding_summary))
        if self.pivot_reason is not None: object.__setattr__(self,'pivot_reason',require_nonempty_text('pivot_reason',self.pivot_reason))
        for n in ('contradictions','evidence_refs'):
            vals=tuple(getattr(self,n));
            for x in vals:require_nonempty_text(n,x)
            object.__setattr__(self,n,vals)

    def to_dict(self):
        d=asdict(self); d['contradictions']=list(self.contradictions); d['evidence_refs']=list(self.evidence_refs); return d
    @classmethod
    def from_dict(cls,d):return cls(d['source_id'],d['revision'],d['objective'],d['current_direction'],d.get('status','OPEN'),d.get('finding_summary'),tuple(d.get('contradictions',[])),tuple(d.get('evidence_refs',[])),d.get('pivot_reason'))


class SourceWorkspaceRegistry:
    def __init__(self,workspace:RunWorkspace): self.workspace=workspace; self._hist:dict[str,list[SourceWorkspaceState]]={}
    def _save(self,s:SourceWorkspaceState)->SourceWorkspaceState:
        hist=self._hist.setdefault(s.source_id,[])
        if s.revision!=len(hist): raise ValueError(f'source {s.source_id} revision must be {len(hist)}')
        hist.append(s)
        self.workspace.write_json(f'sources/{s.source_id}/state-r{s.revision:04d}.json',s.to_dict(),kind='source-state',revision=s.revision)
        self.workspace.write_json(f'sources/{s.source_id}/state.json',s.to_dict(),kind='source-latest',revision=s.revision)
        return s
    def open(self,source_id:str,objective:str,current_direction:str|None=None)->SourceWorkspaceState:
        source_id=validate_component_id('source_id',source_id)
        if source_id in self._hist: raise ValueError('duplicate source_id')
        return self._save(SourceWorkspaceState(source_id,0,objective,current_direction or objective))
    def revise(self,source_id:str,*,objective:str|None=None,current_direction:str|None=None,finding_summary:str|None=None,contradictions:Iterable[str]|None=None,evidence_refs:Iterable[str]|None=None,pivot_reason:str|None=None)->SourceWorkspaceState:
        old=self.latest(source_id)
        return self._save(SourceWorkspaceState(source_id,old.revision+1,objective or old.objective,current_direction or old.current_direction,old.status,finding_summary if finding_summary is not None else old.finding_summary,tuple(contradictions) if contradictions is not None else old.contradictions,tuple(evidence_refs) if evidence_refs is not None else old.evidence_refs,pivot_reason))
    def close(self,source_id:str,finding_summary:str)->SourceWorkspaceState:
        old=self.latest(source_id)
        if old.status=='CLOSED': raise ValueError('source already closed')
        return self._save(SourceWorkspaceState(source_id,old.revision+1,old.objective,old.current_direction,'CLOSED',finding_summary,old.contradictions,old.evidence_refs,'closed'))
    def reopen(self,source_id:str,*,current_direction:str|None=None,reason:str)->SourceWorkspaceState:
        old=self.latest(source_id)
        if old.status!='CLOSED': raise ValueError('source must be CLOSED before reopen')
        return self._save(SourceWorkspaceState(source_id,old.revision+1,old.objective,current_direction or old.current_direction,'OPEN',old.finding_summary,old.contradictions,old.evidence_refs,reason))
    def latest(self,source_id:str)->SourceWorkspaceState:return self._hist[source_id][-1]
    def get(self,source_id:str,revision:int)->SourceWorkspaceState:
        require_nonnegative_int('source revision',revision); return self._hist[source_id][revision]
    def history(self,source_id:str)->tuple[SourceWorkspaceState,...]: return tuple(self._hist[source_id])
    @property
    def states(self)->tuple[SourceWorkspaceState,...]: return tuple(self._hist[k][-1] for k in sorted(self._hist))
    @property
    def open_states(self)->tuple[SourceWorkspaceState,...]:return tuple(x for x in self.states if x.status=='OPEN')
    def exists(self,source_id:str)->bool:return source_id in self._hist
    @classmethod
    def load(cls,workspace:RunWorkspace)->'SourceWorkspaceRegistry':
        obj=cls(workspace)
        root=workspace.path('sources')
        for d in sorted(x for x in root.iterdir() if x.is_dir()):
            hist=[]
            for p in sorted(d.glob('state-r*.json')):
                item=SourceWorkspaceState.from_dict(workspace.read_json(str(p.relative_to(workspace.root))))
                if item.revision!=len(hist) or item.source_id!=d.name: raise ValueError('source revision/identity drift')
                hist.append(item)
            if hist:
                latest=SourceWorkspaceState.from_dict(workspace.read_json(str((d/'state.json').relative_to(workspace.root))))
                if latest!=hist[-1]: raise ValueError('source latest pointer drift')
                obj._hist[d.name]=hist
        return obj


@dataclass(frozen=True)
class SourceActivityEvent:
    seq:int
    clock_event_ref:str
    source_ids:tuple[str,...]
    prev_hash:str|None
    record_hash:str
    def payload(self):return {'seq':self.seq,'clock_event_ref':self.clock_event_ref,'source_ids':list(self.source_ids),'prev_hash':self.prev_hash}
    def to_dict(self):d=self.payload();d['record_hash']=self.record_hash;return d


class SourceActivityLog:
    """Binds each SOURCE state-start journal event to one or more real S IDs."""
    def __init__(self,path:Path):
        self.path=Path(path).resolve(); self.path.parent.mkdir(parents=True,exist_ok=True); self._items:list[SourceActivityEvent]=[]
        if self.path.exists() and self.path.stat().st_size: raise ValueError('source activity log must be new/empty')
    @property
    def items(self):return tuple(self._items)
    def append(self,clock_event_ref:str,source_ids:Iterable[str])->SourceActivityEvent:
        ref=require_nonempty_text('clock_event_ref',clock_event_ref); ids=tuple(dict.fromkeys(validate_component_id('source_id',x) for x in source_ids))
        if not ids:raise ValueError('SOURCE activity requires at least one active source_id')
        seq=len(self._items); prev=self._items[-1].record_hash if self._items else None
        payload={'seq':seq,'clock_event_ref':ref,'source_ids':list(ids),'prev_hash':prev}; digest=sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        item=SourceActivityEvent(seq,ref,ids,prev,digest); self._items.append(item)
        with self.path.open('ab') as f:f.write((json.dumps(item.to_dict(),ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode());f.flush();os.fsync(f.fileno())
        return item
    def by_clock_ref(self):return {x.clock_event_ref:x.source_ids for x in self._items}
    def verify(self)->bool:
        prev=None;seen_clock_refs=set()
        for i,x in enumerate(self._items):
            if x.seq!=i or x.prev_hash!=prev:raise ValueError('source activity chain mismatch')
            if x.clock_event_ref in seen_clock_refs:raise ValueError('duplicate source activity binding for one SOURCE clock event')
            seen_clock_refs.add(x.clock_event_ref)
            digest=sha256(json.dumps(x.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if digest!=x.record_hash:raise ValueError('source activity digest mismatch')
            prev=x.record_hash
        return True
    @classmethod
    def load(cls,path:Path)->'SourceActivityLog':
        path=Path(path).resolve();obj=cls.__new__(cls);obj.path=path;obj._items=[]
        if not path.is_file():return obj
        for raw in path.read_text(encoding='utf-8').splitlines():
            d=json.loads(raw);obj._items.append(SourceActivityEvent(d['seq'],d['clock_event_ref'],tuple(d['source_ids']),d.get('prev_hash'),d['record_hash']))
        obj.verify();return obj
