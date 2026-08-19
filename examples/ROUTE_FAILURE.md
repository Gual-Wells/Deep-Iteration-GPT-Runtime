# Route failure — Alpha 3

A fixed route failure is valid only after the current candidate turn has actual canonical repository-acquisition evidence.

Examples of genuine route failure:
- direct mutable `stable` acquisition fails;
- ref and branch direct observations disagree;
- the returned mutable-ref provenance is search/index/crawl rather than direct live repository access;
- pinned manifest/VERSION bytes cannot be acquired or fail integrity/version equality;
- a manifest-declared mandatory startup path cannot be obtained from the same SHA.

Not a route failure:
- no acquisition tool/callback was invoked;
- the model merely remembers that a previous fetch failed;
- a search result looks stale;
- a fixed failure string is easier to emit than trying the repository.

If a genuine route failure occurs, return only `DIGR 路由失败：未取得仓库运行协议` and do not reconstruct DIGR semantics from conversation history, Memory or a local old protocol copy.
