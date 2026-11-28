# Paper Pool 与学术任务识别

本章随 DIGR Codex 2.0.0 起的执行协议取得。Paper Pool（PP）是论文、学术和科研任务的正式路由目标。首批语料包含原有同批 5,000 篇的作者摘要、逐篇机制证据及九维亲本。PP 可分批扩充语料，承担当前委托中一块有分量、能验收的工作。

## 识别当前任务

Main 在原有 U0 中按任务的**真实目标、原件和交付**识别。论文阅读、翻译、排版、审稿、学术写作、文献调查、选题、研究方案、科研推导、实验设计或结果解释均可构成学术任务；用户已明确的语境、附件和补充内容也参与判断。只在名称、引文、工具输出里出现的词不决定任务类型。混合委托按其中的学术成果分配 PP 职责，规模与该成果相称。

首次任务或实质改向在 foundation 的 brief 中填写以下保持原次序的计划字段。真实续做回读当前委托；已有基准未变则保留绑定。普通追问、状态和费用消息不重开分类。发现实质目标变化时沿原任务的 `task handle --action revise` 和新 U0 更新；旧工作保留为历史，新的完整性由当前委托判断。旧 P_run 保留自己的工作流。薄候选路由按启动切片工作。

```json
{
  "paper_pool_routing": {
    "academic": true,
    "reason": "实际要求对端边推理调度的实验给出基线与证据分析",
    "baseline": {
      "environment": ["当前实验工作区和用户选定的工具环境"],
      "routes": ["原有 DIGR 研究及实验工作"],
      "access": ["用户原实验和约定的数据"],
      "search": ["原计划的公开前作检索"],
      "research": ["既定对照实验及误差解释"]
    },
    "assignment": {
      "question": "哪些已发表的机制能解释调度随负载变化的表现？",
      "work": "比较同题前作的负载、调度动作、结果定义和可迁移条件，并核对当前实验的关键差别",
      "deliverable": "带来源和覆盖范围的基线证据矩阵，供实验解释和限制段落采用",
      "acceptance": "明确与当前设置可比较的量和不成立的迁移，能回到实际原文位置，影响实验解释",
      "source_scope": "pool-and-task"
    }
  }
}
```

原计划各类目标允许明确的空列表；环境和路由使用真实所选者。无学术责任时设 `academic: false` 并保存判定依据与原计划。选择 `task-only` 只用于当前用户约定或真实权限限制了来源的任务，填写 `scope_basis`。它指示 PP 在允许的用户材料或既有任务材料中实际承担工作。

## 保住原路线，派出 Paper Pool

按照本来会采用的方式先定原有环境、路由和已知的访问、搜索、调研目标。这个计划及其资源、顺序和来源准入不受 PP 命中、无命中或故障改变；原路在执行中仍可自行发现并使用后续材料。PP 可独立研读池内相关材料以完成自己的工作，不能代替原路径的搜索、访问、复算或核读。Main 要保留原路实际结果的去向；落选或原源访问失败要能指回实际理由或尝试，不能因 PP 有发现而取消原目标。

在原工作开始时把同一委托版本的 PP 工作包实际交给执行者。具备原生独立执行条件时并行；原路线有自己的优先级和有效权限。宿主按真实能力派发，工具只绑定工作和证据。池未配置、暂时失效或没有相关覆盖时，原路线照常推进。范围允许时，PP 仍可交付真实的任务材料工作，例如逐页译文和公式/图表对照、证明的前提与反例复核、实验的对照与归因检查。零命中、材料工作和相应贡献分别据实登记。

PP 负责一个完整问题、关键章节、一项核心比较或质量责任，覆盖随任务规模调整。不能用固定百分比、论文条数、调用次数、三条检索摘要或者一段泛评充抵。正文主张采用原件时说明支持力度；作者摘要级和全文证据分开。对一篇文学类文章做整篇翻译时，PP 可承担贯穿文章的术语出处与逐段对应审查，并留下会影响译文的勘误或明确的结果核对。

## 证据接入与工具

2.1 起优先使用本机私有索引 `CODEX_HOME/digr-codex/paper-pool.sqlite3`。`paper-pool migrate` 从已有 JSONL 绑定生成索引，保留首批库指纹。`paper-pool append --abstracts NEW_ABSTRACTS.jsonl` 验证并原子追加一批新论文。可同时给出 `--parents` 和 `--extractions`，也可先录入真实作者摘要。每个提供的资料层与该批论文编号一致，原始身份和锚点须能核对。重复投递同一批会返回已有状态，冲突批次整批回滚。

默认查询索引中的当前快照，进行中的 PP 工作沿第一次成功查询的库指纹继续。普通检索只读索引候选，单篇回读按 P 编号查找。`paper-pool check` 查看快照和规模，`paper-pool audit` 核验索引及归档原件哈希。每条证据保留批次、来源文件哈希、行号和句段位置。已有 JSONL 绑定仍可由原精确 pin 恢复。

```text
python -B tools/codex.py paper-pool check
python -B tools/codex.py paper-pool append --abstracts NEW_ABSTRACTS.jsonl
python -B tools/codex.py paper-pool route --root TASK
python -B tools/codex.py paper-pool dispatch --root TASK --actor ACTUAL --source ACTUAL_HANDOFF
python -B tools/codex.py paper-pool search --root TASK --term "edge inference" --term offloading
python -B tools/codex.py paper-pool show P0001 --root TASK
python -B tools/codex.py paper-pool baseline-result --root TASK --kind search --target "原计划的公开前作检索" --disposition used --reason "当前证据矩阵中的实际来源" --attempt ACTUAL_SEARCH_REF --evidence-anchor "日志内的确切结果" --artifact BASELINE_EVIDENCE
python -B tools/codex.py paper-pool result --root TASK --artifact PP_WORK --contribution "真实贡献" --source TASK_QUERY_JSON --cite P0001
python -B tools/codex.py paper-pool consider --root TASK --disposition applied --effect "对候选的具体作用" --artifact MAIN_PRODUCT --return-input RETURN_INPUT
python -B tools/codex.py paper-pool status --root TASK
```

占位符替换为本任务真实材料。检索时按论题调整问题和术语，阅读原件和所需证据后才形成工作。`search`、`show` 的任务回执可支持该工单引用。将带任务回执的实际 JSON 响应交给 `--source`，原文锚点或响应字段遭改动时无法作为引用依据。专题证据、产物和 Main 实际采用、核验或有据排除的后果分别保存。池覆盖不足时 `--pool-issue` 记录真实检索或访问限制，仍需提供实际工作、核对原件和处理。PP 专属结果与原路径结果分别登记；原目标有各自的实际来源或尝试证据。

## 交付

Main 用实际成品判断 PP 工作的贡献与规模，助手校验当前委托、已交接的任务证据、真实产物和处置所绑定的字节。`return status` 报告 PP、原结果以及经 PP 处理的主线候选能否正常收口。在 `consider` 中选择真正返回的正文及成品清单。正文或成品发生实质变化时重新处理后再收口。PP 或原路线尚有缺口时，可以已完成的真实结果照原出口交付，报告相应未完成范围。任务按用户实际停止或撤销结束。无学术责任的任务沿原路收口。
