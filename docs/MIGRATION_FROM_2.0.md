# Migration from 2.0.0 to 2.1.0

这是兼容 `digr-v2` 的次版本升级。

## 新增

- `core/85_EXECUTION_EVIDENCE_REPORT.md`
- `validation/execution-evidence-integrity.yaml`
- `schemas/execution-evidence.schema.json`
- 执行证据完整、部分、降级与反伪证据测试
- 最终输出顺序改为“执行证据 → 最终结果”

## 行为变化

2.0.0 默认只输出最终任务结果。2.1.0 在最终结果前增加简短执行证据摘要。

执行证据不等于独立中间件日志。没有外部记录的阶段只能标为运行时自证，不能宣称具有独立可审计证据。

## 部署

更新仓库文件和本地个性化文本后，保持 `stable/manifest.json` 指向 2.1.0 即可。
