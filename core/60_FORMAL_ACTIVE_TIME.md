# Formal Active Time and Trusted Clock

Every EXECUTING run opens a trusted monotonic clock with at least three samples before parameter resolution/U0/task work. Work states remain `MAIN`, `SOURCE`, `D_EXCLUSIVE`, `META`, `IDLE`: T counts MAIN+SOURCE, t counts SOURCE only; exclusive D, META and IDLE do not count.

Observed duration and hard-verifiable duration are distinct facts. `B=0` / `b=0` makes T/t a soft target rather than a mechanical lower-bound gate. `B=1` / `b=1` upgrades the corresponding target to a hard lower bound and requires continuity evidence for every interval used in the claim. If continuity cannot be proven, hard actual is unknown (`?`) rather than estimated.

Across process/session boundaries Alpha 4 requires same provider plus equal non-empty boot identity even for observed monotonic continuity. Resume does not charge the unknown inter-process gap as task work; it appends a new resume readiness sequence after proving the bridge.

No sleep, waiting, repeated query, mechanical rewrite or logging may pad T/t. Formal time measures useful active work, not wall-clock occupation. Repository pinning, startup-slice/core loading, META contract setup and other initialization/reliability work remain outside T/t unless they themselves become substantive MAIN/SOURCE task work.
