"""Comprehensive DIGR 5.0 Alpha 10 workspace integrity/recovery verification.

Verification proves persisted structure and cross-store bindings.  It deliberately
separates *workspace integrity* from *future clock continuity*: LiveDIGRRun.resume
tries a same-epoch bridge first; if continuity changed, it establishes a fresh trusted epoch and continues without crediting the discontinuity.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path

from .actuals import ActualsProvenance
from .candidate_store import CandidateStore
from .clock_journal import ClockJournal, derive_work_timeline
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
        d['D_s'],SourceDisposition(d.get('source_disposition','REQUIRED')),
        d.get('source_waiver_reason'),
    )


def _derived_actuals(events, sources, activity, dstore, timeline) -> ContractActuals:
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
    T_rel=[x for x in timeline.intervals if x.state in (WorkState.MAIN,WorkState.SOURCE,WorkState.D_EXCLUSIVE)]
    t_rel=[x for x in timeline.intervals if x.state is WorkState.SOURCE]
    T_gaps=[x for x in timeline.gaps if x.state in (WorkState.MAIN,WorkState.SOURCE,WorkState.D_EXCLUSIVE)]
    t_gaps=[x for x in timeline.gaps if x.state is WorkState.SOURCE]
    T_continuity=[x for x in timeline.continuity_gaps if x.state in (WorkState.MAIN,WorkState.SOURCE,WorkState.D_EXCLUSIVE)]
    t_continuity=[x for x in timeline.continuity_gaps if x.state is WorkState.SOURCE]
    T_coverage_complete=not T_gaps and not T_continuity
    t_coverage_complete=not t_gaps and not t_continuity
    return ContractActuals(
        N=events.count(EvolutionKind.MAIN_EVOLUTION,'MAIN'),
        T_seconds=sum(x.observed_ns for x in T_rel)/1e9,
        T_hard_verified=bool(T_rel) and all(x.hard_verified for x in T_rel),
        T_coverage_complete=T_coverage_complete,
        unattributed_T_seconds=sum(x.observed_ns for x in T_gaps)/1e9,
        R=events.count(EvolutionKind.MAIN_REENTRY,'MAIN'),
        S_count=len(actual_source_ids),
        n_min=min(n) if n else 0,
        t_seconds=sum(x.observed_ns for x in t_rel)/1e9,
        t_hard_verified=bool(t_rel) and all(x.hard_verified for x in t_rel),
        t_coverage_complete=t_coverage_complete,
        unattributed_t_seconds=sum(x.observed_ns for x in t_gaps)/1e9,
        r_min=min(r) if r else 0,
        D_s=dstore.completed_count,
    )


def _json_equal(ws: RunWorkspace, rel: str, value: dict) -> bool:
    p=ws.path(rel)
    return p.is_file() and ws.read_json(rel)==value


def recover_run_workspace_fast(root: Path, run_id: str) -> dict:
    """Cheap ordinary-resume preparation.

    Normal continuation repairs only an interrupted transactional write and
    reindexes the three self-verifying append-only journals.  It deliberately
    does not scan revision history or rebuild every derived pointer.
    """
    run_id=validate_run_id(run_id)
    ws=RunWorkspace.open_existing(root,run_id)
    actions=[]
    outcome=ws.recover_pending_write()
    if outcome is not None:
        actions.append(f'workspace-write:{outcome}')
    journal_specs=(
        ('time/clock.journal.ndjson','clock-journal',lambda p: ClockJournal.load(run_id,p).verify(False)),
        ('time/source-activity.ndjson','source-activity',lambda p: SourceActivityLog.load(p).verify()),
        ('events.ndjson','event-log',lambda p: EvolutionEventLog.load(p).verify()),
    )
    for rel,kind,verify in journal_specs:
        p=ws.path(rel)
        if p.is_file():
            verify(p)
            ws.index_existing(rel,kind=kind)
            actions.append(f'reindexed:{rel}')
    return {'run_id':run_id,'recovery_actions':tuple(actions),'mode':'fast'}

def recover_run_workspace(root: Path, run_id: str) -> dict:
    """Full anomaly/crash repair, never the ordinary resume fast path."""
    run_id=validate_run_id(run_id)
    ws=RunWorkspace.open_existing(root,run_id)
    actions=[]
    outcome=ws.recover_pending_write()
    if outcome is not None:
        actions.append(f'workspace-write:{outcome}')

    # Append-only journals can safely refresh their artifact-index digest after
    # their own hash/sequence verification succeeds.
    journal_specs=(
        ('time/clock.journal.ndjson','clock-journal',lambda p: ClockJournal.load(run_id,p).verify(False)),
        ('time/source-activity.ndjson','source-activity',lambda p: SourceActivityLog.load(p).verify()),
        ('events.ndjson','event-log',lambda p: EvolutionEventLog.load(p).verify()),
    )
    for rel,kind,verify in journal_specs:
        p=ws.path(rel)
        if p.is_file():
            verify(p)
            ws.index_existing(rel,kind=kind)
            actions.append(f'reindexed:{rel}')

    def repair_pointer(source_rel,target_rel,kind,revision):
        value=ws.read_json(source_rel)
        if not _json_equal(ws,target_rel,value):
            ws.write_json(target_rel,value,kind=kind,revision=revision)
            actions.append(f'rebuilt:{target_rel}')

    # Immutable revision history is authoritative; latest pointers are caches.
    for prefix,latest_name,kind in (
        ('strategy-r','strategy-latest.json','strategy-latest'),
        ('candidate-r','candidate-latest.json','candidate-latest'),
        ('run-phase-r','run-phase.json','run-phase-latest'),
    ):
        files=sorted(ws.path('state').glob(prefix+'*.json'))
        if files:
            src=files[-1]
            value=ws.read_json(str(src.relative_to(ws.root)))
            revision=value['revision']
            repair_pointer(str(src.relative_to(ws.root)),f'state/{latest_name}',kind,revision)

    src_root=ws.path('sources')
    if src_root.exists():
        for d in sorted(x for x in src_root.iterdir() if x.is_dir()):
            files=sorted(d.glob('state-r*.json'))
            if files:
                src=files[-1]; value=ws.read_json(str(src.relative_to(ws.root)))
                repair_pointer(str(src.relative_to(ws.root)),str((d/'state.json').relative_to(ws.root)),'source-latest',value['revision'])

    d_latest={}
    for p in sorted(ws.path('dictator').glob('*-r*.json')):
        value=ws.read_json(str(p.relative_to(ws.root)))
        iid=value.get('intervention_id')
        rev=value.get('state_revision')
        if isinstance(iid,str) and isinstance(rev,int):
            prior=d_latest.get(iid)
            if prior is None or rev>prior[0]:
                d_latest[iid]=(rev,p)
    for iid,(rev,p) in sorted(d_latest.items()):
        repair_pointer(str(p.relative_to(ws.root)),f'dictator/{iid}.json','d-intervention-latest',rev)

    est_latest={}
    for p in sorted(ws.path('state').glob('est-*-r*.json')):
        value=ws.read_json(str(p.relative_to(ws.root)))
        scope=value.get('scope'); rev=value.get('revision')
        if isinstance(scope,str) and isinstance(rev,int):
            prior=est_latest.get(scope)
            if prior is None or rev>prior[0]:
                est_latest[scope]=(rev,p,value)
    for scope,(rev,p,value) in sorted(est_latest.items()):
        safe=''.join(c if c.isalnum() or c in '._-' else '_' for c in scope)[:48]
        tag=sha256(scope.encode()).hexdigest()[:10]
        rel=f'state/est-{safe}-{tag}-latest.json'
        if not _json_equal(ws,rel,value):
            ws.write_json(rel,value,kind='est-latest',revision=rev)
            actions.append(f'rebuilt:{rel}')

    # completion.json is a summary of immutable gap revisions plus assessment
    # strings.  Keep committed assessments, but rebuild the latest gap view.
    gap_hist={}
    gap_files=sorted(ws.path('state/gaps').glob('*-r*.json')) if ws.path('state/gaps').exists() else []
    for p in gap_files:
        value=ws.read_json(str(p.relative_to(ws.root)))
        gid=value.get('gap_id'); rev=value.get('revision')
        if isinstance(gid,str) and isinstance(rev,int):
            prior=gap_hist.get(gid)
            if prior is None or rev>prior[0]:
                gap_hist[gid]=(rev,value)
    cp=ws.path('state/completion.json')
    current=ws.read_json('state/completion.json') if cp.is_file() else {'assessment_revisions':[]}
    assessments=list(current.get('assessment_revisions',[]))
    expected={'gaps':[gap_hist[k][1] for k in sorted(gap_hist)],'assessment_revisions':assessments}
    if gap_hist and not _json_equal(ws,'state/completion.json',expected):
        revision=len(gap_files)+len(assessments)
        ws.write_json('state/completion.json',expected,kind='completion',revision=revision)
        actions.append('rebuilt:state/completion.json')

    return {'run_id':run_id,'recovery_actions':tuple(actions),'mode':'full'}

def verify_run_workspace(root: Path, run_id: str) -> dict:
    run_id=validate_run_id(run_id)
    ws=RunWorkspace.open_existing(root,run_id)
    required=(
        'authority.json','invocation.json','startup.json','protocol-load.json','time/clock.journal.ndjson',
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
    timeline=derive_work_timeline(journal.events)
    if phase.phase in (RunPhase.FINALIZING,RunPhase.FINISHED) and not timeline.finished:
        raise ValueError(f'phase {phase.phase.value} requires committed FINISH journal event')
    if timeline.finished and phase.phase not in (RunPhase.EXECUTING,RunPhase.FINALIZING,RunPhase.FINISHED):
        raise ValueError(f'committed FINISH is incompatible with phase {phase.phase.value}')
    intervals=timeline.intervals
    clock_hashes={e.record_hash:e for e in journal.events}
    formal_T_ns=sum(x.observed_ns for x in intervals if x.state in (WorkState.MAIN,WorkState.SOURCE,WorkState.D_EXCLUSIVE))
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
        if e.event in ('STATE','WORK_LEASE_OPEN') and e.state is WorkState.SOURCE
    }
    activity_by_ref=activity.by_clock_ref()
    for a in activity.items:
        if a.clock_event_ref not in source_state_refs:
            raise ValueError('source activity clock reference is not a SOURCE state/lease event')
        if any(s not in known_sources for s in a.source_ids):
            raise ValueError('source activity references missing source workspace')
    if source_state_refs-set(activity_by_ref):
        raise ValueError('SOURCE state/lease event lacks active source binding')

    # Event-v2 proves not only that a receipt has a hash, but where in the
    # formal state/time stream the semantic work happened.
    main_r_floor=None
    source_r_floor={}
    for e in events.events:
        clock=clock_hashes.get(e.clock_event_ref)
        if clock is None:
            raise ValueError('semantic event lacks valid clock journal binding')
        if clock.event not in ('STATE','WORK_LEASE_OPEN'):
            raise ValueError('semantic event must bind a foreground STATE/WORK_LEASE_OPEN clock event')
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
            if main_r_floor is not None and e.candidate_revision<main_r_floor:
                raise ValueError('MAIN R cannot move backward to a superseded candidate')
            if not e.retained:
                if e.candidate_after_revision is None or e.candidate_after_revision<=e.candidate_revision:
                    raise ValueError('non-retained MAIN R must bind a newer candidate_after')
                main_r_floor=e.candidate_after_revision
            else:
                main_r_floor=e.candidate_revision
        elif e.kind is EvolutionKind.SOURCE_REENTRY:
            floor=source_r_floor.get(e.source_id)
            if floor is not None and e.source_revision<floor:
                raise ValueError('SOURCE R cannot move backward to a superseded source revision')
            if e.retained:
                if e.source_after_revision is not None:
                    raise ValueError('retained SOURCE R cannot bind source_after')
                source_r_floor[e.source_id]=e.source_revision
            else:
                if e.source_after_revision is None or e.source_after_revision<=e.source_revision:
                    raise ValueError('non-retained SOURCE R must bind a newer source_after')
                try:
                    sources.get(e.source_id,e.source_after_revision)
                except (KeyError,IndexError):
                    raise ValueError('SOURCE R references missing source_after revision') from None
                source_r_floor[e.source_id]=e.source_after_revision

    # D/L is one integrated information-flow lifecycle.  Capability alone does
    # not prove actual isolation, and L2/L3 packets must be real indexed
    # artifacts. Execution and reintegration must be clock-state bound.
    for item in dstore.items:
        iso=dstore.isolation(item.isolation_receipt_id)
        if iso.L_target!=1:
            raise ValueError('Alpha 9 D isolation must use internal L1')
        if iso.L_actual is not None and iso.L_actual>=2:
            ws.require_indexed_artifact(iso.input_packet_ref,kind='d-input-packet')
        if iso.output_packet_ref is not None:
            ws.require_indexed_artifact(iso.output_packet_ref,kind='d-output-packet')

        for de in item.execution_events:
            if de.clock_event_ref is None or de.clock_event_ref not in clock_hashes:
                raise ValueError('D execution lacks valid clock journal binding')
            ce=clock_hashes[de.clock_event_ref]
            if ce.event not in ('STATE','WORK_LEASE_OPEN'):
                raise ValueError('D execution must bind a foreground STATE/WORK_LEASE_OPEN clock event')
            if iso.mode=='exclusive' and ce.state is not WorkState.D_EXCLUSIVE:
                raise ValueError('exclusive D execution is not bound to D_EXCLUSIVE state')
            if iso.mode=='background' and ce.state not in (WorkState.MAIN,WorkState.SOURCE):
                raise ValueError('background D execution is not bound to MAIN/SOURCE state')

        for result in item.results:
            if result.clock_event_ref is None or result.clock_event_ref not in clock_hashes:
                raise ValueError('D result lacks valid clock journal binding')
            rce=clock_hashes[result.clock_event_ref]
            if rce.event not in ('STATE','WORK_LEASE_OPEN'):
                raise ValueError('D result must bind a foreground STATE/WORK_LEASE_OPEN clock event')
            if iso.mode=='exclusive' and rce.state is not WorkState.D_EXCLUSIVE:
                raise ValueError('exclusive D result is not bound to D_EXCLUSIVE state')
            if iso.mode=='background' and rce.state not in (WorkState.MAIN,WorkState.SOURCE):
                raise ValueError('background D result is not bound to MAIN/SOURCE state')
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
            if ce.event not in ('STATE','WORK_LEASE_OPEN') or ce.state is not WorkState.MAIN:
                raise ValueError('D reintegration must bind MAIN foreground work')

    for scope in est.scopes:
        x=est.latest(scope)
        if x.strategy_revision is not None and x.strategy_revision>=len(strategy.items):
            raise ValueError('EST references missing strategy revision')
        if x.candidate_revision is not None and x.candidate_revision>=len(candidates.items):
            raise ValueError('EST references missing candidate revision')

    brief_stale=False
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
        try:
            verify_run_brief(ws,brief_expected)
        except (ValueError,KeyError,TypeError):
            # run-brief is explicitly derived/cache state.  Recovery may rebuild
            # it after authoritative stores have verified.
            brief_stale=True

    summary_path=ws.path('final/run-summary.json')
    if phase.phase is RunPhase.FINISHED and not summary_path.is_file():
        raise ValueError('FINISHED run missing final/run-summary.json')
    if summary_path.is_file():
        if phase.phase not in (RunPhase.FINALIZING,RunPhase.FINISHED):
            raise ValueError('final summary exists before FINALIZING')
        if not timeline.finished:
            raise ValueError('final summary exists without committed FINISH')
        if contract is None or u0 is None:
            raise ValueError('final summary requires U0/contract')
        summary=ws.read_json('final/run-summary.json')
        actual=_derived_actuals(events,sources,activity,dstore,timeline)
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
        if not expected['delivery_ready']:
            raise ValueError('persisted final summary is not delivery-ready')

    return {
        'run_id':run_id,'workspace':str(ws.root),'phase':phase.phase.value,
        'journal_events':len(journal.events),'formal_T_ns':formal_T_ns,'formal_t_ns':formal_t_ns,
        'event_count':len(events.events),'strategy_revisions':len(strategy.items),
        'candidate_revisions':len(candidates.items),'source_count':len(sources.states),
        'D_completed':dstore.completed_count,'artifact_count':len(ws.artifact_records()),
        'integrity_ok':True,'run_brief_stale':brief_stale,
        'hard_continuity_after_recovery':'must_be_reestablished_by_resume',
    }
