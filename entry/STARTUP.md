# DIGR 5.0 Alpha 10 — Contracted Startup

Alpha 10 treats startup as one coarse trust boundary, not a chain of per-helper gates.

1. Classify the pinned invocation as NATIVE | HELP | INVALID | EXECUTING.
2. NATIVE/HELP/INVALID do not create a run.
3. EXECUTING pins P_run and performs one runtime-package attestation before Genesis:
   - obtain one recursive Git tree for the pinned commit;
   - bridge the exact pinned `runtime/runtime_package.py` verifier;
   - obtain the exact-commit runtime archive;
   - execute the verifier once. It verifies manifest, VERSION, every deterministic helper, the execution bundle, and every bundle member against the pinned Git tree.
4. Read the already-attested execution bundle and construct ExecutingProtocolLoadReceipt. The authoritative logical set is manifest.entrypoint + manifest.core[].
5. Bind the verified package to the executor once. Do not repeat component interrogation or per-helper identity fetches inside the same binding.
6. Establish trusted monotonic readiness and create Run Genesis.
7. Resolve parameters, freeze U0 and Effective Contract, enter MAIN.

After Genesis, ordinary task work has no repository-transport gate. Soft timing never requires WorkLease merely to preserve clock credit. WorkLease is used only when cross-boundary formal-time attribution materially matters, especially explicit hard timing.

Ordinary resume uses the lightweight recovery path and validates each required store once. Full workspace audit/rebuild is an anomaly fallback or explicit audit operation, not a normal continuation prerequisite.

No exact package path means startup failure; it never licenses a model-written runtime substitute.
