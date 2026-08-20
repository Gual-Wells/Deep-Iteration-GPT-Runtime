# Repository transport

Alpha 4 keeps repository transport outside DIGR execution semantics and makes transport mode explicit.

## Admissible mutable-ref sources

- `github_connector`: an already-connected GitHub repository connector may read the public repository `stable` branch resource and accept its current full 40-hex HEAD SHA. Connector mode does not require a Git-ref endpoint the connector product does not expose.
- `direct_https`: a real direct GitHub REST client reads both the stable branch resource and Git-ref resource. If a push lands between those two live reads, one bounded re-observation is allowed; only a matching full SHA is accepted.
- search/index/crawl/snippet/browser-search snapshots are never mutable-ref authority.

A public DIGR bootstrap must not require the user to establish a new GitHub OAuth connection merely to read this repository. If a connector is already connected, it is preferred; otherwise a host may use genuine direct REST if available.

## Immutable staged phase

After stable resolves to one SHA, every later resource is read at that exact SHA. `raw.githubusercontent.com/{SHA}/{PATH}` is canonical. GitHub Contents API is an allowed fallback only when the response is raw media or its JSON/base64 wrapper is decoded into actual file bytes.

The first immutable stage remains deliberately small: `manifest.json`, `VERSION`, then `startup_slice`. This preserves cheap NATIVE/HELP/INVALID classification and keeps Clock Genesis at the same early boundary.

For EXECUTING, Alpha 4 separates **logical protocol modularity** from **physical transport count**. The repository continues to maintain one entrypoint and 17 core source files, but the release builder deterministically generates `bundle/EXECUTION_PROTOCOL.json`. After Clock Genesis the host fetches this single pinned bundle, verifies that it contains exactly the manifest-declared entrypoint/core members in order with matching byte lengths and SHA-256 digests, and persists an `ExecutingProtocolLoadReceipt`. Parameter resolution cannot start without that receipt.

Older staged manifests without an execution bundle remain compatible by loading their entrypoint/core individually and normalizing those verified files into the same receipt shape.

A post-genesis mandatory protocol-load failure is a failure of a **born** run: the standard host bridge persists `ABORTED`, and the run cannot continue parameter resolution from an unverified GENESIS state.

Transport receipts prove that real acquisitions occurred. They do not contain or define N/T/R/S/D/L, timing, stop or proof semantics.
