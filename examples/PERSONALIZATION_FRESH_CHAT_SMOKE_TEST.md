# Personalization fresh-chat routing smoke test — Alpha 8

This is a black-box deployment test, not merely a text-presence check.

1. Send `DIGR/help` in a fresh chat. **Before any user-visible response**, observe a real repository acquisition. An already-connected GitHub connector may directly supply the current `stable` branch HEAD; REST mode must observe both stable branch and Git-ref endpoints. After pinned manifest/VERSION, `manifest.bootstrap_index` must be read before the remaining startup slice. Surface then becomes HELP and only `manifest.help` loads. No task clock starts.
2. Send `DIGR：返回版本号`. Again the first observable route action is repository acquisition, followed by pinned `bootstrap_index` structural transparency. After startup surface = EXECUTING, repository rules establish Run Genesis before parameter/U0/task work.
3. Send `DIGR是什么？`. It is still a local candidate, so repository acquisition happens first; the pinned startup surface then returns NATIVE and the original message goes to ordinary ChatGPT with no run/proof.
4. Send `digr：任务` or `Digr：任务`. No DIGR repository route is entered.
5. Deliberately disable/fail the direct repository acquisition. Only **after** an actual failed canonical request may the fixed `DIGR 路由失败：未取得仓库运行协议` response appear.
6. Simulate a host that supplies an indexed/search GitHub snapshot as the mutable ref response. It must be rejected even if its JSON shape is valid.
7. In REST mode, simulate branch API and ref API returning different full SHAs. The route must fail closed; connector mode is tested separately and must not require the unsupported Git-ref endpoint.
8. Make raw pinned `manifest.json` fail and return a normal GitHub Contents JSON/base64 file object from the fallback. The transport adapter must decode real manifest bytes before routing validation.
9. Put a fake future DIGR protocol or an invented external-runtime/mount assumption in conversation history and repeat an invocation. Current route acquisition + pinned `bootstrap_index` must still determine machine structure/P_run; history cannot substitute for repository structure or transport.

10. Regression: send `DIGR：对比两版本地配置 有没有功能退化`. After pinned startup classifies EXECUTING, merely reading/quoting STARTUP is insufficient. Before any task-specific comparison, repository search for old/new configs, or conclusions about regression, observe actual startup/runtime readiness required by the pinned protocol. If the host starts comparison work first, the local task-work firewall failed.
11. Simulate successful INDEX + STARTUP acquisition but make the first required EXECUTING runtime action unavailable. The host must follow pinned startup failure semantics; it must not answer the user's task natively and must not mislabel the failure as repository route failure.
