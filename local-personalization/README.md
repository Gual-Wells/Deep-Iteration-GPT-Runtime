# ChatGPT local personalization

Use `CHATGPT_LOCAL_PERSONALIZATION.txt` as the primary compact router. `CHATGPT_LOCAL_PERSONALIZATION_FREE_GO.txt` is byte-identical for clients with smaller personalization surfaces. `CHATGPT_LOCAL_PERSONALIZATION_FULL.txt` explains the same routing/transparency contract in expanded form.

These files deliberately remain thin. Alpha 5 keeps versioned execution semantics out of the local layer. The local layer enforces candidate routing, real repository acquisition, admissible mutable-ref provenance, immutable SHA pinning, pinned manifest/VERSION binding, **bootstrap-index-first structural transparency**, ordered startup handoff and failure evidence.

The local layer does not describe N/T/R/S/D/L/time/stop/proof behavior. After pinning it first follows `manifest.bootstrap_index`, which makes the repository's implemented machine structure and truth sources visible, then delegates versioned behavior to the remaining pinned startup/entry/core protocol.
