# Formal Active Time and Trusted Clock

Every EXECUTING run establishes trusted monotonic readiness only after full execution-package/protocol readiness.

T = MAIN + SOURCE + D_EXCLUSIVE. t = SOURCE. META/IDLE do not count.

B/b default to 0. Explicit B=1/b=1 requires the target to be reached by hard-verifiable counted intervals.

Hard proof is interval-local, not dependent on one immortal clock lineage. Verified intervals from multiple trusted epochs may be summed. A clock-epoch discontinuity contributes no guessed time and marks coverage incomplete, but does not invalidate prior verified intervals or the run.

A same-epoch work lease may preserve attribution across a host boundary. A cross-epoch lease may restore semantic state only from the new epoch; the discontinuity itself is never charged.

Waiting, padding, logging and pure META never count.
