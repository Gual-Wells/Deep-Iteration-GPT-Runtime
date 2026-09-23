# 25 — Run Session, Persistence and Recovery

Lifecycle remains:
GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED.
ABORTED and FINISHED are terminal.

## Hot path
Authoritative append-only journals and immutable semantic revisions persist. Rebuildable latest pointers and run-brief are caches; updating them must not rewrite the global integrity index.

A STATE transition or WorkLease append is already durable and must not automatically trigger a global checkpoint.

## Ordinary resume
Normal resume is:
1. repair an interrupted transactional write if present;
2. self-verify and reindex append-only journals in one batched index update;
3. load required stores once;
4. re-establish same clock epoch or open a new trusted epoch.

It does **not** run full workspace audit first.

If this fast path detects structural inconsistency, fall back to full recovery + full verification. Full audit is therefore exceptional, not a routine host-boundary tax.

WorkLease is optional and exists for formal-time attribution across a real boundary. Soft timing alone is not a reason to open one.

Committed FINISH remains durable.
