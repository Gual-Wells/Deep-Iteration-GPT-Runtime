# Codex 候选适配 0.3

本分支从 stable Alpha 5 建立，参考 main Berta2。0.3结合本对话、跨厂商官方材料和社区案例，改进纠正之后的实际操作、价值性留痕、分工成果采用、正向创作与自主资源选择。默认轻量与显式深执行同步。显式 DIGR 无参数下限 N12/R4/D3/V3 只自主上调，真实能力和授权允许时优先 L3。

了解结论和理由只需先读[当前研究与改动说明](CODEX_QUALITY_DESIGN.md)。下面是使用入口，不要求逐份通读内部材料。

## 从哪里看

| 入口 | 内容 |
| --- | --- |
| [执行协议](../codex/PROTOCOL.md) | 深入研究问题、竞争解释、路线比较、代表性试作、持续改进成品及原生判断 |
| [参数单位责任](../codex/PARAMETERS.md) | 每一个 N/R/D/V 负责的范围与效果；L 的实际信息边界；禁止通过碎片化缩小单位重量 |
| [工作台指南](../codex/WORKBENCH.md) | 用一份有内容的笔记聚焦当前问题、按需取回原材料、准备 D/V 输入 |
| [研究与设计依据](CODEX_QUALITY_DESIGN.md) | 本轮当前入口：具体机制、官方/社区证据、已采用后果、资源与实际观察 |
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

本分支更新不会自动写入全局 AGENTS/config 或改变 stable/main。选择实验通道时，用实验路由替换既有 DIGR 路由段，避免两个入口并存；保留用户既有的存储、预算、隐私与项目偏好。已明确选择通道之后，常规任务无需重复审批。

## 核查范围

保留必要的版本/文件检查和 Windows LF 配置作为分发维护工作，不把这些表述为交付质量。运行 `python -B tools/codex_profile.py check` 可检查本地分发，不能据此声明模型已完成任务。原稳定执行器保持原有语义；本轮针对新工作台与候选改动完成相关核查即可。
