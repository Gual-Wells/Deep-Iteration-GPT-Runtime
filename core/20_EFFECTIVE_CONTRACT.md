# Effective Contract

The Effective Contract freezes task commitments, never strategy. Alpha 8 contract fields are:

- MAIN: N, T, R, B
- Source: S(n,t,r,b)
- D: minimum completed/reintegrated interventions s
- SourceDisposition plus any explicit waiver reason

L is intentionally absent from the contract. D isolation is an internal fixed L1 reliability rule, not a user-tunable target.

N/R/n/r/D are lower bounds. T/t are B/b-governed timing targets. Explicit B=1 or b=1 makes the corresponding target a hard lower bound over **counted, hard-verifiable formal time**. Unattributed gaps are excluded rather than estimated, so they can only make the proved lower bound smaller; coverage completeness remains an audit fact, not a hard-stop prerequisite. B=0/b=0 leaves timing soft.

SourceDisposition is REQUIRED unless U0/host reality gives a concrete waiver reason. Zero numeric source minima do not themselves waive source use. When SourceDisposition is WAIVED, source instance/n/r/t timing gates are non-applicable even if the structural default b remains 1.


Alpha 9 fixed defaults are B=0 and b=0; hard timing is explicit opt-in.
