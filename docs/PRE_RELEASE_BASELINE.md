# 5.0.0-alpha.10 Liveness-Contraction Baseline

Alpha 10 is a contraction pass over Alpha 9. It does not add another supervisory layer.

Normal-path rules:

1. one package attestation before Genesis, not per-helper verification;
2. seven compact authority modules, not eighteen;
3. source work only when task necessity justifies it;
4. omitted D=0 and compact D persistence by default;
5. append/revision persistence without global checkpoint on every state change;
6. ordinary resume = repair + batched journal reindex + single store load + clock resume;
7. full revision-tree repair/audit only after detected inconsistency or explicit audit.

The retained strict invariants are P_run/U0/contract identity, exact package identity, current-result R/r, evidence/state bindings, explicit hard timing, D reintegration and irreversible FINISH.

This release should be evaluated primarily on whether long, tool-using DIGR runs now reach delivery without reliability machinery consuming the task budget.
