# Run Session, Lifecycle, Workspace and Recovery

Alpha 2 has one authoritative persisted lifecycle: `GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED`, with `ABORTED` reachable from any nonterminal phase. Phase checks prevent lifecycle writes in the wrong order; they do not plan task work.

The workspace persists authority, invocation, startup, parameter resolution, U0, contract, clock/source-activity/event journals, revisioned strategy/candidate/EST/source/D/completion state, evidence, run brief and final summary. `state/artifact-index.json` stores path/revision/digest metadata so recovery can detect mixed revisions or accidental overwrites.

`state/run-brief.json` is a compact derived cache: U0 digest, contract presence, current strategy/candidate revisions, active S IDs, D/completion/evidence/event references. It is never a second truth source.

Recovery first verifies the complete persisted workspace and cross-references. `LiveDIGRRun.resume()` then takes at least three new clock samples. Cross-process/session continuity is accepted only when provider matches and both sides carry the same non-empty boot identity. If that cannot be proven, do not fabricate continuity or hard elapsed time. A valid resume appends `RESUME_*` journal facts and continues from authoritative persisted state.
