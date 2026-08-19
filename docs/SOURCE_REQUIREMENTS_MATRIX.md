# Source Requirement Matrix

| Condition | SourceDisposition | Actual S required? |
|---|---|---|
| Normal DIGR invocation | REQUIRED | yes, at least one |
| S omitted / S / S() | REQUIRED | yes; numeric minima are semantically completed |
| S(0,0s,0,0) | REQUIRED | yes; zero minima do not disable source presumption |
| User explicitly forbids external sources and contract accepts that | WAIVED | no |
| Closed transformation where external material cannot improve result | WAIVED with reason | no |
| No usable external channel in host | WAIVED with reason | no |

WAIVED with non-zero S numeric minimums is contradictory and rejected. SOURCE timing requires active S IDs and uses clock interval union, so parallel source work never double counts t.
