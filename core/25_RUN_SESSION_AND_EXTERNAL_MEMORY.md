# 25 — Run Session, Persistence and Recovery

Lifecycle remains:
GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED.
ABORTED and FINISHED are terminal.

## Hot path
Authoritative append-only journals and immutable semantic revisions persist. Their artifact identities append to a small index-delta WAL instead of rewriting the complete artifact index per semantic write. Rebuildable latest pointers and run-brief are caches and stay outside the global integrity index.

A STATE transition or WorkLease append is already durable and must not automatically trigger a global checkpoint.

## Ordinary resume
Normal resume is:
1. repair an interrupted transactional write if present;
2. self-verify and append journal index deltas in one batched WAL write;
3. load required stores once;
4. re-establish same clock epoch or open a new trusted epoch.

It does **not** run full workspace audit first.

If this fast path detects structural inconsistency, fall back to full recovery + full verification. Full audit is therefore exceptional, not a routine host-boundary tax.

WorkLease is optional and exists for formal-time attribution across a real boundary. Soft timing alone is not a reason to open one.

Committed FINISH remains durable.

Coarse checkpoints and final delivery may compact the index-delta WAL into the base artifact index. Compaction is not a per-event obligation.
