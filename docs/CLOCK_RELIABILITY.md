# Clock Reliability — Alpha 9

Clock readiness starts only after package/protocol preflight.

A run may contain multiple trusted epochs. On continuity failure: close old attributable work at the last persisted old snapshot, record a zero-credit continuity gap, establish >=3 internally consistent samples for a new epoch, then optionally restart a leased semantic state.

Verified intervals before and after the break remain valid. The cross-epoch gap is never counted.

Work leases still allow same-epoch bridge credit; they never authorize waiting, padding, META or cross-epoch guessed time.

T = MAIN + SOURCE + D_EXCLUSIVE; t = SOURCE. Hard actuals are sums of individually hard-verifiable counted intervals. Coverage completeness remains diagnostic.
