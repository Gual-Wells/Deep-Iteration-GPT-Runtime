# 13 — Implementation Execution Integrity

DIGR distinguishes **operating a declared implementation** from merely understanding or reproducing its behavior. When the pinned repository already provides an operational component for a required step, implementation identity has precedence over semantic equivalence.

## Drift inoculation

At each implementation-delivery boundary, the host/model explicitly distinguishes:

- **Correct:** exact pinned package/component → compatible executor → direct invocation → real result.
- **Incorrect:** read/understand component → rewrite/translate/simulate equivalent behavior → hand-construct the expected receipt/result.

Knowing what code does is not evidence that it ran.

## Delivery binding

The interrogation/commitment gate is paid **once when implementation identity is established for a concrete pinned runtime package and executor**, not before every subsequent helper call from that same verified binding.

The compact binding records, at minimum:

1. pinned commit/package identity;
2. concrete executor/channel;
3. direct execution selected;
4. semantic substitution/manual receipt construction rejected.

Once accepted, the next relevant action must be actual delivery/invocation or a concrete failure. After the package has executed successfully, later operations from the same package/executor proceed directly without repeated cognitive interrogation.

Re-open the gate only when:
- a different runtime package/component delivery path is introduced;
- the executor/channel changes in a way that breaks prior identity evidence;
- resume cannot establish that the previously verified binding still applies;
- an actual direct execution/delivery attempt fails and a repository-declared fallback is considered.

This keeps integrity machinery proportional to real identity boundaries rather than ordinary helper-call frequency.

## Substitution boundary

A declared implementation may be substituted only when an actual direct execution/delivery attempt failed and the pinned protocol explicitly permits another authoritative compatibility path. “Same algorithm”, “same output”, “easier in another language”, or “I understand it” are never sufficient.

## Implementation delivery

When the host already has a native same-SHA file-to-executor bridge, use it. Otherwise use a manifest-declared identity-preserving runtime distribution path for the exact P_run commit and verify member identity against the pinned Git tree before execution.

Runtime transport is never protocol authority. A missing exact-commit delivery path plus no native bridge is an implementation-delivery failure, not permission to synthesize runtime code.

## Result sovereignty

These gates exist to prevent silent runtime impersonation, not to become a competing reasoning objective. Verification should be deterministic and coarse-grained at real delivery/resume boundaries; once the binding is valid, return attention to the user's task.
