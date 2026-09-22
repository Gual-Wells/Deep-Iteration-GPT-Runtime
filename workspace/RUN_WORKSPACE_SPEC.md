# DIGR 5.0 Alpha 8 Run Workspace

`workspace/layout-v2.json` remains the current authoritative layout. Alpha 8 changes recovery behavior without changing the persistent public layout version.

Genesis creates authority/invocation/startup, the clock journal, artifact index and RunPhase. Parameter/U0/contract artifacts appear only after their lifecycle transitions. Strategy, Candidate, EST, Source, D, completion and phase histories are revisioned.

## Authority versus cache

Immutable revision files and append-only verified journals are authoritative persisted history. Files such as strategy-latest, candidate-latest, source state.json, D latest pointers, run-phase.json, EST latest pointers and state/run-brief.json are derived convenience views.

A stale derived pointer may be rebuilt from verified revision history. A stale run-brief must never invalidate otherwise consistent authoritative state.

## Crash-safe writes

Ordinary workspace JSON/text writes use an internal single-slot `state/workspace-write-intent.json`. This file is recovery metadata and is intentionally excluded from the artifact index/layout contract.

On recovery:
- intended content present with matching digest → finish artifact-index commit;
- prior content still present → roll back the uncommitted write;
- any third content → fail closed.

Append-only clock/source/event journals are re-indexed only after their own sequence/hash verification succeeds.

## Finalization

The clock journal FINISH event is the durable formal-time commit. phase=FINALIZING and the final summary are subsequent lifecycle commits. Recovery may complete those missing writes but may not reopen formal timing.

Internal isolation packet schemas remain only for historical storage compatibility. Alpha 8 active D semantics are fixed internal L1 and do not expose L2/L3 user behavior.

