# 12 — Repository-Delegated Authority & Self-Hosting Barrier

DIGR separates routing authority from versioned protocol semantics.

## Routing plane vs protocol plane

The local router may only detect candidate route keys, perform/require actual repository transport, locate `Gual-Wells/Deep-Iteration-GPT-Runtime:stable`, resolve it to an immutable commit, read that commit's manifest and follow manifest-declared discovery paths. Versioned semantics come only from the successfully pinned repository protocol.

## P_run

`P_run` is the protocol identity declared by VERSION/manifest.json in the same immutable commit recorded by the route receipt. A mutable branch name, conversation statement, cached copy or local draft is not P_run.

## Protocol-semantic cleanliness

Decisions about invocation/defaults/time/N/R/S/D/stop/proof follow P_run plus higher-priority rules and current user hard constraints. Conversation memory, old protocol text, another commit and P_target may inform task context/U0/evidence but cannot redefine protocol semantics.

`Context !-> ProtocolSemantics`, not `Context !-> TaskContext`.

## P_target / self-hosting

A DIGR version discussed, modified or produced by U0 is `P_target`. It cannot rebind current P_run. Only a later routed user turn may pin a different repository commit.

## Failure boundaries

- **Route failure** occurs before P_run exists only after current canonical acquisition was actually attempted and stable/commit/manifest/discovery still cannot be reliably obtained.
- **Preflight startup failure** occurs after P_run exists but before Genesis when exact implementation delivery, package attestation, full protocol verification or trusted-clock readiness cannot be established. No born run is created.
- **Live-run failure** occurs only after Genesis under the pinned runtime lifecycle. Ordinary repository/bundle transport is not a mandatory post-Genesis dependency in Alpha 9.

These boundaries must never be rewritten as a native answer or as evidence that an unattempted repository route failed.
