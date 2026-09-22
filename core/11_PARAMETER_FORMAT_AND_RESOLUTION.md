# Parameter Format and Resolution

Public parameter order is:

`N < T < R < B < S < D`

Inside S:

`n < t < r < b`

L is not a public parameter in Alpha 7. Any invocation that attempts to provide L/L()/L= or an equivalent L field is INVALID. D isolation uses the internal fixed L1 baseline defined by the implementation-isolation core; L is neither semantically completed nor returned in canonical proof.

B and b default deterministically to 1. Missing N/T/R/n/t/r/s are semantically completed only after Clock Genesis and verified protocol load. Bare numerics never acquire duration semantics. Mixed positional/labeled syntax must resolve to one legal mapping or fail AMBIGUOUS/INVALID.

S and D markers remain legal anchors. S() leaves n/t/r for semantic completion while b keeps its deterministic default. D() leaves s for semantic completion. D(0) means zero completed-D minimum, not “disable D”.

