# Stop, Finalization Admission and Visible Proof

Mechanical gates are N/R/n/r/D minima plus B/b-governed timing. L is not a public or stopping dimension.

For hard timing, a target is satisfied only when the duration target is reached, relevant intervals are hard-verifiable, and semantic-time coverage is complete. Unattributed formal gaps therefore fail hard timing even when their clock duration is itself measurable.

Finalization uses an admission gate **before** timing is closed. While still EXECUTING, the runtime projects a finish at the proposed snapshot and evaluates the resulting mechanical actuals. If any required minimum, hard timing gate or coverage gate fails, finish is denied and the live ledger remains open in EXECUTING. Semantic completion must also be ready.

Only an admitted run may close the ledger, append FINISH and enter FINALIZING. write_run_summary must refuse to transition FINISHED unless delivery readiness is true. A FINISHED run with delivery_ready=false is invalid.

The visible result comes first, followed by canonical proof:

`DIGR（N_target/N_actual，T_target/T_actual，R_target/R_actual，B，S_i（n_target/n_actual，t_target/t_actual，r_target/r_actual，b），D(target)/D(actual)）`

L is intentionally absent. Actual durations are floored to whole seconds for display. With B/b=1, incomplete clock verification or incomplete semantic-time coverage renders the corresponding actual as ? rather than publishing a misleading partial duration.

