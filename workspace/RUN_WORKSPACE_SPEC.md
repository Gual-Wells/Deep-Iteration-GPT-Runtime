# DIGR 5.0 Alpha 10 Run Workspace

Genesis is created only after package/protocol readiness and therefore includes `protocol-load.json` from birth.

## Authority vs cache
Immutable revision files and append-only journals are authoritative. These latest views are rebuildable caches and are intentionally **not** members of the global artifact integrity index:
- state/run-brief.json
- state/strategy-latest.json
- state/candidate-latest.json
- state/run-phase.json
- state/est-*-latest.json
- sources/*/state.json
- dictator/<intervention>.json

They are atomically replaceable and may lag; recovery can rebuild them from authoritative revisions.

## Normal hot path
Semantic events append their own durable journal/revision record. STATE transitions and WorkLease records do not trigger a global checkpoint. Journal artifact-index refresh is batched.

## Resume
Ordinary resume uses fast recovery. Full revision-tree repair and full workspace verification run only after a detected inconsistency or explicit audit request.

## Finalization
FINISH remains the durable timing commit and never reopens.
