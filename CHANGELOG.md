# Changelog

## 5.0.0-alpha.2 — corrected integration baseline

Alpha 2 is the result of a full Alpha 1 code/rule audit plus the project evolution record. It intentionally treats the historical log as evidence of changing requirements and rejected designs, not as a static parser specification.

### Corrected interfaces
- routing schema 2: exact-uppercase `DIGR`, staged startup navigation;
- invocation surface schema 2: `EXECUTING | HELP | NATIVE | INVALID`;
- parameter resolution schema 1: header normalization, typed T/t, unique-or-fail positional/label resolution;
- run session/workspace schema 2: RunPhase lifecycle, revisioned Strategy/Candidate/Source/Completion, artifact index, derived Run Brief, actual resume;
- event receipt schema 2: clock/strategy/candidate/source bindings;
- clock journal schema remains 1; core clock facts are retained and cross-session continuity is tightened.

### Semantic integration corrections
- `Freeze commitments, never freeze strategy` made structural rather than aspirational;
- Strategy Genesis moved into real MAIN task work;
- SourceDisposition decouples source obligation from S numeric minima; normal DIGR source presumption is REQUIRED;
- old standalone source aggregation helper removed; SOURCE time is the clock union and every SOURCE start binds real active S IDs;
- R requires an existing candidate and records candidate-before/challenge/outcome/candidate-after-or-retained;
- D becomes a revisioned intervention session with Decree commitment point and concrete Main reintegration;
- L target/capability/actual are distinct; L2/L3 actual require controlled input/output packet refs; D interventions bind isolation receipts;
- L mismatch is visible but not universally blocking; D=0 makes L non-blocking;
- recovery verifies the full workspace and resume requires a trusted cross-process clock bridge;
- completion gaps and source objectives are revisioned/reopenable;
- help and local personalization rewritten for the corrected architecture.

### Release discipline
Alpha 1's 165 green tests were treated as a verified checkpoint, not proof that Alpha 2 semantics were already correct. Alpha 2 replaces tests that asserted retired Alpha 1 behavior, adds regression coverage for the corrected contracts, and is released only after full tests, repository validator, cold extraction, deterministic double build and standalone personalization byte checks.

## 5.0.0-alpha.1 — first Native Assist substrate

Established repository-only delegated semantic authority, immutable pinning, P_run/P_target isolation, Result Sovereignty, Run Genesis, monotonic clock journal, formal work states, event-backed actual direction, explicit workspace, EST as external memory, deterministic release and non-sticky invocation. Alpha 2 retains these foundations except where the audit found integration defects.

## 4.1.1 and earlier
See `docs/MIGRATION_FROM_4.1.1.md` and repository history. Historical versions are context for why routing/authority and runtime boundaries changed; their semantics are not imported into a pinned Alpha 2 run.
