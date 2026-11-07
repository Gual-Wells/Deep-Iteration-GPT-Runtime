# Codex 专用通道 0.4

本分支从stable Alpha5建立，参考main Berta2。0.4在0.3的内容与方法改进上，修正Codex宿主选择：D/V固定真实独立代理与L3，取消低L默认和兜底；初始化与各轮自举按固定格式在用户可见流报告。显式DIGR无参数下限N12/R4/D3/V3只自主上调，默认轻量保留普通任务的范围。

先读[上一轮记录、D/V局限及本次修订](CODEX_RUN_REVIEW_20261107.md)，可以直接看到各参数的已登记行为。0.3的[历史研究与设计依据](CODEX_QUALITY_DESIGN.md)保留，不把历史L1或三条来源分工追认为新的L3/V3。

## 从哪里看

| 入口 | 内容 |
| --- | --- |
| [执行协议](../codex/PROTOCOL.md) | 内容与方法、真实L3分工、当场输出及主线处理 |
| [参数单位责任与输出格式](../codex/PARAMETERS.md) | N/R/D/V单位重量、Codex固定L3、INIT/START/RETURN/END/ADJUST模板 |
| [工作台指南](../codex/WORKBENCH.md) | 用一份有内容的笔记聚焦当前问题、按需取回原材料、准备 D/V 输入 |
| [历史0.3研究](CODEX_QUALITY_DESIGN.md) | 官方/社区材料、条件化方法及当时实物观察 |
| [单位应用演练](../codex/examples/UNIT_RESPONSIBILITY.md) | 搜索、局部复查、非局部试作、持续观察等工作的责任区分 |
| [历史0.2任务演练](CODEX_TRIAL_RESULTS.md) | 上一版两条件成果、共同缺口和当时修改；不冒充0.3的效果证据 |

## 使用方式

普通任务合并 [轻量交付偏好](../codex/AGENTS.light.md) 后使用；复杂任务把主要投入放在核心问题、真实内容和产物上。显式 DIGR 取得 pinned 候选协议后，读取 PROTOCOL 与 PARAMETERS；辅助工具按实际任务需要使用。

```text
python -B tools/codex_profile.py depth
python -B tools/codex_workbench.py init --request D:/task/request.txt --work D:/task/WORK.md
python -B tools/codex_workbench.py focus --work D:/task/WORK.md --topic "当前研究问题"
python -B tools/codex_workbench.py challenge --kind D --work D:/task/WORK.md --question "这项非局部介入应实际研究什么？" --candidate D:/task/current.md
```

工作台支持的是材料与问题取用。它不替模型执行语义判断、自动派代理或调用付费模型 API。函数/CLI 的功能检查仅检查相关行为；模型实际效果由任务内容和成品判断。

已有公开摘要需要插入时可选 `record --work D:/task/WORK.md --topic "当前研究问题" --text-file D:/task/note.txt`；直接编辑同一笔记照常有效。它没有新建日志数据库，也不自动判断采纳、统计参数或认证执行。已有工具/代理/API授权按实际范围持续有效，资源选择由模型负责。

## 版本与安装状态

独立入口是 `codex/manifest.json` 和 `codex/VERSION`；根目录仍保留 Alpha 5 原协议，不混用其参数解析器。实验路由模板是 [ROUTER.experimental.txt](../codex/ROUTER.experimental.txt)，只承担真实获取、不可变 pin 和版本交接，不复制执行语义。

仓库更新自身不会写入全局AGENTS/config或改变stable/main。本用户本轮已要求本机Codex固定高L，应使用专用路由替换原stable路由段，不能只修改候选文件又让本机继续进旧通道。全局仅保存真实获取、pin和路径交接；L与输出格式仍从同SHA仓库加载，不复制到本地路由。其它存储、预算、隐私与项目偏好保留，安装过程另有D盘原件备份。

OpenAI Docs说明AGENTS指令在运行开始时构建，新运行/会话读取更新，已有运行不视为自动热更新。[官方加载说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。文件已配置与某个现存会话已加载是不同事实，最终以实际路由和INIT的pin/参数为准。离线check中的global_install_performed=false只表示该检查函数不安装，不是全机安装状态检测。

## 核查范围

保留必要的版本/文件检查和 Windows LF 配置作为分发维护工作，不把这些表述为交付质量。运行 `python -B tools/codex_profile.py check` 可检查本地分发，不能据此声明模型已完成任务。原稳定执行器保持原有语义；本轮针对新工作台与候选改动完成相关核查即可。
