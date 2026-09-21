# Routing Contract

The local layer is a broad candidate router plus repository-authority/structural-transparency handoff. It never redefines DIGR execution semantics.

## Candidate capture

After removing leading whitespace only, exact uppercase ASCII `DIGR` or exact `深度迭代` is a route candidate. The remainder is deliberately not interpreted locally. The pinned startup surface decides NATIVE/HELP/INVALID/EXECUTING.

## Task-work firewall

Candidate capture closes a pre-task firewall. From the first repository acquisition until the pinned startup/protocol explicitly permits substantive work, all reasoning and tools are restricted to transport, pinning, INDEX/startup and runtime/protocol setup. Reading startup is not executing startup, and the label EXECUTING is not itself readiness. Any repository instruction to create/call/persist/verify a helper, workspace, state or receipt is an operational obligation.

This firewall exists to prevent a host from successfully acquiring STARTUP and then beginning the user task while silently skipping Run Genesis or later readiness barriers.

## Actual acquisition before failure

A candidate must cause a real repository acquisition action before any task-level route result. No-attempt is not acquisition failure. Search results, snippets, crawled/indexed GitHub pages and remembered results are inadmissible mutable-ref authority.

## `stable → SHA`

Two transport modes are valid:

1. **Already-connected GitHub repository connector:** read the repository `stable` branch resource and accept its current full 40-hex HEAD SHA. No Git-ref endpoint is additionally required in connector mode.
2. **Direct REST client:** read both Branches and Git-ref endpoints during the same route attempt and require the same full SHA. Disagreement fails closed.

Do not require a new OAuth/connector solely to bootstrap this public repository.

## Pinned content and transparent first path

Bind pinned `manifest.json` and `VERSION`, require version equality, then follow only manifest-declared paths. Pinned raw-SHA content is canonical; Contents API fallback must be raw media or decoded JSON/base64 file bytes.

When `bootstrap_index` is declared, it is the first repository-side structural path. If it is also `startup_slice[0]`, acquire it once and then continue the remaining startup paths. INDEX exposes implemented repository components, persistent objects, truth-source ownership and the native-intelligence boundary; it cannot define or override versioned execution semantics.

NATIVE/HELP avoid unnecessary full protocol loading. EXECUTING follows the pinned startup rules and keeps the task-work firewall closed while crossing repository-defined readiness gates, then acquires the same-SHA execution bundle when present (otherwise logical entry/core individually). Verified members remain entry/core authority and produce the receipt required by that protocol.

Legacy manifests retain their own declared navigation. Once P_run exists, startup/runtime failure is not route failure and cannot silently degrade into an ordinary answer.
