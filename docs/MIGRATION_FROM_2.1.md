# Migration from 2.1.x

1. `manifest.version` → `2.2.0`，protocol → `digr-v2.2`。
2. 保留普通触发；新增 `(N,T)` / `（N，T）`。
3. 删除 active core 中的 `85_EXECUTION_EVIDENCE_REPORT`，改为 `85_RUNTIME_REPORT`。
4. 删除 `execution-evidence.schema.json`，新增 invocation/runtime-report schemas。
5. runtime state 删除 evidence_reporting/evidence_status，新增 prompt_iterating、requested/actual iterations、complexity budget、redo count。
6. 最终输出从“执行证据→最终结果”改为“最终结果→DIGR 记录”。
7. 提示词版本不再默认完全隐藏：仅公开最终 P* 与计数，不公开隐藏推理或逐轮思维链。
8. 旧 evidence discipline 中与事实来源质量有关的部分保留；只删除自证型执行证据块。
