# DIGR 5.0 Bootstrap Architecture Note (Non-startup)

This file is explanatory only. Berta1 declares `entry/STARTUP.md` as both `bootstrap_entry` and the sole `startup_slice` member so classification and startup navigation cannot drift across files.

The local shell performs only broad candidate capture and repository transport. Every message whose lstripped text begins with exact uppercase ASCII `DIGR` or exact `深度迭代` reaches this repository path before semantic classification.

Transport resolves `Gual-Wells/Deep-Iteration-GPT-Runtime:stable` to one immutable 40-hex commit. An existing GitHub connector may read the current stable branch HEAD. Direct REST must read both the branch and Git-ref endpoints in the same attempt and require identical SHAs. All later reads use that SHA.

Pinned `manifest.json` is the navigation authority. Its `version` must equal pinned `VERSION`; then every file in `startup_slice` is loaded in declared order. `runtime-descriptor.json` is a manifest-navigated execution/release description, not the first read and not a replacement for manifest navigation.

`entry/STARTUP.md` classifies the untouched original message. NATIVE returns it to ordinary ChatGPT, HELP follows `manifest.help`, and EXECUTING follows `manifest.entrypoint` plus `manifest.core[]` or their verified execution bundle. Context, Memory, previous answers and `P_target` cannot reconstruct missing pinned protocol or rebind `P_run`.
