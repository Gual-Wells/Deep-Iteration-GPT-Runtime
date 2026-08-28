# Source Evolution — Automatic Evidence Decision

Berta1 uses `source=auto`. The model chooses real source work when evidence can materially improve correctness, or records `SourceDisposition=WAIVED` with a concrete, task-grounded reason (for example a closed transformation where external material is prohibited or genuinely irrelevant). External source is broad: web, official docs, repositories/code, user files, datasets, papers, community material, tool/test outputs or any information not solely from model prior.

## What counts as an actual S

Opening a SourceWorkspace is only state preparation. For Source Presumption/completion, an actual S must be supported by **both**:

- a formal `SOURCE` clock state whose source-activity binding names that SourceWorkspace; and
- at least one semantic `SOURCE_EVOLUTION` or `SOURCE_REENTRY` receipt bound to that SOURCE state and a real source revision.

This prevents an empty S object from satisfying the external-research obligation.

## Revision and re-entry

Each S is revisioned: objective, current direction, findings, contradictions, evidence and pivot/reopen history. A source may OPEN → pivot → continue → close → reopen. Distinct research directions may use S2/S3, while minor pivots can revise the same S.

Source `r` is SourceWorkspace-result/revision backed, not dependent on a global Main Candidate. A re-entry binds `source_before`; if the result changes it must bind a newer `source_after`, while independent challenge with justified retention may retain the before revision.

## Time

Formal aggregate source time `t` has one truth source: clock-journal SOURCE intervals. Every SOURCE state-start is bound to a non-empty `active_source_ids` set. `t` is the union of time when any real S is active; parallel/concurrent sources never double-count, and a floating SOURCE state without real source binding is invalid.
