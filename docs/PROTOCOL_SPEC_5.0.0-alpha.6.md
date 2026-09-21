# DIGR 5.0.0-alpha.6 — Execution Integrity / Runtime Delivery

Alpha 6 preserves Alpha 5 result sovereignty, hard-by-default B/b policy, authority, clock, state and execution-protocol bundle semantics. It addresses two live host failures that Alpha 5 did not fully prevent.

## 1. Observed failure classes

### Runtime impersonation
The host correctly discovered repository helpers and understood that they were real implementations, but then read their code and reproduced the behavior manually instead of executing the declared implementation. Task-work firewall remained closed, yet deterministic runtime work was silently substituted.

### Implementation delivery gap
On a later run the host intentionally refused to substitute code, but the connected GitHub reader and Python executor were isolated. Repository source bytes could be read by the connector and Python could execute locally, yet there was no identity-preserving connector-to-executor file bridge. Direct container network access was unavailable, so exact runtime delivery failed before Genesis.

## 2. Alpha 6 correction

Alpha 6 treats execution integrity as a four-part chain:

**drift inoculation → component interrogation → execution commitment → identity-preserving delivery/execution**

The pinned repository explains the correct/incorrect patterns before operational use. Before each declared operational component, the model identifies the exact component, operation and compatible executor and explicitly rejects substitution/manual-result construction. An incomplete or penetrating answer receives at most two lightweight correction rounds. Acceptance constrains the next relevant action to real delivery/execution attempt or concrete failure.

Semantic equivalence never establishes implementation identity.

## 3. Runtime distribution

manifest.runtime_distribution declares a same-commit GitHub Actions artifact. Its artifact name is bound to the immutable commit SHA. The ZIP contains manifest.json, VERSION, every deterministic_helpers member and RUNTIME-INDEX.json.

The runtime index records each helper's byte length and Git blob identity. The host verifies the downloaded artifact against the pinned Git tree before executing it. The Actions artifact is transport only; the pinned repository remains authoritative.

A native same-SHA file-to-executor bridge remains preferred when available. The artifact is the standardized fallback for hosts where repository-reading and code-execution capabilities are isolated.

## 4. Failure semantics

No exact implementation delivery path means **implementation-delivery failure**. It is not permission to rewrite runtime code and not permission to start the user's task natively.

Once an execution commitment is accepted, reading more code, implementing an equivalent algorithm or fabricating expected receipts before an actual attempt is an execution-integrity violation.

## 5. Scope

Alpha 6 does not replace native intelligence with a scheduler and does not require verbose user-visible self-talk. The interrogation is a compact structured commitment; hidden chain-of-thought is neither requested nor stored. Runtime-integrity mechanics are local to operational boundaries and should disappear once the declared component has actually run.
