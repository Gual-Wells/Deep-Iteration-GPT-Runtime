# 77 — L(e): Dictator Isolation Level

`L(e)` 指定 D 的隔离实现等级，`e ∈ {1,2,3}`；**缺省恒为 `L(1)`**。L 是 exact mode，不是 minimum，也不是 D 开关；D 是否启用只由 `D(s)` 决定。

## L1 — Semantic Isolation
同一总体模型/上下文内，通过 Shadow D、D-State、Semantic Firewall 和稀疏高层输入做 best-effort 语义分离。Coup 前 Main 不主动读取 D 的潜在野心/候选 gambit。L1 不声称独立 context/model/memory/compute。

## L2 — Context Isolation
必须同时满足：
- D 不继承完整 Main LLM history/context；
- Main→D 只有 controlled/compressed telemetry；
- latent D-State 在 coup 前不回流 Main；
- application state 也被隔离或过滤，不存在绕过信息墙的共享状态旁路。

仅“第二个 agent 名字”、默认 full-history handoff、nested run、独立 sandbox 或 worktree 任一单项都**不能自动证明 L2**。这些只是实现构件；必须以实际信息边界为准。

## L3 — Agent Isolation
全部 L2 条件 + 独立 Dictator Agent identity、独立 instructions、独立 D-State、独立 execution loop/lifecycle，并可独立调用工具。不同 model/model settings、sandbox、worktree、工具集是可选增强，不是 L3 定义要求。

## Capability honesty
宿主只能声明由事实证明的等级。确定性 helper 可以根据宿主提供的隔离事实计算最多可声称等级，但不把 API 名称当证据。目标等级无法兑现时 best effort，proof 如实显示 actual；无法确定则 `?`。

`D(0)` 只关闭 D，不引入 `L(0)`；L_actual 表示本轮配置/可兑现的隔离模式。
