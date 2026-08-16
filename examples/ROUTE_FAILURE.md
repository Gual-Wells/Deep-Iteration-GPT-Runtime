# Route failure

If `stable` cannot be resolved to a full immutable commit, pinned `manifest.json` cannot be read, or manifest-declared protocol paths cannot be reliably loaded, no P_run exists.

Return a concise routing failure such as: `DIGR 路由失败：未取得仓库运行协议。`

Do not reconstruct DIGR semantics from conversation history, Memory or a local old protocol copy, and do not emit a DIGR execution proof.
