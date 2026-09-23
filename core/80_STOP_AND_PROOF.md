# Stop, Finalization Admission and Visible Proof

Mechanical gates are N/R/n/r/D minima plus B/b-governed timing. L is not a public or stopping dimension.

For hard timing, the counted duration must reach its target and every counted interval used for that claim must be hard-verifiable. Verified intervals may come from multiple trusted clock epochs; epoch discontinuities themselves are excluded. Unattributed gaps are excluded from the number rather than estimated. Therefore incomplete coverage means the displayed/recorded T/t is a **verified lower bound**, not a complete wall-accounting total; it does not by itself block delivery.

If SourceDisposition is WAIVED, source instance/n/r/t gates are non-applicable.

Finalization uses an admission gate **before** timing is closed. While still EXECUTING, the runtime projects a finish at the proposed snapshot and evaluates the resulting mechanical actuals. If an applicable minimum or hard timing gate fails, finish is denied and the live ledger remains open in EXECUTING. Semantic completion must also be ready.

Once FINISH is durably journaled, crash recovery treats it as committed. A missing FINALIZING phase write or a valid final-summary/FINISHED phase crash window is repaired mechanically rather than resurrecting formal timing.

The visible result comes first, followed by canonical proof:

`DIGR（N_target/N_actual，T_target/T_actual，R_target/R_actual，B，S_i（n_target/n_actual，t_target/t_actual，r_target/r_actual，b），D(target)/D(actual)）`

L is intentionally absent. Actual durations are floored to whole seconds. With B/b=1, an actual is shown only when its counted intervals are hard-verifiable; coverage completeness remains available in machine/audit state.

