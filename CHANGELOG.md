# Changelog

## 2.2.0 — Observable Iteration Runtime

### Added
- 参数化触发：`深度迭代（N，T）：` / `深度迭代(N,T):`。
- `N`：提示词有效优化循环的强制最小次数。
- `T`：参考任务复杂度预算，不作为墙钟时间承诺。
- `core/15_INVOCATION_BUDGETS.md`。
- `core/35_PROMPT_ITERATION_LOOP.md`。
- `core/85_RUNTIME_REPORT.md`。
- `schemas/invocation.schema.json` 与 `schemas/runtime-report.schema.json`。
- 可公开最终执行提示词 `P*`、0–5 进化度量、正式重做次数、实际流程链、真实查询/来源记录。
- 无依赖参考解析器与仓库自检脚本。

### Changed
- 默认输出顺序改为“最终结果 → DIGR 记录”。
- 提示词迭代从隐式过程改为可计数但不泄露思维链的优化循环。
- 结果回代明确区分“局部修订”和“正式重做”。
- 本地个性化指令压缩为可直接粘贴版本。

### Removed from active protocol
- `core/85_EXECUTION_EVIDENCE_REPORT.md`。
- `schemas/execution-evidence.schema.json`。
- 强制 `【执行证据】` 前置输出策略。
- 与旧执行证据块绑定的测试与运行状态。

## 2.1.0
- 三目标、三阶段、U0、原生能力保全、执行证据摘要。
