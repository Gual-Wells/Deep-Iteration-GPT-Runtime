# Mutable Strategy and Candidate State

**Freeze commitments, never freeze strategy.** P_run, U0, user hard constraints and Effective Contract commitments are frozen; count/D fields are minima while T/t are B/b-governed targets; task representation, decomposition, Strategy, assumptions, source/validation/tool routes, Candidate and D gambit remain working state.

After Contract freeze, substantive task work enters MAIN. Strategy Genesis forms the current task model, primary/alternative routes, source strategy, validation strategy, tool strategy, assumptions and risks. Because this is real task work it counts toward T and may naturally qualify as N when it is a meaningful evolution.

Strategy snapshots are revisioned and non-authoritative. N, R, source evidence, D reintegration, failed tests and new counterexamples may rewrite the entire strategy. A StrategyState must not contain scheduler fields such as `next_step`, `score` or `priority`; the runtime never decides what the model should think next.

Candidate snapshots externalize the current result at revision boundaries without storing hidden chain-of-thought. They bind summary, artifact/evidence refs, producer and digest. Candidate is what R re-enters; Strategy is how the model currently intends to work; EST is compact continuing memory. These stores reference rather than duplicate one another where possible.
