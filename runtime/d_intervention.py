"""Revisioned Disruptive Gambit intervention sessions for DIGR 5.0 Alpha 3.

The store persists D history and isolation linkage. It does not choose a gambit
or evaluate its intellectual merit; the native model owns those decisions.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable
from .validation import require_nonempty_text, require_nonnegative_int
from .workspace import RunWorkspace, validate_component_id
from .isolation_checks import IsolationReceipt


@dataclass(frozen=True)
class ProposalRevision:
    revision: int
    text: str
    reason: str

    def __post_init__(self):
        require_nonnegative_int('proposal revision', self.revision)
        object.__setattr__(self, 'text', require_nonempty_text('proposal', self.text))
        object.__setattr__(self, 'reason', require_nonempty_text('proposal reason', self.reason))


@dataclass(frozen=True)
class Decree:
    proposal_revision: int
    text: str

    def __post_init__(self):
        require_nonnegative_int('proposal_revision', self.proposal_revision)
        object.__setattr__(self, 'text', require_nonempty_text('decree', self.text))


@dataclass(frozen=True)
class ExecutionEvent:
    seq: int
    summary: str
    evidence_refs: tuple[str, ...] = ()
    clock_event_ref: str | None = None

    def __post_init__(self):
        require_nonnegative_int('execution seq', self.seq)
        object.__setattr__(self, 'summary', require_nonempty_text('execution summary', self.summary))
        object.__setattr__(self, 'evidence_refs', tuple(require_nonempty_text('evidence_ref', x) for x in self.evidence_refs))
        if self.clock_event_ref is not None:
            ref = require_nonempty_text('clock_event_ref', self.clock_event_ref).lower()
            if len(ref) != 64 or any(c not in '0123456789abcdef' for c in ref):
                raise ValueError('clock_event_ref must be lowercase SHA-256 hex')
            object.__setattr__(self, 'clock_event_ref', ref)


@dataclass(frozen=True)
class ResultRevision:
    revision: int
    summary: str
    evidence_refs: tuple[str, ...] = ()
    output_packet_ref: str | None = None

    def __post_init__(self):
        require_nonnegative_int('result revision', self.revision)
        object.__setattr__(self, 'summary', require_nonempty_text('result summary', self.summary))
        object.__setattr__(self, 'evidence_refs', tuple(require_nonempty_text('evidence_ref', x) for x in self.evidence_refs))
        if self.output_packet_ref is not None:
            object.__setattr__(self, 'output_packet_ref', require_nonempty_text('output_packet_ref', self.output_packet_ref))


@dataclass(frozen=True)
class ReintegrationReceipt:
    candidate_before_revision: int | None
    d_result_revision: int
    accepted: str
    rejected: str
    main_consequence: str
    strategy_revision: int | None = None
    candidate_revision: int | None = None
    clock_event_ref: str | None = None

    def __post_init__(self):
        if self.candidate_before_revision is not None:
            require_nonnegative_int('candidate_before_revision', self.candidate_before_revision)
        require_nonnegative_int('d_result_revision', self.d_result_revision)
        for name in ('accepted', 'rejected', 'main_consequence'):
            object.__setattr__(self, name, require_nonempty_text(name, getattr(self, name)))
        for name in ('strategy_revision', 'candidate_revision'):
            if getattr(self, name) is not None:
                require_nonnegative_int(name, getattr(self, name))
        if self.clock_event_ref is not None:
            ref=require_nonempty_text('clock_event_ref',self.clock_event_ref).lower()
            if len(ref)!=64 or any(c not in '0123456789abcdef' for c in ref):
                raise ValueError('clock_event_ref must be lowercase SHA-256 hex')
            object.__setattr__(self,'clock_event_ref',ref)


@dataclass(frozen=True)
class DIntervention:
    intervention_id: str
    state_revision: int
    isolation_receipt_id: str
    proposals: tuple[ProposalRevision, ...] = ()
    decree: Decree | None = None
    execution_events: tuple[ExecutionEvent, ...] = ()
    results: tuple[ResultRevision, ...] = ()
    reintegration: ReintegrationReceipt | None = None
    status: str = 'ACTIVE'
    abort_reason: str | None = None

    def __post_init__(self):
        object.__setattr__(self, 'intervention_id', validate_component_id('intervention_id', self.intervention_id))
        require_nonnegative_int('state_revision', self.state_revision)
        object.__setattr__(self, 'isolation_receipt_id', require_nonempty_text('isolation_receipt_id', self.isolation_receipt_id))
        object.__setattr__(self, 'proposals', tuple(self.proposals))
        object.__setattr__(self, 'execution_events', tuple(self.execution_events))
        object.__setattr__(self, 'results', tuple(self.results))
        if any(not isinstance(x, ProposalRevision) for x in self.proposals):
            raise TypeError('proposals must contain ProposalRevision')
        if any(not isinstance(x, ExecutionEvent) for x in self.execution_events):
            raise TypeError('execution_events must contain ExecutionEvent')
        if any(not isinstance(x, ResultRevision) for x in self.results):
            raise TypeError('results must contain ResultRevision')
        if tuple(x.revision for x in self.proposals) != tuple(range(len(self.proposals))):
            raise ValueError('proposal revision chain is not contiguous')
        if tuple(x.seq for x in self.execution_events) != tuple(range(len(self.execution_events))):
            raise ValueError('D execution event sequence is not contiguous')
        if tuple(x.revision for x in self.results) != tuple(range(len(self.results))):
            raise ValueError('D result revision chain is not contiguous')
        if self.status not in ('ACTIVE', 'ABORTED', 'COMPLETED'):
            raise ValueError('invalid D status')
        if self.status == 'ABORTED':
            if self.abort_reason is None:
                raise ValueError('aborted D requires reason')
            if self.reintegration is not None:
                raise ValueError('aborted D cannot be reintegrated/completed')
        elif self.abort_reason is not None:
            raise ValueError('abort_reason is only valid for ABORTED D')
        if self.abort_reason is not None:
            object.__setattr__(self, 'abort_reason', require_nonempty_text('abort_reason', self.abort_reason))
        if self.decree is not None and self.decree.proposal_revision >= len(self.proposals):
            raise ValueError('decree binds missing proposal revision')
        if self.reintegration is not None and self.reintegration.d_result_revision >= len(self.results):
            raise ValueError('reintegration binds missing D result')
        full = self.decree is not None and bool(self.execution_events) and bool(self.results) and self.reintegration is not None
        if self.status == 'COMPLETED' and not full:
            raise ValueError('COMPLETED status requires full lifecycle')
        if self.status == 'ACTIVE' and self.reintegration is not None:
            raise ValueError('reintegrated D must be terminal COMPLETED')

    @property
    def completed(self) -> bool:
        return self.status == 'COMPLETED'

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['completed'] = self.completed
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> 'DIntervention':
        proposals = tuple(ProposalRevision(**x) for x in d.get('proposals', []))
        decree = Decree(**d['decree']) if d.get('decree') else None
        execs = tuple(ExecutionEvent(x['seq'], x['summary'], tuple(x.get('evidence_refs', [])), x.get('clock_event_ref')) for x in d.get('execution_events', []))
        results = tuple(ResultRevision(x['revision'], x['summary'], tuple(x.get('evidence_refs', [])), x.get('output_packet_ref')) for x in d.get('results', []))
        rein = ReintegrationReceipt(**d['reintegration']) if d.get('reintegration') else None
        return cls(d['intervention_id'], d['state_revision'], d['isolation_receipt_id'], proposals, decree, execs, results, rein, d.get('status', 'ACTIVE'), d.get('abort_reason'))


class DInterventionStore:
    def __init__(self, workspace: RunWorkspace):
        self.workspace = workspace
        self._hist: dict[str, list[DIntervention]] = {}
        self._isolations: dict[str, IsolationReceipt] = {}

    def add_isolation(self, receipt: IsolationReceipt) -> IsolationReceipt:
        if not isinstance(receipt, IsolationReceipt):
            raise TypeError('receipt must be IsolationReceipt')
        if receipt.receipt_id in self._isolations:
            raise ValueError('duplicate isolation receipt')
        self._isolations[receipt.receipt_id] = receipt
        self.workspace.write_json(f'dictator/isolation/{receipt.receipt_id}.json', receipt.to_dict(), kind='isolation-receipt')
        return receipt

    def isolation(self, receipt_id: str) -> IsolationReceipt:
        return self._isolations[receipt_id]

    def _save(self, item: DIntervention) -> DIntervention:
        if item.isolation_receipt_id not in self._isolations:
            raise ValueError('D intervention must reference a persisted isolation receipt')
        history = self._hist.setdefault(item.intervention_id, [])
        if item.state_revision != len(history):
            raise ValueError(f'D state revision must be {len(history)}')
        history.append(item)
        self.workspace.write_json(f'dictator/{item.intervention_id}-r{item.state_revision:04d}.json', item.to_dict(), kind='d-intervention', revision=item.state_revision)
        self.workspace.write_json(f'dictator/{item.intervention_id}.json', item.to_dict(), kind='d-intervention-latest', revision=item.state_revision)
        return item

    @staticmethod
    def _require_active(item: DIntervention) -> None:
        if item.status != 'ACTIVE':
            raise ValueError(f'D intervention is terminal: {item.status}')

    def create(self, intervention_id: str, isolation_receipt_id: str, proposal: str, reason: str = 'initial gambit') -> DIntervention:
        if intervention_id in self._hist:
            raise ValueError('duplicate intervention_id')
        receipt = self._isolations.get(isolation_receipt_id)
        if receipt is None:
            raise ValueError('D intervention must reference a persisted isolation receipt')
        if receipt.L_actual is None:
            raise ValueError('D intervention cannot execute without at least L1 actual isolation')
        return self._save(DIntervention(intervention_id, 0, isolation_receipt_id, (ProposalRevision(0, proposal, reason),)))

    def revise_proposal(self, intervention_id: str, proposal: str, reason: str) -> DIntervention:
        old = self.latest(intervention_id)
        self._require_active(old)
        if old.decree is not None:
            raise ValueError('proposal is committed by decree; abort and start/re-decree explicitly')
        p = ProposalRevision(len(old.proposals), proposal, reason)
        return self._save(DIntervention(intervention_id, old.state_revision + 1, old.isolation_receipt_id, old.proposals + (p,), old.decree, old.execution_events, old.results, old.reintegration, old.status, old.abort_reason))

    def decree(self, intervention_id: str, text: str, proposal_revision: int | None = None) -> DIntervention:
        old = self.latest(intervention_id)
        self._require_active(old)
        if old.decree is not None:
            raise ValueError('decree already exists')
        if not old.proposals:
            raise ValueError('decree requires a proposal')
        revision = len(old.proposals) - 1 if proposal_revision is None else proposal_revision
        d = Decree(revision, text)
        return self._save(DIntervention(intervention_id, old.state_revision + 1, old.isolation_receipt_id, old.proposals, d, old.execution_events, old.results, old.reintegration, old.status, old.abort_reason))

    def record_execution(self, intervention_id: str, summary: str, evidence_refs: Iterable[str] = (), *, clock_event_ref: str | None = None) -> DIntervention:
        old = self.latest(intervention_id)
        self._require_active(old)
        if old.decree is None:
            raise ValueError('execution requires decree')
        ev = ExecutionEvent(len(old.execution_events), summary, tuple(evidence_refs), clock_event_ref)
        return self._save(DIntervention(intervention_id, old.state_revision + 1, old.isolation_receipt_id, old.proposals, old.decree, old.execution_events + (ev,), old.results, old.reintegration, old.status, old.abort_reason))

    def record_result(self, intervention_id: str, summary: str, evidence_refs: Iterable[str] = (), *, output_packet_ref: str | None = None) -> DIntervention:
        old = self.latest(intervention_id)
        self._require_active(old)
        if not old.execution_events:
            raise ValueError('result requires execution evidence')
        r = ResultRevision(len(old.results), summary, tuple(evidence_refs), output_packet_ref)
        return self._save(DIntervention(intervention_id, old.state_revision + 1, old.isolation_receipt_id, old.proposals, old.decree, old.execution_events, old.results + (r,), old.reintegration, old.status, old.abort_reason))

    def reintegrate(self, intervention_id: str, receipt: ReintegrationReceipt) -> DIntervention:
        old = self.latest(intervention_id)
        self._require_active(old)
        if not old.results:
            raise ValueError('reintegration requires D result')
        item = DIntervention(intervention_id, old.state_revision + 1, old.isolation_receipt_id, old.proposals, old.decree, old.execution_events, old.results, receipt, 'COMPLETED')
        return self._save(item)

    def abort(self, intervention_id: str, reason: str) -> DIntervention:
        old = self.latest(intervention_id)
        self._require_active(old)
        return self._save(DIntervention(intervention_id, old.state_revision + 1, old.isolation_receipt_id, old.proposals, old.decree, old.execution_events, old.results, old.reintegration, 'ABORTED', reason))

    def latest(self, intervention_id: str) -> DIntervention:
        return self._hist[intervention_id][-1]

    @property
    def items(self) -> tuple[DIntervention, ...]:
        return tuple(self._hist[k][-1] for k in sorted(self._hist))

    @property
    def completed(self) -> tuple[DIntervention, ...]:
        return tuple(x for x in self.items if x.completed)

    @property
    def completed_count(self) -> int:
        return len(self.completed)

    @property
    def actual_isolation_level(self) -> int | None:
        levels = [self._isolations[x.isolation_receipt_id].L_actual for x in self.completed]
        levels = [x for x in levels if x is not None]
        if levels:
            return min(levels)
        # D=0 keeps L configured/visible but non-blocking.
        if self._isolations:
            return list(self._isolations.values())[-1].L_actual
        return None

    @classmethod
    def load(cls, workspace: RunWorkspace) -> 'DInterventionStore':
        obj = cls(workspace)
        iso = workspace.path('dictator/isolation')
        if iso.exists():
            for p in sorted(iso.glob('*.json')):
                r = IsolationReceipt.from_dict(workspace.read_json(str(p.relative_to(workspace.root))))
                obj._isolations[r.receipt_id] = r
        root = workspace.path('dictator')
        for p in sorted(root.glob('*-r*.json')):
            item = DIntervention.from_dict(workspace.read_json(str(p.relative_to(workspace.root))))
            history = obj._hist.setdefault(item.intervention_id, [])
            if item.state_revision != len(history):
                raise ValueError('D revision chain drift')
            history.append(item)
        for key, history in obj._hist.items():
            latest = DIntervention.from_dict(workspace.read_json(f'dictator/{key}.json'))
            if latest != history[-1]:
                raise ValueError('D latest pointer drift')
            if latest.isolation_receipt_id not in obj._isolations:
                raise ValueError('D references missing isolation receipt')
        return obj
