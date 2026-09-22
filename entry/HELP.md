# DIGR 5.0.0-alpha.8 帮助

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

## 2. 参数解析与缺省

公开参数顺序：`N < T < R < B < S < D`；S 内部：`n < t < r < b`。

B/b 确定性缺省为 1；缺失的 N/T/R/n/t/r/s 在 Clock Genesis 和完整协议加载后按任务语义补全。裸数字不能被猜成 T/t。

L 不是公开参数。L、L()、L=... 均为 INVALID；D 内部固定使用 L1 semantic isolation，L 不进入合同、停止条件或 proof。

## 3. 参数语义

| 参数 | 语义 | 省略时 |
|---|---|---|
| N | MAIN 最少有效进化次数 | 语义补全 |
| T | counted Formal Active Task Time 目标 | 语义补全 |
| R | MAIN 当前结果整体重入最少次数 | 语义补全 |
| B | T：0 soft / 1 hard | 1 |
| S(n,t,r,b) | 来源进化/时间/当前结果重入/时间政策 | n/t/r 语义补全，b=1 |
| D(s) | 最少完成并重新整合的 disruptive intervention | 语义补全 |

N/R/n/r/D 是下限。B/b=1 时，T/t 是**已计入、硬验证时间的下限**。

## 4. SourceDisposition

SourceDisposition 默认 REQUIRED；只有 U0 或宿主现实提供明确理由时可 WAIVED。

WAIVED 后，source instance、n、r、t 的机械 gate 全部不适用；结构上的 b=1 不会把已经豁免的来源义务重新激活。零来源数值目标本身不会自动 WAIVE。

## 5. R 与 D

R/r 必须重新挑战当前结果，而不是拿旧 revision 刷计数。保留结果时 before 必须是当前 revision；发生变化时 after 必须成为当前 revision；持久化 R/r 链不得倒退到已被前一次重入淘汰的结果。

D 使用内部 L1。独占 D 的 execution 和 D Result 都必须留在 D_EXCLUSIVE；只有 reintegration 可以把选定后果带回 MAIN。D_EXCLUSIVE 计入 T，不计入 t。

## 6. 时间、WorkLease 与 coverage

Alpha 8：

- T = counted MAIN + SOURCE + D_EXCLUSIVE
- t = counted SOURCE
- META / IDLE 不计入
- 并行来源共享 SOURCE 时间并集

跨 host/process/tool 边界时，可在离开 runtime 前打开 work lease，使该 same-boot bridged interval 继续计入当前 formal state。SOURCE lease 同时携带 active_source_ids。

如果漏开 lease，runtime 会保留 coverage gap，但**不会猜测也不会计入那段时间**。因为 hard T/t 是最低时长承诺，漏记只会让已证明下限更小，不会让它虚高；因此 coverage completeness 是审计信息，不再单独阻断 delivery。若 counted hard time 不足，就继续积累正确归属的正式时间。

sleep、等待、日志、机械重复和 META 不得用 lease 冒充正式工作。

## 7. 崩溃恢复

Alpha 8 的 recovery 只修机械可重建状态：

- 普通 workspace 写入使用单槽 write-intent，修复“文件已写、索引未写”窗口；
- append-only journal 只有在自身链验证通过后才能刷新 artifact-index digest；
- revision history 是权威，latest pointer 与 run-brief 都可重建；
- journal 中已提交 FINISH 不会因 phase 写入中断而被“复活”为执行中；
- valid final summary 已写入但 FINISHED phase 未落盘时可完成最后一步。

Recovery 不得创造 U0、合同、语义事件、source finding、Strategy 或 D 结论。

## 8. Finalization

finish_time 先在 EXECUTING 中预演 proposed finish。适用的 N/R/n/r/D、hard timing 与 semantic completion 未满足时，live ledger 保持打开。

一旦 FINISH journal 持久化，formal timing 即视为已经提交；之后的 FINALIZING/FINISHED 属于可恢复的 lifecycle commit。

## 9. 输出

结果正文优先，最后附：

```text
DIGR(N_target/N_actual, T_target/T_actual, R_target/R_actual, B,
     S_i(n_target/n_actual, t_target/t_actual, r_target/r_actual, b),
     D(target)/D(actual))
```

L 不出现在 proof。actual duration 向下取整。B/b=1 时，只有 counted intervals 的硬验证失败才显示 ?；coverage 不完整时，显示的 actual 是已验证的保守下界，完整 coverage 状态保留在机器审计数据中。

## 10. 权威

本帮助属于当前 pinned P_run。真正执行权威仍是同 SHA 的 manifest、entrypoint 与 core。

