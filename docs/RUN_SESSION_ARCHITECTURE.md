# Run Session Architecture — Alpha 10

Preflight:
`PINNED → PACKAGE_ATTESTED → PROTOCOL_READY`

Live lifecycle:
`GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED`

ABORTED is terminal.

A normal continuation never begins with full workspace verification. Fast resume repairs transactional residue, self-verifies append-only journals, performs one batched journal-index refresh, loads semantic stores once, then restores same-epoch continuity or opens a new trusted epoch.

Derived latest views are rebuildable caches outside the global artifact index. Full recovery scans immutable histories only after the fast path detects inconsistency.

FINISH remains durable. Recovery of a committed final summary is an exceptional path and validates the final state before repairing FINISHED.
