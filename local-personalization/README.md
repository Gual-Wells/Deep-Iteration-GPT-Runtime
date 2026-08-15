# Local Personalization

把 `CHATGPT_LOCAL_PERSONALIZATION.txt` 复制到你用于 DIGR 的 ChatGPT 本地个性化/自定义指令区域。

它是“控制入口 + 本地 3.0 fallback”，不是完整协议副本。完整解释仍以本包 `core/` 与 `entry/` 为准。

关键行为：
- 当前 turn 显式触发；
- 下一 turn 不粘滞；
- 可选从 GitHub stable 固定到单一 commit；
- 旧 2.x 远程语义不能覆盖本地 3.0 fallback；
- 默认只返回轻量 proof。
