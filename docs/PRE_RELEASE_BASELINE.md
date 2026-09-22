# 5.0.0-alpha.8 Convergence / Crash-Recovery Baseline

Alpha 8 preserves the established 5.0 architecture: immutable P_run/U0/contract commitments, native Strategy/Candidate/Source/D intelligence, pinned implementation delivery, trusted clocks and compact proof.

The release is intentionally a convergence pass:

- source waiver now disables all source mechanical gates;
- hard timing is a verified counted lower bound; unleased gaps are excluded and retained as diagnostics rather than poisoning the run;
- D_EXCLUSIVE remains part of T;
- FINISH is a durable commit point and finalization crash windows are recoverable;
- ordinary workspace writes have a single-slot recovery intent;
- append-only journals may re-index only after chain verification;
- immutable revision history may rebuild derived latest pointers/run-brief;
- R/r cannot move backward to superseded results;
- D Result stays inside the D isolation state until explicit reintegration;
- public L remains removed and current schemas/examples/docs are converged;
- release cleanup cannot delete repository .git metadata;
- stable validation must detect stale checked-in generated metadata rather than silently validating a repaired copy.

No new task-planning controller is introduced. Reliability work should be deterministic, exceptional-path heavy and cognitively cheap during normal task execution.

