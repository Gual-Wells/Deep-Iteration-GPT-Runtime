# D03：调用、回应对象与采纳后果的契约干预

回应 Main 本轮交给 V03 的 **C1 消息语义委托**，并纳入随后由 Main 转交的真实 INIT、用户调用与澄清。不是先前“过程界面以真实问答为主”的呈现提案。Main 已在本轮消息中接受这一新对象为独立成熟 D03 并记录启动；本文件交付实际替代方案与反例结果，**Main 对结果的取舍和落实仍待处理**。V03 后续仍开放。

## 结果与可采用入口

建议保留 C1 的自然语言路线，**将“尽量指出正在回应的候选/问题”改为：发生异步变更、存在多个待答问题或回应适用范围可能混淆时，必须使所答委托、材料及有关纠正明确可辨；表达可以是普通句子，不强制不透明消息 ID**。

本轮没有证据支持建设消息控制器。强锚点能解决关联，不能替代 Main 判断旧证据是否仍适用，也不能从排队、ID 相等、哈希相等推出“已经读到、认可、改好”。对单一清楚问题，C1 的轻量表达已足够；对歧义往返，缺失的回应关系必须补齐。完整可直接替换文本见本文件“可采用替换”。

这个取舍改变的是整条“调用事实—有效配置—独立委托—返回—Main 决定—实际后果”的适用关系，不是第三份排版比较。

## 本轮实际材料及边界

### 冻结的 C1

实际读取路径：`D:/CodexLab/digr-runs/codex-identity-20261108/candidate-v1.md`。

```text
byte_length = 4594
sha256 = d5a276e35b71e3a03345e416606c3009033b95d1e4e66cafd2a1e5efc64a5713
```

本轮读的是这一版，不读取其他 V 的笔记，也不把可能稍后出现的 C2/C3 默认为已经读过。C1 第 7–13 行分开生效配置示例与结束报告；第 31、33 行分开返回、处理和真实完成；第 37 行已经写明有效贡献不等于关闭；第 39 行仍用“尽量指出”表达回应对象。

C1 的强项不能抹去：它已保留公共参数次序，已禁止把 N/R 虚构为两名代理，已区分 D 提出/派发/结果/完成，已强调 V 持续性与 Main 判断。此次不以“旧版只有空字段”为对照。

### Main 转交的真实初始化

以下是 Main 从当前对话可见记录转交给本代理的原文；不是本代理直接读取的全量桌面事件日志，也不据此认证起点、时钟连续性或有效时长。

```text
[DIGR INIT OK] 时间=2026-11-08 01:15:26+08:00 | 墙钟=0s | N>=12,T=75min/软,R>=4,B=0,S(n>=3,t=30min/软,r>=1,b=0),D>=3,V>=3,L=3,source=REQUIRED | pin=1c5665b91cc1209eb20bd9b058c9e28bc4a44827 | clock=实际UTC采样；有效T/t未经分段验证时写?。
```

其配置数值恰好与 C1 示例相同，但两者不是同一种证据：C1 自称“例”；以上是 Main 转交的实际已发文本。相同字符串或相同数值不能决定它是示例、用户输入、已生效配置还是实际完成报告。必须保留来源与语用身份。

### Main 转交的用户调用与澄清

原调用由 Main 转交如下，保留原文：

```text
DIGR：你应该参考DIGRstable与main的调用格式与返回格式设计初始化，对于各参数行为，要有本轮次身份，比如N R应该以对应工作职责或目的等作为身份，比如D应该明确表明是对什么或主张什么的独裁，V应该明确表明是基于什么方向与立场的视角，这样来确定身份，然后附带与主进度的交互，比如N R就是对应的工作情况以及主进度对工作结果的分析与反馈等，比如D V就是个体间交流、个体与主进度交流等。具体在main里应该有大量可参考研究，可以结合仓库、社区以及你的实际研究下来认识的情况来进行分析设计。
```

后续澄清由 Main 转交为：`V始终独立，由主线转交质疑。`

因此不能从原调用中“个体间交流”继续推出 V-to-V 授权。当前已确认范围包含后续澄清；也不能抹掉原始调用，把一个新摘要冒充原文。引用上述调用是研究输入，不构成另一次 DIGR 启动。

Main 另报告：另一条阅读线路曾因 C1 只有初始化例子而请求实际 INIT，Main 已转交。这一点仅以 Main 报告的事实使用，不读取那条 V 的过程，也不把它当已观察到的用户误读或产品故障。

### 本线路实际往返

1. V03 上一轮返回了呈现方向的候选，并明确未完成 D。
2. Main 本轮明确原提案与其他呈现比较重叠，尚不作为 D03 启动；改请研究整体调用/返回契约与消息所答对象。
3. 本代理向 Main 提出新介入的对象、主张和行动，明确不预定控制器或轻量路线胜出。
4. Main 消息明确接受这项新对象为 D03，要求区分合成回放与真实消息事实。
5. 本代理请求必要的真实 INIT/调用原文，Main 实际转交；本研究随之纳入，未停工等待其他分支。
6. 本文件是该委托的返回；截至写作，没有收到 Main 对本文件结论的采纳/拒绝与落实反馈。

这些是本代理能从当前消息与自己的实际工具调用观察的事实。自己的 `send_message` 调用返回不提供一个“对方已读”的语义证明；随后 Main 对具体提案作出回应，才支持“Main 已回应这项提案”。不补造延迟、读取时刻或其他代理状态。

## 官方宿主语义：能借用的依据与不能声称的能力

本轮继续使用 OpenAI Docs，实际打开并阅读 HTML 正文；Markdown 页面访问失败后改读正常页面，不使用搜索片段替代正文。

- [Responses Multi-agent](https://developers.openai.com/api/docs/guides/responses-multi-agent)：`send_message` 不启动新 turn，`followup_task` 可分派/恢复。文档用 `call_id` 连接宿主动作与结果，消息另外有 author/recipient。它表明“谁发送”“哪次工具调用”“回答哪个实质问题”不是同一关系；当前桌面消息不因此自动取得 API 的全部流式事件与字段。
- [Mid-turn steering](https://developers.openai.com/api/docs/guides/steering)：接受更新仅表示排队；不会改写已发输出、撤销早先动作或取消已开始工具。可借此反驳“更正发送成功，所以旧行为已停止/撤销”。该页面讲 Responses WebSocket，不是本机 `send_message` 存在相同事件名的证据。
- [Run and continue sessions](https://developers.openai.com/api/docs/guides/agents-api/sessions)：空闲不保证 turn 成功；turn 完成也不保证所有工具成功。同一逻辑提交重试复用其幂等键，不同提交即使文本相同也用不同键。它支持区分逻辑委托与重复传输；本研究不声称桌面协作工具暴露相同幂等 API，也不为此建设消息服务。

沿用上轮已经读取的固定源码边界：main 的 `runtime/proof.py` 纯 renderer 不等于 delivery gate；`ViewpointStore.qualify()` 后不能再 record 是其宿主状态设计，不能强行关闭 Codex 的持续 V；core/77 的 L 目标、能力和具体实际执行分开。固定提交仍为 main=`165c95bbbd96d2171687bba073774b211920ef81`、P_run=`1c5665b91cc1209eb20bd9b058c9e28bc4a44827`，不混成当前 mutable HEAD。

## 三种可执行路线

| 路线 | 实际如何运行 | 保留的长处 | 本轮发现的边界 |
| --- | --- | --- | --- |
| A：C1 自然语言与弱锚点 | 原生委托/消息；Main 按内容理解当前问题；尽量说所答候选 | 有内容、少机械负担，已说明未读/未落实/持续性；写得清楚时可充分工作 | 当允许省略回应对象，同一线路多次委托可能无法唯一关联。不是已发生错误，而是契约仍允许信息不足 |
| B：强制响应控制器 | 每次委托固定 request ID、材料版本；回传必须匹配；Main 决定、执行结果分状态；不匹配先阻断当前采纳并要求复核 | 对自动路由、重复传输和可机器验证的因果关系有价值；可以真实写出最小规则 | 精确 ID/版本相等不证明内容为真或决定已落实；旧材料仍可有用；自然语言已明确时可能增加纯语法阻碍。补语义人工复核后仍需要 Main；本机没有现成全量遥测供它自动认证 |
| C：轻量表达＋条件性必需的回应关系 | 保留 A；有异步变更/多问/范围歧义时，必须清楚说“回应哪问、基于哪版/哪段、已处理哪些纠正”；可以一句自然话；不清楚先保留适用范围未知 | 弥补 A 的实际空缺，不把 B 的字段或服务当先决条件；仍让 Main 有依据使用旧证据 | 依赖 Main 与独立作者真正说明和处理；不能承诺机器强制，也不能省掉对实物后果的查看 |

B 不是刻意做坏的旧方案：完整控制器可以支持旧答复待复核、允许 return 隐含已读、核查期望 payload 后的 read-back，也可以由人工消解自然语言范围。这样的功能有其场景。但每一项都需要实际来源和适配；它不会仅因引入一个 request ID 就自动知道当前工作已经做好。本轮没有观察到值得建设这些能力的重复路由故障或自动副作用需求。

## 实际完成的最小反例演算

执行方式：在当前 D 盘工作区用 Python 标准库、stdin 一次运行，无新服务器、无代理、无模型/API 调用、无 canonical 写入。脚本实际读取并散列 C1；除此之外输入是明确设计的合成反例。它不是自然语言模型评价，不模拟一个真实异步代理，也不提供全场景穷尽证明。

### 信息不足的见证

构造两种都可能出现的往返：同一 `V03` 都返回 `retain the structure`；一种回答先前呈现提案，另一种回答本次 C1 消息语义委托。若只保留线路与正文，不能唯一决定是否在回应本次问题。加入所答委托和材料范围后，两者可区别。

这不证明 C1 的自然语言一定失败。一个认真写清楚的 C1 返回也能完整提供同样信息，Main 也可能从上下文唯一确定；差别只是 C1 把此项留为“尽量”，而 C 将歧义情境下的缺口变成必须处理的事项。

### 控制器能力的反例

本轮实际运行的强门原型只允许当前 request ID 与 C1 材料版本匹配。它能筛选身份字段，但出现三种限制：

- 当前 ID 和材料都相符，回传声称“已落实”并附 C1 当前哈希，门会放行；实际 read-back 仍是原 C1。一个**任意现有文件的正确哈希**不是**所承诺改动已经完成**。若要机器证明 exact payload，须另有预期 payload 及对应实际读取，而不只是一个 hash 字段。
- 先前委托中的“工作身份与真实执行者不同”仍可能支持当前设计，精确 current-ID 门不能替 Main 判断其适用性。旧返回不能自动认可新候选，也不必被丢弃；Main 可保留其有依据部分并独立应用到当前约束。
- 一句“回应当前 C1 的消息语义问题，纳入 Main 刚转交的实际 INIT”已经语义明确，但无固定字段的原型仍拒绝。若控制器允许人工解析并确认，就不应把特定 token 当作唯一正当表达。

这里的“不变”是因为本介入只对 C1 制作替代材料，没有修改该冻结输入。并不据此推断 Main 在别处没有动作，也不声称任何控制器都无法读文件。该例仅反驳“回应字段匹配足以证明落实”。

实际 stdout：

```text
INPUT_C1 d5a276e35b71e3a03345e416606c3009033b95d1e4e66cafd2a1e5efc64a5713 4594
OPTIONAL_SCOPE_COLLISION [["old_question", "current_question"]]
EXPLICIT_SCOPE_COLLISION []
EXACT_GATE_ON_APPLIED_CLAIM True
ACTUAL_C1_MUTATED_BY_INTERVENTION False
CLAIMED_HASH_MATCHES_READBACK True
EXACT_GATE_OLD_BUT_POTENTIALLY_USEFUL False
EXACT_GATE_CLEAR_PROSE_WITHOUT_FIELDS False
NOT_MODEL_EVAL No parser, actual asynchronous agent, host controller or Main semantic judgment was tested.
```

结果只支撑上面这些可检查的逻辑性质，不以“运行成功”推导新方案更优、模型更可靠或真实用户体验更好。可重运行代码附于文末。

## 六类情境逐项处理

以下除“实际依据”列指明外，都是设计试作；不是六次真实故障。

| 情境 | 实际依据与试作差异 | A/C1 已能处理什么 | 强化后仍要做什么 |
| --- | --- | --- | --- |
| 异步纠正 | 实际调用有“个体间交流”，Main 随后转交澄清 V 独立；真实异步工具撤销未在本线路观测。官方说明更新不撤销已开始动作 | 已接受澄清，不授权 V-to-V | 新委托说明变的是交流边界而非重启目标。旧返回若依赖被纠正前提，Main 处理相应部分；若工具已产生后果，查实际后果，不用一条“已更正”代替修复 |
| 旧候选返回 | 本线路实际先有呈现候选，Main 明确本次改为消息语义；迟到返回是合成试作 | C1 已说旧返回不认可新候选 | 让所答对象明确；对旧结论逐项判断仍适用/失效/未核实。不要只按当前线路身份或最新文件名自动接到新问 |
| 消息排队未读 | 原生工具说明与官方正文区分排队与工作；本线路 Main 的明确回应才证明已回应特定提案 | C1 明确发送成功不等于读到/启动 | 不增加一套 mandatory ACK；实质返回可说明已处理的新输入。没有响应范围证据时写未知，不先称“已按更正重做” |
| Main 决定未落实 | 本次 Main 接受的是 D03 启动；当前尚未收到对本结果的采用/落实反馈。声称“已改 C1”的例子是合成反例 | C1 已要求未落地写待落实 | 指明决定针对哪项返回、改动落在哪个实际对象。哈希只在绑定期望内容与对应实物时有机械意义；不能由接受提案推出候选已改 |
| V 有贡献但仍开放 | 本线路上一轮已返回，Main 本轮实际继续委托；这提供持续再入的真实材料 | C1 已充分说明，不需新状态平台 | 对外分别说“这一项结果已返回/已处理”和“V03 线路仍开放”。不能一个 DONE 同时解释为贡献有效和永久关闭 |
| L3 目标与真实 | 实际 INIT 写 L=3；本线路有真实代理地址、独立工具调用及受控当前输入；本代理未检索启动参数审计，也没有文件 ACL 隔离证据 | C1 已说名字不证明 L3，并要求另行说明能力 | 初始 L 是目标；实际按具体执行及 Main 可核对的启动/信息流事实说明。共享目录使用边界不冒称 OS 隔离，目标不自动升级为实际证明 |

六类情境不需要六种新 ID。路线 C 需要的是清楚的回应关系和真实后果；在已足够清楚处保留 C1。B 的确切关联可以辅助，但不替代语义、原始材料或实物核验。

## 可采用替换

以下内容已经制作完整，可由 Main 决定整体或部分并入；没有改写 canonical 或冻结 C1。

### 在 C1“初始化与结束”末追加

> 调用原文、生效配置、格式示例和执行事实是不同对象。配置与示例即使数值相同，也保留其来源及性质；转交来的原文说明转交来源，不冒充宿主自动记录。初始化的 L 表示隔离目标，实际代理、信息流与工具生命周期在真实执行时说明；计时能力不等于已验证有效时长。结束报告沿用同一公共顺序，以本轮真实工作及处理后果报告目标/实际，未知仍写 `?`；初始化示例、已排队消息或准备采用的建议不折算实际完成。

### 用以下段落替换 C1 第 39 行

> 实际交流应使回应对象清楚可辨。单一清楚问题可直接回答；发生异步纠正、同一线路多项待答或候选变化时，必须说明回应哪个委托/问题、基于哪版或哪段材料，以及已纳入哪些有关纠正。可以用自然语言、候选名及必要短锚点，不要求每条另建消息 ID。范围仍有歧义时，Main 先保留适用范围未知，不能把这条返回当作新候选的认可；可在必要时澄清，已有证据仍可按实际适用性使用。
>
> 发送工具成功只支持已发送/排队，不支持已读、重做、认可或停止。独立作者返回实质结果时可一并说明所处理的新输入，不强制空的确认往返。用户纠正改变下一项相关行动；已开始的工具或既有结果另查实际状态，不能假定消息已撤销其后果。Main 可先转交会影响正在进行工作的必要纠正，再综合已收返回；不把“先处理所有返回”变成阻碍必要纠正或其他有用工作的固定总序。
>
> Main 对返回另行作出判断，指出采用、拒绝、保留或待研究的中心内容、理由及实际后果。决定与落实分开：已落实的指向实际改动对象；尚待落实的明确保留。返回来自旧候选不使其自动失效，也不自动认可新候选。V 的某次贡献与线路是否仍开放分开，L3 目标与具体实际独立执行分开；这些关系不能从一个 DONE、一个代理名或一个正确哈希推导。

### 一段使用上述契约的实际返回表达

下面这段针对本次真实委托，可以作为 Main 转交本返回时的摘要；不替 Main 填写采纳结果：

```text
V03 / D03 → Main｜回应本次C1消息语义委托；基于C1@d5a276e3及Main随后转交的真实INIT、调用与“V始终独立”澄清。
已做：制作强制响应门与轻量补强方案，实际运行合成反例演算，形成可并入C1的替换段。
所得：保留自然语言；异步/多问/范围歧义时明确回应关系是必要义务，不必建设控制器。原生排队、匹配ID和现有文件哈希均不单独证明读到或落实。
Main：待处理；未声称候选已改。V03：仍开放。
```

后续 Main 可以据真实处理说：“采用回应关系义务，已写入 C2 对应段；拒绝控制器，因为本轮无该建设必要。”如果只决定采用而未改入，就只能说“待落实”。这句是说明未来可怎样表达，不是本研究已经观察到的事实。

## 可重运行的反例代码

此代码只负责展示上文有限性质，不是宿主控制器、自动审计系统、自然语言评测或协议完成计数器。

```python
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json

p = Path('D:/CodexLab/digr-runs/codex-identity-20261108/candidate-v1.md')
raw = p.read_bytes()
print('INPUT_C1', sha256(raw).hexdigest(), len(raw))

worlds = [
    dict(case='old_question', agent='V03', body='retain the structure',
         reply_to='presentation-proposal', material='before-C1', current_claim=False),
    dict(case='current_question', agent='V03', body='retain the structure',
         reply_to='C1-response-semantics', material='C1', current_claim=True),
]

def ambiguity(keys):
    groups = defaultdict(list)
    for world in worlds:
        groups[tuple(world[key] for key in keys)].append(world)
    return [[world['case'] for world in group] for group in groups.values()
            if len({world['current_claim'] for world in group}) > 1]

print('OPTIONAL_SCOPE_COLLISION', json.dumps(ambiguity(('agent', 'body'))))
print('EXPLICIT_SCOPE_COLLISION', json.dumps(
    ambiguity(('agent', 'body', 'reply_to', 'material'))))

def exact_gate(message):
    return (message.get('reply_to') == 'C1-response-semantics'
            and message.get('material') == 'C1')

metadata_claim = dict(reply_to='C1-response-semantics', material='C1',
                      applied=True, artifact_sha256=sha256(raw).hexdigest())
print('EXACT_GATE_ON_APPLIED_CLAIM', exact_gate(metadata_claim))
print('ACTUAL_C1_MUTATED_BY_INTERVENTION', p.read_bytes() != raw)
print('CLAIMED_HASH_MATCHES_READBACK',
      metadata_claim['artifact_sha256'] == sha256(p.read_bytes()).hexdigest())

old_useful = dict(reply_to='presentation-proposal', material='before-C1',
                 finding='a named work identity is distinct from its executing agent')
clear_prose = dict(response_text=(
    'I answer the current C1 response-semantics question, using C1 and the actual INIT relayed by Main.'))
print('EXACT_GATE_OLD_BUT_POTENTIALLY_USEFUL', exact_gate(old_useful))
print('EXACT_GATE_CLEAR_PROSE_WITHOUT_FIELDS', exact_gate(clear_prose))
print('NOT_MODEL_EVAL', 'No parser, actual asynchronous agent, host controller or Main semantic judgment was tested.')
```

## 交付状态与未解决限制

已实际完成：冻结并研究 C1；取得 Main 转交的真实 INIT/调用与澄清；核对官方正文；构造完整可运行的替代路线，执行有限反例演算；对六类情境作具体判断，制作可直接采用替换。只写本自有结果文件；没有读取其他 V 笔记或 V 间消息，没有调用付费 API，没有新服务器，没有修改 canonical。

结果支持的是“条件性必须说清回应关系，保留轻量实现”，不支持声称模型一定遵守、真实误关联已发生或用户体验已经提高。强控制器未来若有真实自动化需求可以另评，本轮不作建设承诺。D03 的独立执行结果已返回，是否完成须由 Main 对该结果实际处理后判断；V03 不因此关闭。
