# ChatGPT local personalization

Use `CHATGPT_LOCAL_PERSONALIZATION.txt` as the deployable local router. It now targets ChatGPT Plus-class custom-instruction capacity and is validated against a 5,000-character ceiling. Free/Go compatibility is intentionally not maintained; the old byte-identical Free/Go copy has been removed.

`CHATGPT_LOCAL_PERSONALIZATION_FULL.txt` is the expanded design/reference version. It is not intended for direct deployment into the custom-instructions field.

The local layer remains version-neutral. It owns only:

- exact candidate routing;
- real repository acquisition and admissible mutable-ref provenance;
- immutable SHA pinning and same-SHA content fallback;
- bootstrap-index-first structural transparency;
- a persistent **task-work firewall** from candidate capture through repository-defined startup readiness;
- repository authority handoff and failure-boundary discipline.

The critical invariant is **read ≠ execute**. Acquiring and understanding `startup_slice` does not satisfy operational directives inside it. For an EXECUTING surface, substantive task reasoning/tools remain blocked until the pinned repository has actually completed every startup/protocol readiness gate required before task work.

The local layer still does not define N/T/R/S/D/L/time/stop/proof behavior. Those remain exclusively in the pinned repository protocol.
