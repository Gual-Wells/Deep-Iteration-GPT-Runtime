# Source Requirement Matrix

| Condition | SourceDisposition | Actual S required? |
|---|---|---|
| Normal invocation / S omitted (`source=auto`) | task-grounded REQUIRED or WAIVED | only when REQUIRED; WAIVED needs a concrete reason |
| `source=auto` and external evidence can materially improve correctness | REQUIRED | yes, with evidence-backed source activity |
| `source=auto` closed transformation where external material is prohibited or genuinely irrelevant | WAIVED with reason | no |
| `source=required` | REQUIRED | yes; missing source-tool capability blocks enforced startup |
| `source=off` | WAIVED by explicit policy | no; non-zero S minima are invalid |
| Legacy-compatible explicit non-zero S minimums | REQUIRED | yes, all frozen minima apply |

Berta1 never semantically completes omitted S numeric minima. WAIVED with non-zero S minimums is contradictory and rejected. SOURCE timing requires active S IDs and uses clock interval union, so parallel source work never double counts t.
