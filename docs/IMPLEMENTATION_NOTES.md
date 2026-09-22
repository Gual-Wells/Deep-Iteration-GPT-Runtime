# Alpha 8 Implementation Notes

Alpha 8 is a convergence/recovery release over Alpha 7 rather than a new task-control layer.

## Timing

T counts MAIN + SOURCE + D_EXCLUSIVE; t counts SOURCE. B/b=1 proves a **lower bound over counted hard-verifiable intervals**. Unleased gaps remain recorded but are excluded from the number, so they cannot inflate a hard minimum. Complete coverage is audit information rather than a separate delivery gate.

SourceDisposition=WAIVED makes all source mechanical gates non-applicable, including t/hard-t even when the structural default b remains 1.

## Re-entry and D

Retained MAIN/source re-entry must bind the current result revision. Changed re-entry must end at the current revision and persisted R/r history cannot move backward behind a prior result.

Exclusive D execution and D Result production both remain in D_EXCLUSIVE; only reintegration returns consequences to MAIN. Public L stays removed; internal L1 is the only active isolation baseline.

## Crash recovery

RunWorkspace uses a single-slot write-intent around ordinary artifact writes. On resume, deterministic recovery may complete/roll back that write, verify and re-index append-only journals, and rebuild derived latest pointers from immutable revision history.

run-brief is a cache and no longer has authority to invalidate an otherwise consistent workspace.

FINISH is a durable commit point. If a crash occurs after FINISH but before phase=FINALIZING, resume restores a finished ledger and completes the missing phase transition. A valid final summary written before phase=FINISHED is likewise recoverable.

## Release safety

Release cleanup excludes .git from package traversal but never deletes repository metadata. CI must compare regenerated bundle/tree/hash metadata with committed stable contents rather than silently validating a repaired temporary copy.

## Inherited integrity

Alpha 6 implementation-identity delivery remains active: exact pinned helpers must be executed when available, and semantic-equivalent model rewrites are not substitutes. Alpha 8 does not add another cognitive gate around every helper call.

