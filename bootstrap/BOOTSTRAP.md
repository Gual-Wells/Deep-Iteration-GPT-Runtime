# DIGR 5.0 Bootstrap — Repository Authority and Staged Startup

The local personalization is a transport router, not a copy of DIGR semantics. Each candidate route resolves `stable` to one immutable 40-hex commit, binds `manifest.json` and `VERSION`, and treats that pinned repository version as `P_run`.

For manifests declaring `startup_slice`, acquire only that slice before repository classification. For this Alpha 2 commit the slice is `bootstrap/BOOTSTRAP.md` plus `entry/STARTUP.md`. Do not pre-load the full core before deciding NATIVE/HELP/INVALID/EXECUTING.

All reads after pinning use the same SHA. Context, Memory, previous answers and a target version (`P_target`) may inform task content only after the pinned protocol permits it; `P_target` cannot redefine DIGR semantics or rebind the current `P_run`.

Legacy pinned manifests without `startup_slice` follow their own declared navigation and are not retrofitted with Alpha 2 startup semantics.
