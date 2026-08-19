# Alpha 2 task-clock readiness and hard timing

For a routed candidate, the pinned startup slice first returns `NATIVE`, `HELP`, `INVALID`, or `EXECUTING`. Only `EXECUTING` creates a run. It establishes >=3 compatible monotonic samples and clock-journal genesis **before** parameter resolution, U0 or task analysis.

Example: `DIGR（T=10min，B=1）：工程任务`.

`B=1` makes T a hard minimum. Every interval used for that hard proof must retain trusted continuity. If continuity later cannot be proven, the runtime reports the relevant actual as `?` / fails the hard minimum rather than estimating.

Wrong: analyze or write code first and start the clock later. Wrong: treat wall-clock waiting as task time. Wrong: infer cross-process monotonic continuity merely because numeric values look increasing. Cross-session continuity requires compatible provider facts and equal non-empty boot identity.
