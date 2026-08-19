# DIGR 5.0 Alpha 2 — Minimal Startup Slice

This file is deliberately small enough to load before the full protocol. It defines only repository-surface classification and the clock-genesis boundary for the already pinned `P_run`.

1. Classify the broad-router capture using the pinned repository surface rules: `NATIVE | HELP | INVALID | EXECUTING`.
2. `NATIVE`: return the original user message unchanged to native ChatGPT. Do not create a run, U0, contract or proof.
3. `HELP`: load only `manifest.help`; do not create the task clock.
4. `INVALID`: return a concise invocation-structure diagnostic; do not perform task work.
5. `EXECUTING`: establish trusted clock readiness immediately (at least three monotonic samples) and create Run Genesis **before parameter resolution, U0 or substantive task work**.
6. After successful Run Genesis, load `entrypoint` and all `core[]` from the **same pinned commit** in META. Failure after genesis aborts the born run; it must not be rewritten as “never started”.

The startup slice does not define N/T/R/S/D/L semantics beyond the fact that parameter resolution happens after clock genesis. Full versioned semantics live in the pinned entrypoint/core.
