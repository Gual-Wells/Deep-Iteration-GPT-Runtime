# DIGR for Codex · 0.17.0

0.17将模型策略直接落实[Allot](codex/ALLOT.md)：6.1 Sol/max、6.2 Sol/max为智力主力；明确大批量非智力受控重复劳动才降effort，具体Max不足或真实任务反馈才升级实际模型。`DO：`/`DO:`直接补充当前任务，不重开前置、不重置pin或授权。五档责任、根Stable和旧pin保留。[本版设计](codex/DESIGN_0_17.md)。

0.16把Claude研究成员与正式顾问身份分开：同一原生议会的独立初议、内嵌子议会、屏障与原生再议具有可恢复状态；实际调用使用每exchange锁与共享钱包短事务。新增任务用量返回、原生薄Allot与可导出的Chat同源短/深指令。[确定设计](codex/DESIGN_0_16.md)。单/双冒号、X和旧pin保持各自版本语义。

`DIGR：任务`表示由Codex按既定规格完成执行和工程、不调用Claude、不擅加主观创作；`DIGR：：任务`中凡有实质主观内容判断，都必须请教Claude并落实其有效意见。取材、事实核验、文件组装、工具操作和验证由Codex承担。既有适用指导可直接实现，不为机械步骤制造调用；咨询义务不新增预算。ASCII `:` / `::`等价，五档和X栏仍可置于分隔符前。无前缀补充继承选择，真实用户切换保留原任务；旧pin不静默迁移。[使用说明](codex/HELP.md)。

0.13起的逐提交Split现统一进入DIGR，所有实际Claude通路在每次提交前采用[本机原生Split](codex/SPLIT.md)：Codex研究任务分工、完成必要本机工作，给Claude最小充分的原件和内容问题；工具逐次绑定请求与实际成果，缺少或过期计划不能发送。`consult split --input … --out …`机械附加当前绑定，`call --split-plan …`提交前本机检查。保留Claude内容判断、0.12.1公开增量转播及文本优先取材，旧pin按原版本接续；[完整合成示例](codex/examples/split/README.md)。

0.12起，概念、机制、协议和方案分析以逻辑论证为默认判断基础，论证充分即可直接给结论与完成任务；不把效果实验或后续试用设成默认资格。新版返回第四段采用“论证与适用范围”，保留旧输入兼容。[共同方法](docs/LOGIC_FIRST_ANALYSIS.md)同步进入stable、Codex及本机日常约定。

0.14统一使用`DIGR`：实际采用Sonnet即触发内容协作与相应工程要求，真实整篇论文对象自然接入论文内容驱动。旧C/P拼写兼容，旧pin保留原语义。Light／Less／Default／More／Max控制原生投入，沿实际授权调用外部模型。[协作约定](codex/CONSULT.md)。

本次把当前理解关系、现稿纠正与历史案例证据的方法放进共同核心，并按用途更新论文、知识接续、个人材料、ESP和Voice技能。[全族适用范围](docs/CODEX_FAMILY_UPGRADE_0_11_1.md)区分共同方法与Consult专属权限。五档投入不暗降模型能力或扩张费用授权；裸调用仍为Default=N12/R4/D3/V3/L3/M1。

0.9.0把[X文件交付](codex/DELIVERY.md)接入DIGR、DIGRP：无`X`在当前聊天返回文件；`DIGR(X):…`、`DIGRP(X):…`和`(X=Gmail)`均发送到本机配置的本人Gmail。常规投入参数后可另接一个X栏，例如`DIGRP(N=16,R=4)(X=Gmail):…`。X只控制任务约定的最终文件；没有文件时保留文字答复，不额外造文件。本版仅实现Gmail，个人目标在私有本机配置中，任务建立时解析并保存。

[DIGR 论文0.6.0](paper/PROTOCOL.md)由Sonnet根据原论文和用户用途原生驱动内容与阅读路线，取消预设小m职责及其映射门槛。Codex自主取材、复算、制作和核验，每篇仍有完整M及一份[标准页桌面PDF](paper/PDF_DESIGN.md)。无X的完整论文可直接本地返回；有X时逐篇发送Gmail并读回，所有论文及公共工作完成后才结束父任务。交付工具在外发前保存发送状态，响应不明先对账；真实发送使用已有Gmail原生连接器。[操作技能](.agents/skills/digr-delivery/SKILL.md)随同一不可变pin提供。旧pin和既有Gmail/分卷历史保持原身份。

0.8.3接入社区 Anti-Defensive Writing：有据主张先行，删除重复辩护、叠加保留和自我贬低，必要限定准确落在相关主张。核心规则进入必读PROTOCOL、RETURN及普通任务轻量约定；中英双语完整技能连同不可变来源和MIT许可随分发提供。[来源与接入说明](docs/CODEX_ANTI_DEFENSIVE_UPGRADE.md)。

0.8.2修正现实信息不完备下的决策与未完成任务接续：有据中心判断不被最坏情况替换，普通补充/NEW_TURN不终结DIGR，暂停与终结按真实状态保留，正常结束复用当前RETURN。规则进入所有本通道任务的必读正文与运行工具。[行为、API兼容与验证范围](docs/CODEX_REAL_WORLD_CONTINUITY_UPGRADE.md)。

**让深入研究、竞争方案和实际制作共同推动任务结果。**

0.8 将[默认返回](codex/RETURN.md)纳入必读执行包，并接通实际任务生命周期：显式只读调用仍执行 DIGR；新纠错先改变下一步；已结束任务不能被旧确认或普通讨论复活。0.8.1固定response正文五段与工作表，禁用内嵌页或附件替代；各参与者共用Begin/End文件，收尾按run并集统计T/t，允许有依据的近似补点。消息、决定、产物和当前返回有可核对入口，记录缺口仍如实保留。[本次接口与兼容说明](docs/CODEX_RESPONSE_CLOCK_UPGRADE.md)；[0.8生命周期说明](docs/CODEX_0_8_UPGRADE.md)。

0.7新增[U0前置任务工程](codex/FOUNDATION.md)：先调查已有材料，把完整结果、处理粒度、依赖、竞争路线和资源去向说清，经问答纠偏与明确决定后再全面执行。前置与正式任务独立预算、独立计时；已确认续做只问重要变化。[本轮研究与实际工作](docs/research/codex-task-foundation-20261109/WORK.md)记录了取舍和验证范围。

[Codex效果实验全量归档](docs/research/codex-evaluation-20261109/README.md)保留了试题、全部产物、D/V研究、公开轨迹和方法更正。原默认配置比较因调用与截断条件不匹配而撤回；局部代码改进及原始观测保留。

DIGR 是一套由模型承担研究、判断与制作的工作协议。它鼓励深入真实材料，发展有内容的候选，认真重开整条路线，并让独立研究产生实际后果。目标是用户能拿来使用的结果：一份有依据的研究、一件完整作品，或经过真实路径验证的修复。

本分支提供 **Codex 0.12.0 实验通道**与配套本地工具。模型选择问题和方法、调用宿主能力、处理返回并交付；Python 工具负责取得仓库原文、取回材料、保存接续位置和记录活动区间。

[附属项目入口](addons/README.md)列出 Voice Companion、Paper Knowledge、[English-Spoken-Preprint](spoken-preprint/README.md) 与 [Personal Context](personal-context/README.md)。ESP 0.2 以目标领域中的困难处理为选材中心，提供原场景与独立双语学习听稿；个人资料附属可提供有来源的最小人物视图，保持可选关系。项目回原数据接续，不互相强绑；独立的[真人参与实训](research/codex-participation/README.md)目前只作设计探索。附属各自版本化，不改根 stable 语义。

## 从你的用途进入

| 你现在要做什么 | 从哪里开始 |
| --- | --- |
| 在普通任务中采用这些交付偏好 | 将 [轻量工作约定](codex/AGENTS.light.md) 合并到适用的 AGENTS 指令；照常提问，不建立 DIGR 参数与计时。 |
| 明确让 Codex 为一个任务投入深研究与独立协作 | 按下节启用 [实验路由](codex/ROUTER.experimental.txt)，再发送显式任务。当前协议入口为 [codex/manifest.json](codex/manifest.json)。 |
| 只想取回材料、整理正在进行的工作或接续一个任务 | 使用下方的本地工具。工作台可直接用于普通任务。 |
| 在英语语音里需要伙伴帮忙接话、构思或共同创作 | 使用独立的 [Voice Companion](voice/README.md)：短常驻核待命，完整技能按需；附可直接上传的自足文件，不启动 DIGR 参数。 |
| 继续使用既有 stable 通道 | 使用根 [manifest.json](manifest.json)、[启动协议](entry/STARTUP.md) 与 [帮助](entry/HELP.md)。根版本保持 **5.0.0-alpha.5**。 |

Codex 与根 stable 分别版本化。选择 Codex 时，按 `codex/` 解释参数、时钟前提和返回；stable 保留自己的执行器与证明语义。

## 在 Codex 中开始

1. 明确选用本实验通道后，将 [ROUTER.experimental.txt](codex/ROUTER.experimental.txt) 放入适用的宿主 AGENTS 指令，**替换已有 DIGR 路由段**，日常偏好独立保留。一个入口只保留一个通道。可用 `python -B tools/codex.py profile export codex-agents --out D:/task/AGENTS-codex.txt` 一次导出薄路由与轻量块，合并时保留其它个人约定；导出不自动安装。
2. 在宿主实际加载该指令的新运行中发送 `DIGR/help`，查看当前仓库版本的调用说明。路由文件与 CLI 都不会自动安装或改写全局配置；已有运行也不能据此视为已经加载新指令。
3. 发送一项真实任务，例如：

```text
DIGR：比较这个项目的两种发布方案，实际验证关键路径，给出可直接使用的方案与依据。
```

每条消息只去开头空白，精确大写 `DIGR` 或精确 `深度迭代` 才命中候选路由。命中后，宿主先真实取得 `codex/codex-host-adaptation` 当前 HEAD 的完整 40 位 SHA，再按同一 SHA 读取 `codex/manifest.json`、`codex/VERSION` 和启动切片，由取得的协议分类和继续加载。帮助与普通讨论不建立深执行；`digr`、`Digr` 不命中。运行中的补充消息若再次命中前缀，仍需实际获取，原任务的执行 pin 保持冻结。

可按用途显式选择投入：

| 调用 | 含义 |
| --- | --- |
| `DIGR：任务` | 无参数深执行，从 N12/R4/D3/V3/L3/M1 补齐。 |
| `DIGR：用Sonnet完整处理论文` | 按实际整篇对象自然接入论文内容驱动；一篇一份完整标准页PDF。 |
| `DIGR(M(2))：任务` | 两条完整独立 Main，各自初始化、研究制作、承担本线责任并收敛，然后比较。 |
| `DIGR(target=60min)：任务` | 软时间目标，模型仍按结果决定是否继续。 |
| `DIGR(min=60min)：任务` | 有效工作硬下限，需要真实时间证据。 |
| `DIGR(standard)：任务` | 用户主动选择低档：N2/R1/D0/V0/L3/M1，时间0、来源AUTO。 |

时间目标按本次任务补齐，默认软目标；来源默认 REQUIRED。模型可自主上调投入，显式值、用户纠正和真实限制按协议处理。完整调用与冲突规则见 [HELP](codex/HELP.md) 和 [PARAMETERS](codex/PARAMETERS.md)。

### 怎样判断任务确实在推进

初始化应展示本次生效配置、`P_run=版本@完整SHA` 和真实时钟能力。过程中应看到具体问题、材料、所得以及它们怎样改变研究或成品；独立返回与 Main 的处理分别可辨。最终先交结果和入口，再报责任、时间事实与实际限制。色块与身份的完整格式见 [PARAMETERS](codex/PARAMETERS.md)。

| 责任 | 它在任务里意味着什么 |
| --- | --- |
| **N · 推进** | 一项有交付意义的问题，经研究、比较或制作产生实质进展。搜索、打开、记笔记不能各拆成一轮。 |
| **R · 整体重开** | 重新研究完整候选及其路线，认真比较能改变整体判断的解释或方案，落实改变或给出有内容的保留理由。 |
| **D · 竞争性介入** | 独立者找到攻击口、形成强替代并实际研究或试作；Main 回答中心主张并处理后果。 |
| **V · 持续独立领域** | 从研究形成有距离的分域，发展自己的材料、问题与成果，在相关变化后继续研究。 |
| **M · 完整主进度** | 每条 Main 都承担完整的研究、制作与综合责任；M2 的 N/R/D/V 分别履行。 |
| **L3 · 实际隔离** | 真实独立代理、受控输入、分开的模型历史与工具执行循环。共享磁盘仍受任务边界约束。 |

这些是责任约定，质量要看实际内容与使用结果。目录数量、进度标签和参数达到下限都不能替代判断。宿主缺少真实独立代理时，D/V 的 L3 责任保留未满足状态；有价值且不依赖该能力的工作继续。预算、权限和停止要求按 [PERMISSIONS](codex/PERMISSIONS.md) 处理。

## 本地工具：从一份材料开始

需要 **Python 3.10+**，核心运行时只用标准库；[论文增量](paper/DATA.md)的实际PDF几何核验和[论文知识池](.agents/skills/digr-paper-knowledge/SKILL.md)的PDF摄入另需 `pypdf`。桌面PDF排版还使用已定位的Node、浏览器、MathJax及本地字体，具体依赖与命令见论文文件契约。以下是 Windows PowerShell 示例，任务数据放在 D 盘；其它平台按实际任务目录调整路径。在现有本分支 checkout 根目录运行即可。尚无 checkout 时：

```powershell
git clone --branch codex/codex-host-adaptation --single-branch https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime.git D:/CodexStorage/workspaces/digr-runtime
Set-Location D:/CodexStorage/workspaces/digr-runtime
python -B tools/codex.py --help
```

### 取回当前问题和原材料

准备两个 UTF-8 文件：`D:/task/request.txt` 保存真实委托，`D:/task/notes.md` 保存本次要读的文本材料或原有笔记。选择新的工作笔记路径：

```powershell
python -B tools/codex.py workbench init --request D:/task/request.txt --work D:/task/WORK.md
python -B tools/codex.py workbench topics --work D:/task/WORK.md
python -B tools/codex.py workbench focus --work D:/task/WORK.md --topic "研究、竞争解释与方案" --material D:/task/notes.md
```

`init` 保留委托，且不覆盖已有工作台。随后直接编辑同一份 `WORK.md`，留下交付用途、用户纠正、关键发现、当前产物和下一步。`focus` 输出原始目标、适用的纠正与当前问题，以及选中材料的原位置和行号，供模型继续研究；文本片段可写成 `D:/task/notes.md:20-45`。已有笔记也可用 `focus --work 原笔记 --request 原始委托`，无需重排整份文档。

准备独立研究输入时，可从同一笔记选出必要材料：

```powershell
python -B tools/codex.py workbench challenge --kind D --work D:/task/WORK.md --question "哪条替代路线可能改变当前整体方案？实际研究和试作后比较。" --candidate D:/task/current.md
```

这里的 `current.md` 必须是实际已有候选。输出交给宿主中的真实独立代理，委托、返回与 Main 处理由模型负责。`challenge` 只组装输入。更完整的取材、记录和 D/V 用法见 [WORKBENCH](codex/WORKBENCH.md)；PDF/EPUB 按实际阅读工具取页段。

### 联网获取与本地检查各做什么

```powershell
python -B tools/codex.py profile check
python -B tools/codex.py acquire --stage startup --out D:/task/acquired
# 模型读启动切片并判断为EXECUTING后，同一次获取继续：
python -B tools/codex.py acquire --stage execution --continue-from D:/task/acquired --out D:/task/executing
```

`profile check` 校验 checkout 的版本、声明文件、哈希与聚合包，结果范围为 `LOCAL_FILE_INTEGRITY`。

`acquire` 真正联网解析实验分支：直接 REST 同轮核对 Git-ref 与 Branches SHA，然后只读取该 SHA 的文件。成功后，新目录中的 `acquisition.json` 给出版本、SHA、取得的文件与请求观察，`codex/` 中保存实际原文。`startup` 只取得启动所需文件；后续是否读取 help 或完整执行正文由同 pin 启动协议决定。CLI 的 `help` / `execution` stage 是文件获取范围，不会调用模型。

获取失败就保留失败；本地检查不能替代当前仓库获取。不带continue-from的独立重跑会重新解析HEAD；同次获取用continue-from保持原pin。保存的接续目录不能代替一条新前缀消息要求的在线获取。宿主也可使用已经连接的真实 GitHub connector；传输规则见 [实验路由](codex/ROUTER.experimental.txt)。

### 接续长任务与计时

需要接续时，`task/line`保留原委托、每线完整配置、笔记、产物与未处理事项；0.8.1的`visits`让所有参与者在共同文件记Begin/End，收尾取本run的T/t并集。缺口局部保留，可依据可见记录追加近似补点，不要求进程锚；旧pin仍用自己的`clock`口径。

完整JSON、同pin续读、独立输入、参数修订和恢复操作见[工作工具手册](codex/WORKBENCH.md)。第一次使用只需上面的普通笔记路径，按任务需要再采用这些能力。已有独立工具安装时，可从 CODEX_HOME/digr-codex/toolchain.json 找到绝对CLI入口，从其它项目直接调用，不需把协议复制进项目。

### 其它按需工具

| 命令 | 用途 |
| --- | --- |
| `python -B tools/codex.py profile instructions light` | 输出轻量指令文本，供人工合并；不安装。 |
| `python -B tools/codex.py experience --help` | 保存明确选入的经验片段及出处；后续查看来源位置是否变化。不会自动写入全局 Memory。 |
| `python -B tools/codex.py permissions --help` | 根据实际供给的任务授权、能力与费用事实给行动建议；不执行操作或改变宿主权限。 |

统一 CLI **不调用模型、不启动代理、不认证参数责任或作品质量**。原有 `tools/codex_profile.py`、`tools/codex_workbench.py` 和 `tools/codex_experience.py` 仍可用。

## 协议原文与仓库维护

Codex 的当前执行正文是 [PROTOCOL](codex/PROTOCOL.md)、[CHARACTER](codex/CHARACTER.md)、[PARAMETERS](codex/PARAMETERS.md)、[COLLABORATION](codex/COLLABORATION.md) 和 [PERMISSIONS](codex/PERMISSIONS.md)。执行时按同一不可变 pin 取得全部正文，也可验证后读取 manifest 声明的完整聚合包；[WORKBENCH](codex/WORKBENCH.md) 按需使用。

架构与迁移选择见 [Codex适配说明](docs/CODEX_ADAPTATION.md)。维护代码时，在安装 `requirements-test.txt` 的测试环境运行；修改Codex正文后先显式重建本地聚合包：

```text
python -B tools/codex.py profile refresh
python -B -X utf8 -m unittest discover -s tests -p "test_*.py"
python -B -X utf8 tests/validate_repo.py
```

源码发布工具 [tools/build_release.py](tools/build_release.py) 同时生成Codex聚合包/散列和根stable分发材料，排除本机私有.cache与Git入口。测试、版本与哈希核查验证相应代码和分发行为；0.6.0 是否持续改善跨任务结果，仍需实际任务、成品与使用观察支持。

Codex 0.12.1 默认流式读取并实时转播Claude公开正文；宿主先完成文本/Markdown、公式及必要图表裁取，避免以整页图批量转移前处理和视觉成本。旧pin维持旧传输；新论文增量为0.5.3。
