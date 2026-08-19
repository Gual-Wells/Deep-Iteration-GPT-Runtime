# Routing Transport Contract v3

Candidate match remains version-neutral: remove leading whitespace only, then exact uppercase `DIGR` or exact `深度迭代`; the remainder is unvalidated locally.

## Acquisition is an observable precondition

A candidate route MUST cause an actual repository acquisition action before any user-visible reply or task-level interpretation. Merely knowing the fixed failure string, remembering an earlier SHA, or assuming the network/tool is unavailable is not a route attempt. The fixed route-failure response is admissible only after current-turn acquisition evidence exists and a mandatory stage still fails, conflicts, or has inadmissible provenance.

## Mutable `stable` is the only freshness-sensitive step

Search results, snippets, crawled/indexed GitHub HTML and conversation memory are not ref authority. A connected GitHub repository connector that directly resolves the current branch head is admissible. Direct REST acquisition uses both:

- `GET /repos/Gual-Wells/Deep-Iteration-GPT-Runtime/git/ref/heads/stable`
- `GET /repos/Gual-Wells/Deep-Iteration-GPT-Runtime/branches/stable`

Both observations must identify the same full 40-hex commit SHA. Disagreement fails closed. The standard-library `UrllibDirectFetcher` asks intermediaries to revalidate mutable requests with `Cache-Control: no-cache` and `Pragma: no-cache`; this is transport hardening, not a claim that an external CDN has zero propagation delay.

## Immutable pinned resources

After the SHA is accepted, every later read uses that SHA. Primary pinned transport is the immutable raw URL:

`https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/{PATH}`

A GitHub Contents API fallback is allowed only at the same SHA. It requests `application/vnd.github.raw+json`; if a host still returns the ordinary JSON file object, `runtime/repository_transport.py` decodes its base64 `content` field before routing validators consume the bytes. The Alpha 2 ambiguity—Contents wrapper JSON passed to raw-byte loaders—is therefore closed.

## Staged authority

Bind pinned `manifest.json` and `VERSION`, require version equality, then follow only manifest-declared paths. A manifest with `startup_slice` loads only that slice before repository surface classification. NATIVE/HELP avoid unnecessary full protocol loading; EXECUTING follows the pinned startup rules and only then loads entry/core from the same SHA. Legacy manifests without staged startup retain their own navigation.

Routing/transport failure is not DIGR execution and never authorizes reconstruction from Memory, conversation history or an old local protocol copy.
