# Migration from 4.1.1 and 5.0 Alphas to 5.0.0-Berta2

Berta2 retains the 5.0 Native Assist execution model and makes pinned manifest/VERSION plus a self-contained startup slice the handoff boundary.

## Startup migration

Adapters MUST broadly capture exact-uppercase candidate prefixes, resolve `stable` to an immutable 40-hex commit, read pinned `manifest.json` and `VERSION`, require version agreement, and load the entire manifest-declared startup slice before classification.

`manifest.json` is navigation authority and `VERSION` is its pinned version check. The manifest-declared runtime descriptor describes and integrity-binds generated execution/release artifacts after startup; it does not replace navigation.

Replace Alpha 4 startup reads as follows:

| Alpha 4 | Berta2 |
|---|---|
| broad router + manifest/VERSION authority | broad router + pinned manifest/VERSION authority retained and made explicit |
| multi-file startup slice | sole self-contained `entry/STARTUP.md` slice |
| `entry/HELP.md` fetch | `dist/HELP.zh-CN.md` |
| logical entry/core transport | `dist/MODEL_PROTOCOL.md` + verified `dist/EXECUTION_PROTOCOL.json` |
| hand-maintained personalization variants | one template with deterministic generated variants |

## Invocation and contract continuity

Berta2 retains deterministic structural parsing but restores Alpha4 task-aware completion for missing N/T/R/S/D values and extends it to V. No-group calls are adaptive and source-required; fixed N2/T0/R1/S0/D0/V0/L1/source-auto is selected only by explicit `standard`. A lone duration remains soft T. `min=<duration>` is hard and `target=<duration>` is explicitly soft. B/b may request a positive native time completion.

Host evidence and intellectual execution are now separate. Missing host capabilities produce MODEL_NATIVE plus NONE/PARTIAL attestation instead of cancelling DIGR execution. Only canonical delivery requires verified host enforcement.

## D(0) correction

Any adapter, schema or prompt that interprets `D(0)` as “D disabled” must be changed. Zero means only that no completed D is mechanically required. Native intelligence may still invoke a quality-driven D, `D_actual` may exceed zero, and L conformance becomes applicable when a D actually completes.

## Delivery migration

Canonical-host Berta2 runs terminate as `DELIVERED` or `INCOMPLETE`; `ABORTED` remains the failure terminal. `FINISHED` is accepted only while recovering Alpha 4 workspaces. Delivery schema v2 binds terminal semantic/audit state and a final mutation seal. MODEL_NATIVE execution returns a noncanonical report/log set with unavailable actuals marked `?`.

## Packaging migration

Run `python tools/build_release.py --prepare-only` after editing protocol, Help or personalization sources. The deterministic builder regenerates all dist and configuration artifacts. Package automation must exclude `__pycache__`, bytecode and test-tool caches. The root standalone personalization is byte-identical to compact/FREE_GO and every generated configuration ends with `<!-- DIGR_LOCAL_PERSONALIZATION_END -->`.
