# Architecture 2.3

DIGR 由控制平面与原生执行面组成。控制平面负责：触发解析、U0、N 提示优化、T 语义校准、资源门控、结果回代和运行记录；执行面仍由 ChatGPT 原生规划/推理/工具能力完成。

核心数据流：`Invocation(raw N/T) -> U0 -> P* -> semantic T calibration -> adaptive native execution -> budget adequacy -> result re-entry -> report`。

parser 与 schema 只负责结构，不承担智能决策。T 的任务规模解释和停止判断属于模型运行时。
