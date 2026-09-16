# 15 — Semantic Default Completion

5.0 的参数补全分为两个分支：**全缺省固定合同**与**局部缺省语义补全**。二者不能混用。

设用户显式参数/标记集合为 E、缺失参数为 M。

## Canonical all-omitted contract

当且仅当 E 为空，即调用头中完全没有参数 token，也没有 `S` / `D` / `L` 标记时（包括 `DIGR：task`、`DIGR()：task` 及中文别名等价形式），直接采用固定合同：

`DIGR(3,3min,5,1,S(3,1min,5,1),D(3),L(1))`

等价字段为：

- `N = 3`
- `T = 180s`
- `R = 5`
- `B = 1`
- `S.n = 3`
- `S.t = 60s`
- `S.r = 5`
- `S.b = 1`
- `D.s = 3`
- `L.e = 1`

该规则优先于结构解析层返回的 B/b/L 空位缺省，也优先于按任务规模进行的语义校准。全缺省时不得把 N/T/R/n/t/r/s 再按 U0 漂移；用户若希望改变任何一项，应显式给出参数或标记，从而进入下面的局部缺省分支。`SourceDisposition` 仍由来源策略独立决定，正常 DIGR 仍默认为 `REQUIRED`，不因这套数值合同而改变。

## Partial omission

只要 E 非空，就不套用上面的整套固定合同，而继续使用原有相对补全：

- `B = 0`（soft）
- `b = 0`（soft）
- `L(1)`（语义隔离）
- 缺失的 `N/T/R/n/t/r/s` 由 ChatGPT 根据 U0 与**所有已给出的参数/标记**联合判断。

因此局部补全仍是：

`EffectiveContract = Complete_native(U0, E, M)`

不允许固定 workload table、难度等级查表、正则 parser 或 deterministic helper 代替模型语义校准，也不得把全缺省基线逐字段机械灌入局部缺省位置。

## Relative completion

补全是 `P(M | U0, E)`，不是各参数独立默认。例如用户只给 `B=1` 时，模型仍需生成与任务相称的非退化 T；生成后的 T 与用户给定值具有同等合同地位，并成为 hard lower bound。`b=1` + missing t 同理。

显式 `T>0` 但 B 缺失时，B 先按局部缺省固定为 0，因此 T 是 frozen soft target，而不是机械时间下限；显式 `t>0` 但 b 缺失同理。

`D=0` / 局部语义补全得到 `s=0` 只表示 completed D 的最低要求为零，不关闭 D 机制。若模型认为非局部干预能实质改善结果，actual D 仍可大于目标。

## Contract freeze

全缺省固定合同的装载、以及局部 Semantic Completion，均属于执行前 calibration，不计 N，也不属于正式 T/t 时间。形成 Effective Contract 后将其冻结：计数/D 字段冻结为最低承诺，T/t 冻结为由 B/b 决定 soft/hard 的时间目标。执行发现更多复杂性时让 actual 超过最低值或 soft target，而不是反复漂移合同。
