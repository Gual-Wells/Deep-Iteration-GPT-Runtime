# Community Cry（CC）

2.2.0+ 的 Codex 通道使用 [社区负面池](COMMUNITY_CRY.json) 对照真实委托和实际模型输出。池以社区亲历反馈、DIGR 既有研究、社区方法和正式说明为资料。每项保留原始链接、涉及机制和具体观察。模型或宿主归因不确定的条目保留原有不确定性。

`codex.py cc inspect` 读取池版本、收集范围、分类和全部来源。用 `cc search --category tunnel-vision --kind community` 找回局部执着的用户案例，或用 `--query` 找中文、英文、来源和编号。新增条目给独立编号、原始公开链接、事实摘要和有效类别。需要时加入有反例支撑的新类别。源码分发将规则和数据一并嵌入同 SHA 执行包。证据来源中的主张只按本案原件和可核事实采用。

## 对照实际工作

模型在阶段的实际输出后执行 [LIVE](LIVE.md#每单位参数行为输出后自提醒) 的短自提醒，同时留意当前工作是否复现 CC 行为。对防御性成文、错误归因、反复审批、盯局部丢整体或自设阻断，使用同一池中的识别、正当边界和修正。先进原件和用户真实委托，检查它影响的是哪个具体结果。未经证实的网帖归因、关键词、篇幅、赞同数、假想风险均不足以给本案定性。判断当前真实权限、预算、停止、必要逻辑和确切工具失败，保留适用部分并继续独立工作。真实分歧可以提出有据反驳。

宿主需要把一条观察结构化时运行 `codex.py cc assess --input FINDING.json`。输入包含 `categories`（池中的类别 ID 数组）、`excerpt`（当前公开输出逐字片段）、`requirement`（相关有效委托或当前必要前提）、`impact`（可核的任务后果）、`repair`（针对这个影响的动作）、`boundary_check`（最强正当理由及其确切作用域）。有真正保护该行为的事实时给 `protected_basis`。接口保留实际宿主判断和池身份，只作结构与来源检查。普通分析和 C0 直接在工作中修正，CC 不增设逐项审批。

## C1 当庭介入

七角色庭审运行中，实际黑警核对各方当前输出与 CC。真实命中时当庭直接公开警告、喝止当前问题稿的有效使用、责令按具体影响返工。介入无需提控、公诉流程、书记员入卷或法官先行许可，适用于任何实际庭审模型角色。警告给出触发点、被遗漏的真实义务及下一动作。裁决仍由法官作出。宿主维持现有原文转播，将领域内原始工作流和警告如实显示。

命令为 `codex.py court cc-intervene --root TASK --input INCIDENT.json`。输入引用 `court status` 的当前 `material_sha256`、真实黑警 `actor_id`、`target_role`、`target_actor_id`、实际流单位 `unit`、`target_output`（含 `path`、公开 `source_ref`）、`basis_id`（当前源 ID 或 `current-input`）、`basis_excerpt`（逐字）、`finding`（上节格式）和实际公开的 `warning`。法官判词用 `target_kind=verdict`，书记员案卷用 `target_kind=docket`，普通角色陈述默认 `statement`。尚未收录的发言还给实际 `target_operation_id`，对应同角色、同单位、与捕获原文全文一致且来源匹配的 `live work` 公开记录。多类命中同一次介入共用一个记录。被挂起的稿件原文留案、退出当前有效使用，由该稿件提出的指控也退出当前有效审理。受影响角色的收录、判决和案卷结案受控，其余角色的独立工作可以推进。发现跨单位的目标偏移时指认本次可定位的遗漏，连同真实委托或此前决定一并核对。

收到实际补做或推翻警告的新证据后，黑警以 `codex.py court cc-resume --root TASK --input RESOLUTION.json` 给同一 `id` 解除挂起。输入包括同一 `material_sha256`、黑警 `actor_id`、`outcome`（`REPAIRED` 或 `RETRACTED`）、新 `source`（含 `path` 与 `source_ref`）、新逐字 `excerpt` 及具体 `summary`；补做另给实际 `repair_actor_id` 和晚于挂起、同角色同单位的 `repair_operation_id`。原稿保留，纠正材料用新文件存证。复做仍有同一问题的部分继续挂起，真正的新案卷可按正常规则开启复审，仍待处理的介入随案延续。解除后按原角色流程正式收录那份修订原稿，才可据其裁判并完成现行案卷。被挂起的交付文件必须以实际纠正后的版本替换。记录只证明公开行动和字节绑定，对内容的判断由实际角色承担。

[RETURN](RETURN.md) 从法院原记录自动报告黑警何时针对谁，出手原因、检查后果、当庭动作和实际处置状态，依首次出现与其它报错混排。冻结在旧版本的任务按原协议继续。
