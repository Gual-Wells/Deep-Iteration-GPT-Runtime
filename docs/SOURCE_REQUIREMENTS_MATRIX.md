# Source Requirement Matrix

| Condition | SourceDisposition | Actual S required? | t/hard-t gate? |
|---|---|---:|---:|
| Normal DIGR invocation | REQUIRED | yes | according to b |
| S omitted / S / S() | REQUIRED | yes | according to b |
| S(0,0s,0,0) | REQUIRED | yes; zero minima do not disable presumption | soft because b=0 |
| User explicitly forbids external sources and contract accepts that | WAIVED | no | not applicable |
| Closed transformation where external material cannot improve result | WAIVED with reason | no | not applicable |
| No usable external channel in host | WAIVED with reason | no | not applicable |

WAIVED with non-zero n/t/r is contradictory and rejected. The structural b default may remain 1, but it does not resurrect a waived source obligation.

SOURCE timing requires active S IDs and uses clock-interval union, so parallel source work never multiplies t. Unleased source gaps are excluded from counted t and retained as audit diagnostics.

