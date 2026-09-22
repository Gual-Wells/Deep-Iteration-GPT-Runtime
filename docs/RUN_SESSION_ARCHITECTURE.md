# Run Session Architecture — Alpha 7

The authoritative lifecycle remains:

`GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED`

`ABORTED` is terminal. The lifecycle records reliability state; it does not choose task strategy.

## Startup and contract

GENESIS requires trusted clock readiness. Parameter resolution remains blocked until a verified `ExecutingProtocolLoadReceipt` binds the complete pinned execution protocol to the born run.

Alpha 7 public contract fields are N/T/R/B, S(n,t,r,b), D(s), SourceDisposition and any waiver reason. Public L is removed. D isolation uses internal fixed L1 and is not part of parameter resolution, semantic completion, stop gates or canonical proof.

## Formal execution

The first formal state after contract freeze is MAIN, so Strategy Genesis is charged as task work. SOURCE requires real SourceWorkspace bindings. D_EXCLUSIVE requires a decreed D intervention under the internal L1 isolation receipt.

Formal T includes MAIN, SOURCE and D_EXCLUSIVE. t includes SOURCE only.

## Cross-host continuity

`LiveDIGRRun.open_work_lease()` persists `WORK_LEASE_OPEN` while the current formal state is active.

When `resume()` proves a same-provider, same-nonempty-boot bridge:

- a leased MAIN/SOURCE/D_EXCLUSIVE state is restored automatically;
- SOURCE restores active_source_ids;
- the cross-host interval remains attributable to that formal state;
- an unleased formal boundary becomes a persistent coverage gap instead of being dropped.

Recovery re-derives both intervals and gaps from the journal. Hard timing cannot pass while relevant coverage is incomplete.

## Semantic receipts

Event v2 may bind either a foreground STATE receipt or a foreground WORK_LEASE_OPEN receipt. MAIN receipts require MAIN; SOURCE receipts require SOURCE plus an active source revision/binding.

D execution remains clock-bound to the appropriate foreground state. Reintegration remains MAIN work.

## Finalization admission

Alpha 7 does not close the ledger first and check later.

`finish_time(at)` first creates a non-mutating projected finish and derives prospective actuals. Finalization admission requires semantic completion readiness plus all applicable mechanical minima, hard timing and coverage gates.

If admission fails, the run remains EXECUTING and the ledger remains open.

Only an admitted run closes formal timing, appends FINISH and enters FINALIZING. `write_run_summary()` refuses FINISHED unless delivery readiness is true.

A terminal FINISHED/ABORTED run cannot be resumed as active execution.

