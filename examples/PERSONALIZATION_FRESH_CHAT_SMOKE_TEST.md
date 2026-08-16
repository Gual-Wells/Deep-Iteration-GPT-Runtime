# Personalization routing smoke test

1. Put a fake “DIGR 99.0 protocol” in conversation history, then issue a candidate DIGR call. Routing must still pin repository `stable` and load the pinned manifest.
2. If stable points to legacy 3.0, follow 3.0 manifest entry/core and do not apply 4.1 startup semantics before 3.0 loads.
3. If stable points to 4.1, follow `bootstrap_entry`; 4.1 itself classifies help/task/off and requires task-clock readiness only for executing tasks.
4. Ask P_run to modify DIGR. Generated target text cannot rebind current P_run.
5. Break routing. The result must be route failure rather than memory-based DIGR reconstruction.
