# DIGR 5.0.0-alpha.7 帮助

DIGR（Deep Iteration GPT Runtime）是显式调用的高投入执行模式，只对当前用户消息生效。

## 1. 调用与路由

正式调用：

```text
DIGR：<任务>
DIGR(<参数>)：<任务>
深度迭代：<任务>
深度迭代(<参数>)：<任务>
```

DIGR 必须是精确大写 ASCII。DIGR/help 与 深度迭代/help 只读取帮助，不建立任务 Run。

## 2. 参数解析顺序与缺省规则

公开参数顺序：

`N < T < R < B < S < D`

S 内部：

`n < t < r < b`

B/b 确定性缺省为 1；缺失的 N/T/R/n/t/r/s 在 Clock Genesis 和完整协议加载以后按任务语义补全。裸数字不能被猜成 T/t。

**L 已不是公开参数。** L、L()、L=... 等输入均为 INVALID；D 内部固定使用 L1 semantic isolation，不需要用户输入，也不会出现在返回 proof 中。

## 3. 参数参考

| 参数 | 语义 | 省略时 |
|---|---|---|
| N | MAIN 最少有效进化次数 | 语义补全 |
| T | Formal Active Task Time 目标 | 语义补全 |
| R | MAIN 候选结果最少整体重入次数 | 语义补全 |
| B | T：0 soft / 1 hard | 1 |
| S(n,t,r,b) | 来源进化/时间/重入/时间政策 | n/t/r 语义补全，b=1 |
| D(s) | 最少完成并重新整合的 disruptive intervention | 语义补全 |

N/R/n/r/D 是下限而非上限。B/b=0 时 T/t 为 soft target；B/b=1 时为 hard lower bound。

D(0) 只是“没有必须完成的 D 下限”，不会禁止质量驱动的 D。

## 4. Effective Contract 与来源策略

EXECUTING 调用依次建立 repository authority、trusted Clock Genesis、完整协议加载、参数解析、U0 与 Effective Contract。合同冻结承诺，不冻结策略。

SourceDisposition 默认 REQUIRED。只有 U0 或宿主现实提供明确原因时可 WAIVED。零来源数值目标本身不会自动关闭来源。

真实来源工作必须绑定 SourceWorkspace、SOURCE 状态和语义 receipts。跨 GitHub/Web/connector 等外部工具边界时，应在真正离开 runtime **之前**进入 SOURCE 并开启 work lease，使外部工具工作实际计入 T/t，而不是事后用几毫秒 SOURCE 登记。

## 5. N / R / D

N 是 MAIN 的有效进化次数；R 是已有候选重新进入整个解决过程接受独立挑战的次数。

D 是 disruptive intervention 的完成/重新整合下限。D 内部固定使用 L1 semantic isolation。L 不再是用户合同维度、停止条件或 proof 字段。

D_EXCLUSIVE 是正式任务工作，因此 **计入 T**，但不计入来源时间 t。

## 6. 时间与停止

Alpha 7 Formal Active Time：

- T = MAIN + SOURCE + D_EXCLUSIVE
- t = SOURCE
- META / IDLE 不计入
- 并行来源共享同一 SOURCE 时间并集

跨 host/process/tool 边界时，时钟连续性和语义状态连续性分开证明。若当前 MAIN/SOURCE/D_EXCLUSIVE 工作将继续到外部工具，runtime 先持久化 **work lease**。下一次 same-provider、same-boot 的可信 resume 会恢复该状态并把跨边界工作时间计入。

没有 lease 的正式工作跨边界不会再被静默删除，而会成为 **coverage gap**。对于 B=1/b=1，相关 coverage 不完整即不能声明 hard time 达标，即使 gap 本身的墙钟长度可测。

sleep、等待、日志、机械重复或纯 META 不得通过 lease 冒充正式工作。

停止前采用 finalization admission：runtime 在 EXECUTING 状态先预演“现在结束”的 actuals。只有机械下限、hard time、coverage 与 semantic completion 都满足，才真正关闭 ledger 并进入 FINALIZING。未满足时继续 EXECUTING。

## 7. 执行链与启动成本

```text
stable → immutable P_run
→ transparent INDEX / STARTUP
→ execute-before-interpret
→ execution commitment
→ exact implementation delivery
→ Clock Genesis
→ verified execution bundle
→ ExecutingProtocolLoadReceipt
→ parameters + U0 + Effective Contract
→ MAIN / SOURCE / D with work leases where host boundaries require
→ prospective finalization admission
→ FINALIZING → FINISHED
```

Alpha 6 的 implementation identity / runtime artifact 机制继续保留。Alpha 7 在其上增加 formal-time cross-host continuity 与 coverage 完整性。

## 8. 输出与 canonical proof

正常回答先给任务结果，最后附：

```text
DIGR(N_target/N_actual, T_target/T_actual, R_target/R_actual, B,
     S_i(n_target/n_actual, t_target/t_actual, r_target/r_actual, b),
     D(target)/D(actual))
```

canonical proof **不再返回 L**。

actual duration 向下取整到完整秒。B/b=1 时，若 clock verification 或 semantic-time coverage 不完整，对应 actual 显示 ?，不得用部分时间伪装成 hard-verified actual。

## 9. 版本与权威

本帮助属于当前 pinned P_run。真正执行权威仍是同 SHA 的 manifest、entrypoint 与 core；帮助文本不替代版本化协议。
