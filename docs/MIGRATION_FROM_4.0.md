# Migration from DIGR 4.0 to 4.1

## Retained
Result Sovereignty, Task Commitment, U0, semantic partial-parameter completion, Effective Contract, N/R/S, EST, ABG, D(s), L(e), Formal Active Time, hard verification, source aggregation, isolation evidence, canonical proof, strict schemas and deterministic release validation.

## Removed
- root `DIGR_EXECUTION_GATE.md`;
- `bootstrap/REPOSITORY_ONLY_LOADER.md`;
- `runtime/bootstrap_gate.py` and bootstrap-gate schema;
- local personalization rules for universal clock, P_target, help, no-fallback and other versioned semantics;
- the requirement that an older repository version must contain a future root gate before it can become P_run.

## Added
- minimal Reliable Routing Plane;
- pinned manifest discovery with `bootstrap_entry` and legacy entry/core compatibility;
- route receipt + manifest digest;
- repository-delegated semantic authority;
- explicit RouteFailure vs ProtocolStartupFailure distinction;
- 4.1 repository bootstrap containing the mandatory executing-task clock rule;
- protocol-semantic provenance invariant (`Context !-> ProtocolSemantics`) while preserving context→U0/evidence;
- deterministic standalone personalization export from the exact ZIP-internal source bytes.

## Cutover
The 4.1 router can be installed even while `stable` is the current legacy 3.0 repository because it does not demand a 4.1 root gate. It routes to 3.0's manifest-declared entry/core **without importing 4.1 semantics**, then obeys 3.0. After stable moves to 4.1, the same router discovers `bootstrap_entry` and obeys 4.1.
