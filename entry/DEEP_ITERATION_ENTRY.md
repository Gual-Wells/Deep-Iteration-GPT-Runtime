# DIGR 5.0.0-alpha.9 — Deep Iteration Entry

This entrypoint becomes active only after the exact P_run runtime package and full entrypoint/core set were verified before Genesis and the born run persisted that receipt.

## Authority
P_run, raw-message binding, U0 and Effective Contract remain immutable. P_target cannot rebind the run.

## Execution integrity
Operate declared implementations directly. One verified package/executor attestation covers ordinary helper calls until identity changes or actual execution fails.

## Post-Genesis
Genesis has no mandatory repository/network dependency behind it. Resolve parameters, freeze U0, semantically complete missing N/T/R/n/t/r/s, decide SourceDisposition, freeze contract, then enter MAIN. B/b default to soft (0); explicit B=1/b=1 remains strict hard timing.

## Work semantics
N counts meaningful MAIN evolution. SourceDisposition is REQUIRED unless waived. R/r challenge the current result and cannot move backward. D is a completed/reintegrated minimum, uses internal L1, and D_EXCLUSIVE counts T not t.

## Multi-epoch formal time
T = MAIN + SOURCE + D_EXCLUSIVE; t = SOURCE. Hard actuals sum individually hard-verifiable counted intervals. A same-epoch work lease may bridge host boundaries. If clock continuity changes, prior verified intervals survive, the cross-epoch gap receives no credit, a new trusted epoch starts, and leased work may resume from that point.

## Persistence
Authoritative journals/revisions stay on the hot path. run-brief/latest derived views may lag until checkpoints and are rebuildable.

## Finalization
Mechanical minima and semantic completion remain necessary. finish_time admits before FINISH; FINISH is durable and never reopens.
