# 10 — Invocation, Trigger & U0

**Precondition:** the local routing plane has already pinned one repository commit, loaded this version through its manifest, and delegated DIGR semantic authority to it. For an executing 4.1 task, `bootstrap/BOOTSTRAP.md` has also established mandatory task-clock readiness before this layer freezes U0.

## Canonical parameter space
`DIGR（N，T，R，B，S（n，t，r，b），D（s），L（e））：<任务>`

`深度迭代（N，T，R，B，S（n，t，r，b），D（s），L（e））：<任务>`

两种前缀语义完全等价。中英文括号、逗号、冒号、`soft/hard`、`0/1` 与语义清楚的命名/位置参数都可由 ChatGPT 原生理解；canonical syntax 不是硬字符 parser 合同。

## Trigger
当前 4.1 repository version 对候选消息作最终判定。普通任务调用必须：
1. 当前用户消息首部就是 `DIGR` 或 `深度迭代`；
2. 参数块可有可无；
3. 调用头之后存在 `:` 或 `：`；
4. 冒号后任务非空。

正文中提到、引用或讨论 DIGR 不触发。不要用本地 router 或正则程序替代 repository protocol 对用户调用意图的语义判断。

## Help
`DIGR/help` 与 `深度迭代/help` 是等价 meta-command：只返回当前 repository version 的调用、参数、缺省与 proof 定义；不生成 U0、Effective Contract、EST、D-State、task clock 或进化循环。

## U0
去除有效调用头后，将用户真正任务、事实、约束、授权、偏好与交付目标保真为 U0。历史聊天/Memory 可作为任务上下文进入 U0，但不得因此覆盖本 repository version 的协议语义。后续 N/R/S/D/L 均可改变方法，不得偷改 U0。

## Partial application
4.1 不存在独立 AUTO 模式。裸 `DIGR：任务` 只是所有可选参数均缺失的普通 partial invocation；任意子集参数都可显式给出。
