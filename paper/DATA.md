# DIGRP 文件与命令契约 0.1.0

语义来自同 pin 的 [PROTOCOL.md](PROTOCOL.md)。工具不用模型、不派代理、不发邮件，不验证数学证明、真实意图或学习效果。`check` 是所选文件与记录的检查；原生宿主仍须对照论文与成品。

## 取得增量与私人批次

在新原始调用上完成核心在线获取和分类；需要执行时取得同 SHA 全部核心正文，再续取增量：

```text
python -B tools/codex.py paper acquire --continue-from <本轮execution获取目录> --out <新目录>
python -B tools/codex.py paper init --out <私人批次> --p-run <核心version@完整SHA> --authorization <实际授权原文文件> --source-ref <真实用户消息引用> --recipient <已解析且获授权的邮箱>
python -B tools/codex.py paper add --batch <私人批次> --id <论文ID> --title <论文题名> --line M01 --owner <真实主进度作者> --parameters <本篇完整参数JSON>
```

第一条不重新取 HEAD，也不为下一条原始调用取得路由资格。工具核对核心声明、增量 manifest/VERSION 和全部成员散列。无法在线取得当前必需协议时遵守所属路由失败规则，不能把源码开发目录作为新调用的在线凭据。

批次 `batch.json` 只保存 P_run、实际授权引用、收件地址与各篇索引。每篇 `papers/<id>/paper.json` 有独立 revision、完整参数、来源、映射、候选、交付、单篇返回和接续游标。每个 M line 与论文 ID 在批次内唯一，不能复用同一条完整主进度的身份掩盖其它篇未承担的责任。

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
| `parts` | m1、m4、m2、m3、m5 到实际导读标题的映射；正文中须按阅读顺序出现 |
| `assumptions` | 模型假设与范围，各条有id、anchor、location |
| `claims` | 全局主张、真实依据性质basis、依赖的assumptions/chains/experiments ID |
| `chains` | 每条purpose、prerequisites、source_vs_supplement、result、unresolved，与原页及导读章节相连 |
| `experiments` | 图表/设置/指标/结果的解释及原页、导读去处 |
| `coverage` | 实际原文内容块的去处，disposition为explained、context、non_content或unavailable；原生复核确保粒度足以发现真实遗漏 |

各条统一 `anchor={"source":"已注册ID","page":物理页码,"label":"原节/式/图/脚注标签"}`、`location="实际导读标题"`。工具拒绝越界页码、悬空依赖和不存在的标题；字段存在或覆盖表全绿不证明内容真正解释充分。

`cursor.json` 保存 position、next_action、basis 与可选 anchor，保留当前原式、例子和待接的步骤。暂停不是学习缺陷证据，游标不写入另一套能力状态。

`resume/check`以最新未完成的保存步骤为当前动作；后续实际变更保留旧游标的阅读上下文而不继续执行旧指令。它还按当前候选逐卷显示已核验消息与剩余文件。已返回篇收到尚待处理的改稿保存步骤时，批次不会因此误报全部完成。

发送响应不明时用同一checkpoint记录实际事实，例如：

```json
{"position":"卷一的发送响应不明","next_action":"先在Gmail核对本次SENT与附件，再决定余下发送","basis":"实际工具响应/消息引用","pending_delivery":{"attempt_id":"本次稳定尝试引用","outcome":"uncertain","pdf_names":["卷一.pdf"]}}
```

工具把它绑定到当时的候选与文件身份；另一卷的回执或新的阅读游标不自动消除它。相应候选/卷的真实读回核验可解决这项未知；若实际核对得出其它结果，保存`outcome=resolved`和对应事实依据，再由原生宿主处理。它不自动检索Gmail、不认证依据，也不自动重发。

## 本地渲染与截图PDF组装

`tools/render_paper.cjs`把带实际本地图片的Markdown排成截图页，`tools/assemble_paper.py`将这些截图无损组装成PDF。二者只做文件工作；内容取舍、数学正确性和实际阅读复核仍由本篇作者负责。

### 首次使用：定位已有依赖

在Codex桌面宿主先调用`load_workspace_dependencies`，取得本轮实际的Node可执行文件、Node模块目录和Python可执行文件；不要凭另一台机器的路径推测。在其它宿主使用其已经安装的相应运行时。

- Node模块目录须能加载`marked`和`playwright`。使用支持当前模块的Node；本工具不下载浏览器。通过`--browser-channel`选择已安装的Edge/Chrome，或通过`--browser-executable`传入实际浏览器可执行文件。
- Python须有`Pillow`、`reportlab`、`pypdf`；从最终PDF渲染手机宽度预览时另需`pypdfium2`。优先使用宿主已有依赖，不另建重复运行时。
- 传入本地MathJax **3 CHTML**脚本，例如已有的`tex-chtml-full`构建，以及匹配的CHTML WOFF字体目录。字体目录应实际含有`MathJax_Main-Regular.woff`等文件。工具阻止HTTP/HTTPS资源请求，不依赖CDN补齐文件。
- 传入实际存在的正文常规、粗体字体文件。Windows可从`$env:WINDIR\Fonts`定位已安装的中文字体；其它系统按实际字体位置选择。未给`--font-bold`时复用常规字体，不合成假粗体。字体、脚本和目录要用`Test-Path -LiteralPath`或宿主等效方式核对。

下例中的变量须先填为上述实际路径。`$Markdown`是源稿，`$RenderDir`为这个候选独立的输出目录，`$NodeModules`不是Node可执行文件本身。浏览器临时profile和cache默认也写入输出目录下的`browser-tmp`；可用`--temp-dir`指定另一个实际允许的存储位置。同一输出目录同一时间只运行一个渲染进程。

```powershell
& $Node tools/render_paper.cjs `
  --input $Markdown --output-dir $RenderDir `
  --node-modules $NodeModules `
  --mathjax-script $MathScript --mathjax-font-dir $MathFonts `
  --font-regular $FontRegular --font-bold $FontBold `
  --browser-channel msedge
```

`--help`列出全部参数。默认页面宽780px、正文32px，在390px宽预览时正文等效16px；公式最多缩至原字号的0.875，低于此值会要求源稿分行。默认各页同宽，按正文实际高度裁掉多余底色。`--fixed-height`保留固定高度，`--light`改为浅色正文主题。

### 数学、原图与语义分页

源稿可混用`$...$`、`$$...$$`、`\(...\)`、`\[...\]`；行内和围栏代码中的同样字符保留为代码。明确的未闭合数学界定符、MathJax错误、缺图或资源加载失败会使渲染失败。展示式的`\tag{...}`作为紧邻公式的标签另排，避免长中文标签挤掉公式字号；顶层`\qquad`连接的并列式会上下排列，其余复杂长式由作者按关系、加项或条件分行。

图片相对路径以Markdown所在目录解析，也接受实际本地绝对路径；外链图片须先取得本地文件。**默认保留所有原图的颜色和底色**，黑底白字只应用于正文。图7这类多曲线图的颜色和图例属于阅读内容，不能用整页灰度换体积。仅在确认某些公式截图为纯黑白时，才可显式选用`--invert-formula-images`做公式图反色；普通图、表和算法原件不反色。

标题与正文、引出语与公式/图片、公式与第一段解释尽量保持在同页。表格按行分页并在新页重复表头，宽表按字段卡片重排；可用`--table-mode rows|cards|auto`选择。算法有序步骤按条分页；过长代码按行拆页，须实际复看循环与步骤的连接。保留所有字符不自动保证分段适合阅读。

先诊断整稿而不截图：

```powershell
& $Node tools/render_paper.cjs `
  --input $Markdown --output-dir $DiagnosticDir `
  --node-modules $NodeModules `
  --mathjax-script $MathScript --mathjax-font-dir $MathFonts `
  --font-regular $FontRegular --font-bold $FontBold `
  --browser-channel msedge --diagnostic --layout-only
```

`render-report.json`记录源稿散列、数学输入及源行、字号缩放、图片、字体、语义分段、溢出、内容单元与顺序保持。`NEEDS_REVIEW`或`NEEDS_SOURCE_LINE_BREAKS`应回到对应源行处理；`--diagnostic`允许保留内部比较用的版面，不把它当作最终交付。修正后去掉诊断参数重新渲染，得到`RENDERED`且实际截图齐全的报告。`--capture-pages "1-8,30-40"`可只截取指定全篇页码供复看。

### 组装、最终PDF复看与连贯分卷

```powershell
$Report = Join-Path $RenderDir 'render-report.json'
& $Python -B tools/assemble_paper.py `
  --report $Report --output $FinalPdf `
  --preview-dir $PdfPreviewDir --preview-width 390
```

组装器只接受当前报告中已截图且散列匹配的页，按RGB无损写入PDF。它随后重新打开最终PDF，逐页核对图像像素与页面尺寸；指定`--preview-dir`时，再由PDFium从**写出的PDF**生成预览。`--preview-pages "1,20-24"`可选重点页。配套`.verification.json`记录PDF散列、字节数、所选原页、像素运输与预览事实；这些事实不能代替打开页面读一遍。

原色截图PDF可能较大。按连续章节分卷，复用同一份截图报告，不改字号或曲线颜色来强行压进附件上限。例如先从报告`layout.headings`确认全景与预备的末页，再实际填入相应范围：

```powershell
& $Python -B tools/assemble_paper.py `
  --report $Report --output $VolumeOnePdf --pages "1-37" `
  --title '卷一：全景与预备'
& $Python -B tools/assemble_paper.py `
  --report $Report --output $VolumeTwoPdf --pages "38-104" `
  --title '卷二：关键推导'
```

这里的数字仅示范参数，必须换成本稿真实的连贯边界。`--pages`使用渲染报告中的全篇页码，卷内截图页脚沿用全篇页码；在卷名或发送说明中写清范围。每卷仍各自读回核验。`--allow-diagnostic`只用于明确标识的内部比较稿。

正式复看至少覆盖密集数学、长式、图表和章节边界，并走一条m1结论→m4准备→m2推导→实验→原文回读的路径。390px宽预览是桌面尺寸模拟，真实iPhone打开和用户学习反馈分别记录。原生宿主按实际最终文件整理下节要求的候选QA与复核记录，不能把一个渲染报告状态直接当作候选质量证明。

## 成品候选

```text
python -B tools/codex.py paper candidate --root <本篇目录> --input <candidate.json> --expected-revision <当前值> --operation-id reviewed-edition-1
```

```json
{
  "markdown":"<带实际嵌图的导读.md>",
  "pdfs":["<最终卷一.pdf>","<如确需分卷的卷二.pdf>"],
  "qa":"<实际PDF渲染核验.json>",
  "review":"<原生作者对照原件与最终页面的复核记录.md>",
  "responsibility_report":{"N":16,"R":4,"D":3,"V":3}
}
```

上面计数仅是格式示例，应替换为本篇实际责任事实；工具核对作者报告没有低于本篇承诺，不认证研究的真实性或质量。可解释的原文缺口在导读明确保留，不为“证明全绿”伪造原文结论。

核验JSON至少有 `pages`、`rendered_pages`，以及已经处理完的 `formula_errors=[]`、`overflow=[]`、`missing_images=[]`。配套复核记录写明实际看过什么、改了什么、哪些限制影响使用。规则不强迫每页同一检查粒度，但必须真正看成品与关键路径。

候选绑定当前映射、Markdown、全部PDF卷、实际嵌入本地图片、所选核验与复核文件。改了任一绑定内容，旧候选变为STALE，旧邮件不能代表新候选已交付。外链图片须先按来源边界取得实际文件并嵌入，不能靠联网成功的偶然状态制作缺图PDF。

## Gmail发送、读回和单篇返回

原生宿主使用已授权的连接器发最终PDF；工具不新增API凭据，不替用户授权发消息。一次发送结果不明先核对Gmail，不能靠重复调用刷到成功。每篇分卷可以分封，全部卷核验完才完成该篇。

```text
python -B tools/codex.py paper delivery --root <本篇目录> --input <selected-gmail-facts.json> --expected-revision <当前值> --operation-id sent-message-<实际ID>
python -B tools/codex.py paper return --root <本篇目录> --input <paper-return.json> --expected-revision <当前值> --operation-id paper-return-edition-1
python -B tools/codex.py paper summary --batch <私人批次>
```

交付记录来自实际工具输出中选定的事实：

```json
{
  "candidate_id":"<本篇check返回的候选ID>",
  "message_id":"<实际Gmail消息ID>",
  "recipient":"<读回的已授权地址>",
  "label_ids":["SENT"],
  "attachments":[{"filename":"<最终PDF文件名>","bytes":12345}],
  "authorization_source_ref":"<实际批次用户授权引用>",
  "send_evidence":"<保留的实际发送响应.json>",
  "readback_evidence":"<保留的实际读回响应.json>"
}
```

消息ID、收件人、SENT与附件事实必须由真实Gmail发送/读回取得，不可手填合成冒充实际交付。工具保存的是作者选定证据，非Gmail服务器认证或宿主拦截器。命名/字节数核对只证明相应范围，发送选用的本地PDF散列与候选一起保留。

`paper-return.json` 为 `{"body":"<本篇实际完成说明.md>"}`。状态依次可为DRAFT、READY、SENT_VERIFIED、RETURNED，变化/缺件表现为STALE_OR_UNAVAILABLE。只有全部当前卷有读回证据，才能记录本篇返回。返回文件或凭据本身之后改变也需复核。

`summary` 的 `all_papers_returned=true` 仍不关闭父任务。根协调者完成公共工程并按核心RETURN发出统筹正文、收口原生命周期。准备、发送、读回、单篇返回和全局关闭各自有事实，不互相代替。

## 维护发行

源码作者修改协议/技能后运行 `paper refresh --root <源码>`，再运行 `profile refresh` 和必要检查。前者更新增量清单及核心指针，后者更新核心聚合包与散列。它们是显式源码维护，不是在线获取、安装、执行授权或质量认证。发布后须读取新SHA的实际文件再验证安装/调用。
