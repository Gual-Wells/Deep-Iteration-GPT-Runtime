# Alpha 8 task-clock readiness and hard lower-bound timing

For a routed candidate, the pinned startup slice first returns `NATIVE`, `HELP`, `INVALID`, or `EXECUTING`. Only `EXECUTING` creates a run. It establishes >=3 compatible monotonic samples and clock-journal genesis **before** parameter resolution, U0 or task analysis.

Example: `DIGR（T=10min，B=1）：工程任务`.

`B=1` makes T a hard minimum. Every interval used for that hard proof must retain trusted continuity. If a counted interval itself cannot be hard-verified, the runtime reports the relevant actual as `?` / fails the hard minimum rather than estimating. Unleased gaps are excluded from counted time; they reduce the proved lower bound but do not poison otherwise verified intervals.

Wrong: analyze or write code first and start the clock later. Wrong: treat wall-clock waiting as task time. Wrong: infer cross-process monotonic continuity merely because numeric values look increasing. Cross-session continuity requires compatible provider facts and equal non-empty boot identity.
