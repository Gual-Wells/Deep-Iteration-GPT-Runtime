# Repository Transport — Alpha 3

`runtime/repository_transport.py` is the executable bridge that Alpha 2 lacked between the local routing obligation and `runtime/routing.py`'s deterministic byte validators.

## Host contract

A host provides `FetchRequest -> TransportResponse`. The response must identify its provenance:

- `direct_https` or `github_connector`: admissible direct repository transport;
- anything else (for example a search/index/crawl result): not admissible for mutable `stable`.

Mutable requests additionally require freshness marker `live_direct`. Pinned SHA resources may be `live_direct` or `immutable_sha` because the object cannot change at that commit.

## Stable resolution

REST mode requests both canonical endpoints in one session:

1. Git ref `refs/heads/stable`;
2. Branches `stable`.

Both must return the same full commit SHA. A disagreement is not resolved by version-string heuristics or “newer-looking” content; it fails closed.

The included `UrllibDirectFetcher` sends `Cache-Control: no-cache` and `Pragma: no-cache` for mutable ref requests. Hosts with a connected GitHub connector may use that connector instead if it directly resolves the current branch head rather than searching indexed GitHub pages.

## Pinned file acquisition

Primary URL:

`https://raw.githubusercontent.com/Gual-Wells/Deep-Iteration-GPT-Runtime/{SHA}/{PATH}`

Fallback URL:

`https://api.github.com/repos/Gual-Wells/Deep-Iteration-GPT-Runtime/contents/{PATH}?ref={SHA}`

The fallback requests `application/vnd.github.raw+json`. `normalize_pinned_file_bytes()` also accepts GitHub's ordinary file-object response and base64-decodes `content`. Path mismatches, non-file objects and malformed base64 are rejected.

## Failure model

`RouteAcquisitionError` carries the session's `AcquisitionAttemptReceipt` values. `route_failure_permitted()` is a **necessary** check only: at least one canonical repository request must have occurred. The caller must also be handling a genuine mandatory-stage error. This prevents a host from using the fixed failure sentence as an alternative to making the first repository call.

## Deployment smoke test

`python tools/smoke_repository_transport.py 'DIGR/help'` performs a real public-GitHub transport check from an environment with network access. It prints the pinned SHA, pinned version, startup paths and repository surface. It is intentionally not part of the offline unit suite or deterministic release build.
