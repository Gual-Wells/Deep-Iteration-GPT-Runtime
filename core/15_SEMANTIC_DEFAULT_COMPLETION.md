# 15 — Semantic Default Completion

5.0 将所有调用统一为“用户显式参数 + 模型语义补全”。

设用户显式参数为 E、缺失参数为 M：

`EffectiveContract = Complete_native(U0, E, M)`

## Fixed defaults
只有三个直接缺省值：
- `B = 0`（soft）
- `b = 0`（soft）
- `L(1)`（语义隔离）

其余缺失的 `N/T/R/n/t/r/s` 必须由 ChatGPT 根据 U0 与**所有已给出的参数**联合判断，不允许固定 workload table、难度等级查表、正则 parser 或 deterministic helper 代替模型语义校准。

## Relative completion
补全是 `P(M | U0, E)`，不是各参数独立默认。例如用户只给 `B=1` 时，模型仍需生成与任务相称的非退化 T；生成后的 T 与用户给定值具有同等合同地位，并成为 hard target。`b=1` + missing t 同理。

显式 `T>0` 但 B 缺失时，B 直接缺省为 0，因此 T 为 soft；显式 `t>0` 但 b 缺失同理。

## Contract freeze
Semantic Completion 是执行前的 calibration，不计 N，也不属于正式 T/t 时间。形成 Effective Contract 后将其冻结为本轮 minimum target。执行发现更多复杂性时直接让 actual 超过 minimum，而不是反复漂移合同。
