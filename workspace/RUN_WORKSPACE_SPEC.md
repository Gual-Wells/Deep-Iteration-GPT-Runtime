# DIGR 5.0 Alpha 4 Run Workspace

`workspace/layout-v2.json` is the single current layout contract. Alpha 4 retains the Alpha 2 removal of overlapping legacy runtime-state/invocation state copies and persists one RunPhase lifecycle plus revisioned authoritative stores.

Genesis creates authority/invocation/startup/clock journal, artifact index and RunPhase=GENESIS. Parameter/U0/contract artifacts appear only as their phases are crossed. Strategy, Candidate, EST, S, D/isolation, evidence and completion states are revisioned. Layout v2 maps both latest pointers and immutable revision-history artifacts to schemas; completion-gap revisions have their own schema rather than borrowing the aggregate CompletionState shape. Append-only clock/source-activity/semantic-event journals are re-indexed after writes.

D isolation packets live under `dictator/packets/*.json`. They are immutable indexed artifacts: controlled Input Packets exist before L2/L3 isolated work and Output Packets are produced by that work and referenced from D results. Isolation receipts and intervention state remain separate so capability/actual mode and execution history cannot be conflated.

`state/artifact-index.json` is integrity metadata, not semantic authority. `state/run-brief.json` is a derived compact cache, never a second truth source. Recovery verifies hashes, latest pointers, revision chains, clock/work-state bindings and cross-store references; a FINISHED summary is rederived rather than trusted. A resume attempt may proceed only after that verification and must then establish a fresh trusted clock bridge.
