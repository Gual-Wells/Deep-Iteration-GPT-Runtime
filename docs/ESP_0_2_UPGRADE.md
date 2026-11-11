# ESP 0.2：理解并取用真实困难中的语言

本次将 ESP 的用途落到具体处境中的理解、措辞选择与可复用入口。核心发行另兼容旁路的 Codex 0.8.1；ESP 0.2、Personal Context 0.1 和数据格式分别版本化。此次建设的历史运行依据仍是 `0.8.0@314e513d439829fa1159e6801d1421ed1e569e0a`，不是将活跃任务换 pin。

## 先拿成品

- [四十毫秒量了什么](../spoken-preprint/examples/forty-milliseconds-01/README.md)：端侧推理实习面谈；性能标题和个人贡献两项声明被追问、核查并实际修订。没有新测试或录用结论。
- [屏幕上的余额](../spoken-preprint/examples/balance-on-screen-01/README.md)：英格兰生活；月付、欠额、分摊、预算与承诺的范围不同。另有明确作者议论示范。
- [下一帧之前](../spoken-preprint/examples/before-next-frame-01/README.md)：保留为技术对照。诊断和方案组织偏顺，不能替代尚未成形的思考过程。

每册原场景、双语学习听稿、中文处境回看与幕后版分开。人物、项目和数字均为原创虚构。学习稿解释实际指代、义项、时态/承诺和使用条件，并给明确编辑变式；不会把拟句加成角色曾说过的回合。

## 为什么改变路线

独立竞争实物表明，仅添加来源/能力字段、未解决结尾或复杂物件，仍可能得到完整流畅的专家对答。因此一般推理继续开放；严格限制的是编造个人经历、已经观察的结果和没有执行的行动。新场景用一项已经写出的工作理解与声明承受追问，不规定错误次数或失败结局。

另一实物证明：写入Markdown的释义不会自动进入纯PHONE。故保留完整听剧稿，另做可连续听的双语编辑课。研究中口头解释、回放与课堂参与是实际处理条件，不能把它们的结果直接移给纯旁听。[Zhang与Graham的原研究](https://onlinelibrary.wiley.com/doi/full/10.1111/lang.12411)。本项目没有观察本用户学习收益。

技术选材保留原件范围：张量句柄/共享/独立复制不是一回事，[固定版本Tensor文档](https://github.com/pytorch/executorch/blob/f7140a46ff38e919c557d45b102d3ff26097c8c9/docs/source/extension-tensor.md)提供背景；[Android进程生命周期](https://developer.android.com/guide/components/activities/process-lifecycle)不支持“重开界面必是新进程”；[启动指标定义](https://developer.android.com/topic/performance/issues/launch-time)也不让单条分类显示窗口自动成为TTID/TTFD。场景中的40/210/180均为独立虚构数值。

生活选材区分固定项、月付与个人分摊。[Ofgem](https://www.ofgem.gov.uk/your-energy-supply/your-energy-bill/how-your-electricity-or-gas-bill-calculated)说明固定项与使用收费不同；[Citizens Advice](https://www.citizensadvice.org.uk/consumer/energy/energy-supply/problems-with-your-energy-bill/energy-supplier-has-increased-your-direct-debit/)给出月付可能含旧欠额偿还的制度背景。这不裁决虚构室友比例，也不适用于任意国家或账单。

## 分层责任与选定架构

| 数据/能力 | 实际责任与位置 |
|---|---|
| 公共运行库与技能 | 通用工具、流程和明确虚构样例；不放真实个人资料 |
| 用户选定原件 | 原学习/项目空间，按页、XHTML项、段落或JSON路径取材；提取不等于通读 |
| Personal Context私人目录 | 原件身份/版本、原话、自述/声明/资源/未知、分享范围及本册人物最小胶囊 |
| Paper Knowledge原池 | 真实论文选择、教学过程与有范围证据；不被画像或演员表现覆盖 |
| 本册preprint源 | 真正接受的原生言行、伴生内心、世界决定与感知，以及独立编辑语言资源 |
| phone / study / creator | 完整场景、独立编辑课程、幕后分别交付；手机不需安装本机工具 |
| 本地导航 | 只定位原数据，不是新的任务调用、原件、掌握状态或协议权威 |

比较过把数据放公共运行库、现有辅学项目、已有私人知识仓库及另建独立私库。采用“原件留所选学习项目，通用机制在DIGR，个人依据在已有私库子目录”；维护少一个仓库，也保留数据边界。竞争路线“仅选定来源目录＋每册胶囊”仍成立：ESP可直接从明确材料/虚构创世，Personal Context是可选供给端，不是完整人物数据库的前置要求。

资料源的主要位置、历史副本、逻辑当前版和更正历史分开。旧同版副本不能掩盖原件已改/已删；显式relocate选择同版新位置，withdraw停止新使用。新使用前检查所选条目；缺失不恢复、未知不推出不会。外部大原件未自动随Git克隆，需要实际原件和明确重定位。

## 已落地接口

[Personal Context](../personal-context/README.md)支持选定EPUB/PDF/DOCX/JSON/文本摄入、条目来源约束、版本/撤出和book/role视图。PDF需要已有pypdf；本轮实物摄入主要是已有EPUB的选段。独立使用只读了必要文字块，未读其代码图片，未把书目变成用户技能。实际简历和个人贡献材料缺失时保留未知。

[ESP学习接口](../spoken-preprint/LEARNING.md)支持连续公开案例、实际语言义项、作者短变式、来源绑定课程、内容判断、中文处境查询和跨册关系。exact-use、handling-function、contrastive-use分别保存；后两者不计词汇复现。本次实际系列用handling-function连接不同领域的范围/承诺与贡献动作，没有强造相同词。

[场景接口](../spoken-preprint/CONTEXT.md)支持按需读取自有材料、冻结重要过去、分域世界写入和有限机会。U0/D/V反馈扰动可有新的可见依据、有限反应与停止条件；该扩展已经行为测试，三册主要实际使用的是原生pair内心交流和有界世界后果，不宣称每项扰动都已用于原生故事或建立了人类认知概率模型。

## 版本与真实验证

新源schema 2拒绝旧writer。实测中，旧writer能对一个schema1拷贝绕过新冻结约束；新格式让该writer在读取处拒绝。旧书schema1读取不改字节，显式升级或新机制写入在receipt记迁移。导出和来源归档清单仍为schema1，与源格式无关。

三册来源归档、出版物与复制后的相对关系已实际校验；原生文本没有因教学编辑改写。角色胶囊的错book/role、来源变更/缺失/版本替换、重试/冲突、预算/冻结事实和旧格式迁移有行为测试。最终整库测试数与安装/推送证据见交付记录，不以测试数认证作品或收益。

真实新上下文已完成个人依据选择：只把适合的所选未知交给人物，资源留创作者，并核读原EPUB的有限文字块。另一新上下文只读台前学习稿演出一课，保留动作内原引语，没有要求听者回应。它们验证文字路径；真实手机音色、节奏、听懂、临场检索与长期掌握均未观察。

没有新阅读器、付费模型API、常驻服务或手机回传桥。真人参与式实训仍是[独立设计探索](../research/codex-participation/README.md)，不成为ESP依赖。
