# Effective Contract

The Effective Contract freezes task commitments, never strategy. Alpha 9 contract fields are:

- MAIN: N, T, R, B
- Source: S(n,t,r,b)
- D: minimum completed/reintegrated interventions s
- SourceDisposition plus any explicit waiver reason

L is absent from the contract. D isolation is internal fixed L1.

N/R/n/r/D are lower bounds. T/t are B/b-governed timing targets. B=0/b=0 leaves timing soft and is the Alpha 9 fixed default. Explicit B=1 or b=1 makes the corresponding target a hard lower bound over counted, hard-verifiable intervals.

Verified hard intervals may come from more than one trusted clock epoch. Unattributed and cross-epoch gaps are excluded rather than estimated; they reduce coverage but do not invalidate the run or already verified intervals.

SourceDisposition is REQUIRED unless U0/host reality gives a concrete waiver reason. Zero numeric source minima do not waive source use. When SourceDisposition is WAIVED, source instance/n/r/t timing gates are non-applicable regardless of the structural b value.

The contract freezes minimum commitments and timing policy, not Strategy/Candidate/source/D reasoning choices.
