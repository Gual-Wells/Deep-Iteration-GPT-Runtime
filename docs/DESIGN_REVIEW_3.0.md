# Design Review 3.0

## Why 3.0

2.3 solved several important problems (U0 anchoring, native-capability preservation, source discipline, immutable protocol pinning) but retained four structural mismatches:

1. T was semantic task scale rather than actual closed-loop runtime.
2. Evolution was biased toward linear pre-execution prompt refinement.
3. Result re-entry only became “formal redo” for major defects.
4. Runtime reporting became heavier than its proof/observability purpose.

3.0 makes a major break:
- T/t become real time targets with hard/soft policy and trusted-clock fail-closed semantics.
- evolution is continuous; prompt/execution behavior can change during the whole run.
- R/r are minimum whole-process re-evolution cycles when specified, using default challenge and ABG.
- source work becomes repeatable S instances with per-instance n/r/b and aggregate t.
- Main/S EST preserve progress without becoming an algorithmic search controller.
- proof becomes a single lightweight footer by default.

## Anti-overengineering
3.0 intentionally removes algorithmic scheduling, node scoring, workflow bureaucracy and heavy logs. DIGR should improve the task, not become the task.
