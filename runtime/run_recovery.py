"""Comprehensive DIGR 5.0 Alpha 4 workspace integrity/recovery verification.

Verification proves persisted structure and cross-store bindings.  It deliberately
separates *workspace integrity* from *future clock continuity*: LiveDIGRRun.resume
must establish a fresh, same-boot monotonic bridge before a nonterminal run may
continue.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path

from .actuals import ActualsProvenance
from .candidate_store import CandidateStore
from .clock_journal import ClockJournal, derive_work_intervals
from .completion_state import CompletionState
from .d_intervention import DInterventionStore
from .effective_contract import EffectiveContract, SourceContract, SourceDisposition
from .execution_protocol import ExecutingProtocolLoadReceipt
from .est_store import ESTStore
from .evidence_index import EvidenceIndex
from .evolution_events import EvolutionEventLog, EvolutionKind
from .interval_ledger import WorkState
from .run_brief import verify_run_brief
from .run_lifecycle import RunPhase, RunPhaseStore
from .source_workspace import SourceActivityLog, SourceWorkspaceRegistry
from .stop_checks import ContractActuals, check_mechanical_minima
from .strategy_store import StrategyStore
from .workspace import RunWorkspace, validate_run_id


def _load_contract(d: dict) -> EffectiveContract:
    s=d['S']
    return EffectiveContract(
        d['N'],d['T_seconds'],d['R'],d['B'],
        SourceContract(s['n'],s['t_seconds'],s['r'],s['b']),
        d['D_s'],d['L_e'],SourceDisposition(d.get('source_disposition','REQUIRED')),
        d.get('source_waiver_reason'),d.get('L_mismatch_blocks_delivery',False),
    )


def _derived_actuals(events, sources, activity, dstore, intervals) -> ContractActuals:
    known={s.source_id for s in sources.states}
    active={sid for item in activity.items for sid in item.source_ids}
    semantic={
        e.source_id for e in events.events
        if e.kind in (EvolutionKind.SOURCE_EVOLUTION,EvolutionKind.SOURCE_REENTRY)
        and e.source_id is not None
    }
    actual_source_ids=sorted(known & active & semantic)
    n=[events.count(EvolutionKind.SOURCE_EVOLUTION,f'S:{sid}') for sid in actual_source_ids]
    r=[events.count(EvolutionKind.SOURCE_REENTRY,f'S:{sid}') for sid in actual_source_ids]
    T_rel=[x for x in intervals if x.state in (WorkState.MAIN,WorkState.SOURCE)]
    t_rel=[x for x in intervals if x.state is WorkState.SOURCE]
    return ContractActuals(
        N=events.count(EvolutionKind.MAIN_EVOLUTION,'MAIN'),
        T_seconds=sum(x.observed_ns for x in T_rel)/1e9,
        T_hard_verified=bool(T_rel) and all(x.hard_verified for x in T_rel),
        R=events.count(EvolutionKind.MAIN_REENTRY,'MAIN'),
        S_count=len(actual_source_ids),
        n_min=min(n) if n else 0,
        t_seconds=sum(x.observed_ns for x in t_rel)/1e9,
        t_hard_verified=bool(t_rel) and all(x.hard_verified for x in t_rel),
        r_min=min(r) if r else 0,
        D_s=dstore.completed_count,
        L_e=dstore.actual_isolation_level,
    )


def verify_run_workspace(root: Path, run_id: str) -> dict:
    run_id=validate_run_id(run_id)
    ws=RunWorkspace.open_existing(root,run_id)
    required=(
        'authority.json','invocation.json','startup.json','time/clock.journal.ndjson',
        'state/artifact-index.json','state/run-phase.json',
    )
    missing=[x for x in required if not ws.path(x).is_file()]
    if missing:
        raise ValueError(f'missing run artifacts: {missing}')

    # The artifact index is checked before interpreting any indexed state.
    ws.verify_artifact_index()
    authority=ws.read_json('authority.json')
    startup=ws.read_json('startup.json')
    invocation=ws.read_json('invocation.json')
    if startup.get('invocation')!=invocation:
        raise ValueError('startup/invocation mismatch')
    if startup.get('authority')!=authority:
        raise ValueError('startup/authority mismatch')

    u0=None
    if ws.path('U0.json').is_file():
        u0=ws.read_json('U0.json')
        if sha256(u0['text'].encode()).hexdigest()!=u0.get('sha256'):
            raise ValueError('U0 digest mismatch')
        if u0.get('source_message_sha256')!=invocation.get('raw_message_sha256'):
            raise ValueError('U0 source-message binding mismatch')

    phase=RunPhaseStore.load(ws)
    phase_requires={
        RunPhase.PARAMETER_RESOLVED:('protocol-load.json','parameter-resolution.json'),
        RunPhase.U0_FROZEN:('protocol-load.json','parameter-resolution.json','U0.json'),
        RunPhase.CONTRACT_FROZEN:('protocol-load.json','parameter-resolution.json','U0.json','contract.json'),
        RunPhase.EXECUTING:('protocol-load.json','parameter-resolution.json','U0.json','contract.json'),
        RunPhase.FINALIZING:('protocol-load.json','parameter-resolution.json','U0.json','contract.json'),
        RunPhase.FINISHED:('protocol-load.json','parameter-resolution.json','U0.json','contract.json','final/run-summary.json'),
    }
    for rel in phase_requires.get(phase.phase,()):
        if not ws.path(rel).is_file():
            raise ValueError(f'phase {phase.phase.value} missing {rel}')

    if ws.path('protocol-load.json').is_file():
        pl=ExecutingProtocolLoadReceipt.from_dict(ws.read_json('protocol-load.json'))
        ident=authority.get('P_run',{})
        route=authority.get('route',{})
        if (pl.commit_sha!=ident.get('commit_sha') or pl.version!=ident.get('version') or pl.protocol!=ident.get('protocol')
                or pl.manifest_sha256!=route.get('manifest_sha256')):
            raise ValueError('protocol-load receipt does not match persisted P_run/manifest')

    contract_raw=ws.read_json('contract.json') if ws.path('contract.json').is_file() else None
    contract=_load_contract(contract_raw) if contract_raw is not None else None

    journal=ClockJournal.load(run_id,ws.path('time/clock.journal.ndjson'))
    journal.verify(False)
    intervals=derive_work_intervals(journal.events)
    clock_hashes={e.record_hash:e for e in journal.events}
    formal_T_ns=sum(x.observed_ns for x in intervals if x.state in (WorkState.MAIN,WorkState.SOURCE))
    formal_t_ns=sum(x.observed_ns for x in intervals if x.state is WorkState.SOURCE)

    strategy=StrategyStore.load(ws)
    candidates=CandidateStore.load(ws)
    sources=SourceWorkspaceRegistry.load(ws)
    dstore=DInterventionStore.load(ws)
    est=ESTStore.load(ws)
    evidence=EvidenceIndex.load(ws)
    completion=CompletionState.load(ws)
    events=EvolutionEventLog.load(ws.path('events.ndjson'))
    events.verify()
    activity=SourceActivityLog.load(ws.path('time/source-activity.ndjson'))
    activity.verify()

    known_sources={x.source_id for x in sources.states}
    source_state_refs={
        e.record_hash for e in journal.events
        if e.event=='STATE' and e.state is WorkState.SOURCE
    }
    activity_by_ref=activity.by_clock_ref()
    for a in activity.items:
        if a.clock_event_ref not in source_state_refs:
            raise ValueError('source activity clock reference is not a SOURCE state event')
        if any(s not in known_sources for s in a.source_ids):
            raise ValueError('source activity references missing source workspace')
    if source_state_refs-set(activity_by_ref):
        raise ValueError('SOURCE state event lacks active source binding')

    # Event-v2 proves not only that a receipt has a hash, but where in the
    # formal state/time stream the semantic work happened.
    for e in events.events:
        clock=clock_hashes.get(e.clock_event_ref)
        if clock is None:
            raise ValueError('semantic event lacks valid clock journal binding')
        if clock.event!='STATE':
            raise ValueError('semantic event must bind a foreground STATE clock event')
        if e.strategy_revision is None or e.strategy_revision>=len(strategy.items):
            raise ValueError('semantic event lacks valid strategy revision')
        for r in (e.candidate_revision,e.candidate_after_revision):
            if r is not None and r>=len(candidates.items):
                raise ValueError('semantic event references missing candidate revision')

        if e.kind in (EvolutionKind.MAIN_EVOLUTION,EvolutionKind.MAIN_REENTRY):
            if clock.state is not WorkState.MAIN:
                raise ValueError('MAIN semantic event is not bound to MAIN work state')
        else:
            if clock.state is not WorkState.SOURCE:
                raise ValueError('SOURCE semantic event is not bound to SOURCE work state')
            if e.source_id not in known_sources:
                raise ValueError('semantic event references missing source workspace')
            if e.source_id not in activity_by_ref.get(e.clock_event_ref,()):
                raise ValueError('SOURCE semantic event source is not active at bound clock state')
            try:
                before=sources.get(e.source_id,e.source_revision)
            except (KeyError,IndexError):
                raise ValueError('SOURCE event references missing source revision') from None
            if before.revision!=e.source_revision:
                raise ValueError('SOURCE event source revision drift')

        if e.kind is EvolutionKind.MAIN_REENTRY:
            if e.candidate_revision is None:
                raise ValueError('MAIN R event must bind candidate_before')
            if not e.retained:
                if e.candidate_after_revision is None or e.candidate_after_revision<=e.candidate_revision:
                    raise ValueError('non-retained MAIN R must bind a newer candidate_after')
        elif e.kind is EvolutionKind.SOURCE_REENTRY:
            if e.retained:
                if e.source_after_revision is not None:
                    raise ValueError('retained SOURCE R cannot bind source_after')
            else:
                if e.source_after_revision is None or e.source_after_revision<=e.source_revision:
                    raise ValueError('non-retained SOURCE R must bind a newer source_after')
                try:
                    sources.get(e.source_id,e.source_after_revision)
                except (KeyError,IndexError):
                    raise ValueError('SOURCE R references missing source_after revision') from None

    # D/L is one integrated information-flow lifecycle.  Capability alone does
    # not prove actual isolation, and L2/L3 packets must be real indexed
    # artifacts. Execution and reintegration must be clock-state bound.
    for item in dstore.items:
        iso=dstore.isolation(item.isolation_receipt_id)
        if contract is not None and iso.L_target!=contract.L_e:
            raise ValueError('D isolation target does not match frozen contract L')
        if iso.L_actual is not None and iso.L_actual>=2:
            ws.require_indexed_artifact(iso.input_packet_ref,kind='d-input-packet')
        if iso.output_packet_ref is not None:
            ws.require_indexed_artifact(iso.output_packet_ref,kind='d-output-packet')

        for de in item.execution_events:
            if de.clock_event_ref is None or de.clock_event_ref not in clock_hashes:
                raise ValueError('D execution lacks valid clock journal binding')
            ce=clock_hashes[de.clock_event_ref]
            if ce.event!='STATE':
                raise ValueError('D execution must bind a foreground STATE clock event')
            if iso.mode=='exclusive' and ce.state is not WorkState.D_EXCLUSIVE:
                raise ValueError('exclusive D execution is not bound to D_EXCLUSIVE state')
            if iso.mode=='background' and ce.state not in (WorkState.MAIN,WorkState.SOURCE):
                raise ValueError('background D execution is not bound to MAIN/SOURCE state')

        for result in item.results:
            if iso.L_actual is not None and iso.L_actual>=2:
                if result.output_packet_ref is None:
                    raise ValueError('L2/L3 D result lacks Output Packet artifact')
                ws.require_indexed_artifact(result.output_packet_ref,kind='d-output-packet')
            elif result.output_packet_ref is not None:
                ws.require_indexed_artifact(result.output_packet_ref,kind='d-output-packet')

        if item.reintegration is not None:
            rr=item.reintegration
            if rr.candidate_before_revision is not None and rr.candidate_before_revision>=len(candidates.items):
                raise ValueError('D reintegration references missing candidate_before')
            if rr.strategy_revision is not None and rr.strategy_revision>=len(strategy.items):
                raise ValueError('D reintegration references missing strategy revision')
            if rr.candidate_revision is not None and rr.candidate_revision>=len(candidates.items):
                raise ValueError('D reintegration references missing candidate revision')
            if rr.clock_event_ref is None or rr.clock_event_ref not in clock_hashes:
                raise ValueError('D reintegration lacks valid clock journal binding')
            ce=clock_hashes[rr.clock_event_ref]
            if ce.event!='STATE' or ce.state is not WorkState.MAIN:
                raise ValueError('D reintegration must bind MAIN foreground work')

    for scope in est.scopes:
        x=est.latest(scope)
        if x.strategy_revision is not None and x.strategy_revision>=len(strategy.items):
            raise ValueError('EST references missing strategy revision')
        if x.candidate_revision is not None and x.candidate_revision>=len(candidates.items):
            raise ValueError('EST references missing candidate revision')

    if ws.path('state/run-brief.json').is_file():
        brief_expected={
            'schema_version':1,
            'run_id':run_id,
            'U0_sha256':u0['sha256'] if u0 else None,
            'contract_present':contract is not None,
            'phase':phase.phase.value,
            'strategy_revision':strategy.current.revision if strategy.has_state else None,
            'candidate_revision':candidates.current.revision if candidates.has_state else None,
            'active_source_ids':[s.source_id for s in sources.open_states],
            'D_completed':dstore.completed_count,
            'blocking_gap_ids':[g.gap_id for g in completion.blocking_open],
            'key_evidence_refs':[x.evidence_id for x in evidence.items][-24:],
            'latest_meaningful_event_refs':[e.event_id for e in events.events[-8:]],
        }
        verify_run_brief(ws,brief_expected)

    if phase.phase is RunPhase.FINISHED:
        summary=ws.read_json('final/run-summary.json')
        if contract is None or u0 is None:
            raise ValueError('FINISHED run missing U0/contract')
        actual=_derived_actuals(events,sources,activity,dstore,intervals)
        stop=check_mechanical_minima(contract,actual)
        expected={
            'run_id':run_id,
            'authority':authority,
            'invocation':invocation,
            'phase':'FINISHED',
            'U0':u0,
            'contract':contract.to_dict(),
            'actuals':actual.__dict__,
            'provenance':ActualsProvenance().__dict__,
            'mechanical_checks':stop.__dict__,
            'mechanical_minima_satisfied':stop.minima_satisfied,
            'semantic_completion_assessed':completion.semantically_assessed,
            'blocking_open_gaps':len(completion.blocking_open),
            'delivery_ready':stop.minima_satisfied and completion.ready,
            'clock_journal_events':len(journal.events),
        }
        if summary!=expected:
            bad=sorted(k for k in set(summary)|set(expected) if summary.get(k)!=expected.get(k))
            raise ValueError(f'final run summary drift: {bad}')

    return {
        'run_id':run_id,'workspace':str(ws.root),'phase':phase.phase.value,
        'journal_events':len(journal.events),'formal_T_ns':formal_T_ns,'formal_t_ns':formal_t_ns,
        'event_count':len(events.events),'strategy_revisions':len(strategy.items),
        'candidate_revisions':len(candidates.items),'source_count':len(sources.states),
        'D_completed':dstore.completed_count,'artifact_count':len(ws.artifact_records()),
        'integrity_ok':True,
        'hard_continuity_after_recovery':'must_be_reestablished_by_resume',
    }
