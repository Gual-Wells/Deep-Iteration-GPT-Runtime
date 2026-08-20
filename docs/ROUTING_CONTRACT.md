# Routing Contract

The local layer is a broad candidate router plus repository-authority handoff. It never redefines DIGR execution semantics.

## Candidate capture

After removing leading whitespace only, exact uppercase ASCII `DIGR` or exact `深度迭代` is a route candidate. The remainder is deliberately not interpreted locally. The pinned startup surface decides NATIVE/HELP/INVALID/EXECUTING.

## Actual acquisition before failure

A candidate must cause a real repository acquisition action before any user-visible route result. No-attempt is not acquisition failure. Search results, snippets, crawled/indexed GitHub pages and remembered results are inadmissible mutable-ref authority.

## `stable → SHA`

Two transport modes are valid:

1. **Already-connected GitHub repository connector:** read the repository `stable` branch resource and accept its current full 40-hex HEAD SHA. No Git-ref endpoint is additionally required in connector mode.
2. **Direct REST client:** read both the Branches endpoint and Git-ref endpoint during the same route attempt and require the same full 40-hex commit SHA. Disagreement fails closed.

The standard-library direct fetcher requests cache revalidation on mutable REST reads. This is transport hardening, not a claim of mathematical zero-latency propagation.

## Pinned authority

Bind pinned `manifest.json` and `VERSION`, require version equality, then follow only manifest-declared paths. A manifest with `startup_slice` loads only that slice before repository surface classification. NATIVE/HELP avoid unnecessary full protocol loading; EXECUTING follows the pinned startup rules, crosses Clock Genesis, then acquires the manifest-declared same-SHA execution bundle when present (otherwise logical entry/core individually). The verified bundle members remain the entry/core authority and produce the receipt required before parameter resolution. Legacy manifests without staged startup retain their own navigation.

The fixed route-failure response is allowed only after actual acquisition evidence exists and a mandatory current-stage resource still fails, conflicts or has inadmissible provenance.
