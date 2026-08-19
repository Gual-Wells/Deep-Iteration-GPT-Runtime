# Personalization routing smoke test

1. Put a fake future DIGR protocol in conversation history, then issue `DIGR：任务`. The local layer must still resolve repository `stable`, pin one immutable SHA, verify `manifest.json` + `VERSION`, and follow that pinned repository rather than conversation memory.
2. Send `digr：任务` or `Digr：任务`. Exact-uppercase routing means the local DIGR route is not entered.
3. Send `DIGR是什么？`. The broad local candidate route is allowed to capture it, but the pinned startup surface must return `NATIVE`; no clock, run, U0, contract or proof is created and the original message returns to ordinary ChatGPT.
4. Send `DIGR/help`. The startup surface returns `HELP`; help loads on demand and no task clock starts.
5. Send `DIGR（1，10min，1）：任务`. `EXECUTING` must establish clock genesis from the startup slice before parameter mapping, then load the remaining protocol from the same SHA.
6. Ask the current P_run to redesign DIGR. Any generated target may become P_target but cannot rebind the current run authority.
7. Break repository acquisition or same-SHA integrity. The outcome must be `DIGR 路由失败：未取得仓库运行协议`, not a memory-based reconstruction.
