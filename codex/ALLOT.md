# Allot：Sol Max 主力与反馈驱动的实际调度

Sol/max 是 Main 研究、设计、论证、综合、整体再议和实质 D/V 的智力基线。0.18 pin 的 `default_primary_model` 固定为 GPT-6.2 Sol，effort默认为max；显式 GPT-6.1 Sol/max 继续支持。选择先按任务链、能力、约束与成本机制论证，不设模型评测或效果实验准入；小样tokens不代表Pro套餐效率。Light/Less/Default/More/Max只改变研究职责，不映射effort；不按五档预留Astra席位，不沿用Pro100固定计划点或从Pro名称推断价格与token容量。未另选速度时用Standard，提速不等于智力升级。见[完整适配设计](DESIGN_0_18.md)。

## 持久策略与完整输入身份

`allot plan` 按任务 `P_run` 解析政策。0.18 pin 的工作块省略 `model` 时采用该 pin 的 `default_primary_model`；显式填写的 `model` 按原有规则校验，`null` 无效。宿主缺少选中的型号或所需 effort 时，`plan` 或 `ready` 报错。0.17 仍要求显式型号，0.17 与更早 pin 沿用原有政策及已保存的政策哈希。

当前用户明确改选政策时，可用 `allot set-policy --root TASK --input actual-user-policy.json` 保存 `{profile:"sol-max-feedback",source_ref:"实际当前来源",reason:"决定与后果"}`。该操作记下政策修订和来源。0.18 pin 的 `allot inspect --root TASK` 显示完整生效政策记录，单一默认型号见 `policy.policy.default_primary_model`。恢复包带同一政策的公共字段与安全执行概要。`plan` 绑定完整消息身份和政策修订；同文的两次真实 DO 是不同消息，旧 block 不能跨新输入复用。

## 仅受控批量劳动可降低effort

先用现成脚本完成重复操作；确需原生机械协调时，只有大批量、规格明确、无实质智力判断、重复且执行受控的工作包可以降effort。说明可枚举输入范围、已定操作和覆盖范围的验收；量级依实际工作，不发明最低件数。定义、公式诊断、材料取舍、跨项依赖、审美与规格判断继续Sol/max。篇幅短、维护标签、Light档或D/V身份都不能单独证明可降。

所有低于Max的最终选择均检查，不留requested_effort或kind旁路。输入须有 `fully_specified:true`、明确 `requested_effort`、`allow_downshift:true`，并以controlled_labor保存 `large_batch/repetitive/non_intellectual/controlled:true` 及非空 `scope_ref/validation_ref`。这是原生研究者提供的真实工作依据，不是脚本认证了劳动性质。降档只作用于该工作包。

批内暴露规格歧义、跨项问题或质量/能力失败时，受影响的后续块恢复Sol/max；保留仍符合验收的结果。DO后按实际影响重研剩余范围，不全盘丢弃原件或沿旧选择派发。

## Max不足时升级实际执行模型

Max已是本策略effort顶档。feedback以 `category/evidence_ref/detail` 区分质量、能力与tool/network/permission/input/budget；后者先修对应条件，不能仅凭报错换昂贵模型。裸failed_efforts数组、复杂标签、More/Max档或固定失败次数不构成新策略升级依据。

具体Max能力缺口，或真实任务反馈表明Sol/max仍不能解决问题时，选择宿主实际可用、针对该问题的模型。escalation保存 `trigger`（max_capability_insufficient或task_failure_feedback）、`source_model/source_effort:"max"/evidence_ref/reason`；unresolved保存真实未解问题。task_failure_feedback还须质量/能力类feedback。model为真实目标，不静默换成缺席型号。可只升级决定性子块，交接原件、约束、失败与落实责任，不固定全员换型，也不强制先做无价值的失败实验。

已有同范围原生资源授权持续有效，重要变化简明告知；不新增API美元、充值、外发或越过停止。具体Max不足时，可显式选择宿主实际支持的同型Ultra或有针对性地换型，不假定Ultra必更聪明。Ultra须显式请求、有升级依据且目标精确支持，floor/current不能自动抬升，也不暗增完整M。同一网络/工具故障引用不能伪装为能力缺口，真实独立的能力缺口证据另行处理。

## 选择、执行事实和恢复

新plan记录只给proposed_host_payload。实际派发前用 allot ready --root TASK --block-id ID --catalogue model-list.json，再核对生命周期、前置、完整输入、政策、能力、观察状态和批次资格；只使用当次ready返回的host_payload。它是只读就绪检查，不能原子拦截宿主，Main仍须在真实原生调用前服从新消息和停止。

实际质量/能力反馈用 allot feedback --root TASK --block-id SOURCE --input actual-feedback.json 登记，亦可在observe的feedback字段提交。稳定scope_ref标识受影响工作范围，validation_ref保存验收依据；只改验收引用不能清掉未解反馈。所有质量/能力反馈身份（含已解除）形成资格版本，低档plan冻结该版本，ready要求仍一致且无未解反馈。解除后必须为剩余工作重新plan，旧Low不会自行复活；仍通过实际验收的成果保留。阻断只提高低档下限，不吞掉合法显式Ultra请求。

完成诊断验收后，allot resolve-labor以solver_block_id、feedback_ids、evidence_ref、detail、validation_ref解除明确已解决反馈，未列出及后来反馈继续有效。DO未改实际范围与验收时，可用current_scope在当前处置中明确采用旧Max/Ultra求解观察，不因此授权旧计划派发；范围变更须重新核对。同一块同一实际故障的重试不因无关DO变成新故障。动态失败升级另需source_block_id、feedback_id，核对本任务实际Sol/max观察；预知能力缺口不强制先做失败实验。

旧任务显式改选保存Allot实现的版本、入口与可选implementation_pin，实际应调用该新实现；冻结旧CLI不会自动获得新行为。发布分发使用完整不可变pin，开发checkout不冒充发布身份。须同时将该入口放入旧恢复已读取的共同决定或next_action，不能只藏在新版policy里造成发现循环。

`allot plan --root TASK --input block.json --catalogue model-list.json`读取实际model/list或原生模型缓存。真实传给宿主的host_payload保留fork_turns=none、model、reasoning_effort。不能切换当前Main时，不改全局config冒充切换；真实新上下文承接具体工作须说明执行者与交接。

allot observe保存实际model/effort/source_ref及匹配。新策略选择被DO、暂停或结束取代后，旧实跑块仍可补记，明确superseded，不恢复执行许可或生命周期；旧pin回执不迁移。恢复仅共同政策和安全元数据，不带完整selection_basis.evidence或别线研究；有限摘要明确省略和未观察计数。

Allot仍是薄选择和事实记录能力，不调用模型、不改全局模型、不认证宿主配置。选择文件和助手自述不等于执行回执。按USAGE的真实分母返回费用和用量，不从Max/High名称推导固定倍率。
