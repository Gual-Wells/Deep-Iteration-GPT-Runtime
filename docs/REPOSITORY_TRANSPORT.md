# Repository transport

Alpha 8 keeps repository transport outside task-execution semantics.

## Mutable authority

- an already-connected GitHub connector may resolve the current public `stable` branch HEAD directly;
- direct HTTPS mode corroborates Branches and Git-ref endpoints;
- search/index/crawl snapshots are never mutable-ref authority.

After one full SHA is pinned, all later reads use that SHA.

## Staged startup

Read manifest/VERSION, then bootstrap_index and the remaining startup slice. For EXECUTING, Clock Genesis precedes the manifest-declared execution bundle. The current bundle transports one entrypoint plus 18 core logical members and produces the ExecutingProtocolLoadReceipt required before parameter resolution.

Runtime-distribution artifacts are transport only. Their members must match the exact pinned Git tree and cannot redefine P_run.

Transport receipts do not define versioned parameter, timing, stop or proof semantics.

