# DIGR 5.0 Alpha 10 Architecture

Alpha 10 is a liveness contraction: keep semantic guarantees, remove repeated reliability work.

## Normal path
`stable→SHA → manifest/VERSION/INDEX/STARTUP → one package attestation → compact protocol load → clock Genesis → contract → native work → FINISH`

The package attestation uses one pinned verifier, one recursive pinned Git tree and one exact-commit runtime archive. It replaces per-helper fetching/interrogation.

Execution authority is entrypoint + seven core modules. Deterministic helpers remain implementation, not model reasoning.

## Persistence
Authoritative revisions/journals persist incrementally. Latest pointers/run-brief are unindexed caches. STATE/WorkLease do not trigger global checkpoints. Journal index refresh is batched.

## Resume
Ordinary resume repairs pending write, verifies/reindexes journals once, loads stores once, and resumes/re-epochs the clock. Full workspace audit is reserved for anomaly recovery or explicit audit.

## Workload
B/b default soft. Omitted D=0. Source is REQUIRED only by task necessity. Compact D lifecycle is preferred.

The architecture target is constant/coarse reliability overhead per meaningful boundary, not repeated full-history verification.
