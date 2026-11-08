# 工作工具：取回问题、继续制作、保留真实后果

长任务从已有笔记开始，必要时再使用这些标准库工具。统一入口是 `python -B tools/codex.py`；旧的 codex_profile.py、codex_workbench.py、codex_experience.py 继续可用。它们不调用模型、不派代理，不把本地状态变成思想或交付质量评分。

## 0. 在其它项目找到工具，及时开始记录

本机经验证的工具可安装在D盘的独立版本目录；定位文件为 `CODEX_HOME/digr-codex/toolchain.json`。其中version、root、cli与source_commit只说明已安装工具身份，不是新消息的仓库HEAD、执行授权或完成证明。没有安装时可用实际已知的仓库绝对入口；不要求为了执行一个任务先安装服务。

PowerShell跨项目调用示例：

```powershell
$toolLocation = Get-Content (Join-Path $env:CODEX_HOME 'digr-codex/toolchain.json') -Raw -Encoding utf8 | ConvertFrom-Json
python -B $toolLocation.cli profile check
python -B $toolLocation.cli workbench --help
```

保持当前项目工作目录，request、work和out传该任务的真实绝对路径；运行源码仍在独立工具根，不往当前项目复制协议或改变它的Git状态。工具版本与本轮协议不一致时按实际可用接口处理，不假称本地已经取得最新pin。

把计时准备放进初始化：取实际墙钟起点，核对可用单调钟/锚，准备task与已初始化的line；在首项实质MAIN/SOURCE开始前记begin，INIT说明真实能力。没能力时立即说明未知并继续可做的工作，不延迟任务去造计时平台；不得在几十分钟之后用新起点回填早段。时钟相关命令见第6节。

## 1. 取得协议：在线获取与同 pin 续读

```text
python -B tools/codex.py acquire --stage startup --out D:/task/acquired-startup
python -B tools/codex.py acquire --stage execution --continue-from D:/task/acquired-startup --out D:/task/acquired-execution
```

第一条实际读取实验分支HEAD，以同SHA取得manifest/VERSION/启动切片。模型读启动切片完成表面分类，只有EXECUTING才取第二条；HELP把stage换成help。第二条明确续读原pin，不重新解析HEAD。接续目录核对保存字节，但不是一次新消息所要求的在线获取替代；每条精确前缀新消息仍按ROUTER重新获取，既有执行P_run保持冻结。

薄路由与轻量偏好可用 profile export codex-agents --out D:/task/AGENTS-codex.txt 一次导出；仅创建新文件，不安装、不覆盖全局约定，也不复制深执行语义。

CLI默认使用直接HTTPS：同次读取Git ref和Branches，SHA必须一致。宿主已有GitHub connector时，可由模型直接使用连接器取得真实分支HEAD和同pin原文；代码集成也可给 `CodexRepositoryTransport(fetch)` 传入真实连接器fetch，调用 `acquire(connector=True)`。该响应必须是live_direct、github_connector，不能拿搜索结果或以前保存的JSON当新HEAD。直接API在某台机器返回504，不证明连接器也不可用。

执行可从manifest声明的聚合包一次取得完整正文，校验成员顺序、字节、版本及manifest散列；不是只看摘要。实际声明路径失败则说明获取失败，不用旧协议补。`profile check`只看本地分发；开发者明确修改源文件后用 `profile refresh`重建聚合包和hash。后者是源维护操作，不是修改后再假称旧pin未变。

## 2. 一份普通笔记与按需材料

### 新任务先形成可供决定的完整说明

0.7起的新会话默认要求前置任务说明；旧会话仍保留其真实状态。显式flag也可用于旧版本工具调用。模型先研究实际材料与原话，再提供proposal；脚本不自动识别意图。

```text
python -B tools/codex.py task create --out D:/task/session --request D:/task/request.txt --p-run 0.7.0@<实际SHA> --require-foundation
python -B tools/codex.py clock begin --root D:/task/session --owner COMMON --scope FOUNDATION --state SOURCE
python -B tools/codex.py foundation propose --root D:/task/session --input D:/task/proposal.json --reason "原件调查后的完整候选"
python -B tools/codex.py foundation show --root D:/task/session
```

proposal示例见codex/examples/foundation/proposal.json：内容涵盖目标、成品范围、粒度、真实基础、依赖、路线/最早整体结果、资源和完成条件。内部字段不等于用户问卷；对用户展示连贯说明、必要原件与关键问题。等待用户期间关闭活动段，不算研究。

```text
python -B tools/codex.py foundation answer --root D:/task/session --id Q1 --revision <实际所答版本> --reply-file D:/task/actual-reply.txt --source <真实消息引用> --effect "说明与下一行动的实际变化"
python -B tools/codex.py foundation confirm --root D:/task/session --revision <已展示当前版本> --reply-file D:/task/actual-go-ahead.txt --source <真实明确决定>
python -B tools/codex.py clock end --root D:/task/session --owner COMMON --continued
```

answer不自动确认整体。模型理解真实答复：用户已看完整说明并明确要求改后执行，可按该决定记录，无需固定口令；提出新重要取舍则先讨论。material修订默认使旧确认不再覆盖当前稿；纯文字或无实质影响事实更新可用propose --change-kind non_material，并给出真实理由，保留原确认来源及继承说明。改问题或选项后不沿用旧答案。

确认后才补齐正式参数，line create仍只是准备文件。正式clock begin默认EXECUTION；未确认时MAIN/SOURCE及独占D/V均拒绝，失效后的checkpoint也拒绝，end/recover始终可用。task report的foundation_timing单列前置，timing只算正式，不把前置分钟冲抵T/t。恢复包自动带当前任务说明与决定；无重要变化不重新盘问。

这些命令只检查被管理的入口和记录一致性，不拦截宿主所有工具，也不认证用户真实同意或解释质量。真语义及新纠正仍由模型依据会话处理。短任务可直接对话完成前置，不强制落这些文件。

```text
python -B tools/codex.py workbench init --request D:/task/request.txt --work D:/task/WORK.md
python -B tools/codex.py workbench topics --work D:/task/WORK.md
python -B tools/codex.py workbench focus --work D:/task/WORK.md --topic "原页组装路线" --material D:/task/notes.md:20-45
```

保留原始目标、交付用途、用户纠正、关键问题、研究/竞争方案、实际产物与下一步。重要发现写明依据、取舍及落实后果；自由标题可用，不必先把材料洗成模板。原件不搬进目录，PDF/EPUB按实际阅读工具打开；本工具引用文本/行段，不要求全文转码。相对材料路径以工作笔记所在目录为基准，绝对路径也可。

默认模板使用“用户目标 / 用户纠正与已确认要求”等标题。已有文档可显式选其真实标题：

```text
python -B tools/codex.py workbench focus --work D:/task/existing.md --goal-topic "用户目标 U0" --corrections-topic "已有决定" --corrections-topic "最新用户原话" --topic "当前路线"
```

也可单独给 `--request D:/task/request.txt`，不能与goal-topic同时给而让脚本猜优先级。标题需唯一；超出字符预算报明问题，选择小节/行段或提高max-chars，不静默剪掉目标、条件或纠正。

## 3. 给独立者空间，也给足原件

```text
python -B tools/codex.py workbench challenge --kind D --work D:/task/WORK.md --material D:/task/source-notes.md:1-30
python -B tools/codex.py workbench challenge --kind V --work D:/task/WORK.md --material D:/task/source-notes.md:31-60
python -B tools/codex.py workbench challenge --kind D --work D:/task/WORK.md --question "保留原页组装能否替换当前路线？实际比较。" --candidate D:/task/plan.md
```

前两条允许D先自主侦察、V先研究领域与问题；后者给一个成熟介入问题。默认带目标、用途、纠正和明确选入的材料，不自动带Main全套推导/研究/下一步。生成输入包不代表输入选择必然正确；交给真实受控上下文的独立代理，按COLLABORATION处理返回、实际生产和后果。V可由自己的材料与作品长出新问题，必要交流默认Main忠实转交。

公开摘要直接编辑已有笔记即可。可选record追加到现有唯一小节，不另建事件系统：

```text
python -B tools/codex.py workbench record --work D:/task/WORK.md --topic "原页组装路线" --kind "异议与取舍" --text-file D:/task/note.txt --ref D:/task/sample.pdf
```

它保留BOM/换行，把正文标题留在引用体，父节插入不误归子节。时间戳只表示记录时刻。单一作者写本线笔记，多个代理用原生消息与各自产物返回；工具不自动判断采纳已落实或统计N/R/D/V。

## 4. 可选经验：当时的原话，当前的适用判断

普通笔记和material已足够保留条件与反例。只有想保存原位置的当时片段并自动提示变化时，才用：

```text
python -B tools/codex.py experience capture --note D:/task/case.md --source D:/task/feedback.md:12-18 --out D:/task/case.json
python -B tools/codex.py experience show D:/task/case.json
python -B tools/codex.py workbench focus --work D:/task/WORK.md --experience D:/task/case.json
```

自由case说明可以区分用户原话、模型解释、适用条件、反例和改变的行动。capture不覆盖已有文件，show读取明确选中的案例并比较原位置；片段相同只表示那几行相同，不证明周边上下文、当前目标、权限或经验适用仍成立。没有自动全史扫描、沉默确认、偏好晋级或全局Memory写入。当前任务不用经验工具也可正常工作。

## 5. 多主进度的可接续工作包

模型在同pin下理解任务、真实初始化完整参数后，可把状态保存在任务数据盘：

```text
python -B tools/codex.py task create --out D:/task/session --request D:/task/request.txt --p-run 0.6.0@<实际40位SHA> --decisions D:/task/decisions.md --m 2
python -B tools/codex.py line create --root D:/task/session --id M01 --parameters D:/task/M01-parameters.json --owner <真实执行者> --work D:/task/M01-WORK.md
python -B tools/codex.py line packet --root D:/task/session --id M01
python -B tools/codex.py line update --root D:/task/session --id M01 --input D:/task/M01-status.json
python -B tools/codex.py task report --root D:/task/session
```

角括号是待替换的真实信息。每M参数文件完整给N/T/R/B/S(n,t,r,b)/D/V/L；例如：

```json
{"N":12,"T":"90min","R":4,"B":0,"S":{"n":3,"t":"40min","r":1,"b":0},"D":3,"V":3,"L":3}
```

这是格式示例，不是所有任务都用这组时间。数值T/t API字段单位是秒；字符串显式带单位，不解析用户含糊调用。可选task create --explicit保留用户显式参数原值；工具显示每线差异，不认证差异已获允许。

status示例：

```json
{"candidate":"candidate.pdf","content_status":"DRAFT","responsibility_status":"IN_PROGRESS","next_action":"打开候选核对原件依赖","unhandled":["D02中心主张待处理"]}
```

相对candidate以status文件目录为基准。产物可为文本、PDF或目录；恢复按真实文件类型打开，目录仅指入口。REQUEST.txt冻结原字节；decisions引用当前共同材料。恢复包标记本线旧记录可滞后，带回最新共同要求并区分用户决定与模型提案。一个包不必读其它线私有历史或依赖其计时日志。已有笔记使用自由纠正标题时，line create可加重复的 --corrections-topic，按需案例加 --experience；这些明确选择保存在本线包，后续packet不需再猜。packet也可临时附加两项选择，不自动扫描历史或替换原始U0。

自主调参用 `line parameters --parameters ... --reasons ...`；N/R/D/V不自动降值。真实用户修订可加 `--user-revision "原话或明确引用"`，保留到变更记录，不由脚本认证。所有状态为作者声明；registered_line_count不是effective_M_count。实际作者、原生分工、议会和最终内容综合仍由模型做，不由文件目录代替。

## 6. 真计时：显式边界、已知小计与缺口

```text
python -B tools/codex.py clock begin --root D:/task/session --owner M01 --state SOURCE
python -B tools/codex.py clock checkpoint --root D:/task/session --owner M01 --continued
python -B tools/codex.py clock end --root D:/task/session --owner M01 --continued
python -B tools/codex.py clock recover --root D:/task/session --owner M01 --reason "中断后核对真实文件再继续"
python -B tools/codex.py clock report --root D:/task/session
```

这些是可选动作示例：recover用于确有开放尾段的恢复，不需在正常end后机械执行。begin只开段；checkpoint闭合前段并继续相同状态；end闭合。continued是操作者对真正连续活动的明确声明，不是脚本自动探测。恢复丢弃开放尾段并保存缺口，再begin开新段。状态MAIN/SOURCE可进T，只有SOURCE进t；D_EXCLUSIVE/V_EXCLUSIVE/META/IDLE排除。

Windows跨短命CLI可在task create给 `--anchor-pid <明确核对的存活宿主PID>`，每次读PID+创建时间与单调钟。未提供时只有同进程域，不虚报跨进程连续；Linux取boot_id。可用 `clock anchor --root ... --pid ... --reason ...`明确更换未来时钟域，不修补旧段。主机存活不证明模型在工作。

共同实质综合用owner COMMON，只进全局一次，不反填M。全局取同域并集，多个域分列，未知总数不强加。某线活动日志不可读时，report_status为PARTIAL_READ，可读子集另列available_global_known_union_ns；整项global_known_union_ns与全局可比性保持未知，坏线不当0，也不自动抢救或改写；代理空闲或running不证明有效时间。状态/参数/文件准备均不证明完整M或L3已经执行。

## 7. 任务授权上下文

必要时使用 `permissions --input operation.json`，输入context（scope、authorized、可选既有grants/budget/stopped）、operation、within_task、capability及可选estimated_cost。它分开持续授权、真实能力与费用，不执行操作或改变宿主权限。不是每次行动前的必填审批表；正常任务沿用实际会话决定。完整原则见PERMISSIONS。

所有新增任务材料、缓存、临时解包与发布包遵守本机真实存储分工；本机使用D盘。没有工具需求的短任务直接完成，不先搭工作站。
