# Engineering Validation Log — DIGR 5.0.0 Alpha 4

Release role: black-box corrected integration baseline over the Alpha 3 transport-hardened architecture.

This file records engineering acceptance, not chat-status claims. Alpha 4 is driven by observed deployment evidence: successful live GitHub connector resolution of the actual `stable` HEAD and pinned Alpha 3 files; full-parameter execution exposing D/L, timing-language and proof-presentation inconsistencies; and source audit confirming the corresponding code paths.

## Corrected boundaries under test

1. connector mode resolves `stable` from the current repository branch resource and does not require the product connector to expose the Git-ref REST endpoint;
2. direct REST mode still requires branch/ref full-SHA consensus, with one bounded re-observation for a push-between-reads race;
3. deterministic execution-bundle transport reduces the logical entrypoint/core physical acquisition set to one pinned post-genesis read without changing authority;
4. parameter resolution is mechanically blocked until an `ExecutingProtocolLoadReceipt` bound to P_run/manifest exists; mandatory post-genesis protocol-load failure persists ABORTED;
5. `D(0)` is a zero completed-D minimum, not a disable switch; valid quality-driven D under target zero survives recovery;
6. L mechanical applicability follows actual completed D, while target/capability/actual remain distinct;
7. B/b=0 soft T/t targets remain non-gating; B/b=1 hard targets require trusted evidence;
8. canonical proof actual durations floor to whole seconds and hard-unverified time renders `?`;
9. canonical zh-CN Help carries fixed-default precedence, SourceDisposition, D/L and timing semantics without relying on free translation;
10. staged authority, Clock Genesis, complete protocol verification and META initialization are retained rather than bypassed for latency.

## Final-tree acceptance gates

The final source tree must pass, in this order:

1. full `unittest` discovery over `tests/test_*.py` — current verified checkpoint: **246 tests**;
2. `tests/validate_repo.py` repository-contract validation;
3. connector-specific/direct-REST repository-transport regressions plus bounded consensus retry;
4. deterministic execution-bundle generation/verification and post-genesis protocol-load barrier/abort regressions;
5. zero-minimum D creation/completion/recovery plus actual-D L-gate regressions;
6. Python 3.10 grammar parsing, JSON/schema validation, UTF-8/LF sweep and stale-semantics checks;
7. regeneration and verification of `FILE_TREE.txt` and `SHA256SUMS.txt`;
8. deterministic ZIP creation with fixed metadata and sorted members;
9. ZIP CRC/path/symlink/cache safety plus Windows/case-fold collision checks;
10. cold extraction followed by hash verification, full unit suite and repository validation from that extracted copy;
11. a second independent release build from the unchanged source tree; ZIP and standalone personalization outputs must be byte-identical;
12. final cold extraction/revalidation of the delivered ZIP;
13. byte equality between standalone compact/FULL personalization and package copies.

Acceptance does not claim that Custom Instructions are a platform-level pre-message hook. It proves that the shipped router contract, deterministic transport adapter, D/L semantics, timing/proof contract, documentation and release artifacts converge on the same Alpha 4 behavior. Final release SHA-256 digests are reported alongside delivered artifacts rather than embedded here.
