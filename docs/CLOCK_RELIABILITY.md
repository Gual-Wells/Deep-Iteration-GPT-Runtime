# Clock Reliability — Alpha 7

Clock Genesis remains mandatory for every EXECUTING run: at least three compatible monotonic samples are established before parameter resolution, U0 or substantive task work. The append-only clock journal remains hash-chained and records provider/session/boot identity, monotonic/wall readings, event type and semantic work state.

Alpha 7 separates three timing facts that earlier versions partially conflated:

1. **Observed duration** — monotonic elapsed time between trusted snapshots.
2. **Hard clock continuity** — the elapsed interval is verifiable under the provider/boot continuity rules.
3. **Semantic-time coverage** — the runtime can attribute the interval to MAIN, SOURCE, D_EXCLUSIVE, META or IDLE without guessing.

Hard timing requires both hard clock continuity and complete relevant semantic coverage.

## Cross-host work leases

ChatGPT-style hosts often execute repository runtime code in one process and substantive Web/GitHub/connector work in another. Before known substantive MAIN, SOURCE or D_EXCLUSIVE work leaves the runtime process, Alpha 7 may persist a `WORK_LEASE_OPEN` journal event.

A valid work lease carries the currently active semantic state across exactly the next verified resume boundary. Resume still requires a fresh >=3-sample bridge whose provider and non-empty boot identity prove continuity. After that bridge, the leased state is restored with a new STATE receipt.

For SOURCE, the lease also preserves the active source-workspace binding so that external source-tool time contributes to both T and t.

## Coverage gaps

If formal work crosses a process boundary without a valid lease, Alpha 7 does not silently erase the interval and does not guess its state. The journal derives a `CoverageGap` from the last attributable snapshot to the resume anchor.

A relevant coverage gap makes hard T/t unverifiable. Soft timing may still expose observed attributable time, but hard proof cannot claim a duration whose semantic timeline is incomplete.

## Formal accounting

- T = MAIN + SOURCE + D_EXCLUSIVE
- t = SOURCE
- META and IDLE do not count
- parallel sources share the SOURCE time union and never multiply t

D_EXCLUSIVE now counts T because disruptive execution is substantive task work.

Sleep, deliberate waiting, logging, repeated mechanical query or padding must not be turned into formal time merely by opening a lease. A lease is an attribution mechanism for genuine ongoing work, not permission to charge arbitrary wall-clock occupancy.

