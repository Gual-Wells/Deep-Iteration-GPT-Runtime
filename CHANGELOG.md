# Changelog

## 2.3.0 — Semantic T Calibration

### Changed
- 将 `T` 从“人类任务时长参考 + 离散复杂度档位”重定义为 **GPT-5.6 Sol / High 的语义任务规模**。
- 删除 `Focused / Analytical / Deep / Research` 固定时长分档，避免 11m 与 29m 被压成同一档。
- 明确 parser 只负责调用头抽取，T 的复杂度含义必须由 ChatGPT 结合 U0 解释，不由字符程序、token 公式或 workload 表硬编码。
- 新增停止前 `T budget adequacy` 回检：答案已可用但仍有高价值工作时不得仅因“差不多了”提前停止。
- 允许工具并行和高效率导致墙钟时间短于 T，但禁止把巨大时间差自动合理化；若已知执行明显偏短，应增强预算充分性检查。
- 多交付物任务增加覆盖意识：资源自适应分配，但每个核心交付必须得到针对性验收。
- 远程协议加载改为优先固定到单个 immutable commit，避免一次运行跨版本读取。

### Added
- `core/18_T_COMPLEXITY_CALIBRATION.md`
- `docs/T_COMPLEXITY_SEMANTICS.md`
- `docs/MIGRATION_FROM_2.2.md`
- `workflow/t-complexity-calibration.yaml`
- `validation/t-budget-adequacy.yaml`
- `tests/test_t_semantics.py`

### Engineering
- `runtime/reference_parser.py` 保留 T 原始字符串并明确不承担语义解释。
- 扩展 invocation/runtime report/work package schema。
- 增加 2.3 语义回归测试与仓库静态验证。

## 2.2.0
- 参数化 N/T、可公开 P*、进化度量、重做次数、实际流程链与来源记录。
