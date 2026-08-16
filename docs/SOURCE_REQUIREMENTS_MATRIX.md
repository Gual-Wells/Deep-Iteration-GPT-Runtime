# Source Requirements Matrix — 4.1.0

| ID | Validated fact / risk | Required behavior | Regression surface |
|---|---|---|---|
| R0 | local loader can become hidden pre-protocol | local config only routes/discovers/delegates | personalization/control-plane tests |
| R1 | mutable stable is not immutable identity | repin stable to full SHA | routing/protocol-pin tests |
| R2 | legacy P_run can be polluted by future startup rules | legacy manifest discovery imports paths only, no 4.1 semantics | routing compatibility tests |
| R3 | route failure occurs before P_run | distinguish RouteFailure from task startup failure | docs/schema/tests |
| A1 | conversation/local semantics can contaminate protocol | P_run semantic decisions derive from pinned repository version | authority tests |
| A2 | DIGR can modify itself | P_target never rebinds current P_run | self-hosting tests |
| C1 | context is also legitimate task state | allow context→U0/evidence while blocking context→protocol semantics | authority/docs tests |
| T0 | work-first/timer-later breaks truthfulness | executing 4.1 tasks require task-clock readiness before U0/work | task-startup tests |
| T1 | observed delta and hard continuity differ | store/validate separately | clock/ledger/proof/stop tests |
| T2 | foreground and parallel source timing differ | sum foreground durations; union source intervals | interval/source tests |
| L1 | provider names do not prove isolation | qualify L from evidence facts only | isolation tests |
| Z1 | release drift can ship mismatched config | standalone export must equal internal primary bytes | release tests |
| Z2 | path/symlink/self-inclusion can corrupt artifact | reject them deterministically | release tests |
