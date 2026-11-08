# 前置任务工程：接续的决定、实际资产与投入范围

研究日期：2026-11-09。执行依据：`0.6.0@4b092cf1e9817b1a80e408965a87d17c035950fd`。本文是独立工程侦察及对候选 C1 的再入结果；只写本文，未修改运行代码或执行协议，未调用付费 API。

## 中心判断

采用 C1 的 B 路线：在现有 session 内增加一个小型 `foundation.json`，让研究后的任务说明、待决问题、用户答复和已接受版本进入实际恢复包。使用现有 WORK 保存研究材料和后果，现有工具保存文件与活动事实。A「只加自由笔记和协议文字」可支持讨论，却缺少明确可读的当前确认范围；C「另建调度、审查和证据平台」没有解决当前缺口所必需的独有能力。

本领域的核心对象是**已被理解且可以继续的任务决定**，而非原请求存档。原话、模型解释、材料事实、用户决定各自保留身份。新任务有了材料调查、具体成品定义、可理解的取舍和真实用户答复，才具备全面投入的依据；建立目录和填写 JSON 都不完成这件事。

对 C1 的关键收窄是：**前置先利用 COMMON owner；正式执行门槛检查实际活动入口，不能把创建 M 线文件当作已经执行或已经批准。** 前置投入单列 scope，继续复用已有时钟，不另造时钟服务，也不要求为前置先承担一整条正式 N/R/D/V。

## 已查明的实际基础

| 现有位置 | 真实能力 | 当前缺口及后果 |
| --- | --- | --- |
| [codex_session.py:193](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/runtime/codex_session.py:193) `create_session` | 冻结 REQUEST 原字节及散列，保存 P_run，引用共同决定文件；明确不启动执行 | 没有解释目标、辨认成品或调查依赖，不能称为「意图识别已完成」 |
| [codex_session.py:231](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/runtime/codex_session.py:231) `create_line` | 校验完整参数，接入已有 WORK 或生成模板 | 模板只有原请求，交付、纠正、研究、产物、下一步栏初始为空；文件存在不等于任务说明成立 |
| [codex_workbench.py:71](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/runtime/codex_workbench.py:71) `create_workbench` | 留原话、自由标题、明确选取材料；不会调模型 | 应继续作为研究工作台，不把空模板升级成自动研究器 |
| [codex_session.py:541](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/runtime/codex_session.py:541) `line_packet` | 取回原请求、本线材料、实际候选、最新共同纠正；纠正在旧计划之后；不依赖其它线私有笔记 | 可以接入 foundation 当前说明，复用恢复机制；原有包不能自行判定用户已经同意 |
| [codex_session.py:264](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/runtime/codex_session.py:264) `_artifact_ref` | 文件散列；目录仅作为入口 | 目录没有递归内容认证；需要检查真实选中材料，不能把路径存在当作工作基础可用 |
| [codex_session.py:408](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/runtime/codex_session.py:408) `activity` | COMMON 不要求 M 线存在，支持明确 begin/checkpoint/end/recover | 已有前置活动落点，不必为了计时提前初始化正式生产线 |
| [codex_session.py:438](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/runtime/codex_session.py:438) `summarize_activity` | MAIN/SOURCE 进入 T，SOURCE 进入 t；META/D/V/IDLE 排除 | 前置研究不能简单改标 META：那会丢失其研究成本；应按 scope 分组 |
| [tools/codex.py:43](D:/CodexLab/worktrees/digr-codex-adaptation/digr-runtime-source/tools/codex.py:43) task/line/clock | 统一 CLI，已有文件和恢复通路 | 最合适的新增入口就在这里，不需新常驻进程或独立工作站 |

本轮真实 session 已保留原始 L1，在 line 中记录用户明确改 L3 的原因；`decisions.md` 已明确「研究后的任务说明及关键取舍经用户确认，已确认续做只问变化」。这是可复用的变更依据，不能再次向用户重复询问同一选择。其 `content_status=PREPARED`、`responsibility_status=UNVERIFIED`、`candidate=null` 也没有伪称产物已经完成。

## 建议的最小工程接入

### 数据与模型工作各自承担什么

新增一个小模块，例如 `runtime/codex_foundation.py`，保存、校验和渲染结构。研究、解释、问题选择、对答复的语义理解仍由模型承担。不要写关键词分类器，声称从一句原话自动提取了真实意图。

`foundation.json` 保留两份小范围内容：当前可修订说明，以及最近一次已接受说明及其用户答复引用。保存当前 revision、原请求散列、P_run 和待决问题；原 REQUEST 不改。WORK 继续存研究原料、竞争路线、代表小样和实际处理后果。无需再造事件数据库、评分册、代理收据和独立审批平台。

说明至少覆盖以下对象，允许对明确不适用的项目作有理由的说明：

- **目标和用途**：用户拿结果改变什么；模型如何理解原话，以及哪部分仍待用户决定。
- **可交付结果**：文件、软件、研究判断或其它真实成品；内容范围、完成条件和可打开的入口。中间索引、清洗、评估设施分别说明为何服务成品。
- **粒度**：在哪一层加工和验收，例如原页、段落、词义、接口或完整使用路径；避免把「精细」直接理解为对所有原料逐项深加工。
- **基础与依赖**：实际读过、打开或运行过哪些资产；保留哪些、复用哪些、需要替换哪些，基础不可用会怎样影响结果。
- **路线与投入**：竞争选择的结果差异、剩余工作、前置研究投入、正式参数责任及真实费用边界。
- **问答**：需要用户决定的具体差异、证据、推荐、选择后果；回答记录保持原话和来源，不把沉默、未改稿或部分回答推成全面同意。

资产条目使用「位置/版本、已观察事实、拟如何使用、依赖关系、改变后的影响」就够。关系需要区别：

| 关系 | 例子 | 接续处理 |
| --- | --- | --- |
| 保留或不可变来源 | 指定历史 commit、原始文档、已冻结输入 | 必须取得指定版本；变化可能改变选段、权利或结论，查明实际后果 |
| 允许修改的工作基础 | 本轮要修复的代码树、已有草稿 | 生产中的正常修改不自动撤销整个任务决定；与任务相关的意外差异另查 |
| 可选参考 | 旧研究、可替换示例 | 失效可替换或放弃，不把它升级成全任务阻塞 |
| 正在生成的结果 | 新候选、构建输出 | 变化是正常工作；不能每次输出更新都要求重做前置确认 |

不使用一个「已有基础 80%」数字替代这些关系。目录候选需要明确读选中的文件或真实运行入口；本轮已核实 C 约 7.74 GiB、D 约 97.28 GiB 空余，新增实存仍按用户约定放 D，空间数只代表本轮采样。

### CLI 与恢复的最小行为

沿用 C1 的 `foundation propose/show/answer/confirm` 可以成立，四个表面命令共用一组小型状态更新函数即可。

1. `propose` 保存**研究后的**可讨论任务说明。只提交 REQUEST 或空标题应显示未完成项，不得输出意图已对齐。新增说明与已接受说明比较，保留尚有效的决定。
2. `show` 渲染原话身份、当前说明、已接受范围、重要差异、未决问题和资源后果；能直接拿给用户阅读。它也成为 `line_packet` 的共同输入。
3. `answer` 记录真实答复引用以及已解决/仍未解决的问题。选择一个选项并不自动确认整个任务；明确的用户收窄应立即影响下一项行动。
4. `confirm` 记录对用户已经看过的当前说明和关键取舍的明确接受；检查 current revision 和未决事项。确认引用不是工具签发的可信授权，更不能认证隐藏的理解或自然语言质量。

确认字段只能追溯到真实对话。模拟器中的 `actor=user`、非空 `message_ref` 或 `confirmed=true` 都是调用者提供的数据，不能认证真实用户确实说过。模型必须核对原答复；CLI 只防止遗漏、串版本和误用旧记录。

`create_line` 保持文件准备的原义，不从准备成功推断正式工作已经获准。需要前置的会话在受管理的实际执行入口检查当前说明与确认；旧会话的基础状态不能静默补成已确认。已有真实会话决定可带回，仅对欠缺或改变的重要选择问答。

恢复包先保留原请求和本线事实，再呈现当前基础、已接受范围与变化；旧 TODO 或模型提案不覆盖用户纠正。文件中标记 CONFIRMED 也不覆盖真实会话里的新要求或停止指令。相关候选变化后，模型检查其对任务决定的影响，不能机械地按所有 mtime 或散列变化重问整份任务。

## scope 计时方案与三个必须补上的边界

推荐在现有 begin 增加 `scope=FOUNDATION|EXECUTION`，沿用原有 MAIN/SOURCE/D_EXCLUSIVE/V_EXCLUSIVE/META/IDLE 状态。前置以 COMMON 开始，即使还没有 M 线也能记录；第一次正式生产再初始化其参数和本线记录。它不需要第二套计时器。

活动中的 scope 必须随 checkpoint 继承；旧记录缺省按历史 EXECUTION 读取，未知 scope 值报错，不能猜成另一类。保持原正式 T/t 结构及含义，另列 `foundation_timing`；同域区间各自取并集，未知及开放尾段保留未知。前置和正式各自的 D/V 独占活动也如实可见，不混入 Main T/t。

父线已接受此方向，但以下边界决定它能否兑现用途：

1. **门槛覆盖全部正式实质活动**。EXECUTION 的 MAIN/SOURCE 和 D_EXCLUSIVE/V_EXCLUSIVE 都会消耗正式任务资源，不能只拦 MAIN/SOURCE，让未确认的重研究经 D/V 状态绕过。META/IDLE 等纯维护可按实际作用保留。
2. **确认失效时，开放段不能靠 checkpoint 继续正式工作**。对实质 EXECUTION checkpoint 也检查当前确认；end/recover 始终允许，以便停止及保留真实事实。用户纠正到达时先改变实际行为，闭合能诚实声明的旧段，再进入 FOUNDATION；不能回填事件、追认旧确认或默默丢掉已花成本。
3. **未读日志不能按零处理**。scope 分组不能让坏日志变成「没有前置成本」或「正式全部可知」。沿用原有 PARTIAL_READ 和可读子集边界；确实无法判断坏日志属于哪一范围时，该范围的完整性保持未知。

独立第二 session 是可用备选，适用于前置本来就是另一个独立委托、预算或交付；但每次普通任务都强制新开一整条 session，会增加入口、恢复和跨阶段核对。本轮没有足够收益支持它成为默认。当前这轮「建设前置工程」本身已有完整独立委托，不应为整齐而重写其已记录活动。

## 投入研究要落在剩余成品工作上

正式 N/R/D/V 不是固定价目表。R 要重研完整候选，M 是整条完整主进度；来源研究 t 是 T 的子集，并行墙钟不能直接相加。没有真实 usage、单价和预算时，报告工作量与不确定性，不把参数乘成一个伪精确金额。

可操作的资源研究是：从成品和实际基础列出剩余困难；调查能够改路线的未知；比较结果质量、返工代价和投入后果；由证据决定需要多少深入研究。前置研究的预算和已花投入单独呈现，不冲抵尚未开始的正式责任。

例如本仓库已具备原话冻结、工作包、共同决定和显式活动边界，缺的是研究后的任务说明、答复/确认范围和分 scope 统计。优先复用它们，足以否定「先建设一个全新调度平台」的必要性。还不能声称自然语言意图识别、用户纠偏质量或长期效果已被工具保证。

前置研究继续加深的理由应是一个能改变成品或投入选择的未解问题，例如「必须复用旧生成系统，还是直接导出已有版本」；已有证据足以比较后，就交用户决定并停止扩大该问题的辅助建设。前置预算耗尽而关键歧义仍在时，给出当前认识、未决后果和继续投入选项，不擅自全面生产。

## 可复用输入、问答和纠正实例

以下是基于本仓库资产的设计样例，非当前用户已经确认的正式方案或已实现命令。

```json
{
  "goal": "让新DIGR任务在全面投入前完成有材料依据的任务理解和关键决定",
  "results": ["现有session中的任务说明及问答状态", "可从CLI和恢复包继续使用的入口"],
  "scope": "现有Codex候选profile；正式学习材料生产不在范围内",
  "granularity": "按任务决定、实际依赖和完整使用路径；不逐条把原请求变成生产工单",
  "basis": [
    {"ref": "runtime/codex_session.py", "observed": "已读create_session/create_line/line_packet/activity", "use": "复用原话冻结、接续及活动边界"},
    {"ref": "runtime/codex_workbench.py", "observed": "模板和context_packet已实际运行", "use": "研究工作台和受控输入"}
  ],
  "resources": {"foundation": "单列研究预算及已观察投入", "execution": "用户确认后建立正式参数与成本范围"},
  "question": "任务说明、问答与时钟接入现有session，还是只交研究建议？"
}
```

向用户呈现时可以压缩成一张具体任务说明，然后问：「现有 session 已能冻结原话和恢复候选，缺少的是研究后的说明与确认范围。我建议把这部分做进 session、CLI 和恢复包，并单列前置时钟；这将交付可实际使用的工具。如果你只需要研究规范，范围会少掉这段工程。你选择哪一项？」问题基于已调查差异，不能先问用户替模型盘点本地文件。

| 真实交互 | 下一项行动 |
| --- | --- |
| 用户只答「用现有 session」 | 解决路线选择，继续核对尚待决定的成品范围；不推断整份说明已准开工 |
| 用户明确接受当前说明和关键取舍 | 保存当前 revision 的真实答复引用，建立正式投入，沿已接受范围执行 |
| 已确认续做，范围和关键材料无相关变化 | 直接恢复已接受说明、本线产物和未处理事项，不重问全套问题 |
| 用户纠正「只交研究设计，先别改代码」 | 立即停止代码生产；保留已生成结果的真实状态，把下一步改为研究交付；不把旧工程计划当要求 |
| 用户纠正粒度或发现必需原件未取得 | 调查对成品与投入的实际影响，显示改变部分；只对需要新判断的取舍再问 |
| 模型在确认后自行加网站、全量清洗或新服务 | 新提案保持未确认；这些新工作不因写入 TODO 获得原任务身份 |

拟议可运行 CLI 顺序如下；只有前两行当前已经存在，后续 foundation 子命令、scope 参数和门槛均待主线实现，不能拿此流程冒充已部署功能：

```powershell
python -B tools/codex.py task create --out D:/task/session --request D:/task/request.txt --p-run <version@full-SHA> --decisions D:/task/decisions.md
python -B tools/codex.py workbench init --request D:/task/request.txt --work D:/task/WORK.md
python -B tools/codex.py clock begin --root D:/task/session --owner COMMON --scope FOUNDATION --state SOURCE
# 真实研究：阅读选中的原件、检查基础、必要的小样和独立材料；更新同一WORK。
python -B tools/codex.py foundation propose --root D:/task/session --input D:/task/proposal.json
python -B tools/codex.py foundation show --root D:/task/session
# 用户对具体说明问答后记录真实答复。部分answer不等于confirm。
python -B tools/codex.py foundation answer --root D:/task/session --input D:/task/reply.json
python -B tools/codex.py foundation confirm --root D:/task/session --revision <current> --reply-ref <actual-user-reply>
python -B tools/codex.py clock end --root D:/task/session --owner COMMON --continued
python -B tools/codex.py line create --root D:/task/session --id M01 --parameters D:/task/parameters.json --work D:/task/WORK.md
python -B tools/codex.py clock begin --root D:/task/session --owner M01 --scope EXECUTION --state MAIN
```

实际确认等待不能算作连续研究。上例省略的等待边界应在真实发生时 end/checkpoint；恢复时使用原有 recover 语义，不能把整段问答等待计为活动。

## 本轮实证比较及验证边界

在 `python -B -` 中运行了现有函数及一个无落盘的 B 状态转换小样，未创建新生产模块。

| 比较对象 | 实际观察 | 足以支持的结论 |
| --- | --- | --- |
| 真实 `create_workbench` | 7 个顶层节，仅目标非空 | init 不是意图识别；必须有真实研究后的内容 |
| A：真实 `context_packet`，使用内存模拟 WORK | 原话和「立即全面生产」的旧 NEXT 均能进入包；没有计算当前确认状态 | A 可以取回材料，但单靠模板不提供版本与确认范围；语义仍依赖模型 |
| B：纯内存 proposed reducer | 部分答复后 REVIEW_REQUIRED；明确确认当前 r1 后 CONFIRMED；无变化恢复不重问；结果字段改为 r2 后 REVIEW_REQUIRED，旧 r1 确认被拒绝 | 一个小状态层足以处理串版本与部分回答；这不是仓库已实现能力，也不证明用户语义理解正确 |
| 真实 `summarize_activity`，构造 5 分钟闭合区间 | META 保留 1 个闭合区间但 T/t 汇总为 null；SOURCE 的 T=t=300s | 前置研究不能靠 META 标签获得可见成本统计 |
| 真实 `summarize_activity`，只有 COMMON 的构造 3 分钟来源区间 | 无任何 M 线，COMMON 可汇总来源 180s | 复用 COMMON/现有时钟具备真实函数基础，无需为了计时先造正式 M 线 |
| C：另建完整平台 | 未实现、未运行；没有发现当前最小缺口必须依赖的新能力 | 暂无依据扩大成新平台；不能宣称实测证明 C 更慢或更差 |

以上时间为明确标记的构造区间，不能冒充本轮真实研究耗时。第一次构造夹具遗漏 provider 导致 KeyError，已补齐后重跑；未把失败结果当作实现问题。源代码读取、真实函数运行和设计小样分别说明，未执行新CLI路径或端到端用户任务。

后续实现应验证实际后果：未确认的正式实质 begin/checkpoint 被阻止；前置 COMMON 可研究；部分答复不准开工；错 revision 拒绝；当前确认后正式执行可用；输入改动不会一概把正常生产变成重新审批；更新范围能停止在途相关工作；恢复只重问重要变化；前置/正式并行区间、缺口及坏日志分组仍诚实。还需要一次独立模型使用代表性原件完成「研究—问答—纠正—续做」的真实路径，不能用 JSON 全绿代替。

若该工程改变执行语义，应通过后续版本的 codex profile 正式发布，保持 manifest/VERSION/聚合包及散列一致；不修改根 stable 作为旁路，也不把执行语义复制进本地 AGENTS。本轮仍受已经取得的 P_run 约束，本文建议不能自行替换它。

## C2 实现后的同线再入：纠偏与恢复仍有三处需要落实

本节补充实际 C2 审查，前文「待实现」的说法属于 C1 时点。已重读真实 `runtime/codex_foundation.py`、`runtime/codex_session.py`、`tools/codex.py` 和 `codex/FOUNDATION.md`；使用当前 CLI 在 D 盘仓库 `.cache` 下创建隔离测试 session，流程结束已清理。没有修改主线代码，也没有调用付费服务。

**结论：初始问答、确认和独立前置时钟已经能使用；确认后的纠偏、延迟回答和按变化恢复尚不完整。** 以下三项均由真实 CLI 运行观察，未以模拟 reducer 代替。

| 必须处理的问题 | 实际步骤与观察 | 用户后果与最小修复 |
| --- | --- | --- |
| 已确认问题改答后仍沿用整体开工确认 | r1 已确认代码集成；执行 MAIN 已 begin。调用 `foundation answer` 将答案改成「只交研究，不要代码」，effect 记录取消代码生产。返回仍是 CONFIRMED，confirmation 仍 r1；随后的正式 checkpoint 成功 | 新纠正只被存成一条文字，旧决定仍可指挥执行。变更答案需要显式的实质/非实质处理；有影响的答复默认撤销或暂停当前执行决定，直到解释和必要确认落实。完全相同的重录或明确不改变决定的答复可以沿用；不能把每次 record 都变成重新审批 |
| answer 不能绑定用户实际回答的版本 | r2 把原 id=choice 的「代码还是研究」改成「公开发布还是本地交付」。传入来源为 reply-to-r1 的旧答复 `Use code integration`，命令接受并写成 recorded_at_revision=2，填入新版问题 | 旧回答被赋予用户未答过的新意义，复用 ID 就能串问答。answer 应接收所答 revision 并核对当前问题；过期回答拒绝或保留为待解释材料。若问题确实未变，由模型显式重映射，不必让用户重复回答，但工具不能静默替其完成 |
| 重要修订丢掉最近已接受的完整说明 | material propose r2 后，搜索真实 foundation.json 和 foundation show：r1 独有成品字段已不存在。history 只有 revision、brief_sha256、confirmation、change_kind、change_to_next，无旧 brief | 散列取不回已确认对象。恢复只能看到新解释与旧确认残片，不能对照「保留原说明、只问变化」，也无法辨认旧确认中仍可继续的范围。保留最近已接受 brief 快照及引用，并在 show/恢复包显示与当前提案的相关差异；无需新增事件平台或保存所有全文历史 |

同一真实 CLI 流程也确认了有效部分：`0.7.0@<构造SHA>` 的新 session 默认 foundation_required=true；未建立任何 M 线就能用 COMMON 记录 FOUNDATION SOURCE；未确认的正式 D_EXCLUSIVE begin 被拒；material 修订后的 V_EXCLUSIVE begin 被拒；end 可用。这里的构造 SHA 仅用于本地隔离行为试验，不是线上仓库获取凭据。

原 scope 和受管理入口方案可保留。这三项修复都位于当前的小型 foundation 状态与问答命令，不构成另建调度平台的理由；本次没有发现需要扩大为通用测试或认证设施的依据。

## C2 修复后的窄复测

按同样真实 CLI 路径重跑，未扩大测试面：实质 answer 后现为 REVISION_REQUIRED 且 confirmation=null，正式 checkpoint 和未先 propose 的 confirm 均拒绝，end 可用；answer 明确提供旧 revision 会被拒绝，新版同 ID 问题没有被填答；accepted 保留原 brief 和原决定，show 可见新旧成品及变更理由。新增 unaffected_lines 只放行明确声明的 M01，未声明的 M02 与 COMMON 正式活动仍被阻断。D 盘隔离试验 session 已清理。

同一纠偏路径还复现一项状态余项：

```text
material answer → REVISION_REQUIRED / confirmation=null
同一纠正答复以 non_material 重录 → AWAITING_USER
未 propose，直接 confirm 当前 revision → 成功，brief 仍是旧成品
```

原因是 answer 的 `elif not value['confirmation']` 无条件把已有 REVISION_REQUIRED 改成 AWAITING_USER。应保留该挂起状态，只有 propose 承担落实纠正后才能解除；不改变内容的重录不能清掉纠正要求。这是此次复测唯一新增必须处理项；未发现需要扩大时钟或通用设施的阻碍。

