# Alpha 4 Implementation Notes

Alpha 4 is a black-box integration correction release over the Alpha 3 transport-hardened baseline.

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
