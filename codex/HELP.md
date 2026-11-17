# DIGR Codex 0.14 使用说明

统一入口是 `DIGR：任务` 或 `深度迭代：任务`。真实获取候选分支、固定同SHA协议后，按任务研究、制作与交付。完整只读/询问调用仍是深执行，但操作授权按实际委托；精确`/help`只看帮助，讨论不新建执行。DIGRC、DIGRP仅保留兼容拼写，用户不再需要用它们解锁Sonnet协作。

## 按实际参与触发内容与工程

- 普通DIGR由Codex承担完整原生责任。当前任务实际准备采用Sonnet时，即应用[CONSULT](CONSULT.md)的内容关系和全部发送前工程要求；首次和中途采用相同，不重开任务、不改写冻结原话。
- 通用Sonnet可发展方向、论证、强替代、设计与稿件，同条件有效主观指导优先。真实对象为整篇论文导读/解构时，自然应用[论文协议](../paper/PROTOCOL.md)，Sonnet发展本篇问题、读序、章节和讲法，Codex完成独立研究与制作。普通翻译、局部问答和其它产品保持原委托。
- 每次Sonnet提交前都按[SPLIT](SPLIT.md)完成本机原生分工与必要工作。Codex准备正文/Markdown、可靠文字公式及必要局部图像；公开消息与正文增量到达时按原文及时转播，完整稿/部分稿/连接状态分清。
- 工具在当前实际模型与内容作用域上派生要求，保留当前用户纠正、来源、预算、未知费用和不重试边界。配置存在、历史提及或准备记录不代表发生了外部调用，也不新增费用授权。其它明确选择模型的普通建议不继承Sonnet身份或专属优先级。

| 调用 | 实际用途 |
| --- | --- |
| `DIGR：研究这个问题并完成方案` | 完整原生主线，按任务选择方法与已有授权内资源 |
| `DIGR：让Sonnet参与这份方案的内容与设计` | 统一任务内采用Sonnet，对应内容与工程要求自动适用 |
| `DIGR：用Sonnet完整讲通这篇论文` | 按真实整篇对象自然接入论文内容驱动和交付约定 |
| `DIGR：请Sonnet忠实翻译这段，不加导读` | 按翻译产品完成，保留共用工程，不擅自扩成整篇导读 |
| `DIGR(Less)(X)：任务` | Less原生投入，最终文件按已配置本人Gmail交付 |
| `DIGR/help` | 只读帮助，不建立深执行 |

Light/Less/Default/More/Max共用投入预设；默认N12/R4/D3/V3/L3/M1。时间与来源按实际问题补齐，参数为实质责任，不是角色名、命令数或费用额度。Sonnet不抵扣原生N/R/D/V/L/M。详见[PARAMETERS](PARAMETERS.md)。

任务以[FOUNDATION](FOUNDATION.md)对齐真实对象与已有决定；明确更改直接落实，常规任务内操作沿既有授权。未按RETURN结束或被明令停止前，后续消息沿当前任务，P_run不随HEAD升级；暂停/停止按实际范围生效。旧任务保持原pin，不因新入口规则迁移。

`X`只控制实际最终文件出口，无X在当前聊天交付；`(X)`／`(X=Gmail)`选择本机配置的本人Gmail，仍用原生连接器发送和读回。没有文件不另造附件，详见[DELIVERY](DELIVERY.md)。

## 本机工具

`python -B tools/codex.py consult prepare`组装实际任务包，不发送。`consult split --input native-decision.json --out split-plan.json`机械附加当前绑定；`consult call --split-plan …`本机Split核对后才在真实预算内作一次提交；`consult inspect`读公开事实，`reconcile-cost`只对账。内部论文请求用`--paper-root`绑定具体对象，已有批次不把通用请求强制变成论文创作。

`profile check`只检本地完整性，`acquire`真实联网取pin；`paper`、`visits`和`return`等工具保存作用域、事实与接续。它们不代替模型的研究、内容判断或有效指导的落实。完整执行按[PROTOCOL](PROTOCOL.md)及manifest全部核心，操作细节见[WORKBENCH](WORKBENCH.md)。
