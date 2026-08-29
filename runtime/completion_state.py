"""Revisioned semantic completion/open-gap memory for DIGR 5.0.0-Berta2."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from .validation import require_nonempty_text,require_bool,require_nonnegative_int
from .workspace import RunWorkspace,validate_component_id

COMPLETION_CRITERIA=('objective_coverage','evidence_integrity','adversarial_resilience','residual_risk')

@dataclass(frozen=True)
class CriterionAssessment:
    criterion:str
    satisfied:bool
    rationale:str
    def __post_init__(self):
        if self.criterion not in COMPLETION_CRITERIA:raise ValueError('unknown completion criterion')
        require_bool('satisfied',self.satisfied)
        object.__setattr__(self,'rationale',require_nonempty_text('rationale',self.rationale))

@dataclass(frozen=True)
class Gap:
    gap_id:str
    revision:int
    description:str
    blocking:bool
    status:str='OPEN'
    resolution:str|None=None
    change_reason:str='opened'
    def __post_init__(self):
        object.__setattr__(self,'gap_id',validate_component_id('gap_id',self.gap_id));require_nonnegative_int('revision',self.revision)
        object.__setattr__(self,'description',require_nonempty_text('description',self.description));require_bool('blocking',self.blocking)
        if self.status not in ('OPEN','CLOSED'):raise ValueError('status must be OPEN/CLOSED')
        if self.status=='CLOSED' and self.resolution is None:raise ValueError('closed gap requires resolution')
        if self.resolution is not None:object.__setattr__(self,'resolution',require_nonempty_text('resolution',self.resolution))
        object.__setattr__(self,'change_reason',require_nonempty_text('change_reason',self.change_reason))
    @classmethod
    def from_dict(cls,d):return cls(d['gap_id'],d['revision'],d['description'],d['blocking'],d.get('status','OPEN'),d.get('resolution'),d.get('change_reason','restored'))

class CompletionState:
    def __init__(self,workspace:RunWorkspace):self.workspace=workspace;self._hist:dict[str,list[Gap]]={};self._assessments:list[str]=[];self._structured:list[tuple[CriterionAssessment,...]]=[]
    def _save_gap(self,g:Gap)->Gap:
        h=self._hist.setdefault(g.gap_id,[])
        if g.revision!=len(h):raise ValueError(f'gap revision must be {len(h)}')
        h.append(g);self.workspace.write_json(f'state/gaps/{g.gap_id}-r{g.revision:04d}.json',asdict(g),kind='completion-gap',revision=g.revision);self._persist();return g
    def open_gap(self,gap_id:str,description:str,blocking:bool)->Gap:
        if gap_id in self._hist:raise ValueError('gap already exists')
        return self._save_gap(Gap(gap_id,0,description,blocking))
    def revise_gap(self,gap_id:str,*,description:str|None=None,blocking:bool|None=None,reason:str)->Gap:
        old=self.latest(gap_id);return self._save_gap(Gap(gap_id,old.revision+1,description or old.description,old.blocking if blocking is None else blocking,old.status,old.resolution,reason))
    def close_gap(self,gap_id:str,resolution:str)->Gap:
        old=self.latest(gap_id)
        if old.status=='CLOSED':raise ValueError('gap already closed')
        return self._save_gap(Gap(gap_id,old.revision+1,old.description,old.blocking,'CLOSED',resolution,'closed'))
    def reopen_gap(self,gap_id:str,reason:str)->Gap:
        old=self.latest(gap_id)
        if old.status!='CLOSED':raise ValueError('gap must be closed before reopen')
        return self._save_gap(Gap(gap_id,old.revision+1,old.description,old.blocking,'OPEN',None,reason))
    def latest(self,gap_id:str)->Gap:return self._hist[gap_id][-1]
    def assess(self,summary:str)->None:self._assessments.append(require_nonempty_text('assessment',summary));self._persist()
    def assess_structured(self,assessments)->tuple[CriterionAssessment,...]:
        if isinstance(assessments,dict):
            values=tuple(CriterionAssessment(name,bool(assessments[name][0]),assessments[name][1]) for name in COMPLETION_CRITERIA)
        else:values=tuple(assessments)
        if tuple(x.criterion for x in values)!=COMPLETION_CRITERIA:raise ValueError('structured assessment must cover all criteria in canonical order')
        self._structured.append(values);self._persist();return values
    @property
    def gaps(self):return tuple(self._hist[k][-1] for k in sorted(self._hist))
    @property
    def blocking_open(self):return tuple(g for g in self.gaps if g.status=='OPEN' and g.blocking)
    @property
    def semantically_assessed(self):return bool(self._assessments or self._structured)
    @property
    def structured_ready(self):return bool(self._structured) and all(x.satisfied for x in self._structured[-1])
    @property
    def ready(self):return self.semantically_assessed and not self.blocking_open
    @property
    def delivery_failures(self)->tuple[str,...]:
        failures=[]
        if not self.semantically_assessed:failures.append('SEMANTIC_ASSESSMENT_MISSING')
        failures.extend(f'BLOCKING_GAP:{g.gap_id}' for g in self.blocking_open)
        return tuple(failures)
    def require_delivery_ready(self)->None:
        if self.delivery_failures:
            raise RuntimeError('semantic delivery gate unmet: ' + ','.join(self.delivery_failures))
    @property
    def latest_assessment(self):return self._assessments[-1] if self._assessments else None
    def _persist(self):self.workspace.write_json('state/completion.json',{'gaps':[asdict(g) for g in self.gaps],'assessment_revisions':list(self._assessments),'structured_revisions':[[asdict(x) for x in revision] for revision in self._structured]},kind='completion',revision=sum(len(v) for v in self._hist.values())+len(self._assessments)+len(self._structured))
    @classmethod
    def load(cls,workspace:RunWorkspace)->'CompletionState':
        obj=cls(workspace);root=workspace.path('state/gaps')
        if root.exists():
            for p in sorted(root.glob('*-r*.json')):
                g=Gap.from_dict(workspace.read_json(str(p.relative_to(workspace.root))));h=obj._hist.setdefault(g.gap_id,[])
                if g.revision!=len(h):raise ValueError('gap revision chain drift')
                h.append(g)
        p=workspace.path('state/completion.json')
        if p.is_file():
            d=workspace.read_json('state/completion.json');obj._assessments=list(d.get('assessment_revisions',[]));obj._structured=[tuple(CriterionAssessment(**x) for x in revision) for revision in d.get('structured_revisions',[])]
            current={g.gap_id:g for g in obj.gaps}
            for raw in d.get('gaps',[]):
                g=Gap.from_dict(raw)
                if current.get(g.gap_id)!=g:raise ValueError('completion latest gap drift')
        return obj
