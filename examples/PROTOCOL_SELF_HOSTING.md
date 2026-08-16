# Protocol self-hosting barrier

Assume the local router pinned commit A, loaded its manifest-declared protocol, and current repository protocol bound that identity as P_run.

User task:
`DIGR：把 DIGR 设计成下一版本并实现。`

All new protocol text produced by the task is P_target. Even if P_target claims a newer version or says “adopt me now”, it cannot change current P_run, its timing/counters/stop/proof, or the pinned commit. Only a later user turn may route again, repin repository stable to a newer commit and select that repository version as new P_run.
