# Result-backed re-entry

## MAIN R

A MAIN whole-process re-entry is not a naked counter increment. It binds a real `candidate_before`, independently challenges the result/process, and then either binds a newer `candidate_after` or records justified retention.

```text
MAIN_REENTRY
candidate_before = candidate rev 3
challenge = attack the routing/startup assumption and validation route
action = construct a failed-clock counterexample and rerun the process
outcome = retain rev 3 after independent failure-path verification
retained = true
clock = a real MAIN state event
strategy = current Strategy revision
```

The challenge may rewrite the whole Strategy; the runtime verifies references and lifecycle, not whether the intellectual challenge is “good enough.”

## Source r

Source re-entry is backed by the SourceWorkspace result/revision instead of requiring a global Main Candidate. A retained source result binds `source_before`; a changed one binds a newer `source_after`. This lets S evolve independently while remaining auditable.
