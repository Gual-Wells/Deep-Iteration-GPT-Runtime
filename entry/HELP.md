# DIGR 5.0.0-alpha.9 帮助

DIGR（Deep Iteration GPT Runtime）是显式调用的高投入执行模式，只对当前用户消息生效。

## 1. 调用与路由

正式调用包括 `DIGR：<任务>`、`DIGR(<参数>)：<任务>`、`深度迭代：<任务>`。DIGR 必须是精确大写 ASCII。help 不建立任务 Run。

## 2. 参数解析与缺省

公开参数顺序：`N < T < R < B < S < D`；S 内部：`n < t < r < b`。

B/b 缺省为 0（soft）。缺失的 N/T/R/n/t/r/s 仍由模型按 U0 与全部显式参数联合语义补全。只有显式 `B=1` / `b=1` 才把对应 T/t 变成 hard lower bound。

L 不是公开参数；D 内部固定使用 L1。

## 3. 参数语义

N/R/n/r/D 是最低次数或干预承诺。T/t 是正式投入时间目标：B/b=0 时为 soft，显式 1 时为 hard。D(0) 表示零最低 D 要求，不关闭 D 机制。

## 4. SourceDisposition

默认 REQUIRED；只有 U0 或宿主现实提供明确理由时才可 WAIVED。WAIVED 后 source instance、n、r、t gate 全部不适用。

## 5. R 与 D

R/r 必须挑战当前 revision，不能用旧结果刷计数。D 的独占 execution/result 留在 D_EXCLUSIVE，reintegration 才回 MAIN。D_EXCLUSIVE 计入 T，不计入 t。

## 6. 时间、WorkLease 与 coverage

T = MAIN + SOURCE + D_EXCLUSIVE；t = SOURCE。

同一可信 clock epoch 内，work lease 可为跨 host/process/tool 的已知正式工作保留时间归属。若恢复时 clock epoch 已变化，run 不终止：此前已验证时间保留，跨 epoch 区间不计时并记录 continuity gap，新 epoch 建立可信时钟后继续。coverage gap / continuity gap 都不会被猜测成 T/t。

## 7. 崩溃恢复

普通写入继续使用 write-intent；append-only journal 自验后可重新索引；revision history 是权威。run-brief/latest pointer 属于派生缓存，可在 checkpoint/recovery 重建，不要求每个语义事件后同步刷新。

## 8. Finalization

finish_time 先做 admission。适用 minima、显式 hard timing 与 semantic completion 未满足时保持 EXECUTING。FINISH 一旦提交，formal timing 不再打开。

## 9. 输出

结果正文优先，最后附 canonical proof：

`DIGR(N_target/N_actual, T_target/T_actual, R_target/R_actual, B, S_i(n_target/n_actual, t_target/t_actual, r_target/r_actual, b), D(target)/D(actual))`

## 10. 权威

本帮助属于当前 pinned P_run。真正执行权威仍是同 SHA 的 manifest、entrypoint 与 core。
