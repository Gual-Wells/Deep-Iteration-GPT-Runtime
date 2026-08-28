# Formal Active Time

ClockJournal is the sole time fact stream. Its state projection yields four non-overlapping user-visible clocks:

- `T = MAIN + SOURCE`
- `t = SOURCE`
- `D_time = D_EXCLUSIVE`
- `V_time = V_EXCLUSIVE`

`META` and `IDLE` count toward none. Repository transport, tool queues, repeated polling and sleeps must be IDLE/META. D and V are excluded from T and from each other. Aggregate D/V durations are wall-time unions. Every completed D and qualified V must bind one positive owned interval; attempted, aborted and unsuccessful D/V intervals remain visible in their time logs even when they do not satisfy count minima.

Hard T/t requires continuous trusted monotonic-clock evidence. Unknown continuity stays unknown. Closing a clock records the observed transition snapshot, so delayed UI or tool return cannot inflate active work. The canonical time group is `T目标/T真实（+D真实时间，+V真实时间）`.
