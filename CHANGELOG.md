# Changelog

## 5.0.0-alpha.7 — formal-time continuity and internal L1

Alpha 7 preserves Alpha 6 implementation-execution integrity and same-commit runtime delivery, then fixes cross-host formal-time attribution and finalization.

- Added persisted `WORK_LEASE_OPEN` semantics so substantive MAIN/SOURCE/D_EXCLUSIVE work can cross verified same-boot host/process/tool boundaries without disappearing from formal time.
- Added explicit derived coverage gaps for unleased formal boundaries. Hard T/t now requires both clock verification and complete relevant semantic-time coverage.
- Changed formal T to MAIN + SOURCE + D_EXCLUSIVE; t remains SOURCE only.
- Removed public L from invocation syntax, semantic completion, parameter-resolution schema, Effective Contract, stop checks and canonical proof. D now uses an internal fixed L1 semantic-isolation baseline.
- Added SOURCE lease binding so external GitHub/Web/connector research is timed where it actually occurs rather than by a short post-hoc SOURCE receipt.
- Added finalization admission before ledger closure. Failed minima/hard-time/coverage/completion checks leave the run EXECUTING; FINISHED requires delivery_ready=true.
- Bumped parameter-resolution schema to 2 and run-session schema to 5.
- Added black-box regressions for leased/unleased resume, D time accounting, coverage failure, L rejection and non-destructive finish denial.

## 5.0.0-alpha.6 — execution integrity and runtime delivery

Alpha 6 preserves Alpha 5's hard-by-default B/b timing semantics and the Alpha 4/5 authority, clock, state and execution-protocol transport architecture. It addresses two live failures that remained possible after Alpha 5.

- **Runtime impersonation:** seeing and understanding a repository helper did not mechanically force the host/model to execute it. Alpha 6 adds execute-before-interpret drift inoculation, concrete component interrogation, at most two lightweight corrective rounds, execution commitment, and a rule that semantic equivalence/manual receipts never satisfy implementation execution.
- **Implementation delivery gap:** a GitHub connector could read pinned source while the Python/container executor could not receive those bytes or access GitHub. Alpha 6 makes implementation delivery a first-class startup requirement and adds an exact-commit GitHub Actions runtime artifact whose helper members are verified against the pinned Git tree before execution.
- Added runtime/execution_integrity.py with structured commitment/attempt records and regression tests.
- Added core/13_IMPLEMENTATION_EXECUTION_INTEGRITY.md, runtime-distribution manifest metadata, an artifact builder, and a permanent artifact workflow.
- Startup now fails closed when neither a native identity-preserving bridge nor a verified exact-commit artifact is available; bridge failure is never permission to synthesize replacement runtime code.

## 5.0.0-alpha.5 — hard-by-default timing policy

Alpha 5 is a narrow semantic-default correction over Alpha 4. Omitted `B` and `b` now resolve to `1` rather than `0`, so T/t are hard lower bounds by default once their values are explicitly supplied or semantically completed. Explicit `B=0` / `b=0` remains the supported opt-in soft timing policy. Alpha 4 authority, source, D/L, clock, workspace and transport architecture is otherwise preserved.

Maintenance cleanup: corrected the stale manifest `D.s` description that still said zero disabled D, and normalized current Alpha 5 authority/runtime/schema/operator-facing labels that were still self-identifying as Alpha 4. Historical Alpha 4 specifications, migration notes and validation records remain unchanged.

Bootstrap transparency refinement: added pinned `bootstrap/INDEX.md` as the first repository-side structural path after manifest/VERSION. The local router now performs `pin → bootstrap_index → startup_slice`, so the host/model sees implemented helpers, persistent objects, truth-source ownership and the deterministic-runtime/native-intelligence boundary before interpreting startup. The index is structural only and does not duplicate versioned N/T/R/S/D/L/time/stop/proof semantics.

Plus router execution-firewall correction: a live DIGR invocation successfully acquired INDEX + STARTUP but then began substantive task comparison without actually crossing the EXECUTING startup gates. The local router is therefore retargeted to Plus-only capacity and now keeps a task-work firewall closed from candidate capture until repository-defined startup/protocol readiness is actually satisfied. `read/understand startup != execute startup`; EXECUTING is not itself task-work readiness. The Plus router also restores pre-authority OAuth and Contents/raw/base64 transport safeguards that had been lost during the 1,500-character compression. The Free/Go personalization copy is intentionally removed.

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
