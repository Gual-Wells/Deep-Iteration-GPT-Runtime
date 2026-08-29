# Run Session, Lifecycle, Workspace and Recovery

Berta2 acquires pinned STARTUP before classification. For EXECUTING, it structurally validates parameters and verifies the exact execution set before publishing a born run. Clock Genesis and protocol binding precede native completion of missing values; the one completed receipt is then persisted, followed by exact U0 and Effective Contract.

Lifecycle is `GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → DELIVERED | INCOMPLETE`; ABORTED is terminal. FINISHED is legacy-read-only.

Workspace stores authority, exact task binding, completed parameters, execution/attestation facts, clock evidence, revisioned strategy/candidate/source/D/V/completion state, audit logs and delivery artifacts. Recovery verifies indexed bytes plus semantic cross-bindings.

Berta2 canonical terminal states carry a final mutation seal. DELIVERED also binds a digest of semantic state and audit records, excluding self-referential terminal wrappers. All workspace API mutations are rejected after the seal. Read-only recovery recognizes earlier preflight version families but never silently upgrades their proof format.

Host persistence records facts; it does not choose task strategy. MODEL_NATIVE can execute without this workspace, but must label unavailable receipts/actuals non-canonical.
