# 60 — Formal Active Time & Trusted Clock

DIGR 4.1 T/t are pausable real **formal active work time**, not total call-to-return wall time and not a semantic “think X minutes” scale.

## Mandatory 4.1 task-clock readiness
After the pinned 4.1 repository protocol has classified a candidate message as an **executing task invocation**, but before U0 freeze, semantic calibration or substantive task work, it must initialize trusted monotonic timing. Readiness requires at least two compatible clock snapshots, a non-negative monotonic delta and continuity identity accepted by the runtime. If readiness cannot be proved, 4.1 task startup fails; there is no retroactive reconstruction.

This rule belongs to P_run=4.1. The local router does not know or enforce it, and non-executing help/invalid candidates do not start a task clock.

Readiness is distinct from hard-time satisfaction: readiness proves that timing infrastructure was live before task work; hard T/t also require continuity verification across every formal interval used to prove the target.

## Two time facts
- **observed monotonic duration**: honest non-negative monotonic delta; useful for soft T/t;
- **hard-verification fact**: observed duration plus continuity identity proof; required for hard T/t.

An observed number never upgrades itself into hard proof.

## Foreground states
- `MAIN`: substantive U0 analysis/reasoning/design/code/test/debug/verification/synthesis; counts T.
- `SOURCE`: formal S querying/reading/source inspection/evidence-driven analysis; counts T+t.
- `D_EXCLUSIVE`: D foreground takeover through reintegration; counts neither.
- `META`: invocation interpretation, authority bookkeeping, clock operations, default completion, contract/proof bookkeeping; counts neither.
- `IDLE`: sleep, intentional delay, pure queueing or non-task gaps; counts neither.

Routing occurs before P_run/task runtime and is not Formal Active Time. Real task analysis cannot be relabeled META to hide time.

## Parallel work / identity
The foreground ledger has one foreground state at a time and accumulates each interval's own duration; it must not union absolute monotonic coordinates from unrelated clock epochs. Parallel S source intervals are unioned at source aggregation to avoid double count.

Background L2/L3 Shadow D contributes no D time but does not pause Main T. Only actual D_EXCLUSIVE takeover pauses foreground T/t.

## Trusted continuity
Reference runtime uses integer `time.monotonic_ns()`. Same runtime session can prove local continuity; a stable boot identity may support cross-process continuity. If hard continuity is lost, hard proof fails closed. Actual display must never round upward across a target. Sleep/repetition/log inflation/pseudo-steps may not pad T/t.
