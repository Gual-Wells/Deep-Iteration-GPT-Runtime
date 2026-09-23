# DIGR 5.0 Alpha 9 Architecture

Alpha 9 makes liveness a first-class invariant without weakening authority.

1. Repository preflight: pin P_run, deliver/attest exact runtime package, verify complete protocol.
2. Genesis/contract: only after preflight, establish clock, persist Genesis + protocol receipt, resolve parameters and freeze U0/contract.
3. Mutable task state: Strategy, Candidate, EST, Source, D, completion.
4. Time/evidence: append-only journals, per-interval hard verification, work leases, continuity gaps across clock epochs.
5. Recovery/audit: authoritative revisions/journals plus checkpointed derived caches.

Genesis is the point after which no mandatory repository/runtime transport remains. Clock identity may change; that forfeits only the unverifiable bridge, not the run. Derived cache maintenance is not a semantic hot-path obligation.

P_run/U0/contract identity, implementation identity, evidence bindings, revision monotonicity and FINISH durability remain strict.
