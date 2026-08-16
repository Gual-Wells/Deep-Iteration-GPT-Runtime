# Local Personalization Guide — Reliable Routing Mode

Use `local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt`. It is a router, not a protocol copy.

## The router may do
1. react to message-head `DIGR` / `深度迭代` as candidate route keys;
2. resolve `Gual-Wells/Deep-Iteration-GPT-Runtime:stable` to a full immutable commit SHA;
3. read that commit's `manifest.json`;
4. follow manifest discovery (`bootstrap_entry`, or legacy `entrypoint` + `core`);
5. explicitly delegate DIGR semantic authority to the successfully loaded pinned repository protocol.

## The router may not do
It must not define invocation validity/help/parameters/defaults, clock behavior, N/T/R/S/D/L, stop/proof or self-hosting rules. It must not reconstruct a protocol from conversation, Memory or an old local copy.

## Route failure
If immutable pin/manifest/discovery fails before P_run exists, report route failure only. Do not label ordinary fallback assistance as a DIGR execution.

## Compatibility
This router can route the current legacy 3.0 manifest without importing 4.1 semantics because it follows the manifest's declared entrypoint/core when `bootstrap_entry` is absent. After 4.1 is published to stable, the same local text follows `bootstrap/BOOTSTRAP.md`. No personalization replacement is required for the version transition.

## Smoke tests
- Put a fake DIGR definition in conversation history: repository protocol must still win on protocol semantics.
- Route a legacy manifest: no 4.1 clock/help/default rule may be applied before legacy P_run loads.
- Ask P_run=4.1 to design 5.0: target text cannot rebind current P_run.
- Break repository routing: result is route failure, not a memory-based DIGR run.
