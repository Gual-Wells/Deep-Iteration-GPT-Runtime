# Run Session, Lifecycle, Workspace and Recovery

Berta1 performs broad candidate transport, verifies pinned manifest/VERSION and loads pinned STARTUP before classification. EXECUTING then resolves parameters, negotiates capability and verifies required execution artifacts before Genesis. Clock Genesis creates the workspace only after those gates succeed, and the exact preflight parameters are persisted without re-resolution.

The lifecycle is `GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → DELIVERED | INCOMPLETE`; `ABORTED` is reachable from nonterminal phases. `FINISHED` is readable only for legacy recovery and MUST NOT be created by Berta1.

`DELIVERED` means exact final bytes, media type, current Candidate binding, summary, proof data and envelope completed a two-phase fail-closed preparation/verification commit. A pre-transition crash remains non-success and is recoverable. `INCOMPLETE` is closed with explicit unmet gates and cannot render canonical proof.

Workspace artifacts record pinned authority, exact task binding, parameters, capabilities, clock facts, revisioned strategy/candidate/source/D/V/completion state, evidence, local audit logs and delivery. Recovery verifies artifact digests and lifecycle history. Host persistence mechanisms never choose intellectual strategy.
