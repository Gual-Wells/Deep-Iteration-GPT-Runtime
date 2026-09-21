# DIGR 5.0 Alpha 6 Architecture

Alpha 6 retains five planes and adds an execution-integrity boundary across the first three. Alpha 2 separated the execution/state planes; Alpha 4 made the previously implicit host-transport plane explicit.

1. **Host repository transport:** actual direct acquisition → mutable `stable` corroboration → immutable pinned bytes + attempt receipts.
2. **Transport/authority verification:** candidate route → pinned manifest/VERSION → transparent machine index → startup/full protocol discovery.
3. **Commitment/lifecycle:** clock genesis, parameter resolution, U0, Effective Contract, RunPhase.
4. **Mutable native working state:** Strategy, Candidate, EST, Source workspaces, D interventions, completion gaps.
5. **Evidence/audit:** clock/source-activity/event journals, evidence, isolation receipts, artifact index, run brief, final summary.

The first three are deterministic reliability boundaries. Before startup interpretation, `bootstrap/INDEX.md` provides a pinned structural view of all five planes: implemented component classes, authoritative truth sources and the line between deterministic support and native intelligence. It is a lens over the architecture, not a sixth plane and not execution-semantic authority. The fourth belongs to native intelligence: stores are external memory, not an algorithmic controller. The fifth makes actuals/recovery auditable without exposing hidden chain-of-thought.

## Transport single-truth relationships
- Mutable branch authority comes from direct current GitHub observations, never search/index snapshots.
- REST mode accepts `stable` only when Git-ref and Branches endpoints agree on one full SHA.
- Once pinned, the SHA—not `stable`—is the identity used by all later resource URLs.
- `AcquisitionAttemptReceipt` proves that routing actually attempted repository transport; it does not by itself prove the route succeeded.
- Raw immutable SHA content is the primary file transport. Contents API wrapper decoding is an adapter, not a second authority source.

## Execution-integrity boundary

Repository transparency must not collapse operator and implementation roles. For a declared operational component, the model/host first binds exact pinned component identity, exact operation and a concrete compatible executor; it then commits to direct execution and rejects semantic-equivalent substitution/manual receipt construction. An accepted commitment constrains the next relevant action to real delivery/invocation or a concrete failure.

Repository-reading capability and executor capability are independent. A native same-SHA file→executor bridge is preferred. When absent, manifest.runtime_distribution provides a same-commit GitHub Actions artifact. Artifact members are verified against the pinned Git tree before use. This delivery plane is transport-only and cannot redefine P_run.

## Execution single-truth relationships
- Strategy owns current execution approach; Candidate owns current result snapshot; EST compresses continuing state and references revisions.
- FormalTimeLedger/clock journal own T/t; source activity binds SOURCE intervals to actual S IDs and never recomputes a second total.
- IsolationReceipt owns D's actual L; host capability alone never becomes L_actual.
- Authoritative stores own state; Run Brief is derived and may be regenerated.

## Mutable versus frozen
Frozen: `P_run`, U0, user hard constraints, Effective Contract commitments (count/D minima plus B/b-governed T/t targets).
Revisionable: task model, decomposition, routes, source/validation/tool strategies, assumptions/risks, candidates, source objectives/directions, D proposals before decree, completion gaps and EST.

This distinction remains the defense against turning the exoskeleton into a workflow that traps GPT in its initial plan.
