# Engineering Validation Log — DIGR 5.0.0 Alpha 8

This log records the current engineering acceptance focus. It is not protocol authority and does not treat a green test suite as proof of design correctness.

Alpha 8 was driven by full-tree audit findings in the Alpha 7 stable baseline:

- SourceDisposition=WAIVED could still be blocked by default b=1 hard-t mechanics.
- FINISH could be durably journaled before phase=FINALIZING and then be incorrectly resurrected on resume.
- ordinary workspace writes and derived latest pointers had recoverable crash windows that were treated as fatal integrity drift.
- R/r accepted historical revisions too freely.
- D Result production was not clock-bound to the isolation state.
- complete coverage was unnecessarily required for lower-bound hard timing, making one missed work lease poison an otherwise valid run.
- release cleanup could delete .git when run directly in a real checkout.
- proof schema/examples/docs had drifted from the L-free Alpha 7 runtime.

Alpha 8 fixes these by conservative lower-bound timing, deterministic crash-prefix recovery, current-result re-entry constraints, D-result state binding, source-waiver closure, release cleanup safety and public-surface convergence.

Acceptance for this release requires direct source/runtime review, exact generated-bundle comparison, deterministic cold packaging and targeted execution of the changed recovery paths. Automated tests remain regression aids, not substitutes for this audit.

