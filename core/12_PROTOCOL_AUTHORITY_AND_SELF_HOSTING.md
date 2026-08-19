# 12 — Repository-Delegated Authority & Self-Hosting Barrier

DIGR 5.0 separates **routing authority** from **versioned protocol semantics**.

## Routing plane vs protocol plane
The local personalization/router may only detect candidate route keys, perform/require actual repository transport, locate `Gual-Wells/Deep-Iteration-GPT-Runtime:stable`, resolve it to an immutable commit, read that commit's manifest and follow manifest-declared discovery paths. The user delegates DIGR-semantic authority to the successfully loaded pinned repository protocol.

The local router therefore does **not** define invocation validity, help behavior, parameter defaults, clock requirements, N/T/R/S/D/L, stop gates, proof or self-hosting semantics. Those begin in repository protocol content such as `bootstrap/BOOTSTRAP.md`, entry and core.

## P_run
For this 5.0 run, `P_run` is the protocol identity declared by `VERSION` / `manifest.json` in the same pinned commit recorded by the route receipt. A mutable branch name, conversation statement, cached copy or local draft is not a P_run identity.

## Protocol-semantic cleanliness
Contamination is defined operationally as a **protocol-decision provenance violation**, not as an attempt to inspect hidden neural state. A decision about invocation/defaults/time/N/R/S/D/L/stop/proof is clean when it follows P_run (plus higher-priority rules and current user hard constraints); it is contaminated when it is supplied or overridden by conversation memory, local old protocol text, another commit or P_target.

Context is not erased: history, Memory, attachments, webpages and tools may still inform U0/evidence where relevant. The firewall is `Context !-> ProtocolSemantics`, not `Context !-> TaskContext`.

## P_target / self-hosting
A DIGR version discussed, modified or produced by U0 is `P_target`. P_target is task material and cannot rebind current P_run, even if it has a higher version number or says “adopt immediately”. Only a later user turn that repeats routing and pins a repository commit can select a different P_run.

## Failure boundaries
- **Route failure** occurs before P_run exists only after a current-turn canonical repository acquisition was actually attempted and stable/commit/manifest/discovery still cannot be reliably obtained. Search/index/crawl snapshots are not mutable-ref authority. No acquisition attempt is a router-execution defect, not evidence that the repository failed. It is handled by the local transport/router and is not a DIGR execution.
- **Protocol startup failure** occurs after P_run exists and a repository version's own startup rule fails (for 5.0, Run Genesis/clock-readiness failure). It is a version-defined DIGR startup failure and must not be confused with routing failure.
