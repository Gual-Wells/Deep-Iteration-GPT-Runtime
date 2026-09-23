# DIGR 5.0.0-alpha.10 帮助

DIGR 是当前消息显式调用的深度执行模式。

## 参数
公开顺序：`N < T < R < B < S < D`；S 内：`n < t < r < b`。
B/b 默认 0。省略 D 时 D=0；显式 `D()` 可要求模型按任务语义补全 D。L 不再是公开参数。

缺失的 N/T/R 与实际适用的 source minima 采用“足够但不过度”的语义补全：用于防止过早停止，不用于展示工作量。

## Source
不再默认所有 DIGR 都必须外部检索。明确要求调研/时效事实，或外部证据对正确性有实质价值时为 REQUIRED；闭集创作、改写、纯推理等可 WAIVED 并说明原因。

## D
D(0) 仍表示零最低要求。普通 D 优先使用 compact completed lifecycle，一次记录完整 proposal→decree→execution→result→reintegration；只有中间阶段确有持久化价值时才逐步 revision。

## 时间
T=MAIN+SOURCE+D_EXCLUSIVE；t=SOURCE。只有显式 B=1/b=1 才是 hard timing。soft timing 不要求为了计时而开启 WorkLease。

## 恢复
普通 resume 走轻量路径：写入恢复、journal 批量重索引、stores 单次载入、clock resume。只有发现异常才升级为全量恢复/审计。

## 输出
结果优先，最后附 canonical proof：
`DIGR（N_target/N_actual，T_target/T_actual，R_target/R_actual，B，S_i（n_target/n_actual，t_target/t_actual，r_target/r_actual，b），D(target)/D(actual)）`
