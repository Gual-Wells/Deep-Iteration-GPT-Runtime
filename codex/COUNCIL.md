# 单一原生议会与外部并行成员

Sonnet、Hydrogen 和 Grok 是第一层同等地位的外部研究成员，参与竞争解释、选择与仲裁。每项议会在同一原生研究链上推进。原生独立者完成初议，待两侧达到完整或明确异常终态后，由原生独立者取得真实公开材料，自主再议并形成返回。Main 负责真实调用、权限费用、来源、暂存和原文转交。Main 继续完成主线作品和处理返回。

## 实际身份、观点距离与来源

原生 actor 使用宿主实际创建的独立代理身份；`--native-actor` 是对应关系的本机记录，不是凭名字创造代理。Main 不用自己的总结冒充初议或再议。初议 actor 在取得对侧观点之前，先形成自己的有内容认识、候选问题和候选分域；首次正式采用的领域可以由再议重划。

每位外部成员具有独立 `participation_role=council_member`，按 `council_id/member_id` 保持研究线身份。cycle、共同输入版本和 round 分开绑定。原生初议、外部意见与既有正式指导共用实际要求、原件事实和可行性标准。发生前提冲突时按作用域比较证据与强替代，必要时带材料再入。

共同输入包保存原始用户原话、当前用户消息、已接受事实和约束，以及实际原件正文和散列。Main 负责排除任一初议侧已形成的推导；散列能固定字节，不能证明其中全是事实。引用、附件历史和模型旧话保留数据身份，不变成新的执行或费用授权。文件路径只用于核对，传入请求的是实际正文。

本实现的隔离为 **HOST_LEVEL**：宿主及用户会看到公开流，共享磁盘可读；不会声称 OS 保密或 Main 未受影响。`packet --actor ... --stage INITIAL` 只提供共同输入，不返回任一侧观点。再议 packet 只对配置中的原生 actor 在屏障释放后开放。宿主应将它实际交给相应独立上下文；actor 参数是宿主声明，不是身份认证。成员初轮不接收原生初议；后续子议会交流也不注入本轮原生初议。恢复中的成员保留此前公开历史，不能重新宣称从未受旧观点影响。

## 单冒号的独立首发

Main 按 [PROTOCOL](PROTOCOL.md#单冒号任务的独立首发) 主动发现可能改变交付的开放取舍，在定案前安排一次首发。给两位外部成员真实用途、可指认的材料和仍值得探索的选择，保留它自行发现支配议题或提出选项的空间。公开正文先交付站得住的具体立场，理由可在同次正文的后续段落展开。原生初议者独立研究同一任务，收到可用原文再审视观点、依据和替代方案。

新任务当前为单冒号时，`council create --first-opinion` 登记一次 `INDEPENDENT` 轮。同一任务恢复时沿用原议会和实际尝试记录。默认 Sonnet 5.5、Gemini 4 Hydrogen 和 Grok 4.7 各一条成员线，均用 `high`，各 6,000 总输出 token 起步。推理与公开正文共用各自容量。初始请求和真正的 Codex 工作回传续答累计占用第一层额度，遵守真实钱包与用户更窄限额。

每位成员首次实际提交占用其在该任务的一次首发机会，包括空答。各成员的支出仍共用第一层总额度。有实际的 Codex 支持工作待回传时，沿该请求同线继续。完成或明确结束后封存该成员。费用、空答、部分正文和传输未明各保留自身事实。Main 按 [LIVE](LIVE.md) 及时原文转播，并在屏障释放后把原文和实际状态交给原生 actor。再议返回处理正文中有依据的立场，说明哪些取舍受影响，随后由 Main 落实。

等待限于本次取舍，默认期限 300 秒，可按真实决定窗口设置。局部条件无法满足时，原生工作依可用材料继续。已登记而无法发送时，按实际原因处置成员和当前议会。首发的迟到原文可转交原生参与者再议。已有真正的支持工作回传时，沿当前请求、截止时间和额度续答。后续另有实质研究问题时，按当前权限启动普通议会。首发的正文和费用沿原交换读取、转播和对账。

## 外部成员委托 Codex 支持工作

让外部成员各自抓住材料里可能改变交付的东西。它可提出用户没有预设的比较角度、指出一个决定性的假设，或者试写一个能重新组织作品的片段。为了推进自己的判断，它可发起具体委托，说明要验证的问题、需要的原件或产物，以及何种结果会影响判断。委托可以由有分量的发现自然产生。

Codex 根据当前用户要求，承接定位、提取、核对、复算、试作或其它可交付的支持工作，保留真正的限制和证据。宿主从该成员的实际公开返回登记委托。按成员希望区分的解释，保存并回传可读结果、决定性的原件与相邻定义、约束，以及能推翻当前候选的证据。标明出处、覆盖边界和影响判断的实际缺口。经新一次 Split 送回同一成员，沿其公开历史续答。已有费用、截止窗口和任务范围继续生效。相应 Sonnet 回合保留 `high` 或更高的真实配置。

成员收到后继续自己提出的问题，依据结果决定要保留、修订还是重做，并给出影响交付的判断、写法或候选。例如一篇车载 DNN 导读可以从「同样的切分、上传和算力，为什么两次运行等待不同」切入。成员可委托 Codex 对照上传公式与计算队列、复算一个只改变历史积压的例子。原件显示跨时隙的积压位于按模型类型划分的 RSU 计算队列，成员据此选择如何先解释历史留下的工作，再引出长期约束。原生议会和 Main 按各自原有角色再议与落实。[论文作者公开稿](https://hub.hku.hk/bitstream/10722/353231/1/content.pdf)

每次真实续答在该层保守上界内安排。决定窗口内预计有工作回传时，先给首轮和可能的续答各留合适的空间。若实际受阻，保留该项委托的真实状态及已取得的成果，继续其余工作。具体执行命令见 [WORKBENCH](WORKBENCH.md)。

## 成员研究和通信

成员先进入材料探索，再发现值得争夺的支配前提、突破口或更强的整体路线；没有成熟旗帜时可以继续侦察，不必唱反调。强替代需要研究、比较、论证或实际试作，讲清替代什么、依据和适用条件。探索后协商形成有语义距离的领域，自主发展材料、问题、方法和成果，允许重新划分原问题。它们继承 D/V 的研究性质，不冒称已经履行完整原生 D/V/M 或 L3。

内部通信只转交实际公开消息。`CROSS`、`FINAL` 和 `REENTRY` 请求保留自己的公开链，并传入各成员已观察到的公开原稿及来源和状态；不以 Main 摘要定调，不机械截断。成员本人压缩终稿；正文过长时，再议包按字符顺序分块，块的拼接精确恢复全文，保留完整散列和来源。取得 JSON/本地路径不等于相应代理已经阅读，宿主须真实转交可读正文。

普通议会的资源起点是两个成员，按需要开展独立探索、公开交流和作者收束。人数、输出额度、轮次和 deadline 随真实研究、许可和预算确定。准备追加一轮时，依据仍待解决的取舍和成员这一轮能带来的新推论、反例或候选决定。普通议会首轮传输完整后仍待研究封存，V 研究须按实际责任判断。已有研究足够时用 `seal-member` 封存。单次错误和额度不足均按本次事实结束相应尝试。

## 两阶段、异常与迟到

Stable 的实际成员发送统一从已登记的 `council run-round` 进入，保留单次提交、真实成员和共享钱包检查。当前任务许可及第一层余量支持本轮时直接开展，必要时先估算拟议成员和回传轮的合计上界。已封存成员的待发请求退出本批，其余可派发成员依本轮继续。已经在途的回执按原身份处理，迟到公开正文供后续相关再入。

`INITIAL → REDELIBERATION → COMPLETE` 是本机研究对象的阶段，不代表代码认证了内容质量。每个原生初议 actor 和每个相关外部成员分别封存 `COMPLETE/PARTIAL/FAILED/BUDGET_STOPPED/TIMEOUT/CANCELLED/OUTCOME_UNKNOWN`。只有两侧都进入终态才能释放屏障；异常解除等待，不证明研究完成，不视为支持或反对。

默认 deadline 是每个 cycle 300 秒，可在创建时明确覆盖；不静默延长。屏障只限制相关议会决定，其他主线工作继续。`run-round` 真正并发发送当轮已准备的各成员请求。到 deadline 先返回明确异常阶段，不等待所有 future 的网络工作完成；HTTP 超时也以剩余 deadline 为上限。服务端是否取消和收费仍可能未知，保留共享钱包预留。

屏障释放时固定实际可用的成员 exchange 列表。迟到公开正文保留原 cycle/input 身份，进入 `late_results`，不倒改旧再议包。`reenter-late` 将它作为带来源的新材料开启后续相关再入，不重复发送旧请求。若用户停止，先停止新增请求，再查服务端和费用；断开连接不能当作免费取消。

再议由原生 actor 各自返回实际作品，讨论完整成员材料中的实质主张，尤其是强替代，说明采用、部分采用或反驳的理由及后果。只保存 API 返回或 Main 写“已采纳”不是再议。所有指定原生 actor 返回后才进入 `COMPLETE`。明确停止可 `close --reason ...`，仍保留未完成责任；它不伪造再议已经发生。

## 独立前置意图提取

1.8.0+ 的实际 U1 允许对需要独立提取的输入创建 `council create --foundation-intent`，命名为 `u0-<实际内容消息编号>`。一名原生作者与 Sonnet、Hydrogen、Grok在同一个当前输入包上独立起稿。单、双冒号共用本任务第一层权限和额度。该轮使用独立前置身份，首发及其它第一层研究仍按各自作用域登记。

使用 `prepare-round` 冻结各请求，按成员分别绑定 Split。并行发送后逐方记录公开增量、实际身份与终态。屏障释放后原生作者比较已有完整稿，同等采用实际返回的外部成员意图理解，依据实际来源处理分歧与缺稿。把已比较的当前议会以 `intent_council` 附给 `foundation propose`。早先用户输入的稿件仍可回核；晚到原文按原轮保留。

## 持续发展与相关事件

持续性需要两件事：可恢复的公开研究线，及相关材料出现后实际同线研究。`event` 保存实际新候选、来源、用户纠正或领域问题，生成新共同输入版本和 cycle，给受影响成员及原生 actor 建立待研究责任。只列队和保存记录时，`research_reentry_performed=false`；真实同线返回后保存对应 exchange、版本和状态。未受影响的成员保留旧版本最后研究事实，不代称已读新版。

新消息使旧 prepared 请求过期；先把有关纠正放入新包，再准备 `REENTRY`。多条相关事件未处理时合并保留所有受影响身份，不能被最新事件覆盖。这个助手不监控一切文件，也不在无人授权时无限运行 API；Main 及原生独立者在真实相关候选出现时负有恢复同线的职责。保存“以后能再入”不等于已经持续研究。

新版也不能抹去旧版未完责任。新 cycle 取新事件影响身份、未处理事件身份及所有旧 cycle 尚欠再议的原生 actor／未封存成员的并集；旧 cycle 明确记录迁移目标和身份，未完工作在新事实下继续。已返回且与新事件无关的 actor 不重跑。最终检查逐 cycle 查真实返回或有效迁移链，不能因当前 cycle 已完成就丢掉旧 actor。明确关闭保留未完身份和理由，不把关闭写成完成研究。

## C1生产后的独立庭审

实际C1的本版任务在既定研究和生产责任完成后另按必读COURT组织怀疑审判议会。六类法庭职责及控辩、监庭和法官身份各有真实来源，前期议会人数和参数完成不能替代后期庭审。现有研究者可在有据角色边界内再入，仍须实际审当前材料并处理新争点。成立问题重新估算并实际再执行，直到当前判决允许完成。法院不扩大Claude费用、用户委托或原硬限制。

## 本机可运行路径

首发命令随实际待定取舍、原件与原生 actor 填写。`--facts` 读取共同事实与约束的文本文件。发送计划另给当前价格和钱包的费用事实。

```text
python -B tools/codex.py council create --root TASK --council-id c-first --native-actor REAL --first-opinion "导读先讲任务切分还是成本上界，哪种顺序能让初读者独立复述机制？" --facts FACTS.md
python -B tools/codex.py council packet --root TASK --council-id c-first --actor REAL --stage INITIAL
python -B tools/codex.py council prepare-round --root TASK --council-id c-first --kind INDEPENDENT
```

把初议包交给真实原生 actor。按 [SPLIT](SPLIT.md) 为每个实际准备的 exchange 绑定本机分工。若当前 OpenRouter 配置可查实际钱包，使用 `--member-splits` 指向 JSON，例如 `{"member-1":"sonnet-split.json","member-2":"hydrogen-split.json","member-3":"grok-split.json"}`。请求的独立报价、真实余额与已结费用先核对，0.25 美元覆盖本任务外部成员累计支出。只准备一位成员时沿用 `--split-plan`。必要时带 `--config CONFIG.json`。

```text
python -B tools/codex.py council run-round --root TASK --council-id c-first --round-id 1 --member-splits SPLITS.json
```

无法由当前配置读取实际钱包，或采用其他提供商时，可用实际费用事实运行同一已准备请求。以下是 `FIRST.json` 的单成员结构。费用文件和 Split 路径换成本次真实记录，费用预留填适用限额内的实际保守上界。需要指定凭据时，在成员项内填 `config_path`。

```json
{"members": {
  "member-1": {"facts": "wallet-facts.json", "ceiling_usd": 0.10,
    "split_path": "first-split.json"}
}}
```

```text
python -B tools/codex.py council run-round --root TASK --council-id c-first --round-id 1 --plan FIRST.json
```

发送期间按 [LIVE](LIVE.md) 发布本 exchange 的源文字。以下是原生初议与再议的登记路径，`--input-version` 使用实际材料版本。

```text
python -B tools/codex.py council native-return --root TASK --council-id c-first --actor REAL --input INITIAL.txt --input-version 1
python -B tools/codex.py council barrier --root TASK --council-id c-first
python -B tools/codex.py council packet --root TASK --council-id c-first --actor REAL --stage REDELIBERATION
python -B tools/codex.py council redeliberation-return --root TASK --council-id c-first --actor REAL --input RECONSIDERATION.txt --input-version 1
```

两侧达到终态后实际转交再议包并存下原生返回。发生预检或网络异常时，读回该交换与议会的实际状态，必要时用 `seal-member` 登记可证实的异常，或按已确定范围 `close --reason ...`。已提交或传输结果未明时沿同一交换读回正文和账目。仅在确认请求尚未提交且仍处于有效窗口时，才可从当前有效准备状态提交。

普通议会可用纯原生参与，也可通过 `--claude` 加入第一层。两种分隔符下的子议会均按当前选择、第一层额度与实际共享钱包直接使用。实际发送对每个成员和请求分别核对 Split、费用和当前任务输入。识别模式和费用来源见 [PROTOCOL](PROTOCOL.md) 与 [WORKBENCH](WORKBENCH.md)。

```text
python -B tools/codex.py council create --root D:/task/session --council-id c1 --native-actor <实际原生代理id>
python -B tools/codex.py council create --root D:/task/session --council-id c2 --native-actor <实际原生代理id> --claude --member-count 2 --deadline-seconds 300
python -B tools/codex.py council packet --root D:/task/session --council-id c2 --actor <实际原生代理id> --stage INITIAL
python -B tools/codex.py council prepare-round --root D:/task/session --council-id c2 --kind INDEPENDENT
```

每个成员的 exchange 均须由 Codex 完成本机研究和实际 Split；`consult split` 可读其当前绑定，`consult split --input ... --out ...` 绑定真实决定。然后准备批次 JSON：

```json
{"members": {
  "member-1": {"facts": "facts.json", "ceiling_usd": 0.10,
    "split_path": "member-1-split.json", "config_path": "D:/private/consult.json"},
  "member-2": {"facts": "facts.json", "ceiling_usd": 0.10,
    "split_path": "member-2-split.json", "config_path": "D:/private/consult.json"}
}}
```

数值是演示，不是实际价格或费用授权。facts 须覆盖每个完整公开请求、真实模型和当前价格/余额；两个成员使用同一实际账户的 `wallet_id`，不能分账户名绕共享预留。私有 config 和密钥不复制到任务内。

```text
python -B tools/codex.py council run-round --root D:/task/session --council-id c2 --round-id 1 --plan batch.json
python -B tools/codex.py council native-return --root D:/task/session --council-id c2 --actor <实际原生代理id> --input native-initial.txt --input-version 1
python -B tools/codex.py council prepare-round --root D:/task/session --council-id c2 --kind CROSS
# 每个新exchange重新实际Split；随后run-round。FINAL同理；足够时可直接seal-member。
python -B tools/codex.py council seal-member --root D:/task/session --council-id c2 --member member-1 --status COMPLETE
python -B tools/codex.py council barrier --root D:/task/session --council-id c2
python -B tools/codex.py council packet --root D:/task/session --council-id c2 --actor <实际原生代理id> --stage REDELIBERATION
python -B tools/codex.py council redeliberation-return --root D:/task/session --council-id c2 --actor <实际原生代理id> --input native-reconsideration.txt --input-version 1
python -B tools/codex.py council event --root D:/task/session --council-id c2 --kind RELATED_CANDIDATE --input actual-new-material.txt --member member-1
python -B tools/codex.py council prepare-round --root D:/task/session --council-id c2 --kind REENTRY
```

`inspect` 只显示状态和来源元数据；它不泄露初议观点，也不证明独立上下文已读材料。`completion_status` 为最终返回提供活跃批次、未返回再议和待处理事件的真实范围。只有已声明范围的明确关闭或实际完成才可以收口，费用未知仍单列。

## 跨版本责任与期限边界

新事件只拉回实际相关研究者，同时承接旧cycle尚未完成的原生初议／再议和未封存成员责任。迁移明确指向目标cycle及同一研究身份，全局完成检查逐cycle核对，不能用最新phase覆盖旧义务。已完成且无关的研究者不因历史迁移被反复复活。明确异常关闭保存真实未完范围，不冒称这些返回已经发生。

阶段deadline与底层网络保证分开：已绑定响应的慢字节读可按绝对期限中断；DNS/TLS等操作仍受真实宿主网络能力约束，在途与未知费用不因屏障释放或本机断开而消失。

本层真实U0形成、修订或恢复后，先作FOUNDATION短协议自提醒，尤其保持初议隔离、实际公开流转播与原生再议；不为一次调用或无变化再入强造新U0。
