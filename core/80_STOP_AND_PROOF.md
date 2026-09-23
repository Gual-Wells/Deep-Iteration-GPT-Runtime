# 80 — Stop, Finalization and Proof

Stopping requires semantic completion plus applicable mechanical commitments:
- N/R minima;
- source instance/n/r only when SourceDisposition=REQUIRED;
- D minimum;
- explicit hard T/t when B/b=1.

Soft T/t never block delivery. Coverage gaps never inflate counted time.

Finalization admission occurs while EXECUTING and before FINISH. Once FINISH is durably journaled, formal timing never reopens.

Normal finalization performs one artifact-integrity scan after compacting the index-delta WAL and before FINISHED. It does not rerun the full semantic/recovery audit or repository startup. Full workspace semantic audit remains explicit/anomaly-only.

Visible output remains result first, then canonical proof:
`DIGR（N_target/N_actual，T_target/T_actual，R_target/R_actual，B，S_i（n_target/n_actual，t_target/t_actual，r_target/r_actual，b），D(target)/D(actual)）`

Actual durations floor to whole seconds. Hard-unverified actual time is not claimed.
