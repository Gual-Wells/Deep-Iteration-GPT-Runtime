# DIGR Codex 附属项目入口

这里登记与 DIGR Codex 共存、各有用途的三个附属项目。按要做的动作进入，接续时回到该项目的原数据；目录不保存个人进度，不判断宿主是否已经具备某种能力，也不负责安装或依赖解析。

[index.json](index.json) 仅提供项目 ID、名称和仓库相对入口。发行版本以项目已有的发行材料为准；数据格式、历史协议 pin、产物身份与私人数据 revision 各自表达。登记为附属不意味着彼此成为运行依赖。

| 项目 | 立项目的与责任 | 实际入口 |
|---|---|---|
| DIGR Voice Companion | 在英语语音陪练中帮助构思、接话、创作与继续交流；提供本机短核、完整技能及手机自足材料。 | [使用说明](../voice/README.md)、[手机短核](../voice/MOBILE.txt)、[完整手机材料](../voice/ChatGPT-Voice-Companion.md)、[开始一句话](../voice/START.txt) |
| DIGR Paper Knowledge | 在 Codex 读论文时保留来源、论文局部用法、真实选择、已讲内容和有范围的学习证据，并按实际位置接续。当前数据格式为 schema 2；这不是独立产品 2.0。 | [技能与接续流程](../.agents/skills/digr-paper-knowledge/SKILL.md)、[数据/命令契约](../.agents/skills/digr-paper-knowledge/references/data-contract.md)、[CLI](../tools/codex_knowledge.py) |
| English-Spoken-Preprint | 在 Codex 中由真实独立人物及伴生内心生成场景日志，制作供手机顺畅多角色场景演绎、用户跟听的预印本；台前与幕后分别交付。 | [项目与工作流](../spoken-preprint/README.md)、[统一 CLI 的 preprint 入口](../tools/codex.py)、[具体命令](../tools/codex_preprint.py) |

## Voice Companion：练习与导出分别进入

- **语音陪练**需要宿主确实提供 Voice，或用户明确选择英语陪练。文本中的开练选择不证明麦克风已开启。手机使用自足短核/完整材料，不依赖本机技能目录；完整技能与示例可增强帮助。实际启用条件见项目说明。
- **重新导出**需要本仓库源文件及 Python；现有 `python -B tools/codex.py voice export mobile --out <new-file>` 可创建手机短核，`project` 可创建完整单文件。输出不覆盖原件，也不代表已安装或已观察到 Voice 效果。
- **接续**沿当前交流内容继续；需要跨聊天保留话题时，由用户携带实际材料。目录不创建第二份会话状态，也不从其它项目推断用户经历。
- **关系**：普通陪练不启动 DIGR 参数、计时或正式返回；不依赖 Paper Knowledge 或 ESP。对 ESP，它是可选的教练/演绎适配，不是台前包的必装引擎。自己的发行身份与历史适配依据见 [Voice 清单](../voice/manifest.json)。

## Paper Knowledge：从私人绑定读真实卡片

- **必要条件**：可读的实际来源、负责语义分析的原生宿主、Python 与明确的私人池绑定。PDF 摄入另需 `pypdf`；文本池的文件操作不因此需要 PDF 依赖。CLI 不调用模型，也不替模型判断论文含义。
- **原数据权威**是绑定池中的 `pool.json`。`CURRENT.md` 可作导航；本目录、历史摘要和已安装技能不替代池内冻结问题、实际选择、游标或证据。私人绑定的发现顺序见技能，公共目录不存真实私人位置或记录。
- **接续**先按显式池位置或宿主已有绑定找到实际 CLI/池，读派生卡并检查来源；再按需使用 `resume`、`search`、`show-use` 读取有范围的内容。源码 checkout 的命令为：

```text
python -B tools/codex.py knowledge --pool <private-pool> card
python -B tools/codex.py knowledge --pool <private-pool> check-sources
```

已绑定的独立 CLI 也支持 `python -B <bound-cli> --pool <private-pool> card`。占位符应替换为本次实际私人绑定。找不到绑定或来源时，指出所缺材料；不从目录或记忆重建个人学习状态。

- **关系**：这是独立的论文学习工作流，不要求安装 Voice 或 ESP。它给 ESP 提供来源、局部用法与证据分离的设计参考；论文问卷和私人池不是 ESP 的代码/数据依赖。已讲、已记录证据和长期掌握分别对待，不能因为跨项目检索到相同词或 ID 就迁移学习结论。
- **协议**：池内旧 pin 记录历史来源，不代替新显式 DIGR 消息的真实获取。普通 CLI 文件操作与正式 DIGR 执行分别说明。

## English-Spoken-Preprint：原生生成，手机多角色跟听

| 动作 | 必要条件与入口 | 数据权威与可选关系 |
|---|---|---|
| 原生生成、续写及出版准备 | 可用的原生独立上下文、受控人物视角、文件操作及项目工具；从 `python -B tools/codex.py preprint --help` 与项目说明进入。显式 DIGR 任务使用实际取得的相应 profile。 | 原世界和真实提交记录保存在本册私人工作区；台前人物 M 与伴生 D 是故事身份，不替代协议责任。Voice/论文池均非强依赖。 |
| 手机多角色场景演绎与跟听 | 自足台前包、能实际读取它的宿主；语音演绎另需真实 Voice。按预印本人物和场景顺畅演绎，用户跟听。 | 台前包是公开言行的投影，足以离开源码库使用；不要求手机安装 Codex、Python、原生独立代理、Voice Companion 或私人知识池。Voice Companion 可选。 |
| 语言与跨册回看 | 本册实际表达/用法和可访问的旧册材料；需要学习判断时保留其具体来源、范围与观察。 | 语言标注与学习证据分别对待。历史表达出现过、相同 ID、听过或一本书完成均不表示掌握。Paper Knowledge 的证据设计可参考，私人论文数据不自动导入。 |

原 `preprint.json` 及其实际事件仍是原生制作的世界/角色权威；完整世界、伴生内心和幕后议会材料留在相应私人工作区，手机仅带台前包。ESP 不设置用户接手、插入或回传后真实 D 接续的路径。发行说明和工具命令说明各自能力，目录中的链接不代表产物已经生成、宿主已经加载或真实手机路径已经验证。

## 核心与附属的边界

本目录不会修改、替换或覆盖根 [stable profile](../manifest.json) 与其[启动协议](../entry/STARTUP.md)，也不会另设 DIGR 执行路由。显式调用沿用户已选择的通道取得协议；Codex 入口仍为 [codex/manifest.json](../codex/manifest.json)。附属的说明、历史 pin 或手机材料不取得核心执行权威。

以下内容有各自职责，不登记成附属项目：

- [local-personalization](../local-personalization/)：宿主路由/传输适配，负责将请求交给相应协议入口。
- [时间—工作图](../codex/RETURN_VISUAL.md)：核心返回组件，服务实际深执行的交付。
- [评测归档](../docs/research/codex-evaluation-20261109/README.md)：研究产物与证据，不是供用户安装的能力。

公共运行库与私人学习/剧本数据分开维护。进入哪个项目、取得何种材料、实际完成哪个动作，以该动作的真实输入和输出为依据；项目登记、版本号或一张目录表不代替使用验证。
