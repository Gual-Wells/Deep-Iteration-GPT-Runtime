# Engineering Validation Log — 4.1.0

High-level observable outcomes, not hidden reasoning.

1. Removed 4.0 root pre-protocol gate and repository-only loader artifacts.
2. Converted local personalization into a minimal candidate-response/routing/pinning/delegation plane.
3. Added immutable `RouteReceipt` + manifest digest and manifest-only discovery helper.
4. Added legacy manifest discovery so current 3.0 can be routed without importing 4.1 startup semantics.
5. Bound P_run to the route receipt; removed gate-id and P_target from routing authority records.
6. Moved P_target/self-hosting and mandatory executing-task clock readiness into repository 4.1 bootstrap/core.
7. Separated RouteFailure from repository-defined task startup failure.
8. Preserved observed-vs-hard clock facts, Formal Active Time, source aggregation, isolation checks, stop/proof truthfulness and strict scalar validation.
9. Made primary and Free/Go router files byte-identical.
10. Extended deterministic release builder to export standalone personalization directly from internal source bytes and cold-validate the package.
