# DIGR 5.0 Alpha 9 — Minimal Startup Slice

Alpha 9 keeps task work blocked until the exact pinned execution package and complete logical protocol are ready. All mandatory repository/runtime transport dependencies are resolved before Clock Genesis so a born run cannot later be killed by a transport bridge.

1. Classify: NATIVE | HELP | INVALID | EXECUTING.
2. NATIVE returns the original message to native ChatGPT; HELP reads manifest.help; INVALID returns only structure diagnostics. None creates a run.
3. EXECUTING applies execute-before-interpret: repository implementations are operated directly, never reproduced from understanding.
4. Before Genesis, resolve one identity-preserving implementation-delivery path: native same-SHA file→executor bridge, else exact-commit durable release asset, else same-commit Actions artifact.
5. Verify every deterministic helper against the pinned Git tree. Runtime-distribution schema 3 also requires the same-commit execution bundle in the package. RUNTIME-INDEX schema 2 binds commit, manifest, VERSION, helper identities and bundle identity as one package-attestation boundary.
6. Still before Genesis, verify the complete execution bundle against manifest entrypoint/core order, byte lengths and digests and construct ExecutingProtocolLoadReceipt bound to P_run. Failure here means startup failure; no run is born.
7. Bind the verified package to the concrete executor once. Reject model-written substitution/manual receipts. Re-open only when package/executor identity changes or a real direct attempt fails.
8. Only now establish >=3 trusted monotonic samples and create Run Genesis. Genesis persists the already-verified protocol-load receipt with authority/invocation/startup state.
9. After Genesis there is no mandatory repository/network transport gate. Resolve parameters, freeze U0, complete/freeze Effective Contract, then enter MAIN.
10. For substantive cross-host work, open a work lease when bridge time credit matters. Same-epoch resume may credit the bridge. If clock continuity changed, the run survives: the discontinuity gets zero credit, a new trusted epoch is established, and a leased semantic state may restart at that epoch.
11. Derived caches such as run-brief are checkpointed at coarse lifecycle/host-boundary/finalization points instead of every semantic event.

No identity-preserving package path or failed pre-Genesis protocol verification ever authorizes model-written runtime code or a native fallback answer.
