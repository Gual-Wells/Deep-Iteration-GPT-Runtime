# Effective Contract

The Effective Contract freezes task commitments, never strategy. Alpha 7 contract fields are:

- MAIN: N, T, R, B
- Source: S(n,t,r,b)
- D: minimum completed/reintegrated interventions s
- SourceDisposition plus any explicit waiver reason

L is intentionally absent from the contract. D isolation is an internal fixed L1 reliability rule, not a user-tunable target.

N/R/n/r/D are lower bounds. T/t are B/b-governed timing targets. B=1 or b=1 makes the corresponding target a hard lower bound and therefore requires trusted clock continuity plus complete semantic-time coverage. B=0/b=0 leaves timing soft.

SourceDisposition is REQUIRED unless U0/host reality gives a concrete waiver reason. Zero numeric source minima do not themselves waive source use.

