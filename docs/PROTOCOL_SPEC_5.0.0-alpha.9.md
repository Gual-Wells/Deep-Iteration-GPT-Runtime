# DIGR 5.0.0-alpha.9 — Liveness Convergence

Alpha 9 repairs the systemic long-run liveness regression accumulated across Alpha 5–8.

## Pre-Genesis readiness
All mandatory runtime delivery and full protocol verification move before Genesis. The exact-commit runtime artifact carries deterministic helpers plus the same-commit execution bundle. RUNTIME-INDEX schema 2 binds commit, manifest, VERSION, helper Git-blob identities and bundle identity. Failed preflight creates no born run.

## Multi-epoch clock
Same-epoch resume remains strongest. If continuity cannot be established, the run opens a fresh trusted epoch instead of aborting. Prior verified intervals remain valid; the discontinuity gets zero T/t credit; leased semantic work may restart at the new epoch.

## Hot-path reduction
Append-only journals and immutable revisions remain authoritative. run-brief/latest derived cache work moves to coarse checkpoints rather than every semantic event.

## Soft timing defaults
B/b return to 0. Explicit B=1/b=1 remains strict hard timing.

## Preserved safety
Immutable P_run/U0/contract, exact implementation identity, Source/R/D semantics, evidence-backed actuals, finalization admission and durable FINISH remain fail-closed.
