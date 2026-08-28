# Clock Reliability — Berta1

The standard profile has no T/t time requirement. Hard time exists only through explicit `min=<duration>` and requires continuous trusted monotonic-clock capability during local preflight. `target=<duration>` is soft. ClockJournal projects `T=MAIN+SOURCE`, `t=SOURCE`, `D=D_EXCLUSIVE`, and `V=V_EXCLUSIVE`; META/IDLE count nowhere and D/V never inflate T.

Clock Genesis happens after parameter/capability preflight and descriptor artifact verification, immediately before workspace creation. Only substantive MAIN/SOURCE intervals count. META, transport, waiting, polling, journaling, mechanical rewriting and exclusive D never pad time.

Cross-session continuity requires matching provider and non-empty boot identity. Unknown continuity stays unknown; proof never estimates or rounds actual time upward.
