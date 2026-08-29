# Repository Transport — Berta2

Transport starts for every broad candidate whose lstripped message begins with exact uppercase `DIGR` or exact `深度迭代`; surface classification happens only after pinned startup is loaded.

## Mutable ref

- `github_connector`: accept the current full 40-hex `stable` branch HEAD from an already-connected repository connector.
- `direct_https`: read `/branches/stable` and `/git/ref/heads/stable` in the same attempt; accept only identical full SHAs.
- search/index/crawl/snippet representations are inadmissible.

Do not require new OAuth solely to bootstrap this public repository.

## Immutable navigation and artifacts

Read pinned `manifest.json` and `VERSION` first and require their versions to agree. Follow only manifest-declared paths at the same SHA. Load every `startup_slice` member before classifying the original message. NATIVE returns untouched text; HELP loads `manifest.help`; EXECUTING loads `entrypoint`/`core[]` or their exact verified bundle.

The manifest-declared runtime descriptor records hashes, byte lengths and media types for generated execution/release artifacts. Raw pinned SHA URLs are canonical; Contents API wrappers must be decoded to real bytes. Descriptor verification cannot replace manifest/VERSION startup navigation.
