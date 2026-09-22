# DIGR 5.0.0-alpha.8 — Convergence and Crash Recovery

Alpha 8 is a convergence release over Alpha 7. It keeps immutable P_run/U0/contract authority, implementation-identity delivery, trusted clocks, Source/D/R semantics and compact proof while reducing reliability overhead and repairing crash windows.

## 1. Verified lower-bound timing

T remains MAIN + SOURCE + D_EXCLUSIVE; t remains SOURCE. B/b=1 now means a hard lower bound over counted hard-verifiable intervals.

An unleased host/process gap is retained as coverage evidence and excluded from T/t. Because excluded time cannot inflate a lower-bound claim, incomplete coverage is diagnostic rather than a separate stop gate. Missing a lease forfeits time credit; it does not permanently poison the run.

SourceDisposition=WAIVED makes source instance/n/r/t mechanical gates non-applicable even when the structural b default remains 1.

## 2. Crash-safe workspace recovery

Ordinary artifact writes use a single-slot write intent around target replacement plus artifact-index commit. Recovery may:

- complete indexing when intended content is already present;
- roll back an uncommitted write when prior content remains;
- fail closed when content matches neither prior nor intended digest.

Append-only clock/source/event journals may refresh artifact-index digests only after their own sequence/hash-chain verification succeeds.

Immutable revision history is authoritative over derived latest pointers and run-brief. Recovery may rebuild those derived views but may not invent U0, contract facts, Strategy content, source findings, semantic events or D conclusions.

## 3. Durable finalization

The FINISH clock-journal event is the durable formal-time commit point.

If a crash occurs after FINISH but before phase=FINALIZING, resume reconstructs a finished ledger and completes the missing lifecycle transition. If a valid final summary was durably written before phase=FINISHED, recovery may verify the summary and complete FINISHED.

Formal time never reopens after committed FINISH.

## 4. Current-result re-entry

MAIN R and source r are current-result challenges rather than arbitrary historical-revision challenges.

Retained re-entry binds the current result revision. Changed re-entry ends at the current revision. Persisted re-entry history may not move backward to a result already superseded by an earlier re-entry.

## 5. D isolation closure

Public L remains removed. Active D semantics use fixed internal L1.

For exclusive D, both execution and D Result production remain clock/state-bound to D_EXCLUSIVE. Only explicit reintegration returns selected consequences to MAIN.

Historical L2/L3 storage structures may remain for compatibility but are not active Alpha 8 user semantics.

## 6. Release convergence

Current-facing schemas/docs/examples identify Alpha 8 behavior. Obsolete active L2/L3 examples are removed.

Release cleanup never deletes repository .git metadata. Stable validation must detect checked-in generated metadata drift rather than silently validating a repaired temporary tree.

## 7. Design constraint

Alpha 8 does not add a new supervisory reasoning layer. Reliability work should remain deterministic and cheap on the normal path, with expensive recovery logic paid only after an actual interruption or persisted inconsistency.
