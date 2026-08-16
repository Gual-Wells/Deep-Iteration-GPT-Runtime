# Architecture — DIGR 4.1.0

DIGR 4.1 uses six separated control/evidence layers:

1. **Reliable Routing Plane (local personalization)** — candidate response, repository location, `stable`→immutable SHA, pinned manifest discovery, authority delegation. No versioned DIGR semantics.
2. **Repository Bootstrap Plane** — `bootstrap/BOOTSTRAP.md`, loaded from the pinned commit. This is where 4.1 versioned startup rules begin.
3. **Repository Authority Plane** — bind P_run to the same pinned route receipt; quarantine context/local/other-commit/P_target from protocol semantics while still allowing context into U0/evidence.
4. **Semantic Contract Plane** — repository-defined invocation classification, executing-task clock readiness, U0, explicit parameters, semantic completion and Effective Contract.
5. **Native Execution Plane** — Main evolution, S, R/r, EST, D/L, tools/research/validation remain model-native within protocol boundaries.
6. **Deterministic Evidence Plane** — routing/provenance, clock facts, Formal Active Time, source aggregation, isolation facts, mechanical stop and proof validation. Helpers do not create natural-language semantics.

## No pre-protocol protocol
4.1 intentionally has no root execution-gate file. Local personalization cannot say “clock first”, “help does X”, or “P_target means Y”. It only routes to repository content. This removes the authority cycle that let a future loader impose future rules on a legacy repository version.

## Time
P_run=4.1 classifies invocation first. Only executing tasks then establish mandatory task-clock readiness before U0/substantive work. Soft observed duration and hard continuity verification remain separate facts. Foreground states are mutually exclusive; parallel multi-S source work unions at source aggregation.

## Isolation
L1 is same-context semantic firewall; L2 requires separate LLM history/context + controlled telemetry + state firewall; L3 adds independent agent identity/instructions/loop/tool execution. Provider primitives are substrate, not self-certifying conformance.
