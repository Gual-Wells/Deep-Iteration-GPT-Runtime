# DIGR 5.0 Alpha 8 Architecture

Alpha 8 keeps DIGR as a reliability exoskeleton around native model intelligence. Deterministic code owns authority, persistence, timing, lifecycle and reference integrity; the model owns task representation, strategy, research judgment and result quality.

## Planes

1. **Repository transport and authority** — resolve mutable stable, pin immutable P_run, verify manifest/VERSION and exact implementation delivery.
2. **Lifecycle and contract** — Clock Genesis, protocol load, parameter resolution, U0, Effective Contract and RunPhase.
3. **Mutable native working state** — Strategy, Candidate, EST, SourceWorkspace, D and completion gaps.
4. **Formal time and evidence** — clock/source/event journals, evidence bindings, counted T/t and coverage diagnostics.
5. **Recovery and audit** — artifact index, immutable revision history, derived latest pointers/run brief, final summary.

bootstrap/INDEX.md is a structural lens over these planes, not semantic authority.

## Single-truth relationships

- P_run owns protocol identity.
- U0 and Effective Contract own immutable task commitments.
- Strategy owns current approach; Candidate owns current result; SourceWorkspace owns each source loop.
- ClockJournal + FormalTimeLedger own counted T/t. Coverage gaps are retained diagnostics and excluded from counted lower-bound time.
- D intervention history owns disruptive lifecycle. Public L does not exist; D uses internal L1.
- Immutable revision files are authoritative over latest-pointer caches.
- run-brief is derived and rebuildable.

## Crash recovery

Normal JSON/text writes use a single-slot write-intent so a crash between target replacement and artifact-index update can be completed or rolled back deterministically. Append-only journals may refresh their artifact-index digest only after their own chain verifies. Stale latest pointers and run-brief may be rebuilt from authoritative history.

A committed FINISH journal event closes formal timing durably. Recovery may finish missing lifecycle writes but may not reopen timing or invent semantic task state.

## Task-result sovereignty

Reliability machinery must not become a second reasoning objective. Missing work leases conservatively lose time credit instead of poisoning the run; recovery work is paid only after an actual interruption or persisted inconsistency.

