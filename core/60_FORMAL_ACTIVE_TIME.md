# Formal Active Time and Trusted Clock

Every EXECUTING run establishes trusted monotonic clock readiness before parameter resolution/U0/task work.

Foreground states are MAIN, SOURCE, D_EXCLUSIVE, META and IDLE.

Alpha 7 accounting is:

- T = MAIN + SOURCE + D_EXCLUSIVE
- t = SOURCE
- META and IDLE do not count
- D_EXCLUSIVE counts T because disruptive work is substantive task work; it does not count source time t.

Observed duration, clock verification and semantic-time coverage are distinct facts. B=1/b=1 requires both:
1. every counted interval used for the claim is hard-verifiable; and
2. the corresponding formal timeline has complete semantic coverage.

Across host/process boundaries, same provider plus equal non-empty boot identity proves clock continuity. Semantic attribution is separately carried by an explicit persisted work lease. A leased MAIN/SOURCE/D_EXCLUSIVE interval may cross one verified resume boundary and remains chargeable. An unleased formal boundary becomes an explicit coverage gap; it is never silently dropped and never guessed into a state.

For SOURCE leases, active_source_ids travel with the lease binding. Thus external tool/connector time is counted where the source work actually occurs rather than through a post-hoc receipt.

Sleep, intentional waiting, padding, repeated mechanical query, logging and pure META setup do not become formal time merely because the clock advanced. Hosts should open work leases only around substantive work whose semantic state is known.

