"""Derive DIGR 5.0 Alpha 2 mechanical actuals from bound run facts."""
from __future__ import annotations
from dataclasses import dataclass
from .clock_journal import ClockJournal
from .d_intervention import DInterventionStore
from .evolution_events import EvolutionEventLog, EvolutionKind
from .interval_ledger import FormalTimeLedger, WorkState
from .source_workspace import SourceActivityLog, SourceWorkspaceRegistry
from .stop_checks import ContractActuals


@dataclass(frozen=True)
class ActualsProvenance:
    N: str = 'event-v2-bound'
    R: str = 'candidate-backed-reentry'
    S: str = 'revisioned-workspace+event-v2'
    D: str = 'completed-intervention+reintegration'
    time: str = 'clock-journal+formal-ledger'
    source_time: str = 'clock-ledger+active-source-binding'
    L: str = 'intervention-isolation-receipt'
    quality: str = 'semantic-assessment'


def _verify_source_time_binding(journal: ClockJournal, source_activity: SourceActivityLog,
                                sources: SourceWorkspaceRegistry) -> None:
    """Require every SOURCE start to name at least one existing S workspace.

    The formal duration remains the clock-ledger union, so parallel S instances
    never double count. This function establishes that each SOURCE interval is
    semantically attached to real source work rather than a free-floating state.
    """
    known = {s.source_id for s in sources.states}
    bindings = source_activity.by_clock_ref()
    source_start_refs = [
        e.record_hash for e in journal.events
        if e.event == 'STATE' and e.state is WorkState.SOURCE
    ]
    for ref in source_start_refs:
        ids = bindings.get(ref)
        if not ids:
            raise ValueError('SOURCE clock state lacks active-source binding')
        if any(x not in known for x in ids):
            raise ValueError('SOURCE activity references an unknown source workspace')
    extra = set(bindings) - set(source_start_refs)
    if extra:
        raise ValueError('source activity references a non-SOURCE clock event')


def _verify_semantic_clock_bindings(events: EvolutionEventLog, journal: ClockJournal,
                                    source_activity: SourceActivityLog,
                                    sources: SourceWorkspaceRegistry) -> None:
    """Verify the timing/scope facts used by mechanical event actuals.

    LiveDIGRRun wrappers normally enforce these facts when receipts are written,
    but actual derivation is a trust boundary of its own. A forged/private-log
    mutation must not inflate N/R/S merely because its hash chain is internally
    valid.
    """
    clocks={e.record_hash:e for e in journal.events}
    active=source_activity.by_clock_ref()
    known={s.source_id for s in sources.states}
    for e in events.events:
        ce=clocks.get(e.clock_event_ref)
        if ce is None or ce.event!='STATE':
            raise ValueError('semantic actual requires a valid foreground STATE clock binding')
        if e.kind in (EvolutionKind.MAIN_EVOLUTION,EvolutionKind.MAIN_REENTRY):
            if ce.state is not WorkState.MAIN:
                raise ValueError('MAIN semantic actual is not bound to MAIN work')
            continue
        if ce.state is not WorkState.SOURCE:
            raise ValueError('SOURCE semantic actual is not bound to SOURCE work')
        if e.source_id not in known or e.source_id not in active.get(e.clock_event_ref,()):
            raise ValueError('SOURCE semantic actual is not bound to an active source workspace')
        try:
            sources.get(e.source_id,e.source_revision)
            if e.source_after_revision is not None:
                sources.get(e.source_id,e.source_after_revision)
        except (KeyError,IndexError):
            raise ValueError('SOURCE semantic actual references a missing source revision') from None


def _verify_ledger_journal_parity(ledger: FormalTimeLedger, journal: ClockJournal) -> None:
    from .clock_journal import derive_work_intervals
    derived=derive_work_intervals(journal.events)
    lhs=[(x.state,x.start.monotonic_ns,x.end.monotonic_ns,x.observed_ns,x.hard_verified) for x in ledger.intervals]
    rhs=[(x.state,x.start.monotonic_ns,x.end.monotonic_ns,x.observed_ns,x.hard_verified) for x in derived]
    if lhs!=rhs:
        raise ValueError('formal ledger / clock journal interval drift')


def derive_contract_actuals(events: EvolutionEventLog,
                            sources: SourceWorkspaceRegistry,
                            source_activity: SourceActivityLog,
                            d_store: DInterventionStore,
                            ledger: FormalTimeLedger,
                            journal: ClockJournal) -> ContractActuals:
    events.verify(); source_activity.verify(); _verify_source_time_binding(journal, source_activity, sources)
    _verify_semantic_clock_bindings(events,journal,source_activity,sources)
    _verify_ledger_journal_parity(ledger,journal)
    # A SourceWorkspace is only an external-research actual when it is both
    # attached to real SOURCE-clock activity and has at least one semantic
    # source-work receipt. Merely opening S1 must never satisfy the default
    # Source Presumption.
    known_ids = {s.source_id for s in sources.states}
    active_ids = {sid for item in source_activity.items for sid in item.source_ids}
    semantic_ids = {
        e.source_id for e in events.events
        if e.kind in (EvolutionKind.SOURCE_EVOLUTION, EvolutionKind.SOURCE_REENTRY)
        and e.source_id is not None
    }
    source_ids = sorted(known_ids & active_ids & semantic_ids)
    n_values = [events.count(EvolutionKind.SOURCE_EVOLUTION, f'S:{sid}') for sid in source_ids]
    r_values = [events.count(EvolutionKind.SOURCE_REENTRY, f'S:{sid}') for sid in source_ids]
    return ContractActuals(
        N=events.count(EvolutionKind.MAIN_EVOLUTION, 'MAIN'),
        T_seconds=ledger.formal_T_ns()/1e9,
        T_hard_verified=ledger.T_hard_verified(),
        R=events.count(EvolutionKind.MAIN_REENTRY, 'MAIN'),
        S_count=len(source_ids),
        n_min=min(n_values) if n_values else 0,
        t_seconds=ledger.formal_t_ns()/1e9,
        t_hard_verified=ledger.t_hard_verified(),
        r_min=min(r_values) if r_values else 0,
        D_s=d_store.completed_count,
        L_e=d_store.actual_isolation_level,
    )
