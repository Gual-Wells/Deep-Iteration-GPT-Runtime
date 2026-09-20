# 5.0.0-alpha.5 Hard-Default Timing Baseline

Alpha 2 remains the mother-base for the corrected 5.0 execution/state model. Alpha 3 hardened repository transport and Alpha 4 supplied the black-box corrected integration baseline. Alpha 5 preserves that architecture and changes one contract default: omitted B/b now resolve to 1 (hard) instead of 0 (soft), while explicit B=0/b=0 remains available.

The inherited Alpha 4 correction set remains in force. Alpha 5 additionally changes the fixed B/b default and its resolver/help/test contract:

- `routing_schema=4` and `repository_transport_schema=3` distinguish connector branch-head authority from direct REST consensus with one bounded retry for live push races;
- `run_session_schema=4` preserves corrected D/L semantics and additionally makes verified full execution-protocol load a hard post-genesis prerequisite;
- timing documentation converges on soft/hard T/t targets rather than incorrectly calling all contract fields unconditional minima;
- canonical proof rendering and canonical zh-CN Help are tightened to prevent host-side semantic drift;
- one deterministic immutable execution bundle transports the logical entrypoint + 17 core modules after Clock Genesis, with a persisted `ExecutingProtocolLoadReceipt` and mandatory abort on load failure.

The mother-base invariants remain: immutable P_run/U0/contract commitments, revisable Strategy/Candidate/Source/D state, Source Presumption, Candidate-backed R, D/L evidence binding, trusted monotonic clock-journal, comprehensive workspace recovery, compact proof and deterministic releases.

Change discipline remains behavior first, then schema/docs/examples/tests converge on the same behavior. No prompt-only workaround, remembered result, or “completed” label counts as engineering evidence. Deterministic double build, cold extraction, full tests/validator, cross-platform path checks and standalone personalization byte checks remain mandatory.
