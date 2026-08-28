"""Clock-event bindings for exclusive D and V work."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json,os
from pathlib import Path
from .workspace import validate_component_id
from .validation import require_nonnegative_int

@dataclass(frozen=True)
class ExclusiveActivity:
    seq:int
    kind:str
    clock_event_ref:str
    component_ids:tuple[str,...]
    prev_hash:str|None
    record_hash:str
    def __post_init__(self):
        require_nonnegative_int('seq',self.seq)
        if self.kind not in ('D','V'):raise ValueError('exclusive activity kind must be D/V')
        if not isinstance(self.clock_event_ref,str) or not self.clock_event_ref:raise ValueError('clock_event_ref required')
        ids=tuple(validate_component_id('component_id',x) for x in self.component_ids)
        if not ids:raise ValueError('exclusive activity requires at least one component id')
        if len(ids)!=len(set(ids)):raise ValueError('duplicate component id')
        object.__setattr__(self,'component_ids',ids)
        for name,value in (('clock_event_ref',self.clock_event_ref),('record_hash',self.record_hash)):
            if len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError(f'{name} must be lowercase SHA-256')
        if self.prev_hash is not None and (len(self.prev_hash)!=64 or any(c not in '0123456789abcdef' for c in self.prev_hash)):raise ValueError('prev_hash must be lowercase SHA-256')
    def payload(self):return {'schema_version':1,'seq':self.seq,'kind':self.kind,'clock_event_ref':self.clock_event_ref,'component_ids':list(self.component_ids),'prev_hash':self.prev_hash}
    def to_dict(self):d=self.payload();d['record_hash']=self.record_hash;return d

class ExclusiveActivityLog:
    def __init__(self,path:Path,kind:str):
        if kind not in ('D','V'):raise ValueError('kind must be D/V')
        self.path=Path(path).resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists() and self.path.stat().st_size:raise ValueError('exclusive activity log must be new/empty')
        self.kind=kind;self._items=[]
    @property
    def items(self):return tuple(self._items)
    def by_clock_ref(self):return {x.clock_event_ref:x.component_ids for x in self._items}
    def bind(self,clock_event_ref:str,component_ids)->ExclusiveActivity:
        ids=tuple(component_ids);seq=len(self._items);prev=self._items[-1].record_hash if self._items else None
        payload={'schema_version':1,'seq':seq,'kind':self.kind,'clock_event_ref':clock_event_ref,'component_ids':list(ids),'prev_hash':prev}
        digest=sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        item=ExclusiveActivity(seq,self.kind,clock_event_ref,ids,prev,digest)
        if any(x.clock_event_ref==clock_event_ref for x in self._items):raise ValueError(f'{self.kind} clock event already bound')
        with self.path.open('ab') as f:f.write((json.dumps(item.to_dict(),ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode());f.flush();os.fsync(f.fileno())
        self._items.append(item);return item
    def verify(self)->bool:
        prev=None;seen=set()
        for seq,item in enumerate(self._items):
            if item.seq!=seq or item.kind!=self.kind or item.prev_hash!=prev:raise ValueError(f'{self.kind} activity chain mismatch')
            if item.clock_event_ref in seen:raise ValueError(f'duplicate {self.kind} activity clock binding')
            digest=sha256(json.dumps(item.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if digest!=item.record_hash:raise ValueError(f'{self.kind} activity digest mismatch')
            seen.add(item.clock_event_ref);prev=item.record_hash
        return True
    @classmethod
    def load(cls,path:Path,kind:str):
        path=Path(path).resolve();obj=cls.__new__(cls);obj.path=path;obj.kind=kind;obj._items=[]
        if not path.exists():return obj
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            d=json.loads(line);obj._items.append(ExclusiveActivity(d['seq'],d['kind'],d['clock_event_ref'],tuple(d['component_ids']),d.get('prev_hash'),d['record_hash']))
        obj.verify();return obj
