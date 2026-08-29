"""Isolated persistent viewpoint channels for DIGR 5.0.0-Berta2."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from .validation import require_bool, require_nonempty_text, require_nonnegative_int
from .workspace import RunWorkspace, validate_component_id


@dataclass(frozen=True)
class ViewpointEvent:
    revision: int
    behavior: str
    finding: str
    clock_event_ref: str
    evidence_refs: tuple[str,...]=()
    def __post_init__(self):
        require_nonnegative_int('revision',self.revision)
        object.__setattr__(self,'behavior',require_nonempty_text('behavior',self.behavior))
        object.__setattr__(self,'finding',require_nonempty_text('finding',self.finding))
        object.__setattr__(self,'clock_event_ref',require_nonempty_text('clock_event_ref',self.clock_event_ref))
        object.__setattr__(self,'evidence_refs',tuple(self.evidence_refs))


@dataclass(frozen=True)
class ViewpointState:
    viewpoint_id: str
    premise: str
    events: tuple[ViewpointEvent,...]=()
    status: str='OPEN'
    result: str|None=None
    semantic_distance: str|None=None
    nonredundant: bool=False
    def __post_init__(self):
        object.__setattr__(self,'viewpoint_id',validate_component_id('viewpoint_id',self.viewpoint_id))
        object.__setattr__(self,'premise',require_nonempty_text('premise',self.premise))
        object.__setattr__(self,'events',tuple(self.events))
        if self.status not in ('OPEN','QUALIFIED','DISCARDED'):raise ValueError('invalid viewpoint status')
        require_bool('nonredundant',self.nonredundant)
        if self.status=='QUALIFIED':
            if not self.events:raise ValueError('qualified viewpoint requires persistent work events')
            object.__setattr__(self,'result',require_nonempty_text('result',self.result))
            object.__setattr__(self,'semantic_distance',require_nonempty_text('semantic_distance',self.semantic_distance))
            if not self.nonredundant:raise ValueError('qualified viewpoint requires nonredundant=True')
    @property
    def revision(self)->int:return len(self.events) + (1 if self.status!='OPEN' else 0)
    @property
    def result_digest(self)->str|None:
        return sha256(self.result.encode('utf-8')).hexdigest() if self.result else None
    def to_dict(self)->dict[str,Any]:
        return {
            'schema_version':1,'viewpoint_id':self.viewpoint_id,'premise':self.premise,
            'events':[asdict(x) for x in self.events],'status':self.status,'result':self.result,
            'result_digest':self.result_digest,'semantic_distance':self.semantic_distance,
            'nonredundant':self.nonredundant,'revision':self.revision,
        }
    @classmethod
    def from_dict(cls,d):
        return cls(d['viewpoint_id'],d['premise'],tuple(ViewpointEvent(x['revision'],x['behavior'],x['finding'],x['clock_event_ref'],tuple(x.get('evidence_refs',()))) for x in d.get('events',())),d.get('status','OPEN'),d.get('result'),d.get('semantic_distance'),d.get('nonredundant',False))


class ViewpointStore:
    """Main-owned registry; no API exposes one VLedger to another V channel."""
    def __init__(self,workspace:RunWorkspace):self.workspace=workspace;self._states:dict[str,ViewpointState]={}
    @property
    def states(self):return tuple(self._states[k] for k in sorted(self._states))
    @property
    def qualified(self):return tuple(x for x in self.states if x.status=='QUALIFIED')
    def exists(self,viewpoint_id:str)->bool:return viewpoint_id in self._states
    def get(self,viewpoint_id:str)->ViewpointState:return self._states[viewpoint_id]
    def _save(self,state:ViewpointState)->ViewpointState:
        self._states[state.viewpoint_id]=state
        rel=f'viewpoints/{state.viewpoint_id}/ledger-r{state.revision:04d}.json'
        self.workspace.write_json(rel,state.to_dict(),kind='viewpoint-ledger',revision=state.revision)
        return state
    def open(self,viewpoint_id:str,premise:str)->ViewpointState:
        viewpoint_id=validate_component_id('viewpoint_id',viewpoint_id)
        if viewpoint_id in self._states:raise ValueError('viewpoint already exists')
        return self._save(ViewpointState(viewpoint_id,premise))
    def record(self,viewpoint_id:str,behavior:str,finding:str,clock_event_ref:str,evidence_refs=())->ViewpointState:
        old=self.get(viewpoint_id)
        if old.status!='OPEN':raise ValueError('viewpoint is terminal')
        event=ViewpointEvent(len(old.events),behavior,finding,clock_event_ref,tuple(evidence_refs))
        return self._save(ViewpointState(old.viewpoint_id,old.premise,old.events+(event,)))
    def qualify(self,viewpoint_id:str,result:str,semantic_distance:str,*,nonredundant:bool)->ViewpointState:
        old=self.get(viewpoint_id)
        if old.status!='OPEN':raise ValueError('viewpoint is terminal')
        return self._save(ViewpointState(old.viewpoint_id,old.premise,old.events,'QUALIFIED',result,semantic_distance,nonredundant))
    def discard(self,viewpoint_id:str,reason:str)->ViewpointState:
        old=self.get(viewpoint_id)
        if old.status!='OPEN':raise ValueError('viewpoint is terminal')
        return self._save(ViewpointState(old.viewpoint_id,old.premise,old.events,'DISCARDED',require_nonempty_text('reason',reason),None,False))
    @classmethod
    def load(cls,workspace:RunWorkspace)->'ViewpointStore':
        obj=cls(workspace);root=workspace.path('viewpoints')
        if not root.exists():return obj
        for directory in sorted(p for p in root.iterdir() if p.is_dir()):
            revisions=sorted(directory.glob('ledger-r*.json'))
            previous=None
            for expected,path in enumerate(revisions):
                state=ViewpointState.from_dict(workspace.read_json(str(path.relative_to(workspace.root))))
                if state.viewpoint_id!=directory.name or state.revision!=expected:raise ValueError('viewpoint revision/identity drift')
                if previous is not None:
                    if state.premise!=previous.premise or state.events[:len(previous.events)]!=previous.events:raise ValueError('viewpoint ledger history was rewritten')
                    if previous.status!='OPEN':raise ValueError('terminal viewpoint has later revisions')
                previous=state
            if previous is not None:obj._states[directory.name]=previous
        return obj
