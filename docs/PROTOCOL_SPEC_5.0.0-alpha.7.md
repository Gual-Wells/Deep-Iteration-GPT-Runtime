# DIGR 5.0.0-alpha.7 — Formal-Time Continuity / Internal L1

Alpha 7 preserves Alpha 6 repository authority, execute-before-interpret integrity, execution commitment, and same-commit runtime-delivery semantics. It repairs a separate production failure class: substantive work performed across ChatGPT host/tool boundaries could be real task work but remain uncounted because the formal ledger only observed the short local runtime segments around tool calls.

## 1. Observed failure class

A DIGR run could correctly enter MAIN or SOURCE, leave the Python/runtime process to perform substantive GitHub/Web/connector work, then resume later. Alpha 6 intentionally dropped the unclosed semantic tail at resume because it could not prove what happened during the process gap.

That fail-closed rule protected against false timing, but on hosts where external tools are the actual execution surface it systematically under-counted real work. A multi-minute source investigation could therefore contribute only milliseconds to formal t/T. The same structural problem also affected cross-host MAIN and D work.

A second lifecycle defect followed from the same boundary: final timing could be closed before the runtime had checked whether the projected finished run actually satisfied hard timing and delivery readiness. Once the ledger was closed, the run no longer had a clean way to continue accumulating required formal time.

## 2. Work lease

Alpha 7 adds a persisted, hash-chained WORK_LEASE_OPEN event to the authoritative clock journal.

A lease means: the currently active MAIN, SOURCE, or D_EXCLUSIVE state is intentionally continuing across the next host/process/tool boundary. It must be persisted before leaving the runtime.

On verified same-provider / same-nonempty-boot resume:

- a valid lease restores the same formal work state;
- the cross-host interval remains attributable to that state;
- SOURCE leases also restore active_source_ids;
- the resumed runtime appends a fresh STATE receipt after the resume readiness sequence.

A lease is not a generic wall-clock charging mechanism. It is legal only when substantive work in the same known semantic state is actually continuing. META, IDLE, waiting, padding, or unknown activity must not be leased as task work.

## 3. Coverage gaps

An unleased formal boundary is never silently deleted in Alpha 7.

If a MAIN/SOURCE/D_EXCLUSIVE state was open when a host/process boundary occurs without a valid lease, the clock journal derives an explicit CoverageGap for the unattributed interval. The runtime does not guess whether that interval was work or idle.

This separates three facts:

- observed monotonic duration;
- hard clock continuity;
- semantic-time coverage.

For B=1 or b=1, hard timing requires both clock verification and complete relevant coverage. A measurable but unattributed gap therefore prevents the runtime from claiming a hard-verified T/t actual.

## 4. D time semantics

D_EXCLUSIVE is substantive task work in Alpha 7.

Formal timing is now:

- T = MAIN + SOURCE + D_EXCLUSIVE
- t = SOURCE
- META and IDLE do not count

This removes the previous inconsistency where disruptive work could consume substantial task effort while remaining outside T.

## 5. Public L removal

L is removed from the user parameter surface, semantic completion, Effective Contract, stop gates, and canonical proof.

D uses an internal fixed L1 semantic-isolation baseline. The runtime may retain isolation receipts and capability evidence as implementation/audit structure, but Alpha 7 requires the intervention target used by the run session to be L1. Host capability does not silently upgrade a user-visible isolation level because no public L level exists.

Invocations containing L/L()/L=... are INVALID.

Canonical proof therefore becomes:

DIGR(N_target/N_actual, T_target/T_actual, R_target/R_actual, B,
     S_i(n_target/n_actual, t_target/t_actual, r_target/r_actual, b),
     D(target)/D(actual))

## 6. Finalization admission

Alpha 7 moves the stop check before irreversible timing closure.

finish_time first projects a finish at the supplied trusted snapshot without mutating the live ledger. The projected actuals are checked against:

- N/R/n/r/D minima;
- B/b hard timing;
- semantic-time coverage;
- SourceDisposition semantics;
- semantic completion readiness.

If admission fails, the run stays EXECUTING and the live ledger remains open.

Only an admitted run may:

1. close the formal ledger;
2. append FINISH;
3. enter FINALIZING;
4. persist the final run summary;
5. transition FINISHED.

A FINISHED summary with delivery_ready=false is invalid.

## 7. Host integration rule

On hosts such as ChatGPT where repository/runtime code and external tools execute through different host channels, the required operational sequence for substantive cross-host work is:

active formal state
→ persist WORK_LEASE_OPEN
→ perform the external tool/connector work
→ verified same-boot resume
→ automatic state restoration
→ continue receipts / transitions

For SOURCE, the SourceWorkspace(s) must already exist and be active before the lease is opened.

Performing the tool work first and entering SOURCE only afterwards does not retroactively attribute the earlier interval.

## 8. Compatibility

Alpha 7 intentionally changes the public protocol surface:

- parameter-resolution schema: 2
- run-session schema: 5
- public L removed
- D_EXCLUSIVE now contributes to T

Workspace schema and clock-journal event schema remain at their existing versions because WORK_LEASE_OPEN uses the existing generic journal event/state representation and coverage is derived rather than stored as a new standalone workspace artifact.

Alpha 6 implementation-execution integrity and same-commit runtime-delivery behavior remain mandatory and unchanged.
