# Formal Active Time and Trusted Clock

Every EXECUTING run opens a trusted monotonic clock with at least three samples before parameter resolution/U0/task work. Work states remain `MAIN`, `SOURCE`, `D_EXCLUSIVE`, `META`, `IDLE`: T counts MAIN+SOURCE, t counts SOURCE only; exclusive D, META and IDLE do not count.

Observed duration and hard-verifiable duration are distinct facts. Hard B/b requires continuity evidence for every interval used in the claim. If continuity cannot be proven, hard actual is unknown (`?`) rather than estimated.

Across process/session boundaries Alpha 2 requires same provider plus equal non-empty boot identity even for observed monotonic continuity. Resume does not charge the unknown inter-process gap as task work; it appends a new resume readiness sequence after proving the bridge.

No sleep, waiting, repeated query, mechanical rewrite or logging may pad T/t. Minimum time is a floor for useful active work, not a wall-clock occupation target.
