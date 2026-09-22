# Formal Active Time and Trusted Clock

Every EXECUTING run establishes trusted monotonic clock readiness before parameter resolution/U0/task work.

Foreground states are MAIN, SOURCE, D_EXCLUSIVE, META and IDLE.

Alpha 8 accounting is:

- T = counted MAIN + SOURCE + D_EXCLUSIVE
- t = counted SOURCE
- META and IDLE do not count
- D_EXCLUSIVE counts T because disruptive work is substantive task work; it does not count source time t.

Observed duration, hard clock verification and semantic-time coverage are distinct facts. B=1/b=1 requires every **counted interval used for the lower-bound claim** to be hard-verifiable. Complete coverage is desirable but not required for a lower-bound target: an unattributed gap is excluded, never estimated, so it cannot inflate T/t.

Across host/process boundaries, same provider plus equal non-empty boot identity proves clock continuity. Semantic attribution is carried by an explicit persisted work lease. A leased MAIN/SOURCE/D_EXCLUSIVE interval may cross one verified resume boundary and remains chargeable. An unleased formal boundary becomes an explicit coverage gap and receives no formal-time credit.

For SOURCE leases, active_source_ids travel with the lease binding. Thus external tool/connector time is counted where the source work actually occurs rather than through a post-hoc receipt.

Sleep, intentional waiting, padding, repeated mechanical query, logging and pure META setup do not become formal time merely because the clock advanced. Hosts should open work leases only around substantive work whose semantic state is known. Missing a lease is conservative under-counting, not permission to retroactively guess the gap.

