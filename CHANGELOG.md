# Changelog

## 4.1.0

Control-plane correction over 4.0.0.

- Replaced local pre-protocol gate with a minimal Reliable Routing Plane.
- Removed root `DIGR_EXECUTION_GATE.md`, `REPOSITORY_ONLY_LOADER.md`, `runtime/bootstrap_gate.py` and bootstrap-gate schema.
- Added `bootstrap/BOOTSTRAP.md` as **versioned repository protocol**, loaded only after immutable routing/pinning.
- Added `runtime/routing.py` and route-receipt schema for repository/ref/commit/manifest provenance without DIGR semantic interpretation.
- Added legacy manifest discovery: missing `bootstrap_entry` routes to manifest-declared entrypoint/core without importing 4.1 semantics.
- Reworked `ProtocolAuthority` so P_run is bound to a route receipt; removed gate-id and P_target from the routing/authority record.
- Defined contamination as protocol-decision provenance violation rather than hidden-state introspection; context may still inform U0/evidence.
- Moved P_target/self-hosting and universal task-clock readiness into repository 4.1 semantics.
- Help/invalid candidates no longer require task-clock startup; every executing 4.1 task still does, before U0/substantive work.
- Distinguished pre-protocol RouteFailure from repository-defined ProtocolStartupFailure.
- Made primary and Free/Go local router files byte-identical and added deterministic standalone-personalization export to the release builder.
- Retained 4.0 execution semantics for N/R/S/D/L, Formal Active Time, hard verification, source aggregation, isolation evidence, stop/proof and release safety.

## 4.0.0

Introduced unified partial invocation, semantic default completion, Formal Active Time, D/L disruptive-gambit controls, source aggregation, isolation evidence and strict canonical proof. 4.0.0 also introduced a repository-only root pre-protocol gate; 4.1.0 supersedes that control-plane design.
