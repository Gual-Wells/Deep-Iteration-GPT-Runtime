# Source / Boundary Validation — DIGR 4.1.0

Non-normative engineering conclusions.

## Authority correction
- Mutable `stable` is not a runtime identity; each candidate route resolves it to an immutable commit.
- Local personalization must not be a protocol copy. It only routes/discovers and delegates authority.
- A root pre-protocol gate was rejected because it became a second semantic authority and could impose future rules on legacy P_run.
- Manifest discovery may be backward-compatible without being semantically backward-compatible: it chooses file locations only.
- Protocol cleanliness is provenance-based; hidden cognitive “contamination” is not directly inspectable.
- Context may inform U0/evidence while remaining barred from protocol semantics.
- P_target self-hosting cannot rebind current P_run.

## Clock
- Clock readiness is repository 4.1 semantics and occurs only after 4.1 classifies an executing task.
- Help/invalid candidates do not start task clock.
- A timer API call alone is insufficient: readiness uses compatible monotonic snapshots and continuity verification.
- Hard T/t still require interval-level verification beyond startup readiness.

## L2/L3
Provider primitive names are not isolation conformance. Default full-history handoff is not L2; nested runs can still share application context. L2 requires history/context isolation, controlled telemetry and state firewall; L3 adds independent agent identity/instructions/execution loop/tool capability.

## Release
The standalone direct-copy personalization must be exported from the exact internal primary bytes. Schemas, deterministic helpers, property tests and cold ZIP validation prevent documentation/implementation/release drift.
