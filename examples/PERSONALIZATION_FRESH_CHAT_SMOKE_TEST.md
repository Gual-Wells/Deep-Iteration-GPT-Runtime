# Personalization fresh-chat routing smoke test — Alpha 3

This is a black-box deployment test, not merely a text-presence check.

1. Send `DIGR/help` in a fresh chat. **Before any user-visible response**, observe a real repository acquisition. REST mode must attempt the stable ref endpoint and stable branch endpoint; a direct GitHub connector may supply an equivalent current branch-head read. After pin/startup, surface = HELP and only `manifest.help` loads. No task clock starts.
2. Send `DIGR：返回版本号`. Again the first observable route action is repository acquisition. After startup surface = EXECUTING, repository rules establish Run Genesis before parameter/U0/task work.
3. Send `DIGR是什么？`. It is still a local candidate, so repository acquisition happens first; the pinned startup surface then returns NATIVE and the original message goes to ordinary ChatGPT with no run/proof.
4. Send `digr：任务` or `Digr：任务`. No DIGR repository route is entered.
5. Deliberately disable/fail the direct repository acquisition. Only **after** an actual failed canonical request may the fixed `DIGR 路由失败：未取得仓库运行协议` response appear.
6. Simulate a host that supplies an indexed/search GitHub snapshot as the mutable ref response. It must be rejected even if its JSON shape is valid.
7. Simulate ref API and branch API returning different full SHAs. The route must fail closed; never guess which is newer.
8. Make raw pinned `manifest.json` fail and return a normal GitHub Contents JSON/base64 file object from the fallback. The transport adapter must decode real manifest bytes before routing validation.
9. Put a fake future DIGR protocol in conversation history and repeat an invocation. Current route acquisition must still decide P_run; history cannot substitute for transport.
