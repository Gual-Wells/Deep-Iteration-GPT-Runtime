# DIGR 4.1 Repository Bootstrap

This file is **versioned DIGR protocol content**. It is loaded only after the local router has pinned `stable`, read this commit's manifest, and delegated DIGR-semantic authority to this repository version.

## 1. Freeze repository authority
Use the already-pinned repository commit described by the routing receipt. `P_run` is the protocol/version declared by this same commit's `VERSION` and `manifest.json`. Conversation history, Memory, previous DIGR explanations, local protocol copies, other branches/commits and task-generated DIGR text cannot define or patch DIGR semantics.

## 2. Classify the candidate message using **this version's** invocation rules
Only now decide whether the candidate is:
- an executing DIGR task invocation;
- `DIGR/help` / `深度迭代/help`;
- invalid/non-triggering text.

Help and invalid/non-triggering text do **not** start task runtime or a task clock.

## 3. Mandatory task-clock readiness for executing 4.1 tasks
For an executing task invocation, before U0 freeze, semantic calibration, MAIN/SOURCE work or any other substantive task work, establish trusted monotonic clock readiness with at least two compatible snapshots and a non-negative hard-verifiable delta. If readiness fails, DIGR 4.1 task startup fails. Do not work first and reconstruct timing later.

This is a **4.1 repository rule**, not a local-router rule. Another repository version may define different startup behavior.

## 4. Continue into entry/core
After task-clock readiness succeeds, continue with `entry/DEEP_ITERATION_ENTRY.md` and the core modules declared by the manifest.

## Self-hosting boundary
If U0 asks to design, edit, test or generate another DIGR version, that target is `P_target` task material. It cannot rebind current `P_run`. Only a later candidate route that repins `stable` can select a different repository protocol.
