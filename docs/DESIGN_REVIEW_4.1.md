# Design Review — 4.1.0

## Why 4.1 instead of another 4.0 patch
4.0's execution semantics were largely sound, but its control plane contradicted its own authority claim. The local personalization said it was “only a loader” while defining root-gate existence, universal clock ordering, no-fallback and P_target rules. That made the loader a hidden pre-protocol and allowed anti-contamination logic itself to contaminate a legacy P_run.

4.1 fixes the boundary rather than adding another gate.

## New invariant
`Local Router -> immutable repository discovery -> explicit delegation -> repository protocol semantics`

The local layer may decide only how to locate and load authority. It cannot decide what the authority means.

## Legacy cleanliness
A manifest without `bootstrap_entry` is routed through its own `entrypoint` + `core`; no 4.1 startup rule is applied before that legacy protocol loads. Thus a 3.0 P_run is allowed to be 3.0, rather than being rejected for not containing a future 4.1 gate.

## Context semantics
4.1 does not pretend to detect hidden neural contamination. Instead it makes protocol decisions auditable by provenance: versioned DIGR decisions come from P_run. Context can still supply U0/evidence.

## Retained execution model
Unified partial invocation, B/b/L fixed defaults, semantic completion, N/R/S/D/L, EST, ABG, Formal Active Time, strict hard verification, source aggregation, isolation evidence and canonical proof remain.

## Deliberate non-goals
No fixed difficulty classifier, workload table, numeric ambition/coup algorithm, BFS/DFS/MCTS, mandatory multi-agent system, learned controller or heavy default logging.
