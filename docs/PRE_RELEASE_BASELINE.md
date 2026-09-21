# 5.0.0-alpha.6 Execution-Integrity / Runtime-Delivery Baseline

Alpha 2 remains the mother-base for the corrected 5.0 execution/state model. Alpha 3 hardened repository transport and Alpha 4 supplied the black-box corrected integration baseline. Alpha 5 preserved that architecture and changed the B/b default to hard. Alpha 6 preserves those semantics and adds two integration corrections: execute-before-interpret enforcement and identity-preserving runtime delivery.

The inherited Alpha 4/5 correction set remains in force. Alpha 6 additionally hardens implementation execution and delivery:

- `routing_schema=4` and `repository_transport_schema=3` distinguish connector branch-head authority from direct REST consensus with one bounded retry for live push races;
- pinned `bootstrap/INDEX.md` is now the manifest-declared first repository-side path after manifest/VERSION, exposing implemented-machine structure and truth-source ownership before the remaining startup slice without becoming execution-semantic authority;
- Plus local personalization keeps a pre-task execution firewall closed through repository-defined startup readiness: loading/understanding STARTUP is not execution, EXECUTING is not readiness, and implemented setup steps cannot be replaced by conceptual acknowledgement;
- `run_session_schema=4` preserves corrected D/L semantics and additionally makes verified full execution-protocol load a hard post-genesis prerequisite;
- timing documentation converges on soft/hard T/t targets rather than incorrectly calling all contract fields unconditional minima;
- canonical proof rendering and canonical zh-CN Help are tightened to prevent host-side semantic drift;
- one deterministic immutable execution bundle transports the logical entrypoint + 18 core modules after Clock Genesis, with a persisted `ExecutingProtocolLoadReceipt` and mandatory abort on load failure;
- execute-before-interpret drift inoculation + component interrogation prevents runtime impersonation by semantic-equivalent reimplementation/manual receipts;
- manifest-declared exact-commit runtime distribution gives hosts with isolated repository-reader/executor capabilities a verified GitHub Actions artifact delivery path; no verified delivery path fails closed.

The mother-base invariants remain: immutable P_run/U0/contract commitments, revisable Strategy/Candidate/Source/D state, Source Presumption, Candidate-backed R, D/L evidence binding, trusted monotonic clock-journal, comprehensive workspace recovery, compact proof and deterministic releases.

Change discipline remains behavior first, then schema/docs/examples/tests converge on the same behavior. The deployed personalization is now Plus-only rather than constrained to the old 1,500-character Free/Go envelope. No prompt-only workaround, remembered result, or “completed” label counts as engineering evidence. Deterministic double build, cold extraction, full tests/validator, cross-platform path checks and standalone personalization byte checks remain mandatory.
