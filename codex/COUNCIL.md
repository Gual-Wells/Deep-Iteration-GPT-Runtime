# 单一原生议会与内部 Claude 子议会

本节属于 Codex 0.16 候选 profile；旧 pin 不迁移。只有一个原生议会，Claude 子议会是其内部研究成员。原生独立者完成初议，待两侧达到完整或明确异常终态后，由原生独立者取得真实公开材料，自主再议并形成返回。Main 负责真实调用、权限费用、来源、暂存和忠实转交，不能先筛 Claude 观点、改写成议会结论。Main 继续完成主线作品和处理返回。

## 实际身份、观点距离与来源

原生 actor 使用宿主实际创建的独立代理身份；`--native-actor` 是对应关系的本机记录，不是凭名字创造代理。Main 不用自己的总结冒充初议或再议。初议 actor 在取得对侧观点之前，先形成自己的有内容认识、候选问题和候选分域；首次正式采用的领域可以由再议重划。

Claude 成员具有独立 `participation_role=council_member`，按 `council_id/member_id` 保持研究线身份；cycle、共同输入版本和 round 分开绑定。型号、provider、effort 和成员身份是不同字段。成员没有正式 Consult 的主观指导优先权，不能把 Sonnet 型号当成权威来源。正式 Consult 的原有条件关系继续有效；成员意见与既有指导真正发生前提冲突时，按原规则带来源和强替代选择性再入，不能把每条异议都升级成付费终审。

共同输入包保存原始用户原话、当前用户消息、已接受事实和约束，以及实际原件正文和散列。Main 负责排除任一初议侧已形成的推导；散列能固定字节，不能证明其中全是事实。引用、附件历史和模型旧话保留数据身份，不变成新的执行或费用授权。文件路径只用于核对，传入请求的是实际正文。

本实现的隔离为 **HOST_LEVEL**：宿主及用户会看到公开流，共享磁盘可读；不会声称 OS 保密或 Main 未受影响。`packet --actor ... --stage INITIAL` 只提供共同输入，不返回任一侧观点。再议 packet 只对配置中的原生 actor 在屏障释放后开放。宿主应将它实际交给相应独立上下文；actor 参数是宿主声明，不是身份认证。成员初轮不接收原生初议；后续子议会交流也不注入本轮原生初议。恢复中的成员保留此前公开历史，不能重新宣称从未受旧观点影响。

## 成员研究和通信

成员先进入材料探索，再发现值得争夺的支配前提、突破口或更强的整体路线；没有成熟旗帜时可以继续侦察，不必唱反调。强替代需要研究、比较、论证或实际试作，讲清替代什么、依据和适用条件。探索后协商形成有语义距离的领域，自主发展材料、问题、方法和成果，允许重新划分原问题。它们继承 D/V 的研究性质，不冒称已经履行完整原生 D/V/M 或 L3。

内部通信只转交实际公开消息。`CROSS`、`FINAL` 和 `REENTRY` 请求保留自己的公开链，并传入各成员已观察到的公开原稿及来源和状态；不以 Main 摘要定调，不机械截断。成员本人压缩终稿；正文过长时，再议包按字符顺序分块，块的拼接精确恢复全文，保留完整散列和来源。取得 JSON/本地路径不等于相应代理已经阅读，宿主须真实转交可读正文。

默认资源起点是两个成员，独立探索、公开交流、作者收束三种工作。它不是强制九宫格或最低付费次数：人数、输出额度、轮次和 deadline 随真实研究、许可和预算确定；可以省交流轮，但不能宣称已发生对应交流。首轮传输完整后仍待研究封存，不能把 API stop 当成 V 研究已完成。已有研究足够时用 `seal-member` 封存，无需再买一份短终稿。单次错误和额度不足不自动重发。

## 两阶段、异常与迟到

`INITIAL → REDELIBERATION → COMPLETE` 是本机研究对象的阶段，不代表代码认证了内容质量。每个原生初议 actor 和每个相关 Claude 成员分别封存 `COMPLETE/PARTIAL/FAILED/BUDGET_STOPPED/TIMEOUT/CANCELLED/OUTCOME_UNKNOWN`。只有两侧都进入终态才能释放屏障；异常解除等待，不证明研究完成，不视为支持或反对。

默认 deadline 是每个 cycle 300 秒，可在创建时明确覆盖；不静默延长。屏障只限制相关议会决定，其他主线工作继续。`run-round` 真正并发发送当轮已准备的各成员请求。到 deadline 先返回明确异常阶段，不等待所有 future 的网络工作完成；HTTP 超时也以剩余 deadline 为上限。服务端是否取消和收费仍可能未知，保留共享钱包预留。

屏障释放时固定实际可用的成员 exchange 列表。迟到公开正文保留原 cycle/input 身份，进入 `late_results`，不倒改旧再议包。`reenter-late` 将它作为带来源的新材料开启后续相关再入，不重复发送旧请求。若用户停止，先停止新增请求，再查服务端和费用；断开连接不能当作免费取消。

再议由原生 actor 各自返回实际作品，讨论完整成员材料中的实质主张，尤其是强替代，说明采用、部分采用或反驳的理由及后果。只保存 API 返回或 Main 写“已采纳”不是再议。所有指定原生 actor 返回后才进入 `COMPLETE`。明确停止可 `close --reason ...`，仍保留未完成责任；它不伪造再议已经发生。

## 持续发展与相关事件

持续性需要两件事：可恢复的公开研究线，及相关材料出现后实际同线研究。`event` 保存实际新候选、来源、用户纠正或领域问题，生成新共同输入版本和 cycle，给受影响成员及原生 actor 建立待研究责任。只列队和保存记录时，`research_reentry_performed=false`；真实同线返回后保存对应 exchange、版本和状态。未受影响的成员保留旧版本最后研究事实，不代称已读新版。

新消息使旧 prepared 请求过期；先把有关纠正放入新包，再准备 `REENTRY`。多条相关事件未处理时合并保留所有受影响身份，不能被最新事件覆盖。这个助手不监控一切文件，也不在无人授权时无限运行 API；Main 及原生独立者在真实相关候选出现时负有恢复同线的职责。保存“以后能再入”不等于已经持续研究。

新版也不能抹去旧版未完责任。新 cycle 取新事件影响身份、未处理事件身份及所有旧 cycle 尚欠再议的原生 actor／未封存成员的并集；旧 cycle 明确记录迁移目标和身份，未完工作在新事实下继续。已返回且与新事件无关的 actor 不重跑。最终检查逐 cycle 查真实返回或有效迁移链，不能因当前 cycle 已完成就丢掉旧 actor。明确关闭保留未完身份和理由，不把关闭写成完成研究。

## 本机可运行路径

以下路径仅示例。单冒号可以创建纯原生议会；`--claude` 必须同时具备当前 ALLOW、真实研究对象、适用费用授权及共享钱包可预留空间。双冒号及凭据存在均不授权任意规模。

```text
python -B tools/codex.py council create --root D:/task/session --council-id c1 --native-actor <实际原生代理id>
python -B tools/codex.py council create --root D:/task/session --council-id c2 --native-actor <实际原生代理id> --claude --member-count 2 --deadline-seconds 300
python -B tools/codex.py council packet --root D:/task/session --council-id c2 --actor <实际原生代理id> --stage INITIAL
python -B tools/codex.py council prepare-round --root D:/task/session --council-id c2 --kind INDEPENDENT
```

每个成员的 exchange 均须由 Codex 完成本机研究和实际 Split；`consult split` 可读其当前绑定，`consult split --input ... --out ...` 绑定真实决定。然后准备批次 JSON：

```json
{"members": {
  "member-1": {"facts": "facts.json", "ceiling_usd": 0.2,
    "split_path": "member-1-split.json", "config_path": "D:/private/consult.json"},
  "member-2": {"facts": "facts.json", "ceiling_usd": 0.2,
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
