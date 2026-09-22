# Run Session, External Memory and Cross-Host Continuity

A live run follows the reliability lifecycle:

GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED

ABORTED is terminal. These phases are reliability facts and do not plan task work.

Alpha 7 adds a persisted **work lease** for host/process boundaries. Before substantive MAIN, SOURCE or D_EXCLUSIVE work leaves the runtime process for another host tool, connector or process, the current formal state may open one WORK_LEASE_OPEN event in the hash-chained clock journal. That lease authorizes exactly the current state to remain attributable across the next verified same-boot resume boundary.

On resume:
- a valid lease plus trusted clock bridge restores the same formal state and charges the cross-host interval to that state;
- SOURCE also restores its active_source_ids binding;
- without a lease, the boundary is not guessed. The un-attributable formal interval becomes a persistent **coverage gap** rather than disappearing.

A coverage gap is evidence, not an error-recovery deletion. Hard T/t cannot be declared verified while relevant coverage is incomplete.

Workspace journals/stores remain authoritative across model/tool process changes. Strategy remains native and mutable; commitments and persisted facts remain frozen/auditable.

