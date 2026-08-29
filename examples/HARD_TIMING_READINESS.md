# Hard timing and attestation

`DIGR(min=10min)：任务` fixes a ten-minute hard T while other task-scale values remain adaptive.

A trustworthy session-only monotonic clock may attest one uninterrupted task. If no clock exists, MODEL_NATIVE execution still proceeds, but T actual is `?`/unattested and canonical hard-time proof is unavailable. Capability gaps are proof gaps, not task-execution denial.
