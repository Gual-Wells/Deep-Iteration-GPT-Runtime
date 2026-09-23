# DIGR 5.0 Alpha 9 Run Workspace

`workspace/layout-v2.json` remains authoritative.

Genesis occurs only after complete execution-protocol verification. Every newborn Alpha 9 workspace therefore includes `protocol-load.json` from its first durable run state.

## Authority versus cache

Immutable revision files and append-only verified journals are authoritative persisted history. Latest pointers and `state/run-brief.json` are derived convenience views.

Alpha 9 explicitly allows derived views to lag between coarse checkpoints. A semantic evolution, source, R or D event is not required to synchronously rewrite run-brief. Recovery verifies authoritative stores/journals first and may rebuild stale caches afterward.

## Crash-safe writes

Ordinary workspace JSON/text writes retain the single-slot `state/workspace-write-intent.json` protocol. Recovery may complete indexing when intended content is present, roll back when prior content remains, and fail closed on third-state content.

Append-only clock/source/event journals may refresh artifact-index digests only after their own chain verification succeeds.

## Clock epochs

A clock journal may contain multiple trusted epochs. A cross-epoch discontinuity is recorded as a continuity gap with no guessed duration. It does not invalidate the workspace, the run, or verified intervals from other epochs.

## Finalization

FINISH is the durable timing commit. Recovery may complete subsequent lifecycle writes but may not reopen formal timing.
