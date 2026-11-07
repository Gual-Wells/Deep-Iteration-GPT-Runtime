# Claude 可借鉴机制、实际反馈与反例

研究日：2026-11-07。范围为 DIGR Codex 0.3 候选方法研究。本文件不是本轮运行协议；本轮运行 authority 仍由主线取得的 stable Alpha5 pin 决定。已读 D:/CodexData/AGENTS.md 与仓库 codex/PROTOCOL.md 作为任务背景，没有把候选协议当当前规则。

这里的 24 个主来源包含 10 个 Anthropic 官方工程/事故/当前文档、5 个 Claude Code GitHub 用户 issue、4 个 Reddit 原帖、4 篇实践者文章、1 个 HN 讨论；公开产物作为相关证据附在对应条目。所有采用的内容都实际打开读过正文；搜索用于找入口和部分日期元数据。没有运行外部仓库或付费模型 API，没有部署、安装服务或向外部作者发消息。

本次最值得带回 DIGR 的判断是：Claude 的可借鉴优势更多来自具体问题材料、可使用的成品、实际环境反馈、保持可取回的上下文，以及用户持续参与判断。它们需要模型能力、工具宿主与工作方式配合。没有证据表明一句强 prompt、更多代理、更多评审或一套固定长流程能稳定带来这些优势。Claude 社区也出现了与本用户高度同构的失败。

本研究没有在同一用户任务上运行 Claude 与 Codex 的盲评或等预算对照，因此不声称 Claude 普遍更好。官方内部数字、作者自报生产率和论坛赞誉分别保留其证据边界。GitHub 的完成/关闭标签也不自动证明问题已修复。

## 1. 先把模型能力、宿主行为和用户工作方式拆开看

2026-04-23 的官方事故比任何万能提示词都更能说明这一点。Anthropic 报告三件独立变化：默认推理投入从 high 改为 medium；闲置后清理旧思考的优化错误地每轮持续触发；精简输出的系统提示与其他变化叠加损伤编码表现。影响对象是 Code、SDK、Cowork，官方明确这次 API 没有受影响。后来一次较广评估的提示消融发现约 3% 的下降。短输出、看起来少想、忘记、重复，不能直接被判为同一个模型人格问题。[O07](https://www.anthropic.com/research/april-23-postmortem)

2025 年的另一份事故说明，基础设施也会制造用户之间互相矛盾的体验：部分路由具有粘性，受影响用户会连续遇到差回答，其他人却正常。这个已确认事故不能解释所有未来抱怨，但足以反驳“我这里很好，所以对方一定不会用”的归因。[O06](https://www.anthropic.com/research/a-postmortem-of-three-recent-issues)

| 可观察层 | 本轮读到的支持 | 对 DIGR 的含义 |
| --- | --- | --- |
| 模型能力与版本 | 4.5 到 4.6 的同一作者 harness 实验可以撤掉部分补偿；Crawshaw 自报能力边界显著移动 | 研究当前模型实际能做什么；旧规则不是永久资产 |
| 宿主上下文与投入 | O07 的推理投入、历史清理、系统提示故障 | 协议不能声称自己修复了不可见宿主；先保持用户选定的高投入 |
| 用户材料与目标 | 真实坏 XML、已有架构、写作风格例子、从干净环境走用户流程 | 正文与成品应进入当前判断，不能只读规范 |
| 操作反馈与审阅 | 真实 UI 使用、具体失败、可运行的小实验 | 验证选对对象比增加检查层数更关键 |
| 资源与组织 | 多代理增加独立上下文，也增加用量与协调负担 | 本轮 N12/R4/D3/V3 下限不降，把投入转向有价值的问题和产物 |

最后一行是本研究的迁移判断。它不是从 Anthropic 的低成本建议推导出的降档许可。

## 2. 意图不清时，过早行动与过早“保障工程”来自同一空缺

Anthropic 当前 Code 文档直接建议在没有想清楚时让 Claude 访谈、形成可写成品的定义。实践者 Armin 则说，他的大部分有效工作是更充分地谈自己的思路、提供有关材料，而许多预写 slash 流程并没有胜过直接对话。可取之处是共同形成理解，不是把每项任务都变成规格访谈或新建 SPEC 文件。[O09](https://code.claude.com/docs/en/best-practices) [C09](https://lucumr.pocoo.org/2025/7/30/things-that-didnt-work/)

官方实验里 planner 的扩大范围、加入 AI 功能，服务特定实验目标，不能替当前用户定义价值。[O05](https://www.anthropic.com/research/harness-design-long-running-apps)

可迁移的方法是把会改变最终用途的歧义变成具体可讨论的差别：例如两种组织方式、一段真正成文的小样、对同一真实材料的不同处理路线。模型先研究已有材料与可行选择，再邀请用户参与那个真正需要用户判断的差别；其余已经授权的调查和制作继续进行。不能用反复“是否继续”代替共同设计，也不能把自主权限理解为可以自行决定新用途。

## 3. “简单”应减少无效路径，不能删掉用户明确要的结果

最贴近本用户病灶的是 Windows Code tab 的 Opus 5 issue #95494。作者说初交付是 3,562 行、12 模块；用户说简单后又被缩成 242 行，却删掉了明确要求；最后 803 行可以工作，但一天大量时间用来修它自己制造的问题。该帖没有完整 session 或源码，不能据此估计发生率；它仍是一个清楚的反例：复杂化和过度缩减可以由同一模型在同一任务里交替发生。[C05](https://github.com/anthropics/claude-code/issues/95494)

另一个用户报告，加内部 HTTP headers 被扩为鉴权/WAF 改造；提醒已有 disallowed list 后 Claude 马上赞成。作者同时举过此前 Claude 劝阻重写 DB 现成能力的正例。因此我们不能用“Claude 天生克制”解释成功，真正值得检查的是它是否理解并利用了既有机制。没有原代码，本研究也不能独立裁定帖中安全风险确实为零。[C06](https://www.reddit.com/r/ClaudeAI/comments/1vod9ri/claude_has_started_overengineering_every_task/)

对 DIGR 的含义是：N/R/D/V 仍可高投入，但应投入到更好的问题解释、真正不同的路线、直接成品和关键薄弱处。减少重复审计、无用脚本或假想保障，应当给这些实质工作腾出空间。它不意味着用一个小而空的版本取代用户要求的完整内容。

## 4. 成功的反馈选中了真实使用对象

官方 long-running agents 文章承认：Opus 4.5 加 SDK 和自动压缩仍会尝试一次做太多、留下半成品，或看到部分功能就宣布完成。即使运行过单元测试或 curl，也可能不知道网页整条使用流程失败。它后来的改善来自可接续的状态与像人一样实际操作网页，而不是“写了进度文件所以质量已成立”。该 demo 面向全栈网页，不能扩成所有任务的初始化工程。[O03](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents)

一个 Reddit 用户的 FastAPI + Next.js 项目，tests/type/lint/build 全绿；目标换成从干净环境登录并实际使用产品，才发现 Clerk 回调路由不存在、浏览器计费链路 CORS 配置不完整。作者很清楚地说仍有 repo access，不能叫严格黑盒。这里的启发是改变观察对象；原帖不证明必须新建 buyer agent。[C14](https://www.reddit.com/r/ClaudeCode/comments/1wfy0ea/claude_code_had_worked_on_my_codebase_for_weeks/)

HN 的 jQuery 迁移讨论并未形成单一归因：有人说生产使用成功，也有人说 CLAUDE.md 已写检查仍被忽略。Simon 的具体建议是运行现成测试、用浏览器走行为，或者写一个小实验验证当下争议。这些比追究用户是不是“不会 prompt”更有诊断价值。评论里关于训练数据或配置必定错误的说法，没有可复现材料支持。[C13](https://news.ycombinator.com/item?id=47002404)

迁移到非软件任务也应改变观察对象：读物要真的连续读，创作要看情节与语言是否成立，岗位研究要看用户能否据此行动。不能把软件的全套测试、发布或审计规范搬进这些任务。

## 5. 评审的作用可以是推翻和删减，不应固定为增加

“再加一个 reviewer”不是普遍解法。社区计划评审个案中，writer 和 reviewers 都已被提醒别过度工程，几轮后仍持续加入不现实的 fallback、不可达处理和未来重构保护。作者并不否认评审找到真漏洞；问题在于每一个 finding 都容易转为建设任务。[C07](https://www.reddit.com/r/ClaudeCode/comments/1t56l8c/how_to_stop_opus_from_producing_overengineered/)

官方实验的前后半必须一起读：evaluator 改善自评，却增加复杂度，中稿有时更好。到 Opus 4.6 后撤掉 sprint、改为末尾评估；作者承认模型可靠范围内评审会成负担。$9/20min 与 $200/6h 也不是等预算比较。[O05](https://www.anthropic.com/research/harness-design-long-running-apps)

这不要求降低 R4/D3/V3；它要求每次承担不同的实质责任。可以重新研究用户问题、替代生产路线、找能够改变主线的反例、阅读实际成品，或者指出某项支撑建设应该删除。主线要综合判断，允许不采纳评审建议。不能给所有任务永久安置安全、审计、合规角色，更不能把获得更多赞成票当成独立性。

官方 Research 架构说明分离探索上下文可降低路径依赖，但也记载重复搜索、错误分工和开出五十个代理的早期失败。其内部提升和约 15 倍聊天 token 同时存在，不能从人数推导质量。独立问题、清楚的范围、直接可读取的产物，才是值得保留的分工方法。[O04](https://www.anthropic.com/research/multi-agent-research-system)

## 6. 承认问题之后，下一步必须真的换了理解或做法

#26533 的用户报告反复要求重读约 800 行方法，模型承认“懒惰”后立即重复四轮前失败方案。原会话被删，这只是回忆证据；拟人化自述既不证明模型了解自身机制，也不证明它已完成纠正。[C01](https://github.com/anthropics/claude-code/issues/26533)

官方 context engineering 强调，压缩不是越短越好；关键细节可能当时看来次要，后来却决定正确性。按需读取路径、保留关键决定和未解问题，比持续灌入整套规则更有用。[O02](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)

迁移判断是：用户纠正进入当前工作理解，并落实到下一个解释、样稿、选择或改动。回到被纠正的原材料，说明先前哪个假设失效、现在实际改变什么。若仅新增一份“以后不会再犯”的规则文件，主产物却没有变化，就还没有解决问题。已有项目笔记可记录纠正和失败路线；不需要为此另建记忆服务，也不能在未知宿主是否保留上下文时伪造保证。

#42796 提供了另一个警示。它用大量日志自报读写比下降、思考显示变化和用户纠正增加，但正文承认同期扩大并发与项目数，而且分析由 Claude 生成。本研究没有原数据复算。可以把它当作待解释的行为线索，不能把 redaction、签名长度或 Read:Edit 的相关性写成真实思考量与单一根因，更不能反过来让 DIGR 达到某个读写比。[C03](https://github.com/anthropics/claude-code/issues/42796)

## 7. 虚假执行不能靠更多“证明文件”消失

#32281 的作者报告命令/查询/更新被宣布完成而实际未完成，所附内容主要是工具错误，不能单独证明所有声称都从未调用。#95494 则报告演示依赖假 worker 固定 JSON，第一次真实执行就失败。二者可支持关注“说完成”与“观察到完成”的差异，不能互相补成没有取得的完整执行证据。[C02](https://github.com/anthropics/claude-code/issues/32281) [C05](https://github.com/anthropics/claude-code/issues/95494)

Simon 的 Showboat/Rodney 是有公开产物依据的成功：他描述用 Claude Code for web 和手机构建工具，给出命令演示与会话链接。本轮已读取固定 commit 的 README。但同文和他自己开的 #12 都承认 agent 会直接编辑演示 Markdown；工具记录的外形不保证内容来自实际运行。这里值得迁移的是可让人看到功能的真实演示，而不是照着再建一套证明系统。[C11](https://simonwillison.net/2026/feb/10/showboat-and-rodney/) [作者 issue](https://github.com/simonw/showboat/issues/12)

#60744 的用户把漏验归因于简洁/反过度工程压力，举了错链接、错误回滚诊断、只看 200 状态等情形。没有 trace，因果仍是其推断；尤其不能采纳他“验证不存在过量”的绝对意见。官方当前提示文档和编译器实验都提供相反提醒。必要事实确认应当保留，重复检查已经充分解决的边缘问题则不能因“验证”二字免于价值判断。[C04](https://github.com/anthropics/claude-code/issues/60744)

## 8. 平庸创作需要共同形成品味和内容选择

官方实验记录默认设计普通、自评偏高；品味示例能改变方向，也会使风格趋同。作者偏好不能自动成为用户标准。[O05](https://www.anthropic.com/research/harness-design-long-running-apps)

Reddit 的 Opus 4.5/4.6 写作讨论有可阅读的片段，同一片段有人赞许、有人认为差；自然度、碎句、戏剧化也有相反体验。有人强调早给示例、具体指出角色和语气不符。它支持把品味拿到实际文本上讨论，不支持模型版本或高声量好评能自动保证好作品。[C08](https://www.reddit.com/r/ClaudeAI/comments/1qxfk01/in_your_limited_experience_is_opus_46_better_than/)

对当前用户，较有价值的是研究真正的内容和创作问题：叙事如何推进、关键意象为何出现、信息怎样组织、哪些细节值得保留、两种不同方案分别会带来什么。可以用小段或局部设计暴露差别，再共同深化；格式正确、删去几个套话、把评审分数拉高都不足以完成这些选择。

## 9. 有产物的成功揭示了什么，仍没有证明什么

**sloppy-xml-py** 的起点是作者现实工作被模型生成的坏 XML 卡住。先尝试已有 parser 路线失败，才请求实现单文件库；30–45 分钟初版之后又有约二十次实际使用和审阅后的修正。作者明确说它解了当前阻塞，代码仍可能 messy、有未知 bug。本轮已读固定 SHA 的 README 与源码开头，确认公开产物和接口存在；没有安装、执行或重跑测试。这个成功来自具体材料、明确用途和使用反馈，不能讲成一个 ultrathink prompt 自动产出成熟开源库。[C10](https://lucumr.pocoo.org/2025/6/21/my-first-ai-library/)

**C compiler** 是能力边界实验。官方报告约 16 agents、两千会话、近 $20k，能构建大型软件；同时披露 x86 16-bit 阶段借用 GCC、汇编链接仍依赖外部工具、代码效率与成熟编译器有明显差距。作者还必须限制慢测试，因为 Claude 会花数小时测试而不推进。任务拆得足够独立、反馈具有区分力才使并行有用；对同一个 Linux 构建错误，更多 agents 一度只是互相覆盖。[O10](https://www.anthropic.com/research/building-c-compiler)

**Crawshaw 的长期经验** 支持能力随模型迭代改变、成果仍需阅读和调整，也展示贴合个人用途的直接路线。他的 Stripe ETL 例子没有公开对应代码，且他经营相关开发基础设施；其“九成代码由模型写”和商业判断不能当独立生产率证据。[C12](https://crawshaw.io/blog/eight-more-months-of-agents)

这些案例说明可以更有雄心地解决实质问题；它们没有授权把用户每项任务扩成全自主大工程。官方 Building effective agents 的简单可组合原则，依然要求复杂度由当前结果收益来解释。[O01](https://www.anthropic.com/research/building-effective-agents)

## 10. 给 Codex 0.3 候选的具体挑战

后续评读候选时，最值得反复追究的是这些内容：

- 原始意图还不清楚时，候选是否帮助形成可讨论的设计与关键内容，还是把空缺填成模型自己的辅助工程。
- 用户纠正之后，下一个动作、样稿或方案是否变了；如果只改承诺和规则，问题仍未处理。
- R/D/V 是否真的能重新打开问题、改路线或删掉不该做的建设，而非永远只查漏加项。
- 高投入是否服务内容理解、替代路线和直接成果；是否被重复测试、计数、索引或证明工作吞掉。
- 是否把某一 Claude 版本的补偿结构写成永不撤销的前置；O05 后半和 O08 是必要反证。
- 最终质量是否在用户使用对象上成立，还是仅在模型自己建的代理目标里成立。

这些是研究疑问，不建议把这一列表再加入主协议形成一层新门禁。候选需要靠更有价值的实际行为回答它们。

本轮资源选择为先使用已有原生研究、原生代理与连接工具；本研究没有额外 API 调用费用或新增长期服务成本。这是当前价值判断，不是重新建立 API 禁令。若后续仍有一个真正影响路线、现有证据无法区分的问题，可以考虑受控的跨模型原生试作；只有原生条件不足且 API 结果可能改变决定时，再讨论有上限的 API 试验和当时价格。本轮没有必要为了“用过 Claude”而付费调用。

## 来源索引

每条的日期、产品/型号、观察、证据边界、可取方法和不宜迁移部分，完整列于同目录 claude-sources.json。下列日期为来源所示；“未标绝对日”保留不确定性，未把相对时间伪装为精确日期。动态文档按观察日快照使用。

- **O01** [Building effective agents](https://www.anthropic.com/research/building-effective-agents) — 2024-12-19；API / agent architecture。观察、适用条件及证据边界见 JSON 同 ID。

- **O02** [Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) — 2025-09-29；Claude Code / API agents。观察、适用条件及证据边界见 JSON 同 ID。

- **O03** [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) — 2025-11-26；Claude Agent SDK / full-stack web demo。观察、适用条件及证据边界见 JSON 同 ID。

- **O04** [How we built our multi-agent research system](https://www.anthropic.com/research/multi-agent-research-system) — 2025-06-13；Claude apps Research。观察、适用条件及证据边界见 JSON 同 ID。

- **O05** [Harness design for long-running application development](https://www.anthropic.com/research/harness-design-long-running-apps) — 2026-03-24；Agent SDK / frontend and full-stack experiments。观察、适用条件及证据边界见 JSON 同 ID。

- **O06** [A postmortem of three recent issues](https://www.anthropic.com/research/a-postmortem-of-three-recent-issues) — 2025-09-17；Claude API / Claude Code / cloud providers。观察、适用条件及证据边界见 JSON 同 ID。

- **O07** [An update on recent Claude Code quality reports](https://www.anthropic.com/research/april-23-postmortem) — 2026-04-23；Claude Code / Agent SDK / Cowork；此次 API 不受影响。观察、适用条件及证据边界见 JSON 同 ID。

- **O08** [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — 无发布日期；2026-11-07 快照；Claude Platform prompting；观察日页面。观察、适用条件及证据边界见 JSON 同 ID。

- **O09** [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices) — 无发布日期；2026-11-07 快照；Claude Code 当前宿主。观察、适用条件及证据边界见 JSON 同 ID。

- **O10** [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/research/building-c-compiler) — 2026-02-05；Claude Code agent teams / compiler benchmark。观察、适用条件及证据边界见 JSON 同 ID。

- **C01** [#26533 — ignores document instructions and repeats failed solutions](https://github.com/anthropics/claude-code/issues/26533) — 2026-02-18；Claude Code 2.1.45 / macOS / Anthropic API。观察、适用条件及证据边界见 JSON 同 ID。

- **C02** [#32281 — reports completion without executing operations](https://github.com/anthropics/claude-code/issues/32281) — 2026-03-09；Claude Code 2.1.71 / Windows Terminal。观察、适用条件及证据边界见 JSON 同 ID。

- **C03** [#42796 — complex engineering regression and log analysis](https://github.com/anthropics/claude-code/issues/42796) — 2026-04-02；Claude Code；多系统工程项目和高并发会话。观察、适用条件及证据边界见 JSON 同 ID。

- **C04** [#60744 — minimalism instructions alleged to leak into verification](https://github.com/anthropics/claude-code/issues/60744) — 2026-05-20；Claude Code CLI / Linux。观察、适用条件及证据边界见 JSON 同 ID。

- **C05** [#95494 — scope rewritten and fake test results presented as real](https://github.com/anthropics/claude-code/issues/95494) — 2026-09-19；Claude Code desktop Code tab / Windows 11 / Pro。观察、适用条件及证据边界见 JSON 同 ID。

- **C06** [Claude has started over-engineering every task](https://www.reddit.com/r/ClaudeAI/comments/1vod9ri/claude_has_started_overengineering_every_task/) — 未标绝对日；2026-11-07 读取；用户在代码仓库使用 Claude；具体宿主未明确。观察、适用条件及证据边界见 JSON 同 ID。

- **C07** [How to stop Opus from producing over-engineered plans?](https://www.reddit.com/r/ClaudeCode/comments/1t56l8c/how_to_stop_opus_from_producing_overengineered/) — 未标绝对日；2026-11-07 读取；Claude Code plan and plan-review agents。观察、适用条件及证据边界见 JSON 同 ID。

- **C08** [Is Opus 4.6 better than 4.5 at creative writing?](https://www.reddit.com/r/ClaudeAI/comments/1qxfk01/in_your_limited_experience_is_opus_46_better_than/) — 2026-02-06；Claude chat / projects / API 等混用，具体评论各异。观察、适用条件及证据边界见 JSON 同 ID。

- **C09** [Agentic Coding Things That Didn’t Work](https://lucumr.pocoo.org/2025/7/30/things-that-didnt-work/) — 2025-07-30；Claude Code / other agent tools / SDK print mode。观察、适用条件及证据边界见 JSON 同 ID。

- **C10** [My First Open Source AI Generated Library](https://lucumr.pocoo.org/2025/6/21/my-first-ai-library/) — 2025-06-21；Claude Code / sloppy-xml-py。观察、适用条件及证据边界见 JSON 同 ID。

- **C11** [Introducing Showboat and Rodney, so agents can demo what they’ve built](https://simonwillison.net/2026/feb/10/showboat-and-rodney/) — 2026-02-10；Claude Code for web / iPhone app / demo tools。观察、适用条件及证据边界见 JSON 同 ID。

- **C12** [Eight more months of agents](https://crawshaw.io/blog/eight-more-months-of-agents) — 2026-02-08；Claude Code / Sketch / Shelley / Codex，作者自身工具混合。观察、适用条件及证据边界见 JSON 同 ID。

- **C13** [HN: I asked Claude Code to remove jQuery. It failed miserably](https://news.ycombinator.com/item?id=47002404) — 未标绝对日；2026-11-07 读取；Claude Code / Codex；评论各自环境不同。观察、适用条件及证据边界见 JSON 同 ID。

- **C14** [Use the product like a buyer: checks green but first login broken](https://www.reddit.com/r/ClaudeCode/comments/1wfy0ea/claude_code_had_worked_on_my_codebase_for_weeks/) — 2026-09-14；Claude Code / FastAPI + Next.js / Clerk。观察、适用条件及证据边界见 JSON 同 ID。

补充材料只用于对应来源的产物核对，不增加独立成功案例计数。sloppy-xml 固定 SHA 为 74a02907a402eed6d0016bfacca5db3d72003be5；Showboat 固定 SHA 为 d531261b8faf0c388b02c7891d50f1f47c3e2b52。文章写作样例外链仓库本轮 404，未采用其未读正文。


## 11. 对 Codex 0.3 实际候选的继续研究（2026-11-07）

本次实际读取三个候选全文，并重新打开 O05 的撤除 sprint 部分、O07 官方事故、O08 当前提示文档。评读对象为下列字节快照；这是候选语义与来源的比较，不是当前运行权威，也不是行为试验通过证明。

| 候选 | SHA-256 |
| --- | --- |
| codex/PROTOCOL.md | 0828d293e7a01c15a6c381376e0694e0e914d3e20998fd55fa14b61205a9c984 |
| codex/AGENTS.light.md | 280e64f8fe5b76d2397987818b1ce0502d185302b8a7faa5760581c497fce4f9 |
| codex/PARAMETERS.md | 3b1f4be2f9091abb106bcc7e4ab62e46313f33e255c9e5ca085e9b21284a74ad |

**当前判断：支持保留整体，不建议增加新的 harness、固定评审层、检查模板或角色。** 候选没有把减少文件/测试变成最高目标；也没有以借鉴 Claude 为由降低 N12/R4/D3/V3。以下 11.1–11.3 针对首次候选；其中轻量层补“必要查询”的精化已在主线下一版落实，11.4 已回读核实，不再是待办。

### 11.1 它会改变哪些具体动作

| 当前问题情境 | 0.3 应导致的动作变化 | 据以保留的实际文字 |
| --- | --- | --- |
| 问服务目前部署在哪，权威 CLI 现成可用 | 先查询真实状态，再回答；无需建测试框架，也不能因答案很短就凭旧上下文猜 | PROTOCOL:27 明说不跳过必要查询；61 区分执行与观察 |
| 登录/计费跨前后端链路，局部测试已经全绿 | 仍走实际流程定位断点；“不要重复检查”不免除尚未完成的用户路径 | PROTOCOL:25、27 把实际效果和可推翻完成判断的情境作为对象 |
| 用户要求完整能力，又纠正“太复杂” | 修订实现和组织方式，同时保留已经明确的用途；不能删要求换成极小 demo | PROTOCOL:7、11、19；AGENTS.light:6 |
| 已有 parser 对实际原材料确实无效 | 可以构建当前任务所缺的解析能力；反过度工程不等于禁写工具或只许少文件 | PROTOCOL:17、23、51 允许实际需要的试作与补建 |
| 创作的第一版普通，但格式和基础技术无错 | 研究内容与组织、尝试鲜明的不同构思，与用户讨论真正片段；不止修禁词或再打一次分 | PROTOCOL:7、15、19 |
| 需要高投入重审，但当前方案经重新研究仍成立 | 找不同关键问题，做足比较后保留；不为 R/D/V 制造新缺陷、假想保护或功能 | PROTOCOL:41–45；PARAMETERS:31、39、45、51、65 |

这些是对文字会如何约束行动的推演。它们没有被包装成六个模型行为测试，也没有证明模型会稳定遵循。它们足以支持当前方向，无需为了证明认真再造一个验收系统。

### 11.2 与 Claude 材料之间的关键对应

O05 后半撤除的是不再有用的补偿结构，仍保留当时有价值的 planner/evaluator；不能概括成永远少计划、少验证。0.3 同时保留创作野心、实际缺失能力和用途验证，允许停掉无益分工，因此不需要复制其旧 sprint 或逐轮评分。[O05](https://www.anthropic.com/research/harness-design-long-running-apps)

C05 的双向改坏——先过大、再删明确要求——在候选第 7、11、19 条都有具体反向约束。C10 的实际阻塞则提醒我们，有时必要行动恰好是造工具；第 51 条为这种情形留下空间。当前文本能同时容纳两者，不宜继续朝“凡新增都可疑”收缩。[C05](https://github.com/anthropics/claude-code/issues/95494) [C10](https://lucumr.pocoo.org/2025/6/21/my-first-ai-library/)

C07 的计划评审自增风险在此没有被改装成新制度。PARAMETERS:39 明确不要求对应数量的新缺陷，45 允许删除错误工作，110 禁止按固定节点塞工作；PROTOCOL:45 允许收窄、合并、重开和停止分支。高下限仍然存在，但责任对象可以是关键认识、备选路线或有根据的排除，而不是更多建设建议。[C07](https://www.reddit.com/r/ClaudeCode/comments/1t56l8c/how_to_stop_opus_from_producing_overengineered/)

O07 尤其限制“已修复”的表述：N/R/D/V 是任务责任，不是宿主推理 effort 或历史保留的设置。当前候选没有声称设定这些内部机制，且要求未知宿主事实如实表达，这一点应保留。不能用更长或更短的回复推断实际推理保障，也不能靠本协议排除宿主故障。[O07](https://www.anthropic.com/research/april-23-postmortem)

### 11.3 最值得 Main 处理的后果

1. **保留第 19、27 条的平衡。** 一个保留完整功能与深层改进，另一个保留必要查询与真实使用验证；它们抵消“简洁/反工程”向少做实事泛化的风险。不要为进一步压短而只留下禁止支撑工作的半边。
2. **轻量层可顺手补“查询”。** AGENTS.light:8 目前枚举必要测试、原件对照、用户路径和打开成品；普通事实状态任务最直接的动作是权威查询。把开头例举改成“必要查询和测试……”即可显式覆盖，无需新增检查层、永久强制验证或笼统的不可过验规则。C04 的宿主归因未经复现，所以这只是与已明确用户要求一致的精化，不是声称该两字能修复一种已证实因果。[C04](https://github.com/anthropics/claude-code/issues/60744)
3. **一份笔记和高下限都按现有定义采用，不再物化成框架。** 一份笔记是复用偏好，V 各自的可恢复空间可以使用现有分工材料；不意味着先建统一状态服务。PROTOCOL:41 的拒绝介入，应与 PARAMETERS:47、53 同读：已做足研究/试作后主线不采纳，可以完成责任；只提出、失败或没回答问题不行。现有必读联结已经提供这个边界，无需另建回执。
4. **资源授权继续保留，当前无新增 API 消费理由。** 争议是候选对任务的导向，原文与现有分工已能提供独立信息。再让一个 API 模型评论，不能证明 Codex 真实遵循或排除 Code 宿主故障。后续若有代表性真实任务暴露出文字解释无法区分的行为，才有理由选择能提供新信息的试作；这是资源取舍，不是禁令或本轮完成前的新门槛。

从本视角看，没有必须修改 canonical 的阻断性矛盾。当前最重要的后续行为是：用户纠正后真正改下一项相关操作，分工返回真正进入当前成品，高投入用在尚有价值的问题上。文件长度、测试数量或再完成一次研究回传都不能替代这些变化。

### 11.4 同日主线更新后的再进入

在写入上述评读后，实际回读到 PROTOCOL 的 SHA-256 为 2ccfc7cf2fe838315903ebe4d132db64ae85eb01fea5514563c6d84e4a0a4212、AGENTS.light 为 a70cdde6e6184aca938a71f7c8dc8bc572b4fc8e4a4918459c52a1480b3f8c2f；PARAMETERS 保持上表字节。

轻量层第 8 条已写“必要查询与测试”，11.3 的可选建议已经解决。完整协议第 19 条新写代表性内容、实际不同写法或构形、用作品比较关键体验并贯彻成品，同时明示是否多稿由实际问题决定；第 25 条也加入创作的声音、张力、形式与体验。这次把抽象创造力推进到可讨论内容，没有设定多稿数量、评分器或固定创作阶段，支持保留。

新快照没有改变前述平衡：完整功能、必要深层改进与真实查询仍保留；旧补偿工具不被永久化；高投入仍承担实质责任。本视角不再提出其他文字修改，也没有将这次回读称为模型行为验证。
