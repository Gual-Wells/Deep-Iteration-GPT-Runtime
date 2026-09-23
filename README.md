# Deep Iteration GPT Runtime (DIGR) 5.0.0-alpha.10

**Status:** liveness-contraction candidate on `alpha10-liveness-contraction`; stable promotion is separate.

Alpha 10 is designed around one practical requirement: **ordinary DIGR tasks must be able to finish**. It keeps authority/evidence guarantees that protect result correctness, while removing repeated full-history and per-helper work from the normal path.

## Contracted execution path

```text
stable → immutable SHA
  → manifest / VERSION / INDEX / STARTUP
  → one pinned runtime-package verifier
  → one recursive pinned Git tree + one exact-commit runtime archive
  → package attestation
  → compact execution bundle (entrypoint + 7 core modules)
  → protocol receipt
  → Clock Genesis
  → contract
  → native task work
  → FINISH
```

Key changes from Alpha 9:

- execution authority contracts from 18 core modules to 7;
- package-level attestation replaces per-helper fetching/interrogation;
- normal resume skips full workspace audit and loads stores once;
- journal index refresh is batched;
- latest Strategy/Candidate/Source/D/EST/phase/run-brief files are unindexed caches;
- STATE/WorkLease no longer trigger a global checkpoint;
- omitted D defaults to 0;
- SourceDisposition is decided by task necessity instead of blanket REQUIRED;
- completed D can use one compact lifecycle revision instead of five or more persistence stages;
- full audit and granular histories remain available for anomalies or when they add real value.

B/b remain soft by default. Multi-epoch timing, current-result R/r, D reintegration and durable FINISH remain intact.

## Development validation

Tests and CI are regression guards, not the architecture proof. The release is first reviewed structurally from startup through finish and recovery, then the deterministic suite is used to catch implementation drift.
