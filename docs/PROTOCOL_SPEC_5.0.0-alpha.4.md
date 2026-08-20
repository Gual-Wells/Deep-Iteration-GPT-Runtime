# DIGR 5.0.0-alpha.4 Protocol Specification Index

Normative execution semantics are the pinned `entry/DEEP_ITERATION_ENTRY.md` plus manifest `core[]`. Minimal pre-full-load behavior is the manifest `startup_slice`. `entry/HELP.md` is the canonical zh-CN user reference and does not itself start a task run.

Alpha 4 preserves the Alpha 3 authority/clock/state architecture while correcting live black-box integration defects:

- routing schema 4 + repository transport schema 3 split already-connected GitHub connector branch-head authority from direct REST branch/ref consensus, with one bounded retry for a live push race;
- run-session schema 4 preserves D as a true lower-bound mechanism and adds a post-genesis full-protocol-load barrier: `D(0)` means no required completed D, not disabled D; L applicability follows actual completed D; parameter resolution requires a persisted verified protocol-load receipt;
- execution bundle schema 1 + execution-protocol-load schema 1 aggregate physical transport while preserving logical entrypoint/core authority;
- N/R/n/r/D are unconditional minima, while T/t are frozen targets whose mechanical enforcement is controlled by B/b;
- user-visible proof must follow canonical whole-second actual-duration rendering and hard-verification hiding rules;
- Help/default/source/timing/D/L language is made explicit and canonical in zh-CN.

Repository routing/transport details live in `docs/ROUTING_CONTRACT.md` and `docs/REPOSITORY_TRANSPORT.md`. Timing and contract semantics live in `core/20_EFFECTIVE_CONTRACT.md`, `core/60_FORMAL_ACTIVE_TIME.md` and `core/80_STOP_AND_PROOF.md`.
