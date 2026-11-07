# Codex 候选适配：交付优先，原生执行与证明分开

核对日期：2026-11-07。候选版本：`codex/VERSION` 的 0.1.0。

## 这次具体交付

这是从 stable `6fdde982c2c804efe9702fd4cdd2f715b0aaf421` 建立的独立分支，参考 main `165c95bbbd96d2171687bba073774b211920ef81`，没有合并整个 main。

| 文件/工具 | 用处 |
| --- | --- |
| [`codex/AGENTS.light.md`](../codex/AGENTS.light.md) | 普通任务默认的简短交付偏好；不触发 DIGR。 |
| [`codex/ROUTER.experimental.txt`](../codex/ROUTER.experimental.txt) | 用户明确选择实验通道时的替代路由段，只负责获取与版本交接。 |
| [`codex/manifest.json`](../codex/manifest.json)、`codex/VERSION` | 独立身份、启动导航、来源 pin 和分发文件摘要。 |
| [`codex/STARTUP.md`](../codex/STARTUP.md) | 仓库启动、消息分类、同轮补充与新轮次边界。 |
| [`codex/PROTOCOL.md`](../codex/PROTOCOL.md)、[`HELP.md`](../codex/HELP.md) | 原生深执行、参数、交付、来源、挑战、计时及停止规则。 |
| [`runtime/codex_profile.py`](../runtime/codex_profile.py)、[`tools/codex_profile.py`](../tools/codex_profile.py) | 离线文件检查、指令导出、宿主事件边界预览和保守的能力描述。无第三方依赖。 |

根目录 `manifest.json`、VERSION、Alpha 5 的 entry/core/runtime 和原执行 bundle 仍保持原有语义。Codex profile 不调用旧参数解析器执行新语义。当前用户正在运行的 stable `P_run` 不因本目标分支改变。

**分支文件不是全局安装。** 本交付不写用户的 AGENTS、config.toml，不启服务器、MCP、Goal、代理、付费 API 或自动化，不切换 stable/main。没有新增长期运行成本。

## 需求来自什么问题

资料项目中，用户要的是把原有 PDF/EPUB 或已处理文件裁剪、拼接成一份有目录索引的读物；实际工作却扩成结构重写、内容清洗和多轮付费审查。差距首先是交付定义与停止方式，而不是缺少更多审核文件。

因此轻量层直接约束四件事：产物先明确；沿用已确认的处理粒度；做出可用成品；检查够用后继续交付。复杂任务的计划对齐不被扩大成每条消息审批。保护真实预算、权限与原件，不新增泛化的“安全闭环”。

用户已选择“普通任务默认轻量 + DIGR 深执行”，并允许选择性引入 main 的新执行语义。本版据此设计，不假设必须兼容 Alpha 5 的硬时间默认。

## Codex 与 ChatGPT：差的是宿主形态，不推断智力高低

| 差异/事实 | 适配决定 | 依据 |
| --- | --- | --- |
| Codex 通过全局/项目/子目录逐层加载 AGENTS；默认合并预算32KiB。ChatGPT Work 不读本地 Codex 配置。 | 默认层简短；完整协议按调用读取。不能声称写了本地规则就作用于所有 ChatGPT 产品。 | [AGENTS 官方说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[Developer settings](https://learn.chatgpt.com/docs/developer-settings) |
| App Server 的 `turn/steer` 向进行中轮次追加输入；它不是 `turn/start`。中断另有实际状态。 | 明确区分同轮补充、新轮次、压缩恢复和停止；不重新做已经接受的工作。边界 CLI 是离线预览，并未接入 App Server。 | [App Server](https://learn.chatgpt.com/docs/app-server) |
| Codex 可有本地文件/命令和可观察进程，具体能力随客户端、环境和工具配置变化。 | 工程验证优先用实际文件、命令和结果；不能把工具名、安装状态或配置布尔值当完成证据。 | [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)、本轮实际文件/终端工具 |
| ChatGPT Deep Research 具有专门的来源、研究计划和引用报告工作流；仅支持符合条件的已启用 Apps。 | Codex 中不假设存在同名 Deep Research 后台服务；用实际可用搜索/连接器/文件研究完成来源任务。 | [Deep research 官方说明](https://help.openai.com/en/articles/10500283-deep-research-in-chatgpt) |
| 官方模型使用建议明确讨论了强制反复读文档、过量检查和过度权限用语带来的消耗与提前停止。 | 按具体需求读资料、检查与告知；去掉重复程序，保持完成约定产物的持续性。此为相关设计依据，不保证所有模型效果相同。 | [OpenAI prompting guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) |
| 当前会话有 shell 不代表有最终输出拦截器；墙钟或短进程时钟也不等于持续有效工作计时。 | 执行/证明分开。普通使用以 MODEL_NATIVE 交付；缺失证明写未知，不伪称 CANONICAL。 | [main 的 capability negotiation](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/165c95bbbd96d2171687bba073774b211920ef81/runtime/capabilities.py)、实际宿主边界 |

没有做同题同条件的模型比较，因此本版不把这些事实解释成“Codex 推理不如 ChatGPT”。也不把某一客户端的能力扩大成所有 Codex/ChatGPT 的通性。

## 从 stable / main 分别取什么

- 保留 stable 的原任务忠实、结果主权、候选结果后的实质回查、真实来源、不可变 pin、本地路由不复制语义等原则。
- 参考 [main 的模型协议](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/165c95bbbd96d2171687bba073774b211920ef81/entry/MODEL_PROTOCOL_SOURCE.md)：执行与证明正交；无参数组自适应；单独时长软目标；显式 min 为硬下限；V 是有价值的持续远距视角；能力不足只影响相应可证明的事实。
- 本版不移入 main 的完整 host server、preflight/commit_delivery、最终 envelope/seal 或全套持久日志。没有实际拦截集成就不声称强制执行。也不默认开启 V、D、并行代理或大批 API 工作。
- 本版特有：默认交付约束、同轮补充/压缩恢复边界、以最小充分状态继续工作、禁止把文件拼接擅自扩大为内容重著、按真实产物停止。

## 怎么试用、怎么安装

在本分支根目录运行（Python >=3.10；无安装步骤）：

```text
python -B tools/codex_profile.py check
python -B tools/codex_profile.py instructions light
python -B tools/codex_profile.py instructions experimental-router
```

`check` 只证明这份本地分发的身份/文件摘要匹配，不证明当前 GitHub HEAD、真实模型执行或全局启用。`instructions` 只输出文本，不写设置。

轻量层可以作为用户 CODEX_HOME 下 AGENTS 的一个区块合并，保留原有存储、预算、隐私与项目偏好；若已有 AGENTS.override，应先核对真正生效的层。不要覆盖整个现有文件，也不要只在本仓库放一个 AGENTS 就声称全部项目已生效。全局加载之后需在新会话确认实际加载范围，32KiB 限制也须考虑。

深执行试用需要用户明确选择实验通道，将既有 DIGR 路由段替换为实验路由段；不能两段并列争夺入口。实验路由从 `codex/codex-host-adaptation` 分支实际取得40位 SHA，再只读该 SHA 的 `codex/manifest.json`/VERSION/启动/协议文件。这个显式通道选择是试用前提，不是每次任务的重复审批。

当前生产路由固定 stable，因此**只推送此分支不会激活候选语义**。若未来要把 Codex 设为正式入口，应另行决定发布/通道切换；不能让本轮自举修改偷换正在运行的协议。

宿主边界预览使用一个 UTF-8 JSON 文件，例如：

```json
{
  "event": "STEER",
  "message": "保留原样式，不需要手机适配",
  "active": {"turn_id": "turn-1", "mode": "DEEP"},
  "expected_turn_id": "turn-1"
}
```

```text
python -B tools/codex_profile.py boundary --input path/to/event.json
```

返回 CONTINUE/DEEP，保留原任务。把 event 换成 NEW_TURN 时需去掉 expected_turn_id，普通消息得到 LIGHT；任何候选前缀得到 ROUTE_PENDING，**不是 EXECUTING**。goal_changed 必须由调用者语义判断，不靠关键词猜测。实际用户可见消息若无可用宿主事件，应由模型据上下文判断；不得伪造 turn/steer 遥测。

能力预览的 JSON 用 `AVAILABLE|UNAVAILABLE|UNKNOWN` 值与明示字段；例如 `{"shell":"AVAILABLE"}`，运行 `capabilities --input ...`。即使所有字段 AVAILABLE，工具也只报告 MODEL_NATIVE/NONE，因为能力声明不是本轮执行证据。

## 验证范围与模型效果复查

自动测试检查的是分发完整性、路由候选边界、非粘连轮次、steering 保留、目标变更、压缩/中断、CLI 错误处理和“布尔能力不能铸造 canonical”。同时运行原 stable 回归，防止候选包破坏旧执行器。它们不证明模型必然遵守偏好或内容必然优质。

Windows 验证还处理了三个实际问题：增加 `.gitattributes` 防止 Git 检出把原始 LF 改为 CRLF；测试使用 UTF-8 模式及 `requirements-test.txt` 的测试专用 jsonschema；原有软时间状态测试显式写 `B=0,S(b=0)`，不再与 Alpha 5 的硬默认冲突。三个路径测试改为直接测试同一可移植性边界，避免 Windows 先别名化路径而让测试失效。旧执行器与核心协议未因此改动。

本轮实际结果：Windows / Python 3.12，完整套件259项，257通过、2跳过；其中新增候选测试13项通过。`tests/validate_repo.py`、`tools/codex_profile.py check` 与分发树/摘要校验通过。测试专用 jsonschema 4.26.0 安装在 D 盘隔离目录，未添加运行时依赖。未进行新模型会话的行为效果实验。

以下是实际试用时要观察的场景，**不是声称已通过的模型效果实验**：

| 输入/情况 | 应观察到的结果 |
| --- | --- |
| “将这些 PDF/EPUB 裁剪拼成一本，目录方便跳转，保留样式” | 确定组合形式与内容边界，交付可读文件；不变成重写教材、全量清洗或多端改造。 |
| “继续，只是不需要手机适配”在进行中到达 | 去掉这一要求并继续现有有效工作；不重做已经确认的编排。 |
| 检查通过，仍有未组装的正式成品 | 继续做成品；不把完成检查当成任务完成。 |
| 显式 DIGR 但无最终输出拦截器/可靠分段时间 | 继续能做的研究和制作；报告 MODEL_NATIVE 与未知证明，不输出假 canonical。 |
| 用户纠正了目标或明确停止 | 对齐真实修改或停止；不以冻结契约拒绝纠正，不靠后台任务绕过停止。 |
| 新一轮普通小改动 | 只按轻量层处理，不重建 DIGR 计时或证明文件。 |

维护 profile 时，修改指令后须更新 `codex/manifest.json` 的 file_sha256，再运行 check。根目录 SHA256SUMS/FILE_TREE 仍按原构建工具更新。摘要是分发一致性工具，不是对模型语义或文件内容的独立审查。
