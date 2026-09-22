# Run Session Architecture — Alpha 8

Lifecycle:

`GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED`

ABORTED is terminal. Lifecycle state is reliability metadata, not task planning.

## Execution

The first formal task state is MAIN. SOURCE requires real SourceWorkspace bindings. D uses internal L1 and exclusive execution/result production in D_EXCLUSIVE.

T counts MAIN+SOURCE+D_EXCLUSIVE; t counts SOURCE. Work leases let known cross-host intervals receive credit. Unleased gaps are retained but excluded, producing conservative lower-bound timing rather than permanent run failure.

## Persistence and recovery

Ordinary artifact writes use a single-slot write-intent around target/index commit. Append-only journals are re-indexed only after their own chain verifies. Revision files are authoritative; latest pointers and run-brief are rebuildable caches.

FINISH is the durable formal-time commit. Recovery can repair:
- EXECUTING + committed FINISH → FINALIZING;
- FINALIZING + valid final summary → FINISHED.

It cannot reopen finished timing or synthesize semantic state.

## Re-entry and D integrity

Retained R/r binds the current result revision; changed R/r ends at the current revision; persisted re-entry history cannot move backward. D execution and D Result are clock/state-bound before MAIN reintegration.

