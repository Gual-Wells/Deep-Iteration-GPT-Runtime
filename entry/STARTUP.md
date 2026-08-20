# DIGR 5.0 Alpha 4 — Minimal Startup Slice

This file is deliberately small enough to load before the full protocol. It defines only repository-surface classification and the clock-genesis / full-protocol-ready boundary for the already pinned `P_run`.

1. Classify the broad-router capture using the pinned repository surface rules: `NATIVE | HELP | INVALID | EXECUTING`.
2. `NATIVE`: return the original user message unchanged to native ChatGPT. Do not create a run, U0, contract or proof.
3. `HELP`: load only `manifest.help`; do not create the task clock.
4. `INVALID`: return a concise invocation-structure diagnostic; do not perform task work.
5. `EXECUTING`: establish trusted clock readiness immediately (at least three monotonic samples) and create Run Genesis **before parameter resolution, U0 or substantive task work**.
6. After successful Run Genesis, acquire the full logical `entrypoint + core[]` from the **same pinned commit** in META. If the pinned manifest declares `execution_bundle`, fetch that one immutable bundle and verify that its member list, order, byte lengths and digests exactly cover the manifest-declared entrypoint/core. Otherwise load the logical files individually for compatibility.
7. Persist an `ExecutingProtocolLoadReceipt` bound to `P_run`. Parameter resolution is forbidden until this receipt exists. Any mandatory full-protocol acquisition or verification failure after genesis aborts the born run; it must not remain a resumable GENESIS or be rewritten as “never started”.

The startup slice does not define N/T/R/S/D/L semantics beyond the fact that parameter resolution happens only after Clock Genesis **and** verified full-protocol readiness. Full versioned semantics remain the logical pinned entrypoint/core; the bundle is only a transport aggregation of those source files.
