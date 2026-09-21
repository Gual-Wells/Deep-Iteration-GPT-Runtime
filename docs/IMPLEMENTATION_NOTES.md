# Alpha 6 Implementation Notes

Alpha 6 preserves Alpha 5 hard-default timing semantics and adds execution-integrity plus identity-preserving runtime delivery after two live host failures.

The **contract-policy** behavior inherited from Alpha 5 remains the omitted timing-policy default: deterministic parameter resolution supplies `B=1` and `b=1`. Explicit `B=0` / `b=0` retains the Alpha 4 soft-target behavior. The underlying soft/hard stop mechanics are unchanged. A later Alpha 5 bootstrap refinement adds structural transparency before startup without changing those execution semantics.

## Transparent bootstrap index

After immutable manifest/VERSION binding, current Alpha 6 loads manifest-declared `bootstrap/INDEX.md` first. The index gives the host/model a compact machine map: which protocol files and deterministic helpers are implemented, where workspace/state/schema truth lives, and where deterministic reliability support stops and native model intelligence begins. `runtime/routing.py` now validates that a declared `bootstrap_index` is the first `startup_slice` path. The index is structural only; it does not define N/T/R/S/D/L/time/stop/proof semantics.

This specifically prevents two opposite integration failures: treating repository helpers/workspace as mere concepts or imaginary external services, and treating deterministic helpers as a planner that should replace native task strategy.

## Execute-before-interpret gate

Alpha 5 made implemented helpers visible but did not fully prevent a model from reading a helper and reproducing its behavior. Alpha 6 adds a protocol-level drift inoculation and component interrogation gate. The compact commitment names component, operation and executor, chooses direct execution, and rejects substitution/manual result construction. Incomplete commitments get at most two lightweight correction rounds. After acceptance, the next relevant action must be actual delivery/execution or a concrete failure.

runtime/execution_integrity.py provides deterministic structured records for the commitment and the resulting attempt. It does not store chain-of-thought and does not choose task strategy.

## Runtime implementation delivery

A second live failure showed that GitHub reading and Python execution may exist in separate host domains with no byte bridge. Alpha 6 therefore declares runtime_distribution in manifest.json and ships a permanent GitHub Actions artifact workflow. The artifact is named by the exact commit SHA and contains manifest/VERSION plus deterministic_helpers and a runtime index with Git blob identities. A host that lacks a native same-SHA file→executor bridge can materialize this artifact, verify it against the pinned Git tree, and execute the real implementation.

The artifact is not authority and cannot be used to rebind P_run. If neither native bridge nor exact-commit artifact can deliver verified implementation bytes, startup fails closed instead of synthesizing replacement runtime code.

## Repository transport

`runtime/repository_transport.py` now models transport capability rather than pretending every direct source exposes the same endpoint set. The first mutable observation is the public repository `stable` branch resource. If provenance is `github_connector`, that current branch HEAD is sufficient and no Git-ref endpoint is required. If provenance is `direct_https`, the Git-ref endpoint is additionally read and the two full 40-hex SHAs must agree. Search/index/crawl provenance remains rejected. All later reads are immutable-SHA pinned.

This mirrors the live ChatGPT GitHub connector behavior observed during Alpha 3 testing: the connector returned the same `stable` HEAD as direct `git ls-remote` and successfully fetched pinned VERSION/manifest/startup/help, while its generic fetch surface did not expose the Git-ref REST endpoint.

## D/L correction

`D_s` is mechanically a completed-intervention lower bound. Alpha 3 accidentally introduced an enable/disable interpretation through `EffectiveContract.dictator_enabled`, `LiveDIGRRun.create_d_intervention()` and recovery validation. Alpha 4 removes that gate. D actual may exceed a zero target when the native model judges a disruptive intervention useful.

L remains `target/capability/actual`. Mechanical L applicability is based on actual completed D, not the D minimum. A zero D target with an actual completed D therefore receives normal L validation; a run with no completed D has no completed-intervention L gate.

## Timing and proof

The deterministic stop code already treated B/b=0 as soft and B/b=1 as hard. Alpha 4 aligns protocol language with that behavior: N/R/n/r/D are unconditional minima, T/t are targets whose stop-gate strength is controlled by B/b.

`runtime/proof.py` remains the canonical renderer. Live host output had exposed raw fractional seconds; Alpha 4 makes the protocol-level presentation rule explicit: actual duration floors to whole seconds, and hard-unverified B/b time is hidden as `?`. This is a host-integration requirement, not a change to the renderer algorithm.

## Initialization

Alpha 4 intentionally does not remove staged authority, complete pinned execution-protocol verification, Clock Genesis, U0/contract setup or META verification to reduce wall-clock latency. Full-parameter black-box runs showed that semantic default completion is only one part of startup cost. The logical entrypoint + 18 core modules remain separate source files, while a deterministic execution bundle reduces their post-genesis physical repository acquisitions from 18 to 1. Any later performance work must preserve the same authority/clock/contract boundaries.

## Retained Alpha 2/3 state machinery

`runtime/routing.py`, `runtime/repository_transport.py`, `runtime/invocation_surface.py` and `runtime/parameter_resolution.py` remain boundary helpers. None of these chooses task strategy. `LiveDIGRRun` continues to replace raw `.events.append()` use with thin semantic wrappers. Wrappers validate references, not intellectual quality.

Strategy/Candidate/EST/Source/D/Completion stores remain revisioned. Source time still derives from formal SOURCE intervals plus source-activity bindings rather than a second aggregate truth. Isolation facts describe evidenced capability; isolation receipts bind target-bounded actual mode to interventions. Recovery still verifies complete workspace semantics before resume; integrity alone is not time continuity.
