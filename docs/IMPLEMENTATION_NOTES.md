# Alpha 5 Implementation Notes

Alpha 5 is a narrow hard-default timing correction over the Alpha 4 black-box integration baseline.

The only **contract-policy** change in Alpha 5 remains the omitted timing-policy default: deterministic parameter resolution supplies `B=1` and `b=1`. Explicit `B=0` / `b=0` retains the Alpha 4 soft-target behavior. The underlying soft/hard stop mechanics are unchanged. A later Alpha 5 bootstrap refinement adds structural transparency before startup without changing those execution semantics.

## Transparent bootstrap index

After immutable manifest/VERSION binding, current Alpha 5 loads manifest-declared `bootstrap/INDEX.md` first. The index gives the host/model a compact machine map: which protocol files and deterministic helpers are implemented, where workspace/state/schema truth lives, and where deterministic reliability support stops and native model intelligence begins. `runtime/routing.py` now validates that a declared `bootstrap_index` is the first `startup_slice` path. The index is structural only; it does not define N/T/R/S/D/L/time/stop/proof semantics.

This specifically prevents two opposite integration failures: treating repository helpers/workspace as mere concepts or imaginary external services, and treating deterministic helpers as a planner that should replace native task strategy.

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

Alpha 4 intentionally does not remove staged authority, complete pinned execution-protocol verification, Clock Genesis, U0/contract setup or META verification to reduce wall-clock latency. Full-parameter black-box runs showed that semantic default completion is only one part of startup cost. The logical entrypoint + 17 core modules remain separate source files, while a deterministic execution bundle reduces their post-genesis physical repository acquisitions from 18 to 1. Any later performance work must preserve the same authority/clock/contract boundaries.

## Retained Alpha 2/3 state machinery

`runtime/routing.py`, `runtime/repository_transport.py`, `runtime/invocation_surface.py` and `runtime/parameter_resolution.py` remain boundary helpers. None of these chooses task strategy. `LiveDIGRRun` continues to replace raw `.events.append()` use with thin semantic wrappers. Wrappers validate references, not intellectual quality.

Strategy/Candidate/EST/Source/D/Completion stores remain revisioned. Source time still derives from formal SOURCE intervals plus source-activity bindings rather than a second aggregate truth. Isolation facts describe evidenced capability; isolation receipts bind target-bounded actual mode to interventions. Recovery still verifies complete workspace semantics before resume; integrity alone is not time continuity.
