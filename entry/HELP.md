# DIGR 5.0.0-alpha.4 帮助

DIGR（Deep Iteration GPT Runtime）是显式调用的高投入执行模式。它在单条用户消息内生效，不自动粘连到下一轮；未再次调用时，下一条消息按普通 ChatGPT 处理。

## 1. 调用与路由

正式调用形式：

```text
DIGR：<任务>
DIGR(<参数>)：<任务>
深度迭代：<任务>
深度迭代(<参数>)：<任务>
```

`DIGR` 必须是精确大写 ASCII；`digr`、`Digr` 等不触发。仅调用头中的全角/半角括号、逗号与冒号可等价规范化；任务正文保持原样。

`DIGR/help` 与 `深度迭代/help` 只读取当前固定版本的帮助，不建立 DIGR Run、任务时钟、U0 或执行合同。

本地路由采用宽捕获。某些以 DIGR 开头但并非执行调用的讨论，会在取得当前固定仓库启动协议后被分类为 `NATIVE`，并将原始消息交还普通 ChatGPT；例如“DIGR是什么？”不是执行任务。

## 2. 参数解析顺序与缺省规则

公开参数顺序为：

```text
N < T < R < B < S < D < L
```

`S` 内部顺序为：

```text
n < t < r < b
```

缺省处理分两层，顺序固定：

1. 先应用三个确定性缺省：`B=0`、`b=0`、`L(1)`；
2. 再由原生模型结合 U0 与全部已给参数，对缺失的 `N/T/R/n/t/r/s` 做语义补全；
3. 形成并冻结本轮 Effective Contract。冻结的是本轮承诺，不冻结策略。

因此：

- 显式 `T>0` 而省略 B：B 固定为 0，T 是 soft target；
- 显式 `B=1` 而省略 T：T 仍必须按任务规模语义补全，补全结果成为 hard lower bound；
- `t/b` 同理；
- 裸数字永远不能被猜成 T/t 的时间单位。

参数映射必须唯一。省略字段不会让后续参数任意左移；若无法得到唯一映射，则调用为 AMBIGUOUS/INVALID，不得擅自猜测。

## 3. 参数参考

| 参数 | 语义 | 省略时 |
|---|---|---|
| `N` | MAIN 最少有效进化次数 | 语义补全 |
| `T` | Formal Active Task Time 目标 | 语义补全 |
| `R` | MAIN 候选结果最少整体重入次数 | 语义补全 |
| `B` | T 时间政策：0 soft / 1 hard | `0` |
| `S(n,t,r,b)` | 来源进化下限 / 来源有效时间目标 / 来源重入下限 / t 时间政策 | n/t/r 语义补全，b=`0` |
| `D(s)` | 最少完成并重新整合的 D intervention 数 | 语义补全 |
| `L(e)` | D 隔离实现目标，`e∈{1,2,3}` | `L(1)` |

`N/R/n/r/D` 是无条件下限而非上限。`T/t` 是时间目标：当 `B/b=0` 时为 soft target；当 `B/b=1` 时升级为必须由可信时钟事实证明达到的 hard lower bound。达到任何下限或目标都不自动迫使停止；Result Sovereignty 仍要求判断继续工作是否还能实质改善结果。

`S`、`S()`、`D`、`D()`、`L`、`L()` 都是合法标记。`S()` 表示 n/t/r 留给语义补全且 b=0；`D()` 表示 s 留给语义补全；`L()` 表示 L1。

边界示例：

```text
DIGR(1,1)：任务
# 唯一映射为 N=1，R=1；T 省略

DIGR(1)：任务
# 单个裸计数在 N/R 之间歧义

DIGR(1,10min,1,S())：任务
# N=1，T=10min，R=1；S 的 n/t/r 语义补全，b=0
```

## 4. Effective Contract 与来源策略

EXECUTING 调用先建立可信 Clock Genesis，再做参数解析、U0 冻结与合同形成。Effective Contract 包含显式参数、确定性缺省、语义补全结果、SourceDisposition、L 目标及用户硬约束。

正常执行的 `SourceDisposition` 默认为 `REQUIRED`。只有 U0 或宿主现实给出明确理由时才可 `WAIVED`，例如用户禁止外部来源、任务是封闭变换且外部材料确实无关，或宿主没有任何外部通道。“模型已经知道答案”不能作为 waiver。

`S(0,0s,0,0)` 只把 S 的数值下限/时间目标降到零，不会自动关闭来源研究。真实 S actual 必须绑定 SourceWorkspace、SOURCE 时钟状态与语义 source evolution/re-entry 证据。

## 5. N / R / D / L

`N` 计数的是有实质变化的 MAIN evolution，不是机械改写次数。

`R` 是把已有候选结果重新送回整个解决过程接受独立挑战，可挑战候选、任务表示、策略、分解、证据、来源计划、工具路线或验证方法。经过实质挑战后保留原候选是允许的，但必须有对应 re-entry 证据。

`D(s)` 中的 s 是最少完成次数。`D(0)` 仅表示“没有必须完成的 D 下限”，**不禁止**模型在结果质量需要时主动执行 D；实际 completed D 可以大于目标。

L 始终区分三个事实：

- `L_target`：合同请求的隔离目标；
- `L_cap`：宿主有证据支持的最高能力；
- `L_actual`：某次 D isolation receipt 实际采用的等级。

L1/L2/L3 分别表示语义隔离、受控上下文/信息包隔离、独立 agent 生命周期隔离。能力不能自动升级为 actual。若本轮没有 completed D，proof 中 L actual 可以保持 `?`；若实际完成了 D，则 L 按 intervention-linked receipts 正常判定。L mismatch 默认可见但不普遍阻断交付；只有 U0 明确把精确 L 设为硬交付条件时才成为 stop gate。

## 6. 时间与停止

Formal Active Time 只记录有效主动工作：

- `T = MAIN + SOURCE`；
- `t = SOURCE`；
- `META`、`IDLE`、exclusive D 不计入 T/t；
- 并行来源共享同一 SOURCE 时间并集，不重复累加。

等待、sleep、重复查询、日志、机械重写或纯工具排队不得拿来填充 T/t。

`B=1` / `b=1` 时，只有完整相关区间都具有可验证的单调时钟连续性，才允许声明对应 hard target 已达到；无法可靠证明时 actual 使用 `?`，不得估算或补齐。跨进程/会话恢复必须重新证明连续性，未知间隔不计为任务时间。

停止要求同时考虑机械合同与结果质量。满足机械条件只打开停止资格，不自动命令结束。

## 7. 执行链与启动成本

一次 EXECUTING 调用的规范顺序是：

```text
当前仓库 authority → immutable P_run
→ startup slice 分类
→ trusted Clock Genesis
→ 同 SHA execution bundle / 完整 entrypoint+core 验证
→ ExecutingProtocolLoadReceipt
→ 参数解析 + U0
→ Effective Contract freeze
→ MAIN / Strategy Genesis
↔ N / S / R / 可选 D-L
→ 完成度与开放问题检查
→ timing / workspace 验证
→ 结果 + canonical proof
```

仓库 pin、启动切片、完整执行协议验证、参数/合同建立与 META 验证属于高投入模式的启动/可靠性成本，不应为了缩短墙钟时间而绕过；当前版本用一个确定性 execution bundle 聚合传输逻辑上的 entrypoint+core，以减少仓库往返而不减少协议内容。完整协议验证失败会终止已经出生的 Run，且这些启动成本不会被伪装成 T/t 正式任务时间。

## 8. 输出与 canonical proof

正常回答先给任务结果，最后只附一行紧凑 canonical proof：

```text
DIGR(N_target/N_actual, T_target/T_actual, R_target/R_actual, B,
     S_i(n_target/n_actual, t_target/t_actual, r_target/r_actual, b),
     D(target)/D(actual), L(target)/L(actual))
```

`?` 表示该 actual 无法可靠验证。用户可见 proof 必须遵守 canonical renderer 语义：actual duration 向下取整到完整秒，不输出内部纳秒值或未经规范化的浮点秒；B/b=1 且 hard verification 不成立时，对应 actual time 必须显示 `?`。

正常回答不倾倒隐藏推理、Strategy/EST、查询日志、clock journal、schema 或仓库审计文件。

## 9. 版本与权威

本帮助属于当前 pinned `P_run` 的用户级参考。具体仓库提交 SHA、manifest/VERSION 一致性与启动路径由本轮 repository authority 负责验证；帮助文本本身不替代版本化执行协议。
