"""DIGR 5.0.0-Berta2 Native Assist run session.

The session is a reliability exoskeleton. It freezes authority/U0/minimum
commitments and binds timing/evidence/state, while leaving task strategy and
next-action choice to the native model.
"""
from __future__ import annotations
from dataclasses import dataclass,replace
from hashlib import sha256
from pathlib import Path
import shutil,tempfile,uuid,json
from typing import Any,Callable,Iterable
from .actuals import ActualsProvenance,derive_contract_actuals
from .candidate_store import CandidateSnapshot,CandidateStore
from .clock_journal import ClockJournal,derive_work_intervals
from .clock_probe import ClockSnapshot,snapshot
from .completion_state import CompletionState
from .delivery import (
    DELIVERY_ENVELOPE_PATH,DELIVERY_PAYLOAD_PATH,DELIVERY_PROOF_PATH,
    DELIVERY_SCHEMA_VERSION,DELIVERY_SUMMARY_PATH,DeliveryEnvelope,
    DeliveryGateError,HostDeliveryAuthorityError,verify_delivery_artifacts,
    verify_enforced_host_delivery_authority,terminal_state_sha256,
)
from .d_intervention import DInterventionStore,ReintegrationReceipt
from .effective_contract import EffectiveContract,SourceContract,SourceDisposition
from .execution_protocol import ExecutingProtocolLoadReceipt
from .est_store import ESTStore
from .evidence_index import EvidenceIndex
from .evolution_events import EvolutionEventLog,EvolutionKind
from .interval_ledger import FormalTimeLedger,WorkState
from .invocation_surface import InvocationSurface,InvocationKind,classify_surface
from .isolation_checks import IsolationFacts,make_isolation_receipt
from .parameter_resolution import ParameterResolution,ResolutionStatus,resolve_parameter_surface
from .protocol_authority import ProtocolAuthority,ProtocolIdentity
from .routing import RouteReceipt
from .run_brief import build_run_brief
from .run_lifecycle import RunPhase,RunPhaseStore
from .source_workspace import SourceActivityLog,SourceWorkspaceRegistry
from .exclusive_activity import ExclusiveActivityLog
from .viewpoint_store import ViewpointStore
from .stop_checks import check_mechanical_minima
from .strategy_store import StrategyState,StrategyStore
from .task_startup import ClockReadiness,TaskStartupReceipt,start_task
from .validation import require_nonempty_text,require_nonnegative_int
from .workspace import RunWorkspace,validate_component_id

class RunGenesisError(RuntimeError):
    def __init__(self,stage:str,message:str):self.stage=require_nonempty_text('stage',stage);super().__init__(f'{self.stage}: {message}')
class RunResumeError(RuntimeError): pass

@dataclass(frozen=True)
class U0Receipt:
    text:str;sha256:str;source_message_sha256:str
    def __post_init__(self):
        # U0 may intentionally begin/end with whitespace.  Stable.1 binds the
        # exact task substring from the invocation, so validation must not
        # normalize it here.  The legacy freeze path performs its historical
        # strip before constructing this record.
        if not isinstance(self.text,str) or not self.text.strip():raise ValueError('U0 must be a non-empty string')
        for n in ('sha256','source_message_sha256'):
            v=require_nonempty_text(n,getattr(self,n)).lower()
            if len(v)!=64 or any(c not in '0123456789abcdef' for c in v):raise ValueError(f'{n} invalid')
            object.__setattr__(self,n,v)
    def to_dict(self):return {'text':self.text,'sha256':self.sha256,'source_message_sha256':self.source_message_sha256}
    @classmethod
    def from_dict(cls,d):return cls(d['text'],d['sha256'],d['source_message_sha256'])


def _load_authority(d)->ProtocolAuthority:
    r=d['route']; route=RouteReceipt(r['repository_full_name'],r['requested_ref'],r['pinned_commit'],r['manifest_path'],r['manifest_sha256'],r['version_path'],r['version_sha256'])
    p=d['P_run']; return ProtocolAuthority(route,ProtocolIdentity(p['protocol'],p['version'],p['repository_full_name'],p['commit_sha']))

def _load_invocation(d)->InvocationSurface:
    return InvocationSurface(InvocationKind(d['kind']),d['alias'],d['raw_message_sha256'],d.get('parameter_surface'),d.get('task_raw'),d.get('reason'))

def _load_snapshot(d)->ClockSnapshot:return ClockSnapshot(d['provider'],d['session_id'],d.get('boot_id'),d['monotonic_ns'],d['wall_ns'])
def _load_startup(d)->TaskStartupReceipt:
    return TaskStartupReceipt(_load_authority(d['authority']),_load_invocation(d['invocation']),ClockReadiness(tuple(_load_snapshot(x) for x in d['clock']['samples'])),False)
def _load_contract(d)->EffectiveContract:
    s=d['S'];return EffectiveContract(d['N'],d['T_seconds'],d['R'],d['B'],SourceContract(s['n'],s['t_seconds'],s['r'],s['b']),d['D_s'],d['L_e'],SourceDisposition(d.get('source_disposition','REQUIRED')),d.get('source_waiver_reason'),d.get('L_mismatch_blocks_delivery',False),d.get('V_o',0))

_PREFLIGHT_VERSIONS={'5.0.0-stable.1','5.0.0-Berta1','5.0.0-Berta2'}

class LiveDIGRRun:
    def __init__(self,run_id,startup,workspace,journal,snapshot_fn,*,restoring=False):
        self.run_id=run_id;self.startup=startup;self.workspace=workspace;self.clock_journal=journal;self._snapshot_fn=snapshot_fn
        self.U0=None;self.contract=None;self.parameters=None;self.ledger=None;self.protocol_load=None;self.delivery=None
        if restoring:
            self.events=EvolutionEventLog.load(workspace.path('events.ndjson'))
            self.est=ESTStore.load(workspace);self.evidence=EvidenceIndex.load(workspace);self.sources=SourceWorkspaceRegistry.load(workspace)
            self.source_activity=SourceActivityLog.load(workspace.path('time/source-activity.ndjson'))
            self.d_activity=ExclusiveActivityLog.load(workspace.path('time/d-activity.ndjson'),'D')
            self.v_activity=ExclusiveActivityLog.load(workspace.path('time/v-activity.ndjson'),'V')
            self.viewpoints=ViewpointStore.load(workspace)
            self.strategy=StrategyStore.load(workspace);self.candidates=CandidateStore.load(workspace);self.dictator=DInterventionStore.load(workspace);self.completion=CompletionState.load(workspace);self.phase=RunPhaseStore.load(workspace)
            if workspace.path('protocol-load.json').is_file():
                self.protocol_load=ExecutingProtocolLoadReceipt.from_dict(workspace.read_json('protocol-load.json'))
            if workspace.path(DELIVERY_ENVELOPE_PATH).is_file():
                self.delivery=DeliveryEnvelope.from_dict(workspace.read_json(DELIVERY_ENVELOPE_PATH))
        else:
            self.events=EvolutionEventLog(workspace.path('events.ndjson'));self.est=ESTStore(workspace);self.evidence=EvidenceIndex(workspace);self.sources=SourceWorkspaceRegistry(workspace);self.source_activity=SourceActivityLog(workspace.path('time/source-activity.ndjson'));self.d_activity=ExclusiveActivityLog(workspace.path('time/d-activity.ndjson'),'D');self.v_activity=ExclusiveActivityLog(workspace.path('time/v-activity.ndjson'),'V');self.viewpoints=ViewpointStore(workspace);self.strategy=StrategyStore(workspace);self.candidates=CandidateStore(workspace);self.dictator=DInterventionStore(workspace);self.completion=CompletionState(workspace);self.phase=RunPhaseStore(workspace)
            workspace.write_json('authority.json',startup.authority.to_dict(),kind='authority');workspace.write_json('invocation.json',startup.invocation.to_dict(),kind='invocation-surface');workspace.write_json('startup.json',startup.to_dict(),kind='startup')
            self._reindex_journals()
            self.refresh_brief()

    @classmethod
    def start(cls,authority:ProtocolAuthority,message:str,workspace_parent:Path|None=None,snapshot_fn:Callable[[],ClockSnapshot]=snapshot,run_id:str|None=None):
        surface=classify_surface(message)
        if surface is None or surface.kind is not InvocationKind.EXECUTING:raise RunGenesisError('SURFACE','message is not a pinned executing DIGR 5.0 invocation')
        try: startup=start_task(authority,surface,snapshot_fn)
        except Exception as exc:raise RunGenesisError('CLOCK',str(exc)) from exc
        rid=run_id or ('digr-'+uuid.uuid4().hex);parent=Path(workspace_parent) if workspace_parent is not None else Path(tempfile.gettempdir())/'.digr-runs';ws=None
        try:
            ws=RunWorkspace.create(parent,rid);j=ClockJournal(rid,ws.path('time/clock.journal.ndjson'));j.append_genesis(startup.clock.samples);return cls(rid,startup,ws,j,snapshot_fn)
        except Exception as exc:
            if ws is not None:
                try:shutil.rmtree(ws.root)
                except OSError:pass
            raise RunGenesisError('WORKSPACE_OR_JOURNAL',str(exc)) from exc

    @classmethod
    def resume(cls,root:Path,run_id:str,snapshot_fn:Callable[[],ClockSnapshot]=snapshot):
        from .run_recovery import verify_run_workspace
        report=verify_run_workspace(root,run_id)
        ws=RunWorkspace.open_existing(Path(root).resolve(),run_id);phase=RunPhaseStore.load(ws)
        if phase.phase in (RunPhase.DELIVERED,RunPhase.INCOMPLETE,RunPhase.FINISHED,RunPhase.ABORTED):raise RunResumeError(f'cannot resume terminal run: {phase.phase.value}')
        startup=_load_startup(ws.read_json('startup.json'));journal=ClockJournal.load(run_id,ws.path('time/clock.journal.ndjson'))
        # Load/validate every semantic store before mutating the append-only clock journal.
        obj=cls(run_id,startup,ws,journal,snapshot_fn,restoring=True)
        if ws.path('parameter-resolution.json').is_file():
            obj.parameters=ParameterResolution.from_dict(ws.read_json('parameter-resolution.json'))
            if startup.authority.P_run.version=='5.0.0-stable.1' and obj.parameters.V_o is None:
                obj.parameters=replace(obj.parameters,V_o=0)
            if startup.authority.P_run.version in _PREFLIGHT_VERSIONS:
                obj.parameters.require_stable_ready()
        if ws.path('U0.json').is_file():obj.U0=U0Receipt.from_dict(ws.read_json('U0.json'))
        if ws.path('contract.json').is_file():obj.contract=_load_contract(ws.read_json('contract.json'))
        samples=tuple(snapshot_fn() for _ in range(3))
        try:journal.append_resume(samples)
        except Exception as exc:raise RunResumeError(f'cross-session clock continuity unverifiable: {exc}') from exc
        # Re-index immediately: a crash after this point still leaves the journal/index consistent.
        obj._reindex_journals()
        if obj.contract is not None:
            intervals=derive_work_intervals(journal.events)
            obj.ledger=FormalTimeLedger.resume_from_intervals(
                startup,intervals,journal.events[-1].snapshot,
                hard_T=obj.contract.B==1,hard_t=obj.contract.S.b==1,
                finished=phase.phase is RunPhase.FINALIZING,
            )
        obj.refresh_brief();return obj

    def _reindex_journals(self):
        for rel,kind in [('time/clock.journal.ndjson','clock-journal'),('time/source-activity.ndjson','source-activity'),('time/d-activity.ndjson','d-activity'),('time/v-activity.ndjson','v-activity'),('events.ndjson','event-log')]:
            p=self.workspace.path(rel)
            if p.is_file():self.workspace.index_existing(rel,kind=kind)

    def refresh_brief(self):
        brief=build_run_brief(self);self.workspace.write_json('state/run-brief.json',brief,kind='run-brief');return brief

    def bind_protocol_load(self,receipt:ExecutingProtocolLoadReceipt)->ExecutingProtocolLoadReceipt:
        """Bind verified full execution semantics to this born run before parameters."""
        if self.phase.phase is not RunPhase.GENESIS:
            raise RuntimeError('executing protocol load is only bindable at GENESIS')
        if self.protocol_load is not None or self.workspace.path('protocol-load.json').exists():
            raise RuntimeError('executing protocol load receipt already exists')
        if not isinstance(receipt,ExecutingProtocolLoadReceipt):
            raise TypeError('receipt must be ExecutingProtocolLoadReceipt')
        ident=self.startup.authority.P_run
        if (receipt.commit_sha!=ident.commit_sha or receipt.version!=ident.version or receipt.protocol!=ident.protocol
                or receipt.manifest_sha256!=self.startup.authority.route.manifest_sha256):
            raise ValueError('executing protocol load receipt does not match P_run/manifest')
        # Identity equality alone is insufficient: Alpha 4 accepted a receipt
        # containing only one plausible member.  Re-derive the exact expected
        # entrypoint/core sequence from manifest bytes bound by the route hash.
        receipt.verify_complete_members()
        self.protocol_load=receipt
        self.workspace.write_json('protocol-load.json',receipt.to_dict(),kind='executing-protocol-load')
        self.clock_journal.append('PROTOCOL_READY',self._snapshot_fn(),WorkState.META)
        self._reindex_journals();self.refresh_brief();return receipt

    def abort_protocol_load(self,reason:str):
        """Persist a post-genesis mandatory protocol-load failure as ABORTED."""
        if self.phase.phase is not RunPhase.GENESIS:
            raise RuntimeError('protocol-load abort is only valid before parameter resolution')
        text=require_nonempty_text('protocol load abort reason',reason)
        # ABORTED is the primary safety fact.  A fresh clock read is useful
        # diagnostic evidence but must never be a prerequisite for persisting
        # that terminal state.
        clock_error=None
        try:
            self.clock_journal.append('PROTOCOL_LOAD_ABORT',self._snapshot_fn(),WorkState.META)
            self._reindex_journals()
        except Exception as exc:
            clock_error=f'{type(exc).__name__}: {exc}'
        terminal_reason=text if clock_error is None else f'{text}; abort clock evidence unavailable ({clock_error})'
        self.phase.abort(terminal_reason)
        try:self.refresh_brief()
        except Exception:
            # The authoritative terminal transition has already been persisted.
            # A derived brief failure cannot undo it.
            pass
        if not self.workspace.terminal_sealed:
            self.workspace.seal_terminal(
                phase='ABORTED',binding_sha256=sha256(terminal_reason.encode('utf-8')).hexdigest(),
            )
        return {'phase':'ABORTED','reason':terminal_reason,'clock_evidence_error':clock_error}

    def resolve_parameters(self,semantic_normalizations=None)->ParameterResolution:
        if self.phase.phase is not RunPhase.GENESIS:raise RuntimeError('parameter resolution only allowed at GENESIS')
        if self.protocol_load is None:
            raise RuntimeError('verified executing protocol load receipt required before parameter resolution')
        if self.startup.authority.P_run.version in _PREFLIGHT_VERSIONS:
            raise RuntimeError('stable.1 parameters must be bound from pre-Genesis preflight')
        r=resolve_parameter_surface(self.startup.invocation.parameter_surface,semantic_normalizations);self.parameters=r;self.workspace.write_json('parameter-resolution.json',r.to_dict(),kind='parameter-resolution')
        if r.status is ResolutionStatus.RESOLVED:self.phase.transition(RunPhase.PARAMETER_RESOLVED,'parameter surface uniquely resolved')
        else:self.phase.abort(f'parameter resolution {r.status.value}: {r.reason or "unresolved"}')
        self.refresh_brief();return r

    def bind_preflight_parameters(self,resolved:ParameterResolution)->ParameterResolution:
        """Bind the one completed preflight/native parameter receipt."""
        if self.startup.authority.P_run.version not in _PREFLIGHT_VERSIONS:
            raise RuntimeError('preflight parameter binding is not supported by this pinned version')
        if self.phase.phase is not RunPhase.GENESIS:
            raise RuntimeError('stable preflight parameters may be bound only once at GENESIS')
        if self.protocol_load is None:
            raise RuntimeError('verified executing protocol load receipt required before parameter binding')
        if not isinstance(resolved,ParameterResolution):
            raise TypeError('resolved must be ParameterResolution')
        resolved.require_stable_ready()
        self.parameters=resolved
        self.workspace.write_json('parameter-resolution.json',resolved.to_dict(),kind='parameter-resolution')
        self.phase.transition(RunPhase.PARAMETER_RESOLVED,'stable preflight parameters bound')
        self.refresh_brief()
        return resolved

    def freeze_u0(self,text:str|None=None)->U0Receipt:
        if self.phase.phase is not RunPhase.PARAMETER_RESOLVED:raise RuntimeError('resolve parameters before U0')
        if self.startup.authority.P_run.version in _PREFLIGHT_VERSIONS:
            task_raw=self.startup.invocation.task_raw
            if not isinstance(task_raw,str) or not task_raw.strip():raise RuntimeError('stable.1 invocation task_raw missing')
            if text is not None and text!=task_raw:raise ValueError('stable.1 U0 must exactly equal invocation task_raw')
            value=task_raw
        else:
            # Alpha.4 recovery/callers retain the historical explicit, stripped
            # U0 behavior; stable.1 never enters this compatibility branch.
            if text is None:raise ValueError('legacy U0 requires explicit text')
            value=require_nonempty_text('U0',text)
        d=sha256(value.encode('utf-8')).hexdigest();self.U0=U0Receipt(value,d,self.startup.invocation.raw_message_sha256);self.workspace.write_json('U0.json',self.U0.to_dict(),kind='u0');self.clock_journal.append('U0_FROZEN',self._snapshot_fn(),WorkState.META);self._reindex_journals();self.phase.transition(RunPhase.U0_FROZEN,'immutable U0 frozen');self.refresh_brief();return self.U0

    def _validate_contract_against_parameters(self,contract:EffectiveContract):
        if self.parameters is None or self.parameters.status is not ResolutionStatus.RESOLVED:
            raise RuntimeError('resolved parameters missing')
        p=self.parameters
        if self.startup.authority.P_run.version in _PREFLIGHT_VERSIONS:
            p.require_stable_ready()
        checks=(('N',p.N,contract.N),('T_seconds',p.T_seconds,contract.T_seconds),('R',p.R,contract.R),('D_s',p.D_s,contract.D_s),('V_o',p.V_o,contract.V_o))
        for name,explicit,actual in checks:
            if explicit is not None and explicit!=actual:raise ValueError(f'contract changes explicit parameter {name}')
        for name,explicit,actual in (('S.n',p.S.n,contract.S.n),('S.t_seconds',p.S.t_seconds,contract.S.t_seconds),('S.r',p.S.r,contract.S.r)):
            if explicit is not None and explicit!=actual:raise ValueError(f'contract changes explicit parameter {name}')
        # B/b/L are fixed-default-or-explicit structural values, never semantic completion.
        if p.B!=contract.B:raise ValueError('contract changes resolved/default B')
        if p.S.b!=contract.S.b:raise ValueError('contract changes resolved/default b')
        if p.L_e!=contract.L_e:raise ValueError('contract changes resolved/default L')
        if p.source_policy=='required' and contract.source_disposition is not SourceDisposition.REQUIRED:
            raise ValueError('source=required requires REQUIRED source disposition')
        if p.source_policy=='off':
            if contract.source_disposition is not SourceDisposition.WAIVED:
                raise ValueError('source=off requires WAIVED source disposition')
            if any((contract.S.n,contract.S.t_seconds,contract.S.r,contract.S.b)):
                raise ValueError('source=off requires zero S contract values')

    def freeze_contract(self,contract:EffectiveContract):
        if self.phase.phase is not RunPhase.U0_FROZEN:raise RuntimeError('freeze U0 before contract')
        if not isinstance(contract,EffectiveContract):raise TypeError('contract must be EffectiveContract')
        if contract.B==1 and contract.T_seconds<=0:raise ValueError('B=1 requires T_seconds > 0')
        if contract.S.b==1 and contract.S.t_seconds<=0:raise ValueError('b=1 requires source t_seconds > 0')
        self._validate_contract_against_parameters(contract)
        self.contract=contract;self.ledger=FormalTimeLedger(self.startup,hard_T=contract.B==1,hard_t=contract.S.b==1);self.workspace.write_json('contract.json',contract.to_dict(),kind='effective-contract');self.clock_journal.append('CONTRACT_FROZEN',self._snapshot_fn(),WorkState.META);self._reindex_journals();self.phase.transition(RunPhase.CONTRACT_FROZEN,'contract commitments frozen; strategy remains mutable');self.refresh_brief()

    def save_strategy(self,state:StrategyState):
        # Strategy Genesis is real task work.  The run must already be in MAIN/
        # EXECUTING so it cannot be silently performed in META calibration.
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('strategy is task work and requires EXECUTING phase')
        out=self.strategy.save(state);self.refresh_brief();return out
    def save_candidate(self,item:CandidateSnapshot):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('candidate requires EXECUTING phase')
        out=self.candidates.save(item);self.refresh_brief();return out

    def save_candidate_bytes(self,content:bytes,*,summary:str,artifact_refs=(),evidence_refs=(),produced_by:str='MAIN')->CandidateSnapshot:
        """Persist exact candidate content and bind it into CandidateSnapshot.

        Summary-only candidates remain readable for legacy recovery and R
        analysis, but stable delivery requires this content-addressed path.
        """
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('candidate requires EXECUTING phase')
        if not isinstance(content,(bytes,bytearray)):raise TypeError('candidate content must be exact bytes')
        raw=bytes(content)
        if not raw:raise ValueError('candidate content must not be empty')
        digest=sha256(raw).hexdigest();rel=f'state/candidate-payloads/{digest}.bin'
        dest=self.workspace.path(rel)
        if dest.is_file():
            if dest.read_bytes()!=raw:raise ValueError('candidate content-address collision')
            self.workspace.index_existing(rel,kind='candidate-payload',revision=len(self.candidates.items),expected_digest=digest)
        else:
            written=self.workspace.atomic_write_bytes(rel,raw)
            self.workspace.index_existing(rel,kind='candidate-payload',revision=len(self.candidates.items),expected_digest=written)
        extras=tuple(artifact_refs)
        if rel in extras:raise ValueError('candidate payload path is added automatically')
        item=CandidateSnapshot(
            len(self.candidates.items),summary,(rel,*extras),tuple(evidence_refs),produced_by,
        )
        out=self.candidates.save(item);self.refresh_brief();return out

    def open_source(self,source_id:str,objective:str,current_direction:str|None=None):
        if self.phase.phase is not RunPhase.EXECUTING or not self.strategy.has_state:
            raise RuntimeError('source work requires EXECUTING phase after Strategy Genesis')
        out=self.sources.open(source_id,objective,current_direction);self.refresh_brief();return out
    def revise_source(self,source_id:str,**changes):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('source revision requires EXECUTING phase')
        out=self.sources.revise(source_id,**changes);self.refresh_brief();return out
    def close_source(self,source_id:str,finding_summary:str):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('source close requires EXECUTING phase')
        out=self.sources.close(source_id,finding_summary);self.refresh_brief();return out
    def reopen_source(self,source_id:str,*,current_direction:str|None=None,reason:str):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('source reopen requires EXECUTING phase')
        out=self.sources.reopen(source_id,current_direction=current_direction,reason=reason);self.refresh_brief();return out

    def open_viewpoint(self,viewpoint_id:str,premise:str):
        if self.phase.phase is not RunPhase.EXECUTING or not self.strategy.has_state:
            raise RuntimeError('V work requires EXECUTING phase after Strategy Genesis')
        out=self.viewpoints.open(viewpoint_id,premise);self.refresh_brief();return out

    def record_viewpoint_event(self,viewpoint_id:str,behavior:str,finding:str,evidence_refs=()):
        if self.ledger is None or self.ledger.foreground_state is not WorkState.V_EXCLUSIVE:
            raise RuntimeError('V event requires V_EXCLUSIVE work state')
        clock_ref=self.clock_journal.events[-1].record_hash
        if viewpoint_id not in self.v_activity.by_clock_ref().get(clock_ref,()):
            raise RuntimeError('V event is not bound to the active private VLedger')
        out=self.viewpoints.record(viewpoint_id,behavior,finding,clock_ref,evidence_refs);self.refresh_brief();return out

    def qualify_viewpoint(self,viewpoint_id:str,result:str,semantic_distance:str,*,nonredundant:bool=True):
        if self.ledger is None or self.ledger.foreground_state is not WorkState.MAIN:
            raise RuntimeError('V qualification is a Main value decision and requires MAIN state')
        out=self.viewpoints.qualify(viewpoint_id,result,semantic_distance,nonredundant=nonredundant);self.refresh_brief();return out

    def discard_viewpoint(self,viewpoint_id:str,reason:str):
        if self.phase.phase is not RunPhase.EXECUTING:
            raise RuntimeError('V discard requires EXECUTING phase')
        if self.ledger is None or self.ledger.foreground_state is not WorkState.MAIN:
            raise RuntimeError('V discard is a Main decision and requires MAIN state')
        out=self.viewpoints.discard(viewpoint_id,reason);self.refresh_brief();return out

    def transition(self,state:WorkState,at:ClockSnapshot,*,active_source_ids:Iterable[str]=(),active_d_ids:Iterable[str]=(),active_v_ids:Iterable[str]=()):
        if self.ledger is None:raise RuntimeError('freeze contract before execution')
        state=state if isinstance(state,WorkState) else WorkState(state);ids=tuple(active_source_ids);dids=tuple(active_d_ids);vids=tuple(active_v_ids)
        # The first post-contract task state is MAIN.  This makes Strategy
        # Genesis chargeable task work without making the runtime a planner.
        if self.phase.phase is RunPhase.CONTRACT_FROZEN:
            if state is not WorkState.MAIN:raise RuntimeError('first formal task state after contract freeze must be MAIN')
            self.phase.transition(RunPhase.EXECUTING,'formal MAIN task work started')
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('work-state transition requires EXECUTING')
        if state in (WorkState.SOURCE,WorkState.D_EXCLUSIVE,WorkState.V_EXCLUSIVE) and not self.strategy.has_state:
            raise RuntimeError('Strategy Genesis must exist before SOURCE, D, or V work')
        if state is WorkState.SOURCE:
            if not ids:raise ValueError('SOURCE transition requires active_source_ids')
            if any(not self.sources.exists(x) for x in ids):raise ValueError('SOURCE transition references unknown S workspace')
        elif ids:raise ValueError('active_source_ids only valid for SOURCE')
        if state is WorkState.D_EXCLUSIVE:
            if len(dids)>1:raise ValueError('one D interval must belong to exactly one D intervention')
            if any(x not in {d.intervention_id for d in self.dictator.items} for x in dids):raise ValueError('D transition references unknown intervention')
        elif dids:raise ValueError('active_d_ids only valid for D_EXCLUSIVE')
        if state is WorkState.V_EXCLUSIVE:
            if len(vids)!=1:raise ValueError('V_EXCLUSIVE requires exactly one active_v_id')
            if any(not self.viewpoints.exists(x) for x in vids):raise ValueError('V transition references unknown viewpoint')
        elif vids:raise ValueError('active_v_ids only valid for V_EXCLUSIVE')
        self.ledger.transition(state,at);ev=self.clock_journal.append('STATE',at,state)
        if state is WorkState.SOURCE:self.source_activity.append(ev.record_hash,ids)
        if state is WorkState.D_EXCLUSIVE and dids:self.d_activity.bind(ev.record_hash,dids)
        if state is WorkState.V_EXCLUSIVE:self.v_activity.bind(ev.record_hash,vids)
        self._reindex_journals();self.refresh_brief()

    def _event_context(self, expected_state: WorkState):
        if self.phase.phase is not RunPhase.EXECUTING:
            raise RuntimeError('semantic evolution event requires EXECUTING phase')
        if not self.strategy.has_state:
            raise RuntimeError('semantic evolution event requires current StrategyState')
        if self.ledger is None or self.ledger.foreground_state is not expected_state:
            raise RuntimeError(f'{expected_state.value} semantic event requires active {expected_state.value} work state')
        clock_ref=self.clock_journal.events[-1].record_hash
        strategy_rev=self.strategy.current.revision
        candidate_rev=self.candidates.current.revision if self.candidates.has_state else None
        return clock_ref,strategy_rev,candidate_rev

    def _require_source_active(self, source_id: str, clock_ref: str) -> None:
        ids=self.source_activity.by_clock_ref().get(clock_ref)
        if not ids or source_id not in ids:
            raise RuntimeError('SOURCE semantic event must bind an actively timed source workspace')

    def record_main_evolution(self,summary,action,result,*,evidence_refs=()):
        c,s,r=self._event_context(WorkState.MAIN)
        e=self.events._append(EvolutionKind.MAIN_EVOLUTION,'MAIN',summary,action,result,evidence_refs=evidence_refs,clock_event_ref=c,strategy_revision=s,candidate_revision=r)
        self._reindex_journals();self.refresh_brief();return e

    def record_source_evolution(self,source_id,summary,action,result,*,evidence_refs=()):
        if not self.sources.exists(source_id):raise ValueError('unknown source workspace')
        c,s,r=self._event_context(WorkState.SOURCE);self._require_source_active(source_id,c)
        source_rev=self.sources.latest(source_id).revision
        e=self.events._append(EvolutionKind.SOURCE_EVOLUTION,f'S:{source_id}',summary,action,result,evidence_refs=evidence_refs,clock_event_ref=c,strategy_revision=s,candidate_revision=r,source_id=source_id,source_revision=source_rev)
        self._reindex_journals();self.refresh_brief();return e

    def record_main_reentry(self,candidate_before:int,challenge,action,outcome,*,candidate_after:int|None=None,retained:bool=False,evidence_refs=()):
        require_nonnegative_int('candidate_before',candidate_before);before=self.candidates.get(candidate_before);c,s,_=self._event_context(WorkState.MAIN)
        if retained:
            if candidate_after is not None and candidate_after!=candidate_before:raise ValueError('retained re-entry cannot name a different candidate_after')
            after=None
        else:
            if candidate_after is None:raise ValueError('non-retained R requires candidate_after')
            after=self.candidates.get(candidate_after)
            if after.revision<=before.revision:raise ValueError('candidate_after must be newer')
        e=self.events._append(EvolutionKind.MAIN_REENTRY,'MAIN',challenge,action,outcome,evidence_refs=evidence_refs,clock_event_ref=c,strategy_revision=s,candidate_revision=before.revision,candidate_after_revision=after.revision if after else None,retained=retained)
        self._reindex_journals();self.refresh_brief();return e

    def record_source_reentry(self,source_id,source_before_revision:int,challenge,action,outcome,*,source_after_revision:int|None=None,retained:bool=False,evidence_refs=()):
        if not self.sources.exists(source_id):raise ValueError('unknown source workspace')
        require_nonnegative_int('source_before_revision',source_before_revision);before=self.sources.get(source_id,source_before_revision)
        c,s,candidate_context=self._event_context(WorkState.SOURCE);self._require_source_active(source_id,c)
        if retained:
            if source_after_revision is not None and source_after_revision!=source_before_revision:raise ValueError('retained source re-entry cannot name a different source_after_revision')
            after=None
        else:
            if source_after_revision is None:raise ValueError('non-retained source R requires source_after_revision')
            after=self.sources.get(source_id,source_after_revision)
            if after.revision<=before.revision:raise ValueError('source_after_revision must be newer')
        e=self.events._append(EvolutionKind.SOURCE_REENTRY,f'S:{source_id}',challenge,action,outcome,evidence_refs=evidence_refs,clock_event_ref=c,strategy_revision=s,candidate_revision=candidate_context,source_id=source_id,source_revision=before.revision,source_after_revision=after.revision if after else None,retained=retained)
        self._reindex_journals();self.refresh_brief();return e

    def write_d_packet(self,packet_id:str,direction:str,payload:Any)->str:
        if self.phase.phase is not RunPhase.EXECUTING or not self.strategy.has_state:
            raise RuntimeError('D packet requires EXECUTING phase after Strategy Genesis')
        packet_id=validate_component_id('packet_id',packet_id)
        if direction not in ('input','output'):
            raise ValueError('D packet direction must be input/output')
        rel=f'dictator/packets/{packet_id}.json'
        if self.workspace.path(rel).exists():
            raise ValueError('D packet artifacts are immutable; duplicate packet_id')
        self.workspace.write_json(rel,{'schema_version':1,'packet_id':packet_id,'direction':direction,'payload':payload},kind=f'd-{direction}-packet')
        self.refresh_brief();return rel

    def add_isolation_facts(self,receipt_id:str,facts:IsolationFacts,*,input_packet_ref=None,output_packet_ref=None,mode='exclusive'):
        if self.contract is None or self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('isolation receipt requires an executing contracted run')
        if not self.strategy.has_state:raise RuntimeError('Strategy Genesis must exist before D isolation')
        r=make_isolation_receipt(receipt_id,self.contract.L_e,facts,input_packet_ref=input_packet_ref,output_packet_ref=output_packet_ref,mode=mode)
        if r.L_actual is not None and r.L_actual>=2:
            self.workspace.require_indexed_artifact(r.input_packet_ref,kind='d-input-packet')
            if r.output_packet_ref is not None:self.workspace.require_indexed_artifact(r.output_packet_ref,kind='d-output-packet')
        out=self.dictator.add_isolation(r);self.refresh_brief();return out

    def create_d_intervention(self,intervention_id:str,isolation_receipt_id:str,proposal:str,reason:str='initial gambit'):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('D intervention requires EXECUTING phase')
        if not self.strategy.has_state:raise RuntimeError('Strategy Genesis must exist before D intervention')
        if self.contract is None:raise RuntimeError('D intervention requires a frozen contract')
        out=self.dictator.create(intervention_id,isolation_receipt_id,proposal,reason);self.refresh_brief();return out
    def revise_d_proposal(self,intervention_id:str,proposal:str,reason:str):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('D proposal revision requires EXECUTING phase')
        out=self.dictator.revise_proposal(intervention_id,proposal,reason);self.refresh_brief();return out
    def decree_d(self,intervention_id:str,text:str,proposal_revision:int|None=None):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('D decree requires EXECUTING phase')
        out=self.dictator.decree(intervention_id,text,proposal_revision);self.refresh_brief();return out
    def record_d_execution(self,intervention_id:str,summary:str,evidence_refs=()):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('D execution receipt requires EXECUTING phase')
        item=self.dictator.latest(intervention_id);iso=self.dictator.isolation(item.isolation_receipt_id)
        if self.ledger is None:raise RuntimeError('D execution requires formal work state')
        state=self.ledger.foreground_state
        if self.startup.authority.P_run.version=='5.0.0-Berta2' and (iso.mode!='exclusive' or state is not WorkState.D_EXCLUSIVE):
            raise RuntimeError('Berta2 canonical D requires one owned D_EXCLUSIVE interval')
        if iso.mode=='exclusive' and state is not WorkState.D_EXCLUSIVE:
            raise RuntimeError('exclusive D execution requires D_EXCLUSIVE work state')
        if iso.mode=='background' and state not in (WorkState.MAIN,WorkState.SOURCE):
            raise RuntimeError('background D execution requires concurrent MAIN/SOURCE foreground work')
        clock_ref=self.clock_journal.events[-1].record_hash
        if state is WorkState.D_EXCLUSIVE and clock_ref not in self.d_activity.by_clock_ref():
            # Stable.1 callers did not supply active_d_ids on transition. Bind
            # the interval at first execution while retaining one-owner truth.
            self.d_activity.bind(clock_ref,(intervention_id,));self._reindex_journals()
        elif state is WorkState.D_EXCLUSIVE and intervention_id not in self.d_activity.by_clock_ref().get(clock_ref,()):
            raise RuntimeError('D execution is not bound to the active D interval')
        out=self.dictator.record_execution(intervention_id,summary,evidence_refs,clock_event_ref=clock_ref);self.refresh_brief();return out
    def record_d_result(self,intervention_id:str,summary:str,evidence_refs=(),*,output_packet_ref:str|None=None):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('D result receipt requires EXECUTING phase')
        item=self.dictator.latest(intervention_id);iso=self.dictator.isolation(item.isolation_receipt_id)
        if iso.L_actual is not None and iso.L_actual>=2:
            if output_packet_ref is None:raise ValueError('L2/L3 D result requires controlled Output Packet artifact')
            self.workspace.require_indexed_artifact(output_packet_ref,kind='d-output-packet')
        elif output_packet_ref is not None:
            self.workspace.require_indexed_artifact(output_packet_ref,kind='d-output-packet')
        out=self.dictator.record_result(intervention_id,summary,evidence_refs,output_packet_ref=output_packet_ref);self.refresh_brief();return out
    def reintegrate_d(self,intervention_id:str,*,accepted:str,rejected:str,main_consequence:str,strategy_revision:int|None=None,candidate_revision:int|None=None,candidate_before_revision:int|None=None):
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('D reintegration requires EXECUTING phase')
        if self.ledger is None or self.ledger.foreground_state is not WorkState.MAIN:
            raise RuntimeError('D reintegration is Main work and requires MAIN foreground state')
        current=self.dictator.latest(intervention_id)
        if not current.results:raise ValueError('D reintegration requires a D result')
        if candidate_before_revision is None:
            candidate_before_revision=self.candidates.current.revision if self.candidates.has_state else None
        elif candidate_before_revision>=len(self.candidates.items):raise ValueError('candidate_before_revision does not exist')
        if strategy_revision is not None and strategy_revision>=len(self.strategy.items):raise ValueError('strategy_revision does not exist')
        if candidate_revision is not None and candidate_revision>=len(self.candidates.items):raise ValueError('candidate_revision does not exist')
        receipt=ReintegrationReceipt(candidate_before_revision,current.results[-1].revision,accepted,rejected,main_consequence,strategy_revision,candidate_revision,self.clock_journal.events[-1].record_hash)
        out=self.dictator.reintegrate(intervention_id,receipt);self.refresh_brief();return out

    def finish_time(self,at:ClockSnapshot):
        if self.ledger is None:raise RuntimeError('no active ledger')
        if self.phase.phase is not RunPhase.EXECUTING:raise RuntimeError('finish_time requires formal MAIN execution to have started')
        if not self.strategy.has_state:raise RuntimeError('finish_time requires Strategy Genesis/current StrategyState')
        if self.ledger.foreground_state is not WorkState.MAIN:
            raise RuntimeError('final synthesis/finalization must return to MAIN before formal timing finishes')
        self.phase.transition(RunPhase.FINALIZING,'formal timing finalized')
        self.ledger.finish(at);self.clock_journal.append('FINISH',at,WorkState.META);self.clock_journal.verify(self.contract.hard_timing_required if self.contract else False);self._reindex_journals()
        derived=derive_work_intervals(self.clock_journal.events)
        lhs=[(x.state,x.start.monotonic_ns,x.end.monotonic_ns,x.observed_ns,x.hard_verified) for x in self.ledger.intervals];rhs=[(x.state,x.start.monotonic_ns,x.end.monotonic_ns,x.observed_ns,x.hard_verified) for x in derived]
        if lhs!=rhs:raise RuntimeError('clock journal / formal ledger parity failure')
        self.refresh_brief()

    def actuals(self):
        if self.ledger is None:raise RuntimeError('contract/timing not initialized')
        return derive_contract_actuals(self.events,self.sources,self.source_activity,self.dictator,self.ledger,self.clock_journal,self.viewpoints,self.d_activity,self.v_activity)
    def stop_check(self):
        if self.contract is None:raise RuntimeError('contract missing')
        return check_mechanical_minima(self.contract,self.actuals())
    def _require_finalizing(self):
        if self.phase.phase is not RunPhase.FINALIZING or self.ledger is None or not self.ledger.finished:raise RuntimeError('finish formal timing before finalization')

    def _delivery_gate_failures(self)->tuple[str,...]:
        failures=[]
        if self.protocol_load is None or not self.protocol_load.completeness_verified:
            failures.append('PROTOCOL_LOAD_INCOMPLETE')
        stop=self.stop_check()
        failures.extend(stop.unmet_requirements)
        failures.extend(self.completion.delivery_failures)
        # Structured completion is the preferred Berta evidence shape. The
        # legacy semantic assessment remains accepted during Berta2 migration;
        # readiness is disclosed in the final summary instead of silently
        # converting old prose into four affirmative claims.
        if not self.candidates.has_state:failures.append('FINAL_CANDIDATE_MISSING')
        try:
            host_authority=verify_enforced_host_delivery_authority(self.workspace)
            if self.contract.source_required and not host_authority.source_tools:
                failures.append('REQUIRED_SOURCE_TOOLS_UNAVAILABLE')
        except HostDeliveryAuthorityError as exc:failures.append(exc.code)
        return tuple(failures)

    def _candidate_payload_binding(self,candidate:CandidateSnapshot,payload_sha256:str)->str|None:
        # save_candidate_bytes defines artifact_refs[0] as the candidate's
        # primary content-addressed payload. Extra refs are evidence/context and
        # can never substitute an older candidate's bytes at delivery.
        if not candidate.artifact_refs:return None
        rel=candidate.artifact_refs[0]
        if not rel.startswith('state/candidate-payloads/'):return None
        record=self.workspace.require_indexed_artifact(rel,kind='candidate-payload')
        return rel if record.sha256==payload_sha256 else None

    def _summary_for_delivery(self,actual,stop,final_binding,audit_logs=None):
        prov=ActualsProvenance()
        return {
            'run_id':self.run_id,'authority':self.startup.authority.to_dict(),
            'invocation':self.startup.invocation.to_dict(),'phase':'DELIVERED',
            'U0':self.U0.to_dict() if self.U0 else None,
            'contract':self.contract.to_dict(),'actuals':actual.__dict__,
            'provenance':prov.__dict__,'mechanical_checks':stop.__dict__,
            'mechanical_minima_satisfied':True,
            'semantic_completion_assessed':True,'structured_completion_ready':self.completion.structured_ready,'blocking_open_gaps':0,
            'delivery_ready':True,'clock_journal_events':len(self.clock_journal.events),
            'final':final_binding,
            'audit_logs':audit_logs or {},
        }

    def _mark_incomplete(self,unmet):
        values=tuple(unmet)
        payload={
            'run_id':self.run_id,'phase':'INCOMPLETE','unmet':list(values),
            'mechanical_minima_satisfied':self.stop_check().minima_satisfied,
            'semantic_completion_assessed':self.completion.semantically_assessed,
            'blocking_open_gaps':len(self.completion.blocking_open),
            'delivery_ready':False,
        }
        summary_sha=self.workspace.write_json('final/incomplete-summary.json',payload,kind='incomplete-summary')
        self.phase.transition(RunPhase.INCOMPLETE,'delivery gates unmet: ' + ','.join(values))
        try:
            self.refresh_brief()
        finally:
            if not self.workspace.terminal_sealed:
                self.workspace.seal_terminal(phase='INCOMPLETE',binding_sha256=summary_sha)

    def commit_delivery(self,final_bytes:bytes,*,media_type:str='text/markdown',candidate_revision:int|None=None)->DeliveryEnvelope:
        """Two-phase, crash-safe commit of the exact bytes a host may deliver.

        Artifacts are prepared and verified while FINALIZING; the persisted
        DELIVERED phase is the commit marker.  A crash may leave partial final
        artifacts but cannot create a successful terminal claim.  Retrying the
        same exact delivery after success is idempotent.  Any different bytes,
        media type, or candidate selection are rejected.
        """
        if not isinstance(final_bytes,(bytes,bytearray)):raise TypeError('final_bytes must be exact bytes')
        raw=bytes(final_bytes)
        if not raw:raise ValueError('final delivery bytes must not be empty')
        media_type=require_nonempty_text('media_type',media_type)
        if self.phase.phase is RunPhase.DELIVERED:
            envelope=self.delivery or DeliveryEnvelope.from_dict(self.workspace.read_json(DELIVERY_ENVELOPE_PATH))
            envelope.verify_payload(raw)
            if envelope.media_type!=media_type:raise ValueError('delivery retry media_type mismatch')
            if candidate_revision is not None and envelope.candidate_revision!=candidate_revision:
                raise ValueError('delivery retry candidate revision mismatch')
            verify_delivery_artifacts(self.workspace,envelope);self.delivery=envelope;return envelope
        self._require_finalizing()
        payload_sha=sha256(raw).hexdigest()
        unmet=list(self._delivery_gate_failures())
        candidate=self.candidates.current if self.candidates.has_state else None
        requested_revision=None if candidate_revision is None else require_nonnegative_int('candidate_revision',candidate_revision)
        selected=candidate.revision if candidate is not None and requested_revision is None else requested_revision
        candidate_payload_path=None
        if candidate is not None:
            if selected!=candidate.revision:
                unmet.append('FINAL_CANDIDATE_NOT_CURRENT')
            else:
                candidate_payload_path=self._candidate_payload_binding(candidate,payload_sha)
                if candidate_payload_path is None:unmet.append('FINAL_PAYLOAD_NOT_BOUND_TO_CANDIDATE')
        if unmet:
            self._mark_incomplete(unmet)
            raise DeliveryGateError(unmet)
        assert candidate is not None and candidate_payload_path is not None
        host_authority=verify_enforced_host_delivery_authority(self.workspace)
        actual=self.actuals();stop=self.stop_check()
        from .audit_logs import materialize_audit_logs
        audit_logs=materialize_audit_logs(self,actual)
        state_sha=terminal_state_sha256(self.workspace)
        final_binding={
            'payload_sha256':payload_sha,'payload_byte_length':len(raw),
            'media_type':media_type,'candidate_revision':candidate.revision,
            'candidate_digest':candidate.digest,'candidate_payload_path':candidate_payload_path,
            'terminal_state_sha256':state_sha,
            **host_authority.binding,
        }
        summary=self._summary_for_delivery(actual,stop,final_binding,audit_logs)
        from .proof import proof_data_from_contract_actuals
        proof_data=proof_data_from_contract_actuals(self.contract,actual)
        proof_document={
            'schema_version':1,'run_id':self.run_id,'status':'DELIVERED',
            'delivery':final_binding,'proof':proof_data.to_dict_berta() if self.startup.authority.P_run.version=='5.0.0-Berta2' else proof_data.to_dict(),
        }
        persisted_payload_sha=self.workspace.atomic_write_bytes(DELIVERY_PAYLOAD_PATH,raw)
        self.workspace.index_existing(DELIVERY_PAYLOAD_PATH,kind='final-delivery-payload',expected_digest=persisted_payload_sha)
        summary_sha=self.workspace.write_json(DELIVERY_SUMMARY_PATH,summary,kind='run-summary')
        proof_sha=self.workspace.write_json(DELIVERY_PROOF_PATH,proof_document,kind='stable-proof')
        envelope=DeliveryEnvelope(
            DELIVERY_SCHEMA_VERSION,self.run_id,'DELIVERED',DELIVERY_PAYLOAD_PATH,
            payload_sha,len(raw),media_type,candidate.revision,candidate.digest,
            candidate_payload_path,state_sha,
            host_authority.preflight_receipt_path,host_authority.preflight_receipt_sha256,
            host_authority.capability_negotiation_path,host_authority.capability_negotiation_sha256,
            DELIVERY_SUMMARY_PATH,summary_sha,DELIVERY_PROOF_PATH,proof_sha,
        )
        self.workspace.write_json(DELIVERY_ENVELOPE_PATH,envelope.to_dict(),kind='delivery-envelope')
        verify_delivery_artifacts(self.workspace,envelope)
        self.phase.transition(RunPhase.DELIVERED,'exact final bytes and delivery evidence committed')
        self.delivery=envelope
        try:
            self.refresh_brief()
        finally:
            if not self.workspace.terminal_sealed:
                self.workspace.seal_terminal(phase='DELIVERED',binding_sha256=envelope.digest)
        return envelope

    def write_run_summary(self,final_bytes:bytes|None=None,*,media_type:str='text/markdown',candidate_revision:int|None=None):
        """Compatibility facade; stable callers must supply exact final bytes."""
        if final_bytes is None:
            raise DeliveryGateError(('EXACT_FINAL_BYTES_REQUIRED',))
        self.commit_delivery(final_bytes,media_type=media_type,candidate_revision=candidate_revision)
        return self.workspace.read_json(DELIVERY_SUMMARY_PATH)

    def delivery_ready(self):
        if self.phase.phase is RunPhase.DELIVERED:
            try:
                envelope=self.delivery or DeliveryEnvelope.from_dict(self.workspace.read_json(DELIVERY_ENVELOPE_PATH))
                return verify_delivery_artifacts(self.workspace,envelope)
            except (OSError,TypeError,ValueError):return False
        if self.phase.phase is not RunPhase.FINALIZING or self.ledger is None or not self.ledger.finished:return False
        return not self._delivery_gate_failures()

    def render_proof(self):
        if self.phase.phase is not RunPhase.DELIVERED:
            raise DeliveryGateError(('RUN_NOT_DELIVERED',))
        envelope=self.delivery or DeliveryEnvelope.from_dict(self.workspace.read_json(DELIVERY_ENVELOPE_PATH))
        verify_delivery_artifacts(self.workspace,envelope)
        if (not self.candidates.has_state or self.candidates.current.revision!=envelope.candidate_revision
                or self.candidates.current.digest!=envelope.candidate_digest
                or not self.candidates.current.artifact_refs
                or envelope.candidate_payload_path!=self.candidates.current.artifact_refs[0]):
            raise ValueError('delivery envelope candidate binding drift')
        from .proof import proof_data_from_contract_actuals,render_canonical_proof
        expected=proof_data_from_contract_actuals(self.contract,self.actuals())
        stored=self.workspace.read_json(DELIVERY_PROOF_PATH)
        expected_proof=expected.to_dict_berta() if self.startup.authority.P_run.version=='5.0.0-Berta2' else expected.to_dict()
        if stored!={'schema_version':1,'run_id':self.run_id,'status':'DELIVERED','delivery':envelope.final_binding,'proof':expected_proof}:
            raise ValueError('stable proof document drift')
        return render_canonical_proof(
            self.contract,self.actuals(),delivery_status=self.phase.phase.value,
            delivery_verified=True,
        )
