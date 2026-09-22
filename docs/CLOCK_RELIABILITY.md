# Clock Reliability — Alpha 8

Every EXECUTING run establishes >=3 compatible monotonic samples before parameter resolution, U0 or task work. The append-only clock journal records provider/session/boot identity, monotonic/wall readings, event type and semantic work state.

Three facts remain distinct:

1. observed duration;
2. hard clock verification of counted intervals;
3. semantic-time coverage.

B/b=1 is a lower-bound claim over **counted hard-verifiable intervals**. Complete coverage is not required to prove a minimum because unattributed gaps are excluded rather than estimated. A gap therefore reduces the proved lower bound but cannot inflate it.

## Cross-host work leases

Before known MAIN/SOURCE/D_EXCLUSIVE work leaves the runtime for another host/process/tool, a work lease can carry that semantic state through the next verified same-provider/same-boot resume. SOURCE leases carry active source IDs.

Without a lease, the interval becomes a CoverageGap and receives no T/t credit. It remains visible for audit.

## Accounting

- T = counted MAIN + SOURCE + D_EXCLUSIVE
- t = counted SOURCE
- META/IDLE do not count
- parallel sources share the SOURCE time union

Waiting, sleep, padding, logging and mechanical query must not be converted into formal time merely by opening a lease.

