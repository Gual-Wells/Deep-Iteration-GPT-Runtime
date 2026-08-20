# D — Disruptive Gambit Intervention Session

D is a non-local intervention for escaping Main's current frame. It is not a second planner. Each intervention binds one IsolationReceipt and has revisioned proposals, a Decree, execution events, result revisions, then Main reintegration.

`D(s)` freezes only the minimum number of completed/reintegrated interventions. `D(0)` therefore means no D completion is mechanically required; it does not prohibit the native model from invoking D when a non-local challenge can materially improve the result. Actual D may exceed the target.

Before Decree the proposal may pivot freely. Decree is the commitment point and binds one proposal revision. If the decreed route is fundamentally wrong, abort the intervention and explicitly start/re-decree another instead of silently rewriting committed history. `ABORTED` and `COMPLETED` interventions are terminal and cannot later accumulate proposals, execution, results or reintegration edits.

D execution is state-bound. Exclusive isolation executes only while formal foreground state is `D_EXCLUSIVE`; background isolation is allowed only where the actual L mode supports it and the foreground remains MAIN/SOURCE. Every execution receipt binds the clock event proving that state.

A completed D requires result evidence and a ReintegrationReceipt. Reintegration is itself MAIN work: it binds a real MAIN clock state, the D result, candidate-before when available, accepted/rejected material, concrete Main consequence, and any resulting Strategy/Candidate revision. Rejecting all D output is valid after independent evaluation; a bare “reintegrated” string is not.
