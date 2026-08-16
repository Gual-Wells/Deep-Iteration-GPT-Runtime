# DIGR 4.1 Entry

The local router has already pinned and loaded this repository version. This entry contains **versioned 4.1 task behavior**, not repository discovery logic.

0. **Repository P_run (already bound)**: accept only the pinned repository identity delivered by the route receipt and this commit's manifest. Do not replace it with context, memory, local protocol copies, another commit or P_target.
1. **Invocation classification (META)**: using 4.1 rules, classify the candidate as task/help/off-invalid. Help returns repository-defined help and starts no task runtime. Off/invalid does not execute DIGR.
2. **Task clock readiness (META, executing tasks only)**: before U0 or substantive task work, obtain at least two compatible trusted monotonic snapshots and verify a non-negative hard-verifiable delta. Failure means 4.1 task startup fails. No “work first, timer later”.
3. **U0 (META)**: remove the invocation head and faithfully freeze user facts, objectives, constraints, permissions, preferences and deliverables. Context can inform U0 but not protocol semantics. If U0 modifies DIGR, that material is P_target only.
4. **Explicit parameters (META)**: read explicit values. Arbitrary parameters may be missing; there is no AUTO/parameterized split.
5. **Semantic Default Completion (META)**: direct fixed defaults are `B=0`, `b=0`, `L(1)`; missing N/T/R/n/t/r/s are jointly completed from U0 + all explicit parameters + host capability.
6. **Effective Contract (META)**: freeze targets/minima. Calibration does not count as N/T/t; actual may exceed minima without mutating the contract.
7. **Native execution**: enter MAIN/SOURCE as appropriate; maintain Main EST, contract/quality-driven S, R/r, and D/L. `D(0)` disables D.
8. **Formal time**: MAIN contributes T; SOURCE contributes T+t; D_EXCLUSIVE/META/IDLE contribute neither. Hard T/t additionally require continuity verification for every claimed hard interval.
9. **Stop**: mechanical minima + Result Quality Gate; unverified hard actual cannot pass.
10. **Return (META)**: task result first; then only canonical proof. Unknown hard actual is `?`.
11. **Destroy task runtime**: non-sticky. A later candidate route repins current stable; it must not assume the previous pinned commit is still authoritative.

`DIGR/help` / `深度迭代/help` is non-executing help. It is classified by this repository version and does not create U0, task clock, contract, EST or counters.
