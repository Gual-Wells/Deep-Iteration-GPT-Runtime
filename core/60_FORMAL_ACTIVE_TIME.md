# 60 — Formal Active Time

T = MAIN + SOURCE + D_EXCLUSIVE. t = SOURCE. META/IDLE never count.

B/b default to 0. Soft timing is descriptive guidance and never forces WorkLease, cross-host persistence or waiting. Explicit B=1/b=1 requires counted intervals to be hard-verifiable.

A run may contain multiple trusted clock epochs. Verified intervals from different epochs may be summed. Cross-epoch discontinuity receives zero credit and is recorded diagnostically; it does not invalidate prior verified intervals or the run.

WorkLease may bridge same-epoch attribution when that credit matters. Unleased or cross-epoch gaps are excluded rather than estimated.

Waiting, padding, protocol bookkeeping and pure recovery are not formal task time.
