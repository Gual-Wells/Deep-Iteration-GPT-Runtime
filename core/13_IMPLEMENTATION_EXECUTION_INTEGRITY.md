# 13 — Implementation Execution Integrity

DIGR distinguishes **operating a declared implementation** from merely understanding or reproducing its behavior. When the pinned repository already provides an operational component for a required step, implementation identity has precedence over semantic equivalence.

## Drift inoculation

Before the first operational component is used, the host/model must explicitly recognize the main failure mode:

- **Correct:** bind the exact pinned component, select a host channel that can actually execute it, then execute that component and consume its real result.
- **Incorrect:** read/understand the component and then reproduce, translate, simulate, manually reconstruct, or fabricate an equivalent result/receipt.

Knowing what code does is not evidence that the code ran. A semantically equivalent reimplementation is not the declared implementation.

## Component interrogation gate

Immediately before a repository-declared operational component is used, the model must form a compact structured commitment that answers all of the following without hidden chain-of-thought:

1. Which exact pinned component is about to be operated?
2. Which concrete operation/function is being invoked?
3. Which available host execution channel will actually run that implementation?
4. Is direct execution selected now?
5. Are model-written substitution, cross-language reimplementation, manual receipt construction and semantic simulation explicitly rejected?

A generic statement such as “I will follow the protocol” is insufficient. The commitment must identify the concrete component and execution channel.

If the answer is incomplete, ambiguous, or chooses substitution, insert one lightweight corrective reminder of the execute-vs-penetrate distinction and interrogate again. At most two corrective rounds are allowed. Repeated failure is a startup/runtime integration failure, not permission to continue task work.

## Execution commitment

Once the gate accepts a commitment, the next relevant action is constrained to one of:

- an actual attempt to deliver/materialize the exact pinned implementation into a compatible executor;
- an actual attempt to invoke that exact implementation;
- recording a concrete delivery/execution failure.

New semantic analysis, alternate implementation, manual result construction or task work between accepted commitment and actual execution attempt reopens the gate and is non-conforming.

## Substitution boundary

A declared implementation may be substituted only when:

- an actual direct execution/delivery attempt has failed;
- the pinned protocol explicitly permits a compatibility fallback; and
- the fallback preserves implementation identity or is explicitly defined as a different authoritative path.

“Same algorithm”, “same output”, “easier in another language”, or “I already understand it” are never sufficient substitution grounds.

## Implementation delivery

Execution intent is useless if repository bytes cannot reach an executor. Alpha 6 therefore treats **implementation delivery** as a first-class startup concern.

When the host already has a native same-SHA file-to-executor bridge, use it. Otherwise, if manifest.runtime_distribution declares an immutable same-commit artifact path, acquire that artifact for the exact P_run commit, materialize it into the executor, and verify its member identity against the pinned Git tree before execution.

Artifact transport is not protocol authority. The pinned repository remains authoritative; the artifact is only a byte-delivery vehicle.

A missing exact-commit artifact plus no native identity-preserving bridge is an implementation-delivery failure. It must not be converted into model-written runtime code.

## Result sovereignty

These gates exist to prevent silent runtime impersonation, not to add bureaucracy. They should remain compact and local to actual operational boundaries. Once the declared component has executed successfully, return control to native intelligence immediately.
