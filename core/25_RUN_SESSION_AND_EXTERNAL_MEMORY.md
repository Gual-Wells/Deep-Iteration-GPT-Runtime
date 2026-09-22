# Run Session, External Memory and Cross-Host Continuity

A live run follows the reliability lifecycle:

GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED

ABORTED is terminal. These phases are reliability facts and do not plan task work.

A persisted **work lease** lets known MAIN, SOURCE or D_EXCLUSIVE work remain attributable across the next verified same-boot host/process boundary. SOURCE leases carry active_source_ids. A lease is useful because the bridged interval can then contribute to T/t.

If a formal boundary has no lease, the runtime does not guess. It preserves a **coverage gap** and excludes that interval from counted formal time. Because T/t are lower-bound commitments, such exclusion does not invalidate already hard-verified counted time; it only forfeits credit for that gap. Coverage completeness remains visible for audit.

Crash recovery is deterministic and conservative. A single-slot write intent repairs a file/index crash window; append-only journals may refresh their artifact-index digest only after their own chain verification; immutable revision history may rebuild stale latest pointers and the derived run brief. Recovery never invents semantic events, U0, contract decisions, Strategy content, source findings or D conclusions.

A committed FINISH journal event is itself durable. If a crash occurs before the matching FINALIZING phase write, resume reconstructs the finished ledger and advances only the missing lifecycle step. Likewise, a valid final summary written before FINISHED may be verified and completed rather than orphaning the run.

