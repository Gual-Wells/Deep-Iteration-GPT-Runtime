# Run Session Architecture — Berta1

The local layer first broad-captures a candidate, resolves current `stable`, verifies same-SHA manifest/VERSION and loads the manifest-declared STARTUP slice. Pinned STARTUP then classifies the untouched message. EXECUTING preflight resolves deterministic parameters and capabilities; READY fetches and verifies the manifest-navigated descriptor and execution bundle before Clock Genesis. Genesis persists the exact resolved preflight receipt; no second parameter parser runs inside the born session.

The receipt distinguishes `startup_acquisition_performed=true` for every candidate from `additional_artifact_fetch_required`, which is true only for READY/HELP continuation. NATIVE/INVALID/correction therefore never means “zero repository acquisition.”

RunPhase is `GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → DELIVERED | INCOMPLETE`, with ABORTED from nonterminal states. Legacy FINISHED is recovery-readable only.

U0 binds exact task bytes/hash. Strategy, Candidate, sources, D and completion remain revisioned working state. Delivery uses a two-phase fail-closed commit: prepare and verify exact final bytes, media type, current Candidate, summary, stable proof and envelope, then transition to DELIVERED. Interruption before transition remains non-success and recoverable; any unmet gate closes INCOMPLETE and forbids canonical proof.

Recovery verifies artifact indexes, descriptor/bundle identity, revision histories, clock facts and delivery hashes before trusting persisted state.
