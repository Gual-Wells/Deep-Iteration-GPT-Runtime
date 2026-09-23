# 13 — Implementation Execution Integrity

DIGR distinguishes operating a declared implementation from merely understanding or reproducing its behavior. When the pinned repository provides an operational component for a required step, implementation identity has precedence over semantic equivalence.

## Drift inoculation

Correct path:

`exact pinned package/component → compatible executor → direct invocation → real result`

Incorrect path:

`read/understand → rewrite/translate/simulate → hand-construct expected receipt`

Knowing what code does is not evidence that it ran.

## Alpha 9 package boundary

Implementation delivery and complete execution-protocol transport are prepared before Genesis. A manifest-declared schema-3 runtime package carries the deterministic helpers and the same-commit execution bundle. Its RUNTIME-INDEX schema 2 binds P_run commit, manifest, VERSION, helper identities and protocol-bundle identity.

The host verifies that package against the pinned Git tree and verifies the bundle against manifest entrypoint/core before a live run exists.

## Delivery binding

The execution commitment gate is paid once for a concrete verified package/executor binding, not before every helper call. It records package identity, concrete executor, direct execution selected, and rejection of substitution/manual result construction.

Re-open only when package/executor identity changes, resume cannot re-establish it, or a real direct attempt fails and a repository-declared fallback is considered.

## Substitution boundary

Semantic equivalence never establishes implementation identity. Missing exact delivery is a startup failure, not permission to synthesize runtime code.

## Result sovereignty

These gates prevent runtime impersonation; they must not become a competing reasoning objective. Verification is coarse-grained at real identity boundaries, then attention returns to the user's task.
