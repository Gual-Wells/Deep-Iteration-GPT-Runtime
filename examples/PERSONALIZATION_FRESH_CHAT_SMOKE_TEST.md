# Stable personalization fresh-chat smoke test

1. `digr：任务` and ordinary non-candidates stay native and perform no DIGR repository acquisition.
2. `DIGR是什么？` first pins current `stable`, verifies pinned manifest/VERSION/STARTUP, then returns NATIVE with the exact original message.
3. `DIGRAPH` follows the same acquisition-first path before pinned STARTUP returns NATIVE.
4. `DIGR：` and `DIGR(1：任务` acquire the same startup slice before returning INVALID/correction and create no run.
5. `DIGR/help` acquires startup, then fetches the same-SHA `manifest.help` artifact and creates no run.
6. `DIGR：任务` acquires startup before `digr.preflight`; only READY then fetches descriptor/execution artifacts and may proceed to Genesis.
7. Every preflight receipt records completed startup acquisition separately from whether additional artifact fetches are required.
8. Without HostAdapter enforcement, output is `DIGR~` ADVISORY and has no canonical proof.
9. Truncate the local configuration before its sentinel; installation validation must reject it.
