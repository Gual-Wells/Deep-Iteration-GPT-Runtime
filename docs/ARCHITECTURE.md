# DIGR 5.0 Alpha 2 Architecture

Alpha 2 separates four planes that Alpha 1 partially conflated:

1. **Transport/authority:** local broad route → immutable repository pin → pinned startup/full protocol.
2. **Commitment/lifecycle:** clock genesis, parameter resolution, U0, Effective Contract, RunPhase.
3. **Mutable native working state:** Strategy, Candidate, EST, Source workspaces, D interventions, completion gaps.
4. **Evidence/audit:** clock/source-activity/event journals, evidence, isolation receipts, artifact index, run brief, final summary.

The first two are deterministic reliability boundaries. The third belongs to native intelligence: stores are external memory, not an algorithmic controller. The fourth makes actuals/recovery auditable without exposing hidden chain-of-thought.

## Single-truth relationships
- Strategy owns current execution approach; Candidate owns current result snapshot; EST only compresses continuing state and references revisions.
- FormalTimeLedger/clock journal own T/t; source activity only binds SOURCE intervals to actual S IDs, never recomputes a second time total.
- IsolationReceipt owns D's actual L; host capability alone never becomes L_actual.
- Authoritative stores own state; Run Brief is derived and may be regenerated.

## Mutable versus frozen
Frozen: `P_run`, U0, user hard constraints, Effective Contract minima.
Revisionable: task model, decomposition, routes, source/validation/tool strategies, assumptions/risks, candidates, source objectives/directions, D proposals before decree, completion gaps and EST.

This distinction is the primary defense against a protocol becoming a workflow that traps GPT in its initial plan.
