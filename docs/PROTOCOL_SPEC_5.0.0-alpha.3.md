# DIGR 5.0.0-alpha.3 Protocol Specification Index

Normative execution semantics are the pinned `entry/DEEP_ITERATION_ENTRY.md` plus manifest `core[]`. Minimal pre-full-load behavior is the manifest `startup_slice`. `entry/HELP.md` is user-facing documentation and does not itself start a task run.

Alpha 3 keeps the Alpha 2 corrected execution baseline—immutable commitments plus perpetually revisable Strategy/Candidate/Source/D working state, Source Presumption, Candidate-backed R, integrated D/L information flow, comprehensive recovery, event/source/clock binding and compact proof.

The Alpha 3-specific normative change is **before P_run exists**: routing schema 3 + repository transport schema 1 require actual acquisition evidence, admissible mutable-ref provenance, REST ref/branch consensus when that path is used, immutable SHA-pinned content, and raw/base64 Contents normalization. See `docs/ROUTING_CONTRACT.md` and `docs/REPOSITORY_TRANSPORT.md`.
