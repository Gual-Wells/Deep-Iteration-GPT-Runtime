# Codex 候选适配 0.2

本分支从 stable Alpha 5 建立，参考 main Berta2；当前候选改为以问题研究、流程探索、交付质量与注意力聚焦为中心。用户已选择显式 DIGR 起点 N12/R4/D3/V3，真实能力和授权允许时优先 L3，复杂任务上调。

## 从哪里看

| 入口 | 内容 |
| --- | --- |
| [执行协议](../codex/PROTOCOL.md) | 深入研究问题、竞争解释、路线比较、代表性试作、持续改进成品及原生判断 |
| [参数单位责任](../codex/PARAMETERS.md) | 每一个 N/R/D/V 负责的范围与效果；L 的实际信息边界；禁止通过碎片化缩小单位重量 |
| [工作台指南](../codex/WORKBENCH.md) | 用一份有内容的笔记聚焦当前问题、按需取回原材料、准备 D/V 输入 |
| [研究与设计依据](CODEX_QUALITY_DESIGN.md) | 原问题、方案取舍、Anthropic/OpenAI 一手资料、main 对照及具体实现理由 |
| [单位应用演练](../codex/examples/UNIT_RESPONSIBILITY.md) | 搜索、局部复查、非局部试作、持续观察等工作的责任区分 |
| [本轮任务演练结果](CODEX_TRIAL_RESULTS.md) | 两条件实际成果、独立比较、共同缺口及其导致的候选修改 |

## 使用方式

普通任务合并 [轻量交付偏好](../codex/AGENTS.light.md) 后使用；复杂任务把主要投入放在核心问题、真实内容和产物上。显式 DIGR 取得 pinned 候选协议后，读取 PROTOCOL 与 PARAMETERS；辅助工具按实际任务需要使用。

```text
python -B tools/codex_profile.py depth
python -B tools/codex_workbench.py init --request D:/task/request.txt --work D:/task/WORK.md
python -B tools/codex_workbench.py focus --work D:/task/WORK.md --topic "当前研究问题"
python -B tools/codex_workbench.py challenge --kind D --work D:/task/WORK.md --question "这项非局部介入应实际研究什么？" --candidate D:/task/current.md
```

工作台支持的是材料与问题取用。它不替模型执行语义判断、自动派代理或调用付费模型 API。函数/CLI 的功能检查仅检查相关行为；模型实际效果由任务内容和成品判断。

## 版本与安装状态

独立入口是 `codex/manifest.json` 和 `codex/VERSION`；根目录仍保留 Alpha 5 原协议，不混用其参数解析器。实验路由模板是 [ROUTER.experimental.txt](../codex/ROUTER.experimental.txt)，只承担真实获取、不可变 pin 和版本交接，不复制执行语义。

本分支更新不会自动写入全局 AGENTS/config 或改变 stable/main。选择实验通道时，用实验路由替换既有 DIGR 路由段，避免两个入口并存；保留用户既有的存储、预算、隐私与项目偏好。已明确选择通道之后，常规任务无需重复审批。

## 核查范围

保留必要的版本/文件检查和 Windows LF 配置作为分发维护工作，不把这些表述为交付质量。运行 `python -B tools/codex_profile.py check` 可检查本地分发，不能据此声明模型已完成任务。原稳定执行器保持原有语义；本轮针对新工作台与候选改动完成相关核查即可。
