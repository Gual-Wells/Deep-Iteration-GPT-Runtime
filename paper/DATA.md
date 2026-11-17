# DIGRP 文件与命令契约 0.4.1

语义来自同 pin 的 [PROTOCOL.md](PROTOCOL.md)。工具不用模型、不派代理、不发邮件，不验证数学证明、真实意图或学习效果。`check` 是所选文件与记录的检查；原生宿主仍须对照论文与成品。

## 取得增量与私人批次

在新原始调用上完成核心在线获取和分类；需要执行时取得同 SHA 全部核心正文，再续取增量：

```text
python -B tools/codex.py paper acquire --continue-from <本轮execution获取目录> --out <新目录>
python -B tools/codex.py paper init --out <私人批次> --p-run <核心version@完整SHA> --authorization <实际授权原文文件> --source-ref <真实用户消息引用> --task-root <父DIGR会话目录>
python -B tools/codex.py paper add --batch <私人批次> --id <论文ID> --title <论文题名> --line M01 --owner <真实主进度作者> --parameters <本篇完整参数JSON>
```

第一条不重新取 HEAD，也不为下一条原始调用取得路由资格。工具核对核心声明、增量 manifest/VERSION 和全部成员散列。无法在线取得当前必需协议时遵守所属路由失败规则，不能把源码开发目录作为新调用的在线凭据。

批次 `batch.json` 只保存 P_run、实际授权引用、冻结X目标、父任务入口与各篇索引。每篇 `papers/<id>/paper.json` 有独立 revision、完整参数、来源、映射、候选、交付、单篇返回和接续游标。每个 M line 与论文 ID 在批次内唯一，不能复用同一条完整主进度的身份掩盖其它篇未承担的责任。

## 逐篇写入

写命令使用 `--expected-revision <当前篇revision> --operation-id <稳定ID>`；重试同一操作和内容用同一ID，不会重复写入。改变内容须新ID。revision冲突先重读本篇并处理事实差异，不能强行覆盖。单篇短锁只协调该工作目录；锁残留须先查是否仍有写者，不自动删除活动锁。多篇主进度可以并行，多个m通过实际产物与消息返回，由该篇作者串行维护映射。

```text
python -B tools/codex.py paper source --root <本篇目录> --input <source.json> --expected-revision 0 --operation-id source-journal
python -B tools/codex.py paper map --root <本篇目录> --input <mapping.json> --expected-revision 1 --operation-id first-complete-map
python -B tools/codex.py paper checkpoint --root <本篇目录> --input <cursor.json> --expected-revision 2 --operation-id pause-at-bridge
python -B tools/codex.py paper resume --root <本篇目录>
```

`source.json`：

```json
{"id":"journal-v1","path":"<实际原PDF>","pages":18,"identity":"期刊版本、DOI和获取来源"}
```

源ID不可覆盖，改版用新ID并明确受影响的解释。工具保存真实字节身份，PDF物理页数用当前 Python 中的 `pypdf`核验；普通JSON操作只用标准库。外部未取得的证明依赖，定位在本篇引用它的原页并说明缺失，不能冒充已摄入全文。

`mapping.json` 由原生宿主依据实际原文编写，包含：

| 字段 | 内容 |
| --- | --- |
| `parts` | m1、m4、m2、m3、m5 到真实内容位置的完整映射；0.4允许共用标题或非空标题列表，按实际阅读路线组织；旧pin保留原顺序契约 |
| `assumptions` | 模型假设与范围，各条有id、anchor、location |
| `claims` | 全局主张、真实依据性质basis、依赖的assumptions/chains/experiments ID |
| `chains` | 每条purpose、prerequisites、source_vs_supplement、result、unresolved，与原页及导读章节相连 |
| `experiments` | 图表/设置/指标/结果的解释及原页、导读去处 |
| `coverage` | 实际原文内容块的去处，disposition为explained、context、non_content或unavailable；原生复核确保粒度足以发现真实遗漏 |

各条统一 `anchor={"source":"已注册ID","page":物理页码,"label":"原节/式/图/脚注标签"}`、`location="实际导读标题"`。工具拒绝越界页码、悬空依赖和不存在的标题；字段存在或覆盖表全绿不证明内容真正解释充分。

`cursor.json` 保存 position、next_action、basis 与可选 anchor，保留当前原式、例子和待接的步骤。暂停不是学习缺陷证据，游标不写入另一套能力状态。

`resume/check`以最新未完成的保存步骤为当前动作；后续实际变更保留旧游标的阅读上下文而不继续执行旧指令。它显示当前完整PDF及其已核验消息。已返回篇收到尚待处理的改稿保存步骤时，批次不会误报全部完成。旧0.1候选可按原事实回读，但不自动升级其交付契约。

0.3的新X批次将发送事务放在父任务的共同delivery ledger。发送前保留本篇候选ID、完整PDF及真实目标，只有首次mark-sending授权一项发送；响应不明保持SENDING/UNCERTAIN并先核对，不用事后checkpoint抹去未知。旧0.2游标和Gmail事实仍按原契约读取。

## 本地排成一份标准页PDF

`tools/typeset_paper.cjs`负责本地Markdown的标准页排版，`tools/inspect_paper.py`读取实际写出的PDF，核对页面与文字并生成单页/对页预览。先读同pin的[PDF产品规范](PDF_DESIGN.md)。新默认面向电脑双页阅读；截图是可选技术，旧`render_paper.cjs`/`assemble_paper.py`保留旧任务的工具身份，不作为新0.2分卷或手机长页交付入口。

### 定位已有依赖

在Codex桌面先调用`load_workspace_dependencies`，取得实际Node、Node模块和Python路径；其它宿主用其已经安装的相应运行时。

- Node须能加载`marked`、`playwright`，并定位已安装的Edge/Chrome或实际浏览器可执行文件。工具只在独立本地制作上下文渲染新文档，不附着用户现有浏览器会话。
- 本地MathJax构建及其所需字体必须实际可用；CHTML与SVG的依赖按构建区分，不能缺资源后偷偷联网补齐。
- 传入实际字体文件，记录所用字体和字重。官方开源字体或既有本地字体可复用，不要求系统安装；分发字体时保留相应许可。渲染与最终PDF检查分别确认实际字体/字级，而不只看CSS声明。
- Python实际需有`pypdf`及成品渲染/图片所需依赖；优先使用宿主已提供的运行时。临时profile、字体下载、缓存、样张和成品使用允许的实际存储目录。

先运行`node tools/typeset_paper.cjs --help`与`python -B tools/inspect_paper.py --help`查看当前参数，再用实际存在的输入、字体、MathJax、依赖及输出路径运行。同一制作目录同一时刻只运行一个生成进程。

以下路径是占位，须替换为已定位的本地依赖。默认使用本地CHTML构建和真实数学字体打印；SVG可显式选用，各自脚本/字体依赖不能混作等价参数。

```text
node tools/typeset_paper.cjs --input <完整导读.md> --output-dir <制作目录> --output <完整导读.pdf> --node-modules <实际Node模块目录> --math-output chtml --mathjax-script <本地tex-chtml-full.js> --mathjax-font-dir <匹配的本地woff目录> --font-regular <正文常规字体> --font-bold <正文粗体字体> --font-heading <标题常规字体> --font-heading-bold <标题粗体字体> --browser-channel chrome --body-pt 13.5 --math-pt 13.5 --caption-pt 11 --caption-leading-pt 16 --line-height 1.5407407407
python -B tools/inspect_paper.py --pdf <完整导读.pdf> --report <制作目录/typeset-report.json> --output <实际检查.json> --preview-dir <离线预览目录> --preview-pages 1-4 --spread-pairs 2-3 --screen-width 1600 --screen-height 1000
```

示例页范围只说明预览参数，不等于全篇验收；根据实际页数和密集内容选择单页及连续对页。检查器输出需要再由作者读实际成品，补齐真实渲染范围和复核说明后，才形成候选所用的QA记录。

SVG数学字符是轮廓；正文可搜索不代表公式可复制，改变正文CSS字体也不改变已经生成的数学路径。需要公式复制能力时另比较带嵌入数学字体的输出。构建版本与选项应对应实际本地版本，参见[MathJax 3.2的SVG说明](https://docs.mathjax.org/en/v3.2/output/svg.html)；PDF的实际字重、描边和相对大小仍以成品为准。

### 制作与复看

正文保留完整推理与来源身份，内部角色只留在私有映射。自然章节进入目录/书签，图表和数学实际嵌入。统一标准纸型和方向，固定页高内处理段落、公式、图题、表头和算法；不裁成长短不一的图片页。

优先保留可搜索文字及矢量公式。公式按有意义的关系分行，必要说明紧随；图像保留原色，密集图例不足以细读时用原件子图展开。正常表保持可比较的列行，跨页重复表头，不默认改成长字段卡片。

对实际写出的PDF检查统一页面几何、旋转/CropBox、实际文字、图像、字体与内容顺序，然后渲染单页及连续对页。分别模拟双页适合宽度、整组双页完整显示，记录画布/视口条件，读正文、行内上下标、密集长式、原图图例、章节和页间衔接。工具报告几何和文字事实，不认证内容准确或视觉合格。

GUI查看器的实际观察与离线模拟分开。遇到浏览器工具的本机文件访问拒绝，不换地址、会话或surface绕过；继续可用的本地PDF制作/渲染，并明确未覆盖的查看器范围。

新版交付始终是一篇的一份完整PDF。文件大小先由字体子集、图像编码/分辨率及向量输出优化；不能用`--pages`等选择局部页的方法把一篇再拆成多个交付。私人样张与比较稿不是对用户分部返回，不能当作整篇已经交付。

## 成品候选

```text
python -B tools/codex.py paper candidate --root <本篇目录> --input <candidate.json> --expected-revision <当前值> --operation-id reviewed-edition-1
```

```json
{
  "markdown":"<带实际嵌图的导读.md>",
  "pdfs":["<本篇唯一完整导读.pdf>"],
  "page_profile":"A4",
  "qa":"<实际PDF渲染核验.json>",
  "review":"<原生作者对照原件与最终页面的复核记录.md>",
  "responsibility_report":{"N":16,"R":4,"D":3,"V":3}
}
```

上面计数仅是格式示例，应替换为本篇实际责任事实；工具核对作者报告没有低于本篇承诺，不认证研究的真实性或质量。可解释的原文缺口在导读明确保留，不为“证明全绿”伪造原文结论。

新0.2候选的`pdfs`必须恰有一项；保留列表形状便于读取旧数据，不再借它支持分卷。`page_profile`默认为A4；其它支持的标准竖版规格须显式声明。工具实际读取PDF，核对页数、MediaBox/CropBox、旋转后的统一可见纸型；不能把QA字段全绿当作标准页几何。

核验JSON至少有`pages`、`rendered_pages`及已经处理完的`formula_errors=[]`、`overflow=[]`、`missing_images=[]`，真实页数须匹配。若声明`sha256`，必须匹配最终所选PDF；声明`status=NEEDS_REVIEW`的报告不能只补页数后入候选。原始检查报告保留；若存在误报，由实际页面和内容核对说明原因，形成独立的最终QA与复核记录。后处理改变了PDF字节时重新检查和绑定，不能沿用旧散列。

配套复核记录写明实际渲染、读过什么、双页模拟窗口与缩放、哪些限制影响使用。几何检查不认证字体、图文美感或数学正确性；必须真正读成品与关键路径。

候选绑定当前映射、Markdown、唯一完整PDF、实际嵌入本地图片、所选核验与复核文件。改了任一绑定内容，旧候选变为STALE，旧邮件不能代表新候选已交付。外链图片须先按来源边界取得实际文件并嵌入，不能靠联网成功的偶然状态制作缺图PDF。

## 按X记录送达和单篇返回

无X候选在内容、覆盖和最终PDF复核完成后显示`READY_LOCAL`，直接`paper return`，不发送邮件。

有X时，按核心[DELIVERY](../codex/DELIVERY.md)在**父DIGR会话目录**操作`delivery prepare / mark-sending / reconcile`，`candidate_id`用该篇`paper check`返回的候选ID，files只选本篇完整PDF。真实发送由Gmail原生连接器执行；CLI不运行发件程序、不复制凭据。每个读回记录绑定账号、收件人、文件和实际尝试，实际附件元数据与取回内容按各自证据范围说明。

父ledger已验证后，本篇只登记它的引用，不再发送：

```text
python -B tools/codex.py paper delivery --root <本篇目录> --input <verified-entry.json> --expected-revision <当前值> --operation-id record-edition-1
python -B tools/codex.py paper return --root <本篇目录> --input <paper-return.json> --expected-revision <当前值> --operation-id return-edition-1
python -B tools/codex.py paper summary --batch <私人批次>
```

`verified-entry.json`为`{"candidate_id":"<本篇已审候选ID>","delivery_id":"<父ledger已验证条目ID>"}`。条目必须恰含本篇唯一完整PDF、相同候选与冻结X目标、相同批次授权引用；本篇绑定稳定交付身份和回执摘要，由父ledger核对当前证据。别篇新增条目不使本篇失效；同一消息的真实新读回可以补证，历史缺失记录保留，不重新发送。

`paper-return.json`为`{"body":"<本篇实际完成说明.md>"}`。状态包括DRAFT、READY、READY_LOCAL、SENT_VERIFIED、RETURNED；文件、来源或当前证据失效为STALE_OR_UNAVAILABLE。单篇RETURNED不表示用户打开或理解，也不关闭父任务。父RETURN列实际最终PDF，复用共同ledger，不重复发件。

旧pin的0.2单PDF/Gmail和0.1分卷历史保持原语义；不对旧包倒套无X规则。新0.9核心/0.3论文批次使用`--task-root`，旧式`--recipient`不改选新任务出口。

## 维护发行

源码作者修改协议/技能后运行 `paper refresh --root <源码>`，再运行 `profile refresh` 和必要检查。前者更新增量清单及核心指针，后者更新核心聚合包与散列。它们是显式源码维护，不是在线获取、安装、执行授权或质量认证。发布后须读取新SHA的实际文件再验证安装/调用。

## 0.4的Consult与自然职责定位

新核心0.10的批次记录`consult_enabled=true`与`mapping_contract=integrated-functions-v1`；旧核心0.9仍创建0.3契约，旧候选/发送按原事实回读。新批次在父任务保存实际论文addon选择，即使父原话使用DIGR前缀也不伪改其initial mode。

新mapping.parts仍完整包含m1/m4/m2/m3/m5，每值可为一个真实标题或非空标题列表；职责可共用或跨章节，所有位置必须实际存在。其余原页锚、主张依据、推理链、实验和覆盖责任保持；位置可解析不认证讲透。内部角色不进入正文。

新候选增加`consultation={guidance:<实际公开稿路径>,source_ref:<实际exchange/来源引用>,scope:<当前适用指导范围>}`；实际非空公开稿与已有native review一起绑定。review说明Main怎样处理中心指导、确定事实及真实页面；不是要求Consult填表或每版重审。指导文件变化会使绑定候选过时，但候选版本变化本身不要求另开Consult终审。原生responsibility_report不减少、不由外部稿件代填。

`consult prepare/call/inspect/reconcile-cost`提供公开上下文和费用事实；CLI只在显式call按配置调用模型，见核心CONSULT和实际--help。原稿/图像必须实际传入，不能只交Windows路径。完整指导和费用对账状态分开；未知预留不记零、无自动推理重试。
