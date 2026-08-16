# Implementation Notes — DIGR 4.1.0

Non-normative. Core semantics live in `core/`.

## Routing
`runtime/routing.py` validates already-resolved repository provenance: authoritative repo, `stable`, full commit SHA, `manifest.json` and its digest. `discovery_plan_from_manifest()` follows `bootstrap_entry` when present or legacy `entrypoint`+`core` when absent. It intentionally has no invocation/time/default/stop/proof logic.

## Protocol authority
`ProtocolAuthority` binds P_run to the exact `RouteReceipt`; repository and commit must match. P_target is not a routing field. Self-hosting semantics begin only after P_run is loaded.

## 4.1 task startup
`runtime/task_startup.py` contains versioned 4.1 task-startup evidence. `ClockReadiness` requires hard-verifiable compatible snapshots. `TaskStartupReceipt` is created before U0 freeze. Help/off candidates do not instantiate it.

## Clock and Formal Active Time
`time.monotonic_ns()` is the integer-ns substrate. Observed monotonic delta and hard-verifiable continuity are distinct. `FormalTimeLedger` sums per-interval duration; parallel S activity is unioned separately by `source_aggregate.py`.

## L2/L3
Provider API names are not conformance evidence. Default full-history handoff is not L2. Nested agent/tool runs can still share application context. L2 requires separate LLM history/context, controlled telemetry, D-State firewall and no unfiltered app-state bypass. L3 adds independent agent identity/instructions/execution loop/tool capability.

## Strict data / proof
Count/policy fields reject bool-as-int; durations reject NaN/Infinity. Hard actual is visible only when verification is true; otherwise proof uses `?`.

## Release builder
The builder rejects symlinks and unsafe paths, runs source tests, regenerates FILE_TREE/SHA256SUMS, creates a fixed-timestamp sorted ZIP, cold-extracts and reruns validation. With `--personalization-output`, it copies the canonical internal source bytes after validation. This prevents ZIP/standalone configuration drift.
