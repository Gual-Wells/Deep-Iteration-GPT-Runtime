# 工作工具：取回问题、继续制作、保留真实后果

长任务从已有笔记开始，必要时再使用这些标准库工具。统一入口是 `python -B tools/codex.py`；Claude提交的原生分工及`consult split`／`call --split-plan`见必读[SPLIT](SPLIT.md)。工作台、版本和访时工具保存实际事实。外部推理仅从满足角色、费用与 Split 条件的调用入口提交。

按 [PROTOCOL](PROTOCOL.md) 解释任务冻结版本和用户当前选择。Stable 的 `task lifecycle/report` 给出当前 `claude_policy`。单冒号为 `COUNCIL_ONLY`，双冒号为 `ALLOW`。普通话明确更改时用 `task handle --claude-selection COUNCIL_ONLY|ALLOW|DENY` 绑定真实当前原话。已有任务按原 pin 的枚举及费用契约恢复。`profile classify --pin <版本@完整SHA>` 可离线预览对应语义，省略 pin 时预览当前分发，真实获取仍走 `acquire`。

论文辅学另有可选的[知识池技能](../.agents/skills/digr-paper-knowledge/SKILL.md)与 `python -B tools/codex.py knowledge --help`。原生 Codex 读论文、分层批量问询和教学，工具保存冻结问项、论文局部用法、真实选择、有范围证据及接续位置。个人数据与原件放在独立私有项目，不进入本公共库；可从私有项目的相对路径入口接续，本机定位缓存仅用于发现。它不替代本轮在线 DIGR 协议获取，也不需要阅读器或付费模型接口。普通读取只用标准库，摄入 PDF 另需所选 Python 环境中的 `pypdf`。具体数据与命令见技能的按需引用。

统一 DIGR 第二层实际委托 Sonnet 制作整篇解构、导读或完整读物时，应用同 SHA 声明的[论文协议](../paper/PROTOCOL.md)、[技能](../.agents/skills/digr-paper/SKILL.md)与 `python -B tools/codex.py paper --help`。它保存每篇的来源/导读映射、候选和Gmail读回事实；不替知识池写学习证据，单篇返回也不关闭当前DIGR任务。

必读[RETURN](RETURN.md)要求最终response正文固定五段：结果、关键变化、工作过程、论证与适用范围、参数。过程用正文时间／工作表，不能由文件、内嵌页或截图替代；真实任务产物仍可链接。`return seal/status/body/close`保存选定正文并收口；body输出待发送Markdown，不证明宿主已发送。历史timeline是按需工具，不再是默认报告。

## 0. 在其它项目找到工具，及时开始记录

本机经验证的工具可安装在D盘的独立版本目录；定位文件为 `CODEX_HOME/digr-codex/toolchain.json`。其中version、root、cli与source_commit只说明已安装工具身份，不是新消息的仓库HEAD、执行授权或完成证明。没有安装时可用实际已知的仓库绝对入口；不要求为了执行一个任务先安装服务。

已有任务先取其冻结的完整 `P_run=version@SHA`，使用 `installed_distributions[P_run]` 中的工具。只有顶层 `version + '@' + source_commit` 与 P_run 相同时才使用顶层 root/cli。没有精确分发时取得相应发布版本。

PowerShell跨项目调用示例：

```powershell
$toolLocation = Get-Content (Join-Path $env:CODEX_HOME 'digr-codex/toolchain.json') -Raw -Encoding utf8 | ConvertFrom-Json
python -B $toolLocation.cli profile check
python -B $toolLocation.cli workbench --help
```

保持当前项目工作目录，request、work和out传该任务的真实绝对路径；运行源码仍在独立工具根，不往当前项目复制协议或改变它的Git状态。工具版本与本轮协议不一致时按实际可用接口处理，不假称本地已经取得最新pin。

把访时准备放进初始化：task只关联共同文件与run_id，准备已初始化的line；各实际参与者在实质WORK/SOURCE开始前记Begin，INIT说明实际口径。没能力时立即说明未知并继续可做的工作，不延迟任务去造计时平台；不得在几十分钟之后用新起点回填早段。时钟相关命令见第6节。

## 1. 取得协议：在线获取与同 pin 续读

```text
python -B tools/codex.py acquire --stage startup --out D:/task/acquired-startup
python -B tools/codex.py acquire --stage execution --continue-from D:/task/acquired-startup --out D:/task/acquired-execution
```

第一条实际读取 Codex 分支 HEAD，以同 SHA 取得 manifest、VERSION 和启动切片。按启动语义分类，EXECUTING 才取第二条，HELP 把 stage 换成 help。第二条续读原 pin。新消息的获取按真实入口发生，既有执行 P_run 保持冻结。

薄路由与轻量偏好可用 profile export codex-agents --out D:/task/AGENTS-codex.txt 一次导出；仅创建新文件，不安装、不覆盖全局约定，也不复制深执行语义。

CLI默认使用直接HTTPS：同次读取Git ref和Branches，SHA必须一致。宿主已有GitHub connector时，可由模型直接使用连接器取得真实分支HEAD和同pin原文；代码集成也可给 `CodexRepositoryTransport(fetch)` 传入真实连接器fetch，调用 `acquire(connector=True)`。该响应必须是live_direct、github_connector，不能拿搜索结果或以前保存的JSON当新HEAD。直接API在某台机器返回504，不证明连接器也不可用。

执行可从manifest声明的聚合包一次取得完整正文，校验成员顺序、字节、版本及manifest散列；不是只看摘要。实际声明路径失败则说明获取失败，不用旧协议补。`profile check`只看本地分发；开发者明确修改源文件后用 `profile refresh`重建聚合包和hash。后者是源维护操作，不是修改后再假称旧pin未变。

### 可见流

按 [LIVE](LIVE.md) 直接在 commentary 发布实际工作身份、阶段和结果。Claude 请求运行时持续读当前公开流。使用持久游标时，`live read --format commentary` 输出供宿主直接发布的正文，实际发布后才 ACK。已收到的独立返回另显示 Main 的实际取舍。

### 两层 Claude 的费用依据

在本版新单冒号任务中，用 `council create --first-opinion "仍然开放的具体取舍" --facts FACTS.md` 加所用任务根、议会 ID 和真实原生 actor，进入 [COUNCIL](COUNCIL.md#单冒号的独立首发) 的单成员首发。宿主判断真实决定窗口，按需以 `--deadline-seconds` 调整默认 300 秒。用 `prepare-round` 准备 exchange，为该 exchange 实际完成 Split。默认 Sonnet 5.5／high／16,000 总输出 token。有预期回传时，在第一层累计上限内为首轮及必要续答估算余量。

首发的问题可以是希望 Claude 帮忙发现选项的真实用途或构形选择。把它可能改变的决定和已具备的材料落在当前 Split 和公开阶段。后续按实际所得选择有新贡献的议会研究或正式指导，沿对应角色及费用入口准备。

纯文本首发走 OpenRouter 官方接口，且同一配置能查询模型价格及账户实际余额时，用 `council run-round --root TASK --council-id ID --round-id 1 --split-plan SPLIT.json`。价格与余额取该配置实际响应，预留受分层上限、共享钱包和用户限额约束。密钥用量或密钥额度单列。采用其他提供商或无账户余额查询权限时，用 `--plan PLAN.json` 提供同一实际账户的费用事实。已提交的首发含空答均沿原 exchange 读回和对账，有实际 Codex 工作回传才按该请求另作同线续答。

1.3 起，当前实际用户选择直接提供对应层的额度内费用许可。单冒号和双冒号的第一层每任务累计 0.20 美元，双冒号第二层累计 1.00 美元。发送时提供当前价格、完整请求输入量上界、真实钱包余额与保守费用上界。共享钱包在同一事务中核对本层已知费用、未结预留和本次预留，沿用用户实际任务限额。

两种入口均可用 `consult budget-preview --root TASK --input INPUT.json --out PREVIEW.json` 提前估算。输入 `wallet_id`、`task_ceiling_usd`、`scope` 和 `jobs`。每项给当前费用 `facts`、`ceiling_usd` 及已准备的 `exchange_id`。为在议会开始前估算，也可用 `planned_council_member` 代替 `exchange_id`，写明实际用途 `purpose`、型号 `model` 和合计输出上限 `max_tokens`。预览的 `layer_budgets` 给出适用层的实际余量和拟预留额度。发送按当前入口授权、钱包和 Split 执行。

可同批估算正式产出的候选与裁决。未准备的阶段用 `planned_production` 代替 `exchange_id`，内含已登记的 `production_id`、`stage`（`candidate` 或 `arbitration`）、`model`、`max_tokens` 和真实 `purpose`。该项同时给当前 `facts` 与 `ceiling_usd`。同一对象两阶段用同一 Claude 型号。两份实际候选、必要材料及公开历史计入裁决的输入上界。

用户给出更窄额度时，用 `consult budget-limit --root TASK --reply-file RAW.txt --source ACTUAL_REF --quote ACTUAL_EXACT_WORDS --task-ceiling-usd LIMIT` 登记实际原话。更窄限额跨后续发送和入口切换生效。费用单独更新可用 `task handle --action budget` 保留工作输入。实质工作改变则按实际作用域更新请求和 Split。历史 `budget-approve` 按旧 pin 使用。

### 子议会成员交办的 Codex 工作

Claude 可在实际公开正文末尾发出如下独立区块，区块放在引文和代码围栏之外。每项说明要交付的工作和它会影响的判断。

```text
[[CODEX NATIVE WORK]]
[{"work":"从论文找到清楚区分上传耗时和路侧计算积压的原式及定义","informs":"决定导读要从信道条件还是历史计算负担切入"}]
[[END CODEX NATIVE WORK]]
```

通过正常议会发送后，真实提出支持请求的成员进入 `AWAITING_NATIVE_WORK`。先完成本机工作，再以实际回包和选定的 UTF-8 原件片段登记结果。多个片段重复使用 `--source`，无法完成时登记 `--outcome UNAVAILABLE` 并上传真实遇阻说明。按角色、编号和来源用 [LIVE](LIVE.md) 显示实际状态。

```text
python -B tools/codex.py council native-work --root TASK --council-id ID --actor Main
python -B tools/codex.py council native-work-return --root TASK --council-id ID --actor Main --work-id WORK --input RESULT.md --source EXCERPT.md
python -B tools/codex.py council prepare-round --root TASK --council-id ID --kind NATIVE_WORK_RETURN --member MEMBER
python -B tools/codex.py consult split --root TASK --exchange-id NEXT --input NATIVE-DECISION.json --out SPLIT.json
python -B tools/codex.py council run-round --root TASK --council-id ID --round-id ROUND --plan ROUND.json
```

当前成员的委托结果齐备后再准备回传。轮次使用实际返回的编号和 exchange ID，沿原成员及同一公开历史传入对应的结果。适用的纯文本 OpenRouter 首发同线续答可沿 `run-round --split-plan SPLIT.json` 自动取价和核对余额。常规 `--plan` 每项指明本次费率、保守上界和 Split。续答仍占用第一层余额，沿原决定窗口和 `high` 或更高配置运行。

### 第二层准备、两份成品与实际落实

采用正式双边产出协议的任务按 [CONSULT](CONSULT.md) 判断实际目的。仅委托意见的请求用 `consult prepare --root TASK --input GUIDANCE.txt --exchange-id G --guidance`。委托实际成品时，把当前用户要求、交付范围和验收条件写入 UTF-8 的 `SCOPE.md`，向实际原生 L3 派发该工作。用真实代理身份和本次派发出处登记，再准备 Claude 候选请求。制作所选论文读物时，下列两条命令分别加上同一个 `--paper-root PAPER`。

```text
python -B tools/codex.py production start --root TASK --production-id F --scope SCOPE.md --actor NATIVE_ACTOR --dispatch-ref ACTUAL_DISPATCH
python -B tools/codex.py consult prepare --root TASK --input CANDIDATE_TASK.md --exchange-id C --production-id F --production-stage candidate
```

每次准备可选择必要原文与图。准备后按 [SPLIT](SPLIT.md) 绑定该请求的计划，按当前已批准阶段与费用事实实际发送。调用中的公开正文按 [LIVE](LIVE.md) 转播。原生完成后登记同范围真实候选的完整 UTF-8 正文与返回出处。取得两份同版本可用成品后，准备终裁请求。

```text
python -B tools/codex.py production submit-native --root TASK --production-id F --actor NATIVE_ACTOR --output NATIVE.md --return-ref ACTUAL_RETURN
python -B tools/codex.py consult inspect --root TASK --exchange-id C
python -B tools/codex.py consult prepare --root TASK --input ARBITRATION_TASK.md --exchange-id A --production-id F --production-stage arbitration --candidate-exchange C
```

终裁准备复用实际 Claude 候选交换，按原样回放其公开正文，在当前提交加入共同作用域及原生候选全文。按真实对象加所需原件和图，让 Claude 能判断两份作品。两轮 `prepare` 使用同一个实际型号，选择非默认型号时两轮均明确传入 `--model`。终裁另做当前 Split、费用核对和发送。`consult inspect` 查看实际交换，`production inspect` 查看原生派发、实际稿件及当前应用状态。

Main 实际采纳裁决后，将交付的文件或完整答复正文与裁决绑定。记录具体作品变化，交付按 [RETURN](RETURN.md) 和 [DELIVERY](DELIVERY.md) 进行。

```text
python -B tools/codex.py production record-applied --root TASK --production-id F --arbitration-exchange A --output FINAL --effect ACTUAL_EFFECT
python -B tools/codex.py production inspect --root TASK --production-id F
```

受到实质纠正时，旧稿、公开交换和费用仍按来源保存，新的正式产出用当前范围登记。用户明确接受单侧降级结果时，用 `production release --root TASK --production-id F --disposition fallback --source ACTUAL_REF --quote ACTUAL_EXACT_WORDS --effect ACTUAL_EFFECT` 保存其真实选择。已有替代对象时，`release --disposition superseded --replacement-production-id CURRENT_F` 保存原对象与替代的关系，仍需实际决定的来源及原话。等待和失败按实际状态保留，未知传输先读回并对账。

## 2. 一份普通笔记与按需材料

### 新任务先形成可供决定的完整说明

0.7起的新会话默认要求前置任务说明；0.8起另有当前任务生命周期与消息来源闸门。旧pin仍保留其真实状态，不静默升级。模型先研究实际材料与原话，再提供proposal；脚本不自动识别意图。

```text
python -B tools/codex.py task create --out D:/task/session --request D:/task/request.txt --p-run <真实版本@完整SHA> --visits D:/shared/digr-visits.jsonl --run-id <本任务唯一分组> --require-foundation
python -B tools/codex.py visits begin --root D:/task/session --actor Main --line COMMON --phase FOUNDATION --category SOURCE
python -B tools/codex.py foundation propose --root D:/task/session --input D:/task/proposal.json --reason "原件调查后的完整候选"
python -B tools/codex.py foundation show --root D:/task/session
```

proposal示例见codex/examples/foundation/proposal.json：内容涵盖目标、成品范围、粒度、真实基础、依赖、路线/最早整体结果、资源和完成条件。内部字段不等于用户问卷；对用户展示连贯说明、必要原件与关键问题。等待用户期间关闭活动段，不算研究。

```text
python -B tools/codex.py foundation answer --root D:/task/session --id Q1 --revision <实际所答版本> --reply-file D:/task/actual-reply.txt --source <真实消息引用> --effect "说明与下一行动的实际变化"
python -B tools/codex.py foundation confirm --root D:/task/session --revision <已展示当前版本> --reply-file D:/task/actual-go-ahead.txt --source <真实明确决定>
python -B tools/codex.py visits end --root D:/task/session --actor Main --line COMMON --phase FOUNDATION
```

answer不自动确认整体。模型理解真实答复：用户已看完整说明并明确要求改后执行，可按该决定记录，无需固定口令；提出新重要取舍则先讨论。material修订默认使旧确认不再覆盖当前稿；non_material只允许不改变决策的基础观察维护，并保留原接受内容。目标/成品/范围/粒度/依赖/路线/资源/完成字段改变会拒绝这条快捷路径。改问题或选项后不沿用旧答案；revoke立即失效旧确认，不因仍有accepted历史而可继续。

### 当前输入、真实续做与结束

0.8原始request必须是完整显式调用。后续用户消息先保存原文，再摄入；前缀消息仍先实际获取仓库，route-pin只引用已获取结果。普通说明无需route-pin。摄入后 begin/checkpoint 暂停，直至模型处理当前消息或有明确来源的foundation答复成功；reply-file的原文与source必须精确对应当前所选消息。

```text
python -B tools/codex.py task message --root D:/task/session --source-file D:/task/actual-reply.txt --source-ref <真实消息引用>
python -B tools/codex.py task handle --root D:/task/session --message-id <本次返回ID> --action continue --reason "仍在实际未完成任务内，说明相应后果"
python -B tools/codex.py task lifecycle --root D:/task/session
```

明确实质变更使用action revise，它先使旧决定失效；pause保留任务但禁止继续，resume须真实恢复指示。stop/cancel先终结，再收尾，旧确认不能复活。真实停止消息可优先越过较早pending：task terminate --status STOPPED（或CANCELLED）--source-file <真实停止原文> --source-ref <唯一消息引用> --reason <实际后果>；保留旧pending摘要，这条优先路径只能终结。无source pair时明确为操作者清理记录，不能伪引旧答复为停止来源。

source-ref是本地不可变消息身份，同引用不重新编号；编辑后的真实新消息使用新的引用。它不是用户认证，模型仍须核对实际对话。0.8.2中ordinary只处置消息：ACTIVE保留活动、决定与原P_run，并更新输入锚点使旧返回失效；PAUSED保持暂停，已终结保持终结。普通补充不重开前置或要求再次开工。真的新显式调用须在旧任务明确结束后建新任务，不能复活已终结session。handle是模型记录实际含义，不是工具判断用户同意。边界预览ActiveContext须显式提供从实际lifecycle读取的状态；NEW_TURN本身不结束DIGR。正常关闭使用return close，裸CLOSED或任意草稿不能代替当前RETURN。0.8.0新会话写session-2，早期pin保留session-1；0.8.1起新会话写session-3，共用访时缺口保留，可有据近似修复，不通过recover自动补点或重新激活。详见[兼容说明](../docs/CODEX_REAL_WORLD_CONTINUITY_UPGRADE.md)。

### 返回快照与收口

先结束真实活动，编写一个明确选定的返回输入，例如：

```json
{"schema_version":2,"result":"完整答案或成品入口","key_changes":"形成的认识与实际后果","work_process":"| 时间／记录范围 | 工作与后果 |\n| --- | --- |\n| 未单列 | 真实工作与所得 |","verification_limits":"实际验证与限制","parameters":"真实参数及T/t、补点、缺口、P_run","artifacts":[],"sources":[]}
```

文字研究以完整正文交付；文件成品用artifacts的label/path补充链接。sources只选必要文件，路径相对输入；不扫描聊天。schema2不接受timeline替代过程表，schema1仅供旧pin路径。

```text
python -B tools/codex.py return seal --root D:/task/session --input D:/task/return-input.json
python -B tools/codex.py return status --root D:/task/session
python -B tools/codex.py return body --root D:/task/session
python -B tools/codex.py return close --root D:/task/session --reason "约定结果已完成并交付"
```

CURRENT_RETURN.md仅是保存入口；schema2只保存RETURN.md正文副本和机器记录，不生成HTML/互动图报告。把body直接贴回最终response，链接副本不能代交付。相关任务事实或产物变动使其STALE，其他run追加及相同事件重放不会；READY不是语义批准或UI发送认证。close才终结生命周期，澄清/等待不close，P_run不随当前工具升级而重写。

确认后按 [PARAMETERS](PARAMETERS.md) 推断正式配置。`line create` 保存本线配置，宿主按 [LIVE](LIVE.md) 实际显示 INIT。`visits --root ... begin` 核对本任务生命周期及正式前置。直接 `--file/--run-id` 用于低层事实登记。`task report` 分开 `foundation_timing` 和 `timing`。正常结束前 End。缺 End 可据可见记录近似修复，未补缺口按原口径参与报告收口。

这些命令只检查被管理的入口和记录一致性，不拦截宿主所有工具，也不认证用户真实同意或解释质量。真语义及新纠正仍由模型依据会话处理。短任务可直接对话完成前置，不强制落这些文件。

```text
python -B tools/codex.py workbench init --request D:/task/request.txt --work D:/task/WORK.md
python -B tools/codex.py workbench topics --work D:/task/WORK.md
python -B tools/codex.py workbench focus --work D:/task/WORK.md --topic "原页组装路线" --material D:/task/notes.md:20-45
```

保留原始目标、交付用途、用户纠正、关键问题、研究/竞争方案、实际产物与下一步。重要发现写明依据、取舍及落实后果；自由标题可用，不必先把材料洗成模板。原件不搬进目录，PDF/EPUB按实际阅读工具打开；本工具引用文本/行段，不要求全文转码。相对材料路径以工作笔记所在目录为基准，绝对路径也可。

默认模板使用“用户目标 / 用户纠正与已确认要求”等标题。已有文档可显式选其真实标题：

```text
python -B tools/codex.py workbench focus --work D:/task/existing.md --goal-topic "用户目标 U0" --corrections-topic "已有决定" --corrections-topic "最新用户原话" --topic "当前路线"
```

也可单独给 `--request D:/task/request.txt`，不能与goal-topic同时给而让脚本猜优先级。标题需唯一；超出字符预算报明问题，选择小节/行段或提高max-chars，不静默剪掉目标、条件或纠正。

## 3. 给独立者空间，也给足原件

```text
python -B tools/codex.py workbench challenge --kind D --work D:/task/WORK.md --material D:/task/source-notes.md:1-30
python -B tools/codex.py workbench challenge --kind V --work D:/task/WORK.md --material D:/task/source-notes.md:31-60
python -B tools/codex.py workbench challenge --kind D --work D:/task/WORK.md --question "保留原页组装能否替换当前路线？实际比较。" --candidate D:/task/plan.md
```

前两条允许D先自主侦察、V先研究领域与问题；后者给一个成熟介入问题。默认带目标、用途、纠正和明确选入的材料，不自动带Main全套推导/研究/下一步。生成输入包不代表输入选择必然正确；交给真实受控上下文的独立代理，按COLLABORATION处理返回、实际生产和后果。V可由自己的材料与作品长出新问题，必要交流默认Main忠实转交。

公开摘要直接编辑已有笔记即可。可选record追加到现有唯一小节，不另建事件系统：

```text
python -B tools/codex.py workbench record --work D:/task/WORK.md --topic "原页组装路线" --kind "异议与取舍" --text-file D:/task/note.txt --ref D:/task/sample.pdf
```

它保留BOM/换行，把正文标题留在引用体，父节插入不误归子节。时间戳只表示记录时刻。单一作者写本线笔记，多个代理用原生消息与各自产物返回；工具不自动判断采纳已落实或统计N/R/D/V。

## 4. 可选经验：当时的原话，当前的适用判断

普通笔记和material已足够保留条件与反例。只有想保存原位置的当时片段并自动提示变化时，才用：

```text
python -B tools/codex.py experience capture --note D:/task/case.md --source D:/task/feedback.md:12-18 --out D:/task/case.json
python -B tools/codex.py experience show D:/task/case.json
python -B tools/codex.py workbench focus --work D:/task/WORK.md --experience D:/task/case.json
```

自由case说明可以区分用户原话、模型解释、适用条件、反例和改变的行动。capture不覆盖已有文件，show读取明确选中的案例并比较原位置；片段相同只表示那几行相同，不证明周边上下文、当前目标、权限或经验适用仍成立。没有自动全史扫描、沉默确认、偏好晋级或全局Memory写入。当前任务不用经验工具也可正常工作。

## 5. 多主进度的可接续工作包

在正式 INIT 前，Main 依据同 pin 的任务原文和前置判断推断配置。`profile presets` 给出档位目录。`profile parameters --text '(Less,N=8)'` 展示档位来源 `preset`/`preset_explicit`、`preference_baseline`、`explicit_overrides` 和待解释的 `unparsed_tokens`。Main 按原话解释位置参数、来源和时间控制。新会话的 `session.json` 中，`parameter_selection` 保存初始调用预览，`explicit_parameters` 只保存创建时取得的真实用户参数声明。`task create --explicit` 用于补记已从实际原话确认的值。最新纠正以当前消息和相应决定为据。按已取得的 P_run 解释并恢复旧会话。

负责该线的 Main 把较高参数与多承担的实际工作一起落实在生效配置和 INIT。后续有新论证、候选、原件或领域时，用同一理由判断该工作应进入当前责任还是追加相应参数。

`profile parameters --text '(Less,F=3)'` 预览 F 的显式值。新会话把 F 的初次声明随任务原文保存在 `explicit_parameters`，各线参数仍按各自责任填写。将合格项目与实际决定记入任务现有工作笔记。委托变化时沿 `task message/handle` 保留用户的新要求，接续时以当前要求及笔记中的实际研究为准。显示任务级 `F（目标/实际）`，细则见 [PARAMETERS](PARAMETERS.md#f-公开社区项目先研)。

若创建会话时已确定 M 目标，使用 `task create --m` 记录。以下示例在创建时已确定两条完整独立路线。

```text
python -B tools/codex.py task create --out D:/task/session --request D:/task/request.txt --p-run <实际版本@完整SHA> --decisions D:/task/decisions.md --m 2
```

若创建会话时尚未确定 M，U0 后用 `task main-target` 保存实际推断和理由，然后按对应 M 目标初始化各线。它写入独立记录，`task report`、恢复包和返回核对读取同一生效值。已委托范围内可直接记录，用户显式的 M 和实际限制按原意生效。前置研究发现两条值得独立推进的完整路线时可这样登记。

```text
python -B tools/codex.py task main-target --root D:/task/session --m 2 --reason "原件恢复与直接组合各有独立材料及完整交付路线"
```

在实际执行决定及 M 目标明确后，为各线保存生效配置。`line create --reasons` 可随配置保存推断依据。各线生效配置记录在对应 `line.json` 的 `parameters`。

```text
python -B tools/codex.py line create --root D:/task/session --id M01 --parameters D:/task/M01-parameters.json --owner <真实执行者> --work D:/task/M01-WORK.md
python -B tools/codex.py line packet --root D:/task/session --id M01
python -B tools/codex.py line update --root D:/task/session --id M01 --input D:/task/M01-status.json
python -B tools/codex.py task report --root D:/task/session
```

角括号是待替换的真实信息。每条 M 的参数文件完整给 N/T/R/B/S(n,t,r,b)/D/V/L。

```json
{"N":12,"T":"90min","R":4,"B":0,"S":{"n":3,"t":"40min","r":1,"b":0},"D":3,"V":3,"L":3}
```

示例展示文件格式，参数取值由当前任务决定。T/t 在该接口中可以用秒数或带明确单位的字符串。用户原话中的歧义由 Main 处理。每线记录会列出实际显式值与生效配置的差异，Main 依协议和实际用户决定判断这些差异。

status示例：

```json
{"candidate":"candidate.pdf","content_status":"DRAFT","responsibility_status":"IN_PROGRESS","next_action":"打开候选核对原件依赖","unhandled":["D02中心主张待处理"]}
```

相对candidate以status文件目录为基准。产物可为文本、PDF或目录；恢复按真实文件类型打开，目录仅指入口。REQUEST.txt冻结原字节；decisions引用当前共同材料。恢复包标记本线旧记录可滞后，带回最新共同要求并区分用户决定与模型提案。一个包不必读其它线私有历史或依赖其计时日志。已有笔记使用自由纠正标题时，line create可加重复的 --corrections-topic，按需案例加 --experience；这些明确选择保存在本线包，后续packet不需再猜。packet也可临时附加两项选择，不自动扫描历史或替换原始U0。

INIT 后用 `line parameters --parameters ... --reasons ...` 保存实际变更。已经生效的 N/R/D/V 承诺只可自主上调。真实用户修订可加 `--user-revision "原话或明确引用"`，保留到变更记录。各线初始推断、已生效的承诺和之后的用户决定均按实际来源解释。完成 M 的数量依据真实工作，`registered_line_count` 为登记数。实际作者、原生分工、议会和最终内容综合仍由模型做。

## 6. 共用Begin/End访时

```text
python -B tools/codex.py visits begin --root D:/task/session --actor Main --category WORK --work N01-topic
python -B tools/codex.py visits end --root D:/task/session --actor Main
python -B tools/codex.py visits begin --file D:/shared/digr-visits.jsonl --run-id <本任务唯一分组> --actor D01 --line M01 --category SOURCE --work competing-route
python -B tools/codex.py visits end --file D:/shared/digr-visits.jsonl --run-id <本任务唯一分组> --actor D01 --line M01
python -B tools/codex.py visits report --root D:/task/session
python -B tools/codex.py visits repair --root D:/task/session --actor D01 --begin-id <需修复Begin的event_id> --at <有依据的ISO8601结束时刻及UTC偏移> --basis <可见依据>
```

所有参与者共用同一文件；未指定--visits时用DIGR_VISITS_PATH，或CODEX_HOME/digr-codex/visits.jsonl。本机CODEX_HOME与实际任务数据在D盘。无这两个环境变量则明确指定路径，不暗放系统盘。分组ID初始化一次，子代理不携带运行timer状态。

正常Begin/End直接实采，category只按实际工作分WORK/SOURCE/META/IDLE，角色不决定是否计时。换类别先End再Begin，等待前End。T为所有WORK/SOURCE并集，t为SOURCE并集；U0用FOUNDATION，其余默认EXECUTION。每M单算本线，全局去重，COMMON不回填。

缺End不延到现在，新Begin不替旧尾补点。repair必须指向旧Begin并提供有效边界和依据，实际补录时刻另记；保留未补缺口。reader和writer共用短锁，坏行、重复事件和倒退时刻局部报告；按run筛选不混入其它任务。统计是登记覆盖，不认证每秒持续活动，T/t详见PARAMETERS与RETURN。

0.8.0及更早session保持旧pin与逐owner activity路径；新任务用session-3/schema2，旧writer不能误读。旧clock/anchor命令仍供原会话使用，不能成为新任务默认入口。产物路径、缓存和日志遵守实际存储分工；无工具需求的短任务直接完成，不先搭工作站。
