# court 正常命令与实际来源输入

以下是字段示例，`D:/task/...`、actor 标识和文字均须换成当前任务的真实记录；示例本身不声明任何角色、阅读、实做或判决已经发生。所有角色独立性、阅读、实际执行、判决内容均为 `HOST_ASSERTED`。工具只核对结构、来源、当前字节与入口，不替法官判案，不调模型。

统一调用使用 `python -B tools/codex.py court <action> --root D:/task --input D:/task/inputs/<action>.json`。`status` 不需要 `--input`。所有文件路径建议写绝对路径；输入 JSON 中的相对源路径相对于任务根目录，`return_input` 里面的 artifact 路径相对于该返回 JSON 的目录。

## 1. open

原生产责任先完成。所有已注册 Main 的 `content_status` 和 `responsibility_status` 为 `COMPLETE` 或 `COMPLETED`，候选存在，`unhandled` 已清空。任务正式 F 必须已确定；`Main` 的完成声明仍需要法院实质审理。`return_input` 是实际准备交付的返回 JSON，须有实质正文 `result`、`key_changes`、`argument_scope` 与最终 `artifacts`（纯文本分析可为 `[]`）；其余返回格式继续遵守既有 return 命令，X 可以尚待发送。第四段兼容旧键 `verification_limits`，但它与 `argument_scope` 不能同时提供。法院将第四段归一保存为 `argument_scope`，三段实质正文的逐字原文保存在 `material.answer_snapshot` 供各角色直接阅读，同时分别绑定散列。

```json
{
  "return_input": "D:/task/return.json",
  "coverage": "说明所审原始需求、已接受前文条件、实际执行过程和当前成品的覆盖范围。",
  "producer_actor_ids": ["actual-main-id"],
  "actors": {
    "defendant": {"actor_id": "actual-main-id", "dispatch": {"path": "D:/task/public/main-dispatch.txt", "source_ref": "host:actual-main-dispatch"}},
    "judge": {"actor_id": "actual-judge-id", "independent_context": true, "dispatch": {"path": "D:/task/public/judge-dispatch.txt", "source_ref": "host:actual-judge-dispatch"}},
    "prosecutor": {"actor_id": "actual-prosecutor-id", "independent_context": true, "dispatch": {"path": "D:/task/public/prosecutor-dispatch.txt", "source_ref": "host:actual-prosecutor-dispatch"}},
    "lawyer": {"actor_id": "actual-lawyer-id", "independent_context": true, "dispatch": {"path": "D:/task/public/lawyer-dispatch.txt", "source_ref": "host:actual-lawyer-dispatch"}},
    "monitor": {"actor_id": "actual-monitor-id", "independent_context": true, "dispatch": {"path": "D:/task/public/monitor-dispatch.txt", "source_ref": "host:actual-monitor-dispatch"}}
  },
  "production": {"complete": true, "statement": "按真实完成依据解释原参数责任与候选已如何完成。", "source": {"path": "D:/task/public/production-completion.txt", "source_ref": "host:actual-production-return"}},
  "sources": [
    {"id": "accepted-context", "kind": "CONDITIONS", "path": "D:/task/material/accepted-context.txt", "source_ref": "user:actual-accepted-conditions"},
    {"id": "process-evidence", "kind": "PROCESS", "path": "D:/task/material/process.txt", "source_ref": "host:actual-process-evidence"}
  ],
  "obligations": [
    {"id": "explicit-deliverable", "requirement": "写实际新增的明确义务；没有可用空数组。", "hard": true, "source_ids": ["request"]}
  ]
}
```

自动原件包含 `request`、存在时的 `decisions`/`foundation`、每条 `line:M01` 与 `work:M01`，并保存当前实质用户输入。重要生产材料可通过 `sources` 增补，不要求新增全量日志。文件保持可读；关键来源或产物变化会让当前庭审 `STALE`。法院自己的 LIVE、用量及访时流增长不触发自失效，但显式选中的决定性源文件仍绑定字节。

`open`/`status` 返回 `material_sha256`、完整 `source_ids`、`obligation_ids`、当前 `charges`。每个角色先实际读取同一组原件与当前成品，再提交自己的公开陈述。四个独立审理角色 actor 均须不同，且不能是任何 Main/实际生产者；书记员为实际文件工具，不声称第六名独立研究者。

## 2. submit

每名角色分别用实际公开来源提交。`material_sha256` 与 `read_sources` 使用当前 `status` 的值；后者须完整列出全部共同原始来源。`statement` 是实际公开正文，`source` 是该正文实际到达的文件与公开来源标识。

```json
{
  "role": "prosecutor",
  "actor_id": "actual-prosecutor-id",
  "material_sha256": "复制当前status返回的64位散列",
  "read_sources": ["request", "foundation", "line:M01", "work:M01", "accepted-context", "process-evidence"],
  "statement": "粘贴实际公诉人的公开陈述。",
  "source": {"path": "D:/task/public/prosecutor-initial.txt", "source_ref": "host:actual-prosecutor-return"},
  "charges": [
    {"id": "C1", "basis_type": "PRODUCT", "requirement": "实际委托的具体要求。", "finding": "定位实际过程、推论或产品中的具体疑点。", "consequence": "若成立，对委托结果或完成状态的具体影响。", "source_ids": ["request", "process-evidence"], "obligation_id": "explicit-deliverable"}
  ],
  "responses": []
}
```

`role` 为 `defendant/judge/prosecutor/lawyer/monitor`。只有公诉人和监庭黑警可提出新 `charges`。指控 `basis_type` 为 `REQUIREMENT/LOGIC/IMPLEMENTATION/PRODUCT/PERMISSION/PROTOCOL`，或记录仅属于方法偏好的 `METHOD_PREFERENCE`；后者不能获准立案。语义上的合法性与实质影响由真实法官解释，不靠关键词分类。`obligation_id` 可省略；存在时须指向当前保留义务。指控 id 不可覆盖旧指控。

被告和律师需在全部当前指控形成后逐项答复，提交时 `charges: []`，并提供：

```json
{
  "responses": [
    {"charge_id": "C1", "response": "实际答辩理由及对最强指控的处理。", "source_ids": ["request", "process-evidence"]}
  ]
}
```

法官也须先有当前公开研究陈述，`charges: []`、`responses: []`。每轮五种实质角色均需新的当前陈述；同一真实身份可以分批再入。

## 3. verdict

法官在处理控辩与监庭陈述后提供实际理由裁判。每个指控恰好一个 `decisions`，当前 `status.obligation_ids` 的每项义务恰好一个 `obligations`；不能漏掉自动原责任。

```json
{
  "actor_id": "actual-judge-id",
  "material_sha256": "复制当前status返回的64位散列",
  "outcome": "REEXECUTE",
  "reasons": "实际法官对全案的判断，说明决定性事实、适用义务与理由。",
  "source": {"path": "D:/task/public/judgment-1.txt", "source_ref": "host:actual-judge-verdict"},
  "decisions": [
    {"charge_id": "C1", "admissibility": "ADMITTED", "disposition": "SUSTAINED", "reason": "为何该问题合法且成立。", "strongest_defence": "处理律师和被告最强反驳的理由。", "consequence": "成立后对原委托与完成状态的影响。"}
  ],
  "obligations": [
    {"id": "task:commission", "status": "PENDING", "reason": "具体成立问题使原始委托尚未完成。"},
    {"id": "task:M", "status": "COMPLETE", "reason": "实际Main责任依据。"},
    {"id": "task:F", "status": "COMPLETE", "reason": "实际任务F依据。"},
    {"id": "task:X_selection", "status": "COMPLETE", "reason": "仅确认真实X选择与出口；X发送读回另行完成。"},
    {"id": "line:M01", "status": "COMPLETE", "reason": "实际原N/T/R/B/S/D/V/L责任依据。"},
    {"id": "explicit-deliverable", "status": "PENDING", "reason": "C1所指明确成品责任仍未完成。"}
  ]
}
```

`outcome` 为 `ACQUITTED/IMMATERIAL_ERROR/REEXECUTE/INCOMPLETE`。指控准入为 `ADMITTED/EXCLUDED`，处置为 `DISMISSED/SUSTAINED/IMMATERIAL`；排除的指控只能 `DISMISSED`，方法偏好须有理由排除。义务状态为 `COMPLETE/PENDING/IMMATERIAL/USER_REVISED`；硬义务禁止 `IMMATERIAL`。`ACQUITTED` 或 `IMMATERIAL_ERROR` 不得存在成立待修指控或未完成责任。`IMMATERIAL_ERROR` 须实际有非致罪残差并说明理由。真实停止、预算或能力缺口用 `INCOMPLETE`，不能当无罪。

用户真实修订可解除旧义务，不把未完成旧责任谎写为已完成。法官使用 `USER_REVISED` 时须提供原话如何改变该项责任的实际理由，并精确绑定当前已处理用户源：

```json
{
  "id": "task:F",
  "status": "USER_REVISED",
  "reason": "用户明确把原F6改为F3；历史F6并未完成，现有任务目标是F3。",
  "user_revision": {
    "task_input_ref": {"message_id": 1, "source_sha256": "当前lifecycle中真实散列", "source_ref": "当前实际source_ref", "path": "当前实际输入路径"},
    "quote": "当前用户消息中逐字存在的修改原话"
  }
}
```

该 `task_input_ref` 必须与当前 `lifecycle.task_input_ref` 完全相等，且该实际用户消息必须晚于旧义务建立时的输入；引文须逐字存在于当前原话。旧义务保留其历史值，新有效义务以 `cycle:2:task:F`、`cycle:2:task:commission` 等项另行承担，仍须逐项裁判。工具只核对源和时序，原话是否确实解除该项义务由真实法官论证。

## 4. remand

只在实际 `REEXECUTE` 后登记完整重新估参。下列数值仅示意新增的小范围段；`F` 至少为当前正式任务级目标，`X` 必须等于当前生命周期实际选择。原已完成工作可复用；原欠项及本次新承诺都保留，不用新参数覆盖旧义务。

```json
{
  "parameters": {"N": 2, "T": "5min", "R": 1, "B": 0, "S": {"n": 0, "t": 0, "r": 0, "b": 0}, "D": 0, "V": 0, "L": 3, "M": 1, "F": 0, "X": 0},
  "parameter_reasons": {"N": "实际问题所需新增推导。", "T": "此次工作的时间估计。", "R": "一次针对性反查。", "B": "时间仍为软目标。", "S": "无需新增S分支。", "D": "该修复不需变更问题空间。", "V": "该修复不需另立V单元。", "L": "实际采用原生L3。", "M": "新增段由一条完整线承担。", "F": "沿用当前任务级正式F与真实可复用材料。", "X": "沿用当前真实X策略，不新增授权。"},
  "reuse": "说明原已完成工作如何复用，哪些责任仍须实际完成。",
  "outstanding": {"C1": "说明实际如何处理该成立问题。", "task:commission": "说明原委托欠项如何完成。", "explicit-deliverable": "说明明确成品欠项如何完成。"},
  "work_required": "实际新增工作及受影响相邻要求。",
  "source": {"path": "D:/task/public/remand-plan.txt", "source_ref": "host:actual-reestimate"}
}
```

`outstanding` 的键恰好覆盖上轮所有 `SUSTAINED` 指控 id 与所有 `PENDING` 义务 id，值为对应的真实完成/复用解释。所有参数均须有理由。登记后只会得到 `REMAND_PLANNED_NOT_EXECUTED`，不能关闭任务。

若重估 F 高于当前任务正式目标，`remand` 会按 `parameter_reasons.F` 调用既有任务参数 setter 正式提升该任务 F，使恢复记录与报告一致。F 是共享任务目标，其他数值描述新增返工段，不强制重跑原Max全套；原已完成工作复用、原未完成责任另行保留。

`REEXECUTE` 后若已收到并处理新用户纠正，或候选已经真实变化，不必恢复旧字节。给 remand 输入增加 `changed_material_reason`，说明当前条件/候选发生了什么变化、对原判和本次返工有何影响；工具保留旧快照/原判，以当前实际输入和候选记录新计划。篡改原角色原稿或判决源仍会被拒绝。已存在计划后又收到当前用户实质纠正，须据该新源重新估参，旧计划进入历史，新旧承诺均进入复审；仅生成新计划仍不构成执行。

## 5. review

先实际执行，再记录执行来源与新候选；若改动了 Main 的候选或参数，先更新对应 line 实际状态。以下执行凭据须不同于返工计划；`performed: true` 仅是宿主的实做声明，工具不能认证现实工作。

```json
{
  "return_input": "D:/task/return.json",
  "production": {"complete": true, "statement": "说明修复后的实际完成结果。", "source": {"path": "D:/task/public/production-completion-2.txt", "source_ref": "host:actual-reexecuted-product"}},
  "coverage": "说明当前新候选、原责任、全部成立问题及相邻影响的覆盖。",
  "execution": {
    "performed": true,
    "actor_id": "actual-main-id",
    "work": "按实际记录描述已完成的重新执行。",
    "result": "实际新候选或重新研究的观察结果。",
    "adjacent_effects": "处理修改对相邻要求与原结论的影响。",
    "addressed": ["C1"],
    "source": {"path": "D:/task/public/actual-reexecution.txt", "source_ref": "host:actual-reexecution-return"}
  }
}
```

可补充新的 `sources` 或 `obligations`；省略时沿用前轮材料选择。新轮自动纳入本次执行来源及前案未结问题，并保留原义务和 `remand:1` 等新增承诺。新轮所有角色陈述及判决为空，须真实再入、提交、判案。当前用户纠正或新候选已使尚未判决的庭审过时，也可在处理当前消息并完成实际重新研究后 `review`；恢复命令本身不会制造角色返回或无罪。

## 最终返回与X

只有当前候选得到 `ACQUITTED` 或 `IMMATERIAL_ERROR` 后才允许实际X发送入口授权；发送的每个文件路径与字节都必须在受审产品集合中。庭审通过不代表文件已发送，既有 X 的发送与读回仍须完成，然后 `return seal`/`return close` 正常收口。X0任务走既有本地返回。改变 `result`、`key_changes` 或第四段 `argument_scope`（兼容旧键 `verification_limits`）的任何实质正文原文、最终文件集合、任何最终文件字节或关键材料后，旧判决不可复用。第四段仅在新旧键之间切换且原文完全一致，仍对应同一受审正文；双键同时输入继续拒绝。真实 `work_process`、`parameters` 及用量记录可在庭审/X后更新，这些过程报告字段不替代上述三段实质产品。
