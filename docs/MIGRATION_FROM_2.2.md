# Migration from 2.2 to 2.3

## Breaking semantic change

2.2：T = “人类约 T 时间任务”的参考复杂度，并建议固定时长档位。

2.3：T = **GPT-5.6 Sol / High 约 T 级有效执行的任务规模**；删除固定档位。

迁移要求：
1. 删除任何 `Focused/Analytical/Deep/Research` 时间映射。
2. 删除“人类研究/分析/设计时长”表述。
3. parser 保留 T raw，不把 T 编译成工作量。
4. 在任务停止前加入 T budget adequacy check。
5. 运行报告加入 `t_budget_adequacy`。
6. 远程协议优先固定 commit。
7. 增加测试，防止以后又把 T 退化为字符串标签、硬计时或固定 workload。
