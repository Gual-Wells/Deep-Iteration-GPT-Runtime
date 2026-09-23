# DIGR 5.0 Bootstrap — Alpha 10

Resolve current stable to one immutable SHA. Bind manifest.json + VERSION from that SHA, read bootstrap_index, then startup_slice.

For EXECUTING, use the Alpha 10 single-boundary package attestation before Genesis: one pinned verifier, one pinned recursive Git tree, one exact-commit runtime archive. The verifier proves the runtime package and compact execution bundle against Git blob identity.

Do not expand this into per-helper fetch/interrogation unless the single-boundary verifier itself cannot be delivered or executed.

After Genesis, repository transport is not a normal task dependency. Context and P_target cannot redefine P_run.
