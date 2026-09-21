# DIGR Transparent Machine Index — Alpha 5

This pinned file is the first repository-side structural view after `manifest.json` + `VERSION`. It is a **machine map**, not versioned execution semantics and not user-task work. Its purpose is to make the already-implemented DIGR system transparent before the host/model operates it.

## 1. Reality model

DIGR is a repository-implemented runtime/protocol system, not a prompt whose machinery is left for the model to invent.

Treat the manifest-declared objects as real repository objects:

- protocol semantics: `entrypoint` + `core[]`;
- deterministic executable support: every path in `deterministic_helpers[]`;
- startup navigation: `bootstrap_index` + ordered `startup_slice`;
- persistent runtime layout: `workspace_spec` plus `runtime/workspace.py`;
- persisted object contracts: `schemas/*.json`;
- execution transport: `execution_bundle.path`;
- user reference: `manifest.help`.

If the pinned protocol requires a declared helper or runtime step, use the **actual implementation** through the host's available execution channel. Do not downgrade implemented code/workspace/state into a conceptual simulation, and do not invent an external runtime, daemon, mount, attachment or service unless the pinned repository explicitly declares one.

## 2. Machine topology

**Transport / authority.** `runtime/routing.py`, `runtime/repository_transport.py`, `runtime/protocol_pin.py`, `runtime/protocol_authority.py`, `runtime/execution_protocol.py` establish repository acquisition, immutable identity and verified protocol transport.

**Lifecycle / contract.** `runtime/invocation_surface.py`, `runtime/clock_probe.py`, `runtime/task_startup.py`, `runtime/parameter_resolution.py`, `runtime/effective_contract.py`, `runtime/run_lifecycle.py`, `runtime/run_session.py` implement the deterministic execution boundary and persisted lifecycle.

**Native intelligence.** The model owns task representation, decomposition, research/validation/tool strategy, substantive evolution, re-entry challenges and disruptive ideas. The runtime is an exoskeleton, not a planner or scheduler.

**Persistent working state / evidence.** Strategy, Candidate, EST, Source, D, Completion and Evidence are real revisioned stores implemented by `runtime/strategy_store.py`, `runtime/candidate_store.py`, `runtime/est_store.py`, `runtime/source_workspace.py`, `runtime/d_intervention.py`, `runtime/completion_state.py`, `runtime/evidence_index.py` and `runtime/evolution_events.py`.

**Audit / recovery / output.** `runtime/clock_journal.py`, `runtime/interval_ledger.py`, `runtime/actuals.py`, `runtime/isolation_checks.py`, `runtime/state_checks.py`, `runtime/stop_checks.py`, `runtime/run_recovery.py`, `runtime/run_brief.py`, `runtime/proof.py` and the workspace/schema layer own mechanical facts, integrity, recovery and canonical rendering.

## 3. Truth-source map

- current protocol identity → pinned `manifest.json` + `VERSION`;
- execution meaning → pinned `entrypoint` + `core[]`;
- complete implemented helper set → `manifest.deterministic_helpers[]`;
- current persisted run facts → workspace authoritative stores/journals, not chat memory;
- timing truth → clock journal + formal ledger;
- N/R/S/D/L and related mechanical actuals → bound persisted evidence re-derived by runtime actuals logic, not model self-report;
- current Strategy/Candidate/Source/D/Completion state → their revision stores;
- recovery validity → `run_recovery.py` over the persisted workspace;
- mechanical stop gates → `stop_checks.py`;
- visible compact proof → `proof.py`;
- intellectual next action and quality judgment → native model intelligence under the pinned protocol.

## 4. Operating boundary

**Structure-closed, intelligence-open.** Reliability structure, object identity, lifecycle, persistence, references, timing, actual derivation and proof are repository-defined. Intellectual strategy remains model-native. Never use ordinary Agent/runtime/host conventions to override a repository-defined meaning; use general software knowledge only after the pinned repository has resolved the term.

## 5. Continue startup

After this index is understood, continue the remaining manifest-declared `startup_slice` in order. For this pinned Alpha 5 structure that means `bootstrap/BOOTSTRAP.md` then `entry/STARTUP.md`.

This index has no authority to alter N/T/R/S/D/L, timing, stop or proof semantics. If any wording here conflicts with the pinned manifest/startup/entry/core, the latter wins.
