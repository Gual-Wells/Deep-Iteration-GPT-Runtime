# Migration from 4.1.1 and 5.0 Alphas to 5.0.0-Berta1

Berta1 retains the 5.0 Native Assist execution model and makes pinned manifest/VERSION plus a self-contained startup slice the handoff boundary.

## Startup migration

Adapters MUST broadly capture exact-uppercase candidate prefixes, resolve `stable` to an immutable 40-hex commit, read pinned `manifest.json` and `VERSION`, require version agreement, and load the entire manifest-declared startup slice before classification.

`manifest.json` is navigation authority and `VERSION` is its pinned version check. The manifest-declared runtime descriptor describes and integrity-binds generated execution/release artifacts after startup; it does not replace navigation.

Replace Alpha 4 startup reads as follows:

| Alpha 4 | Berta1 |
|---|---|
| broad router + manifest/VERSION authority | broad router + pinned manifest/VERSION authority retained and made explicit |
| multi-file startup slice | sole self-contained `entry/STARTUP.md` slice |
| `entry/HELP.md` fetch | `dist/HELP.zh-CN.md` |
| logical entry/core transport | `dist/MODEL_PROTOCOL.md` + verified `dist/EXECUTION_PROTOCOL.json` |
| hand-maintained personalization variants | one template with deterministic generated variants |

## Invocation and contract continuity

Berta1 replaces Alpha-era model completion with deterministic preflight after pinned STARTUP classifies EXECUTING. The standard profile is N2/R1/no-time/source-auto/D0/L1. `min=<duration>` is hard and `target=<duration>` is soft; explicit overlays are parser-owned and unique-or-fail.

## D(0) correction

Any adapter, schema or prompt that interprets `D(0)` as “D disabled” must be changed. Zero means only that no completed D is mechanically required. Native intelligence may still invoke a quality-driven D, `D_actual` may exceed zero, and L conformance becomes applicable when a D actually completes.

## Delivery migration

New Berta1 runs terminate as `DELIVERED` or `INCOMPLETE`; `ABORTED` remains the failure terminal. `FINISHED` is accepted only while recovering Alpha 4 workspaces. A run that closes `INCOMPLETE` cannot render a canonical proof as though delivery gates passed.

## Packaging migration

Run `python tools/build_release.py --prepare-only` after editing protocol, Help or personalization sources. The deterministic builder regenerates all dist and configuration artifacts. Package automation must exclude `__pycache__`, bytecode and test-tool caches. The root standalone personalization is byte-identical to compact/FREE_GO and every generated configuration ends with `<!-- DIGR_LOCAL_PERSONALIZATION_END -->`.
