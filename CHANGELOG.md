# Changelog

## 5.0.0-alpha.3 — host transport hardening

Alpha 3 is a focused follow-up to the Alpha 2 corrected integration baseline. It was triggered by two real fresh-chat deployment failures: `DIGR/help` and `DIGR：返回版本号` both emitted the fixed route-failure message without any observable repository acquisition. A source audit then found a second concrete gap: the personalization advertised GitHub's Contents API while `runtime/routing.py` expected raw file bytes.

### Corrected interfaces
- routing schema 3: actual acquisition is a precondition for route failure; mutable-ref provenance is explicit;
- repository transport schema 1: attempt receipts, direct/fresh provenance, immutable pin request identity;
- Alpha 2 invocation-surface/parameter/run-session/workspace/event schemas remain unchanged;
- clock-journal schema remains 1.

### Transport corrections
- new host-facing repository transport adapter with a standard-library direct HTTPS implementation and injectable connector/fetch interface;
- search/index/crawl responses are inadmissible as mutable `stable` authority;
- direct REST mode requires Git-ref and Branches endpoints to agree on the same full commit SHA;
- mutable direct requests ask caches to revalidate rather than accepting a search snapshot;
- pinned resources prefer immutable raw-SHA URLs;
- Contents API fallback requests raw media and decodes ordinary base64 file wrappers when necessary;
- fixed route failure is forbidden as a zero-cost shortcut before current-turn acquisition evidence exists;
- local personalization explicitly orders repository acquisition before any user-visible response/task interpretation.

### Regression discipline
Alpha 3 adds black-box-transport unit coverage for actual attempt ordering, no-attempt failure rejection, untrusted search provenance, ref/branch mismatch, immutable raw pinning and Contents wrapper normalization. It retains Alpha 2's full execution/recovery test suite and the same deterministic double-build/cold-validation discipline.

## 5.0.0-alpha.2 — corrected integration baseline

Alpha 2 was the result of a full Alpha 1 code/rule audit plus the project evolution record. It treated the historical log as evidence of changing requirements and rejected designs, not as a static parser specification.

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
Alpha 1's 165 green tests were treated as a verified checkpoint, not proof that Alpha 2 semantics were already correct. Alpha 2 replaced tests that asserted retired Alpha 1 behavior and was released only after full tests, repository validator, cold extraction, deterministic double build and standalone personalization byte checks.

## 5.0.0-alpha.1 — first Native Assist substrate

Established repository-only delegated semantic authority, immutable pinning, P_run/P_target isolation, Result Sovereignty, Run Genesis, monotonic clock journal, formal work states, event-backed actual direction, explicit workspace, EST as external memory, deterministic release and non-sticky invocation.

## 4.1.1 and earlier
See `docs/MIGRATION_FROM_4.1.1.md` and repository history. Historical versions explain why routing/authority and runtime boundaries changed; their semantics are not imported into a newer pinned run.
