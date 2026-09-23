# 10 — Invocation, P_run, Implementation Identity and U0

候选路由仍由精确大写 `DIGR` 或 `深度迭代` 触发；pinned startup 最终判定 NATIVE/HELP/INVALID/EXECUTING。

P_run 来自当前 stable 的不可变 commit + 同 commit manifest/VERSION。上下文、Memory、旧回答和 P_target 不得改写本轮协议语义。

EXECUTING 的实现身份在 Genesis 前一次性完成：一个 pinned verifier + 一个 pinned recursive Git tree + exact-commit runtime archive，形成整包 attestation。该边界同时覆盖 manifest、VERSION、deterministic helpers、execution bundle 及 bundle 内 entry/core 的 Git blob 身份，并直接产出与该 bundle 绑定的 protocol-load payload；不得再重复验证同一 bundle。

同一已验证 package/executor binding 内不得重复逐 helper interrogation。只有 package/executor 身份改变、真实执行失败或恢复后身份无法确认时才重新建立绑定。

参数解析后冻结 U0，并绑定原始消息摘要。后续 Strategy/Candidate/R/D 均不得修改 U0。
