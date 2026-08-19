# Run Session Architecture v2

RunPhase is the authoritative lifecycle: GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED, with ABORTED available from nonterminal phases. It validates legal persistence/lifecycle operations only; it does not choose task strategy. CONTRACT_FROZEN cannot skip directly to FINALIZING: real task work begins in MAIN/EXECUTING.

`LiveDIGRRun` owns thin semantic wrappers for event receipts, SOURCE transitions with active-S binding, D packet/isolation/execution/reintegration binding, final timing parity and recovery/resume. Strategy/Candidate/EST/Source/D/Completion stores remain explicit and revisioned.

Semantic Event v2 binds a real foreground STATE clock event plus Strategy context. MAIN events must bind MAIN; SOURCE events must bind SOURCE plus an active source and valid Source revision. MAIN R uses Candidate before/after; S-r uses SourceWorkspace before/after.

D execution is clock-bound to D_EXCLUSIVE or supported background MAIN/SOURCE. L2/L3 Input/Output Packets are indexed artifacts. Reintegration is clock-bound MAIN work. Final synthesis must return to MAIN before `finish_time`; closing formal timing transitions to FINALIZING and no later task analysis is allowed outside the ledger.

Artifact index detects byte drift, but recovery also rederives semantics. Run Brief is a derived cache whose digest and authoritative fields are checked. A FINISHED run's summary is independently rebuilt from the authoritative stores/journals and compared. Resume additionally proves a fresh clock bridge; a terminal FINISHED/ABORTED run cannot be resumed as active execution.
