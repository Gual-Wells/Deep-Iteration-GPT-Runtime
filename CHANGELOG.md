# Changelog

## 5.0.0-Berta1 — V, four-clock and local-audit integration candidate

Berta1 is based on stable.1 and selectively absorbs alpha5-r3 reliability mechanisms. It is intentionally a Berta-series candidate, not a formal stable release.

- public parameters are `N,T,R,B,S,D,V,L`; V(o) is a persistent, qualified, semantically distant viewpoint minimum between D and L;
- typed parameters may be reordered, flat nested labels are supported, duplicates fail, and remaining unlabeled values are unique-or-fail with candidate diagnostics;
- V channels have private revisioned VLedgers, no V-to-V API, positive owned V_EXCLUSIVE time and Main-sovereign reintegration;
- ClockJournal projects T, t, D and V clocks; D/V are excluded from T, and IDLE/META count nowhere;
- D retains one public mechanism while internally supporting opaque D+, D− and Dx/D⊥ semantic directions;
- completion can record four structured criteria while preserving migration compatibility with stable.1 assessments;
- delivery emits content-addressed TOTAL and independent N/T/R/B/S/D/V/L local NDJSON logs;
- MCP, dynamic UI, PWA, remote bridge and backend implementation branches are absent;
- ClockJournal appends are durable before in-memory publication; stable.1 exact-candidate and two-phase fail-closed delivery remain intact.

## Inherited stable.1 pinned-manifest foundation

Berta1 preserves the validated 5.0 execution foundation while making the pinned navigation boundary explicit.

### Authority and distribution

- exact-uppercase DIGR/深度迭代 prefixes are broadly captured and always acquire pinned startup before classification;
- connector reads current stable HEAD; direct REST requires same-attempt branch and Git-ref SHA agreement;
- pinned `manifest.json` is navigation authority, pinned `VERSION` must agree, and the sole startup slice is self-contained `entry/STARTUP.md`;
- `runtime-descriptor.json` is a later execution/release artifact description, not the first read or navigation authority;
- `dist/MODEL_PROTOCOL.md`, `dist/HELP.zh-CN.md` and `dist/EXECUTION_PROTOCOL.json` are deterministically generated from the logical protocol sources;
- one personalization template generates compact, FREE_GO, expanded and root standalone copies, each with a terminal truncation sentinel;
- the release builder gains a prepare-only mode and excludes Python/test caches from reproducible packages.

### Semantic and lifecycle closure

- the last contradictory `zero_disables_D` descriptor text is removed: `D(0)` is only a zero minimum and never an off switch;
- new runs use a two-phase, fail-closed, recoverable delivery commit; only verified payload/summary/proof/envelope preparation may transition to `DELIVERED`;
- bootstrap, Help, migration and routing documentation agree on pinned manifest/STARTUP handoff.

## 5.0.0-alpha.4 — live black-box integration corrections

Alpha 4 follows Alpha 3 after successful live GitHub-connector routing and subsequent full-parameter black-box runs exposed remaining integration defects. It preserves Alpha 3 immutable repository authority, staged startup, trusted clock genesis, workspace/state model and recovery design.

### Corrected interfaces
- routing schema 4 + repository transport schema 3: connector branch-head acquisition remains first-class; direct REST keeps branch/ref consensus with one bounded re-observation for push-between-reads races;
- run-session schema 4: post-genesis full execution-protocol readiness is now a persisted prerequisite for parameter resolution; mandatory load failure aborts the born run;
- execution bundle schema 1 + execution-protocol-load schema 1: the 1 entrypoint + 17 core logical modules remain independent source authority but are transported in one deterministic immutable bundle after Clock Genesis;
- `D(0)` remains a zero minimum rather than a disable switch, D actual may exceed target, recovery accepts such runs and L applicability follows actual completed D;
- timing terminology converges on unconditional N/R/n/r/D minima versus B/b-governed soft/hard T/t targets;
- canonical proof presentation is made explicit to the host: actual durations floor to whole seconds and hard-unverified time is `?`;
- canonical `entry/HELP.md` is rewritten in zh-CN as a normative user reference with fixed-default precedence and exact Source/D/L/timing semantics.

### Black-box evidence preserved
- connected GitHub connector resolved live `stable` to the same SHA as direct `git ls-remote`, then successfully loaded pinned VERSION/manifest/startup/help;
- full-parameter invocation showed initialization wall-clock cost is dominated by authority/protocol/host orchestration rather than semantic default completion, so Alpha 4 does not remove or bypass startup reliability work;
- user-visible proof output demonstrated host-side rendering drift (fractional actual seconds), motivating explicit canonical rendering requirements rather than weakening the deterministic proof helper.

### Release discipline
Alpha 4 adds connector-specific transport tests, bounded direct-REST consensus retry, deterministic execution-bundle generation/verification, post-genesis protocol-load barrier/abort tests, zero-minimum D execution/recovery tests, actual-D L-gate tests, timing-policy documentation checks and stronger Help/proof conformance checks. Cross-platform ZIP path validation introduced in late Alpha 3 remains mandatory.

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
