# DIGR Codex 实验全量归档

这是2026年11月9日对Codex profile 0.7.0的探索性试验及后续更正。当前有效结论是：**原默认配置比较不成立**。试验保留默认N12/R4/D3/V3，却在函数头外另加900秒和代理配额限制，实际采用协议文本模拟；不能据截断后的参数缺口评价默认配置。局部预算索引改进及原始观测保留。

协议原文固定于 `b258276632054f7f8d1d8a060e01b98b9c7aa3be`。这里是研究归档，不是新的路由、执行入口或默认参数。

## 当前入口

- [更正后的报告](readable/report.html)
- [逐项更正与撤回判断](readable/interpretation_correction.json)
- [当前结果与解释边界](readable/results.json)
- [全部文件及字节摘要](archive-manifest.json)

## 原件快照和阅读副本

| 位置 | 内容 |
| --- | --- |
| [完整原件快照](snapshots/original-study.zip) | 571个原始文件，包含试题、冻结评分器、全部有效及作废被试、提示文本、CLI探针、D/V研究与再入、产物、原报告及更正记录、QA截图，保留七份试题Git元数据及缓存越界证据 |
| [公开轨迹快照](snapshots/public-trajectories.zip) | 试验主线及子线的公开消息、工具调用和返回、数值用量，以及父会话的实验讨论文字，共11份导出 |
| [阅读副本](readable) | 便于GitHub查阅的材料，统一为UTF-8和LF，Markdown链接改为可移植引用 |
| [归档工具](archive_tools.py) | 校验每个原件摘要、核对阅读副本、向新目录恢复完整实验 |

**字节校验和重评分必须从原件快照恢复。** 阅读副本经过换行及链接转换，且不展开嵌套Git元数据与Python缓存；不能把它当作原始文件系统状态运行评分。快照保存了新增1662字节缓存这一真实范围失败，没有为了得到全绿而删除。

唯一排除的源目录是 `qa/browser-profile/`，即浏览器运行配置和缓存。公开轨迹不包含系统或开发者指令、隐藏推理、全局个性化上下文、账户额度状态和记忆引用元数据。落盘委托字段原本加密，导出只保留摘要和长度，没有尝试解密。排除和转换范围均列入归档清单。

## 主要材料

- [试题和交付规范](readable/frozen_seed/TASK.txt)、[建题器及外部评分器](readable/support/suite.py)、[评分器反例验证](readable/support/fixture-verification.json)
- [原预注册及历史修订](readable/preregistration.json)、[固定运行计划](readable/native_plan.json)、[各组请求文本](readable/native_prompts)
- [普通单代理第一次](readable/native_subjects/b01/portfolio)、[普通协作](readable/native_subjects/b03/portfolio)、[普通单代理第二次](readable/native_subjects/b04/portfolio)
- [被外部截断的模拟组产物](readable/native_subjects/b05/portfolio)、[模拟组研究和主线处理](readable/native_subjects/b05/run)
- [因答案泄漏作废的模拟组](readable/native_subjects/b02)、[被污染的CLI启动](readable/cli_subjects/a01)、[CLI日志](readable/cli_logs)
- [逐题外部验收](readable/scores.json)、[数值用量与会话身份](readable/telemetry.json)、[输入与执行条件核查](readable/verification.json)
- [A原件身份研究及再入](readable/native_subjects/b05/run/explore_a/reentry.md)、[B引用状态研究及完整替代](readable/native_subjects/b05/run/b_followup_findings.md)、[C证据前沿与冻结身份研究](readable/native_subjects/b05/run/c_exploration/research.md)
- [局部代码性能原始测量](readable/artifact_performance.json)、[测量脚本](readable/benchmark_budget.py)、[研究记录的独立审查](readable/support/fidelity-review.json)
- [此前解释归档](readable/interpretation_archive)，原错误保留以供追溯，当前入口以上述更正为准

在本批材料中，各组四项功能验收均通过。模拟组预算函数采用有界引用状态，减少辅助索引存储；其他三类交付未显示明确功能优势。这是已交付文件的局部比较，不能替代完整默认DIGR的有效实验。

## 恢复与复核

需要Python 3.11以上及Git，不需要模型调用、网络服务或第三方依赖。在本目录运行：

~~~powershell
python -B -X utf8 archive_tools.py verify
python -B -X utf8 archive_tools.py extract --out D:/CodexStorage/workspaces/digr-evaluation-replay
Set-Location D:/CodexStorage/workspaces/digr-evaluation-replay
python -B -X utf8 score.py b01 b05 b03 b04
~~~

恢复目录必须尚不存在。本机实验数据按既有约定放在D盘。预期重现四组的功能通过，以及模拟组原有的缓存范围失败；**预期结果不是所有约束全绿**。`telemetry.py`和原始CLI脚本涉及历史宿主路径与模型接入，不应为重评分而运行。

阅读副本中的绝对宿主路径是历史记录。原协议快照、原调用及原目标没有事后改写，也没有把截断实绩倒填为显式函数头。
