# DIGRP 文件与命令契约 0.5.4

语义来自同 pin 的 [PROTOCOL.md](PROTOCOL.md)。论文文件工具本身不调用模型、不派代理、不发邮件，不验证数学证明、真实意图或学习效果。`check` 是所选文件与记录的检查；原生宿主仍须对照论文与成品。

## 取得增量与私人批次

在新原始调用上完成核心在线获取和分类；需要执行时取得同 SHA 全部核心正文，再续取增量：

```text
python -B tools/codex.py paper acquire --continue-from <本轮execution获取目录> --out <新目录>
python -B tools/codex.py paper init --out <私人批次> --p-run <核心version@完整SHA> --authorization <实际授权原文文件> --source-ref <真实用户消息引用> --task-root <父DIGR会话目录>
python -B tools/codex.py paper add --batch <私人批次> --id <论文ID> --title <论文题名> --line M01 --owner <真实主进度作者> --parameters <本篇完整参数JSON>
```

第一条不重新取 HEAD，也不为下一条原始调用取得路由资格。工具核对核心声明、增量 manifest/VERSION 和全部成员散列。无法在线取得当前必需协议时遵守所属路由失败规则，不能把源码开发目录作为新调用的在线凭据。

批次 `batch.json` 保存 P_run、实际授权引用、冻结X目标、父任务入口、各篇索引和所选契约。新核心0.11对应论文0.5，批次与单篇记录 `authoring_contract=sonnet-native-v1`、`mapping_contract=source-bound-native-v1`。每篇 `papers/<id>/paper.json` 有独立 revision、完整参数、来源、映射、候选、交付、单篇返回和接续游标。每个 M line 与论文 ID 在批次内唯一，不能复用同一条完整主进度的身份掩盖其它篇未承担的责任。

`--parameters` 是本篇已冻结的完整配置，由 Codex 维护，不交给 Sonnet 填。时间保留单位，例如 `T="90min"`、`S.t="25min"`；下例说明形状，各值须换成本篇实际承诺，并非新的默认档位：

```json
{"N":12,"R":4,"D":3,"V":3,"L":3,"T":"90min","B":0,"S":{"n":4,"t":"25min","r":2,"b":0}}
```

## 逐篇写入

写命令使用 `--expected-revision <当前篇revision> --operation-id <稳定ID>`；重试同一操作和内容用同一ID，不会重复写入。改变内容须新ID。revision冲突先重读本篇并处理事实差异，不能强行覆盖。单篇短锁只协调该工作目录；锁残留须先查是否仍有写者，不自动删除活动锁。多篇主进度可以并行，该篇作者处理实际研究与公开创作返回，并串行维护来源去处。

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

`mapping.json` 由 Codex 依据实际原文和真实作品编写。新契约只要求来源去处，不预设论文应有的论证类别：

```json
{
  "mapping_contract":"source-bound-native-v1",
  "coverage":[
    {
      "id":"source-block-03",
      "anchor":{"source":"journal-v1","page":3,"label":"实际原节、段落或图的标识"},
      "location":"Sonnet实际形成并已写入作品的章节标题",
      "disposition":"explained",
      "note":"这一原文内容在此处得到的实际处理"
    }
  ]
}
```

`coverage` 为非空列表，各条必须有唯一 `id`、有效 `anchor`、真实作品标题 `location` 及 `disposition`。后者可为 `explained`、`context`、`non_content` 或 `unavailable`；`note` 等原生来源事实可按需要保留。原文内容可汇入同章，也可依实际需要分开，章节数量和顺序自由。新映射不接受旧 `parts`；没有必须填写的 assumptions/claims/chains/experiments 数组，也不把它们改名为另一组必填栏目。需要核对的假设、推导或观察由当前原文和用户目的决定，Codex实际完成这些工作。

上例只说明一条记录形状，不是一篇的完整覆盖。原生作者实际读完整约定原件，按足以发现实质遗漏的粒度记录去处；不能用一条“全文”记录、页数配额或占位条目冒充这项工作。工具核对来源身份、物理页码和位置标题，不能判定解释是否忠实、粒度是否足够或整篇是否真的处理。

`cursor.json` 保存 position、next_action、basis 与可选 anchor，保留当前原式、例子和待接的步骤。暂停不是学习缺陷证据，游标不写入另一套能力状态。

`resume/check`以最新未完成的保存步骤为当前动作；后续实际变更保留旧游标的阅读上下文而不继续执行旧指令。它显示当前完整PDF及其已核验消息。已返回篇收到尚待处理的改稿保存步骤时，批次不会误报全部完成。旧0.1候选可按原事实回读，但不自动升级其交付契约。

0.3的新X批次将发送事务放在父任务的共同delivery ledger。发送前保留本篇候选ID、完整PDF及真实目标，只有首次mark-sending授权一项发送；响应不明保持SENDING/UNCERTAIN并先核对，不用事后checkpoint抹去未知。旧0.2游标和Gmail事实仍按原契约读取。

## 本篇的真实 Sonnet 公开创作

首次 `consult prepare` 用 `--paper-root <本篇目录>` 绑定实际0.5论文。后续用 `--continue-from <本篇exchange ID>` 继承这篇及其公开上下文，不从普通DIGRC历史中途切入论文，也不把另一篇续接成当前篇。任务原话、实际论文选择与当前用户要求保留各自来源身份；Sonnet收到的是自然的论文委托，不接收内部line、计数或映射schema作为创作指令。

来源目录中的路径、页数、文件名和散列只说明本机已取得材料，不表示正文已传入。按当前 `consult --help` 用 `--material <实际UTF-8正文>`、`--image <实际图像>` 提供所需真实内容，保留版本、范围和提取缺损。Sonnet可自然要求更多原件、核对和试作，不必填输出模板或运行命令。`prepare`不发出；核心0.13起`consult split`读取本次绑定，Codex按[SPLIT](../codex/SPLIT.md)完成原生分工及私有记录，`call --split-plan`在本机运行Split后才在实际费用授权内调用。绑定包含本篇作用域、当前用户输入和全部实际请求。公开内容与费用对账分别记录，未知费用不记零，失败推理不自动重试。

候选通过父任务consult ledger中的实际 `COMPLETE` exchange绑定本篇公开稿。工具检查该交换对应同一完整论文与当前父任务，并读取、绑定实际公开文件及其散列；不得用任意本地文本冒称真实参与。工具有这项来源绑定，仍不能认证Sonnet的内容质量或指导是否实际进入作品。具体调用、能力、费用和恢复依同pin核心CONSULT，普通DIGRC及旧0.4交换沿原契约。

论文请求只接受规范 Sonnet 型号标识。`consult inspect` 的 `paper_model_identity` 只有实际请求与服务响应所报型号精确一致时为 `CONFIRMED`；候选自动绑定稳定的 `model_identity={status,requested_model,response_model}`，操作者不在候选输入中自填身份。型号缺失、不符或只返回别名时，公开稿和费用记录保留，但不能登记为 Sonnet 原生候选；不据此丢稿、推断别名相同或自动重试。

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

正文保留本篇所需的完整解释与来源身份，内部运行记录留在私有区。Sonnet形成的自然章节进入目录/书签，实际需要的图表和数学嵌入。统一标准纸型和方向，固定页高内处理段落、公式、图题、表头和算法；不裁成长短不一的图片页。

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
  "consultation":{"exchange_id":"<本篇实际COMPLETE公开交换ID>","scope":"<本候选采用该公开创作的实际范围>"},
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

## 0.5的候选绑定与历史兼容

新候选的 `consultation={exchange_id,scope}` 从父ledger取得真实公开稿；`scope`说明其在当前整篇候选中的实际适用范围。native review对照当前原件和最终页面，说明公开创作及独立发现怎样落实，真实差异和未解决处如何影响使用。它不是要Sonnet填表，也不因工程字节变化要求新一轮终审。已绑定公开稿、映射或成品改变时，旧候选过时；仍适用的公开创作可以继续形成新的候选。原生responsibility_report不减少、不由外部稿件代填。

新核心0.11创建0.5，核心0.10仍创建0.4并保留 `integrated-functions-v1`，核心0.9仍创建0.3。0.4的真实指导文件绑定、五职责位置映射及更早的读序/交付继续按原事实回读，不被0.5自动重写。新批次在父任务保存实际论文addon选择，即使父原话使用DIGR前缀也不伪改其initial mode。新契约不以兼容旧数据为由继续要求小m结构。
