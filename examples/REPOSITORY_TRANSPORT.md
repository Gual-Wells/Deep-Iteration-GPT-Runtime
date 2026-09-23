# Repository transport example — Alpha 10

Connected GitHub route:

```text
stable branch HEAD → immutable SHA
manifest + VERSION
bootstrap/INDEX.md + remaining startup slice
EXECUTING
recursive Git tree (one acquisition)
runtime/runtime_package.py (one pinned verifier bridge)
exact-commit runtime archive
one package attestation
verified compact execution bundle
Clock Genesis
```

The verifier proves every packaged helper and every bundle member against the pinned Git tree. The host does not fetch 30+ helpers individually.

Direct REST uses branch/ref consensus for the mutable stable pin, then the same immutable flow.
