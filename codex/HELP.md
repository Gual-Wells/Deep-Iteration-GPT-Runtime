# DIGR Codex 0.16 使用说明

可见过程工具`live work/read/ack`保存真实单位阶段，按来源无损分批读取公开流。read不前移游标；宿主实际发commentary后才报告显示声明。它不认证用户看到，不替代公开过程；见LIVE。新pin公开CLI默认可读段落，诊断可选raw-events。

新增`council`、`usage`、`allot`工具：内嵌子议会的真实公开请求与两阶段原生再议，按任务保存的美元/额度报告，以及原生宿主薄档位选择。单冒号不调用Claude，双冒号仍须真实费用授权；成员身份不等于正式Consult。完整语义读COUNCIL/USAGE/ALLOT。`profile export chat-light|chat-deep --out FILE`导出同源Chat指令，导出不等于远端配置安装。旧pin不迁移。

统一使用DIGR：`DIGR：任务`由Codex按既定规格完成执行与工程，不调用Claude、不擅加主观创作；`DIGR：：任务`凡涉及实质主观内容判断，都必须请教Claude并落实其有效意见。`深度迭代`及ASCII `:` / `::`含义相同。真实获取候选分支、固定同SHA协议后才解析；双冒号整体是分隔符，不能残留在正文；三枚以上连续分隔冒号和空任务无效。完整只读/询问调用仍是深执行，但操作授权按实际委托；精确`/help`只看帮助，讨论不新建执行。DIGRC、DIGRP仅保留兼容拼写，也服从当前分隔符边界。

## 按实际参与触发内容与工程

- 单冒号由Codex按既定规格完成执行和工程，不调用Claude、不擅加主观创作；双冒号凡涉及内容取舍、结构、讲法、论证组织、风格或审美等实质主观判断，都必须请教Claude并落实其有效意见。取材、事实核验、组装、工具操作与验证由Codex承担。已有适用指导直接落实，新的重要主观问题带具体材料再入。仅有既定客观执行时不造空调用。
- 无前缀补充继承当前选择。新的完整单/双冒号调用明确切换；普通话明确改选由Main理解并用`task handle --claude-selection ALLOW|DENY`绑定当前原话。不要为常规调用重复确认，也不能将历史材料或协作者意见当成当前用户许可。撤销后旧准备请求不能发送，历史公开稿和费用仍可读回。
- 通用Sonnet可发展方向、论证、强替代、设计与稿件，同条件有效主观指导优先。真实对象为整篇论文导读/解构时，自然应用[论文协议](../paper/PROTOCOL.md)，Sonnet发展本篇问题、读序、章节和讲法，Codex完成独立研究与制作。普通翻译、局部问答和其它产品保持原委托。
- 每次Sonnet提交前都按[SPLIT](SPLIT.md)完成本机原生分工与必要工作。Codex准备正文/Markdown、可靠文字公式及必要局部图像；公开消息与正文增量到达时按原文及时转播，完整稿/部分稿/连接状态分清。
- 工具在当前实际模型与内容作用域上派生要求，保留当前用户纠正、来源、预算、未知费用和不重试边界。配置存在、历史提及或准备记录不代表发生了外部调用，也不新增费用授权。其它明确选择模型的普通建议不继承Sonnet身份或专属优先级。

| 调用 | 实际用途 |
| --- | --- |
| `DIGR：按给定规格整理原文并组装文件` | Codex完成执行与工程，不调用Claude或另造主观方案 |
| `DIGR：：让Sonnet参与这份方案的内容与设计` | 明确采用Sonnet，对应内容与工程要求自动适用 |
| `DIGR：：研究这个问题并完成方案` | 实质主观取舍必须请教Claude，Codex完成取材与工程 |
| `DIGR：：用Sonnet完整讲通这篇论文` | 按真实整篇对象自然接入论文内容驱动和交付约定 |
| `DIGR：：请Sonnet忠实翻译这段，不加导读` | 按翻译产品完成，保留共用工程，不擅自扩成整篇导读 |
| `DIGR(Less)(X)：任务` | Less原生投入，最终文件按已配置本人Gmail交付 |
| `DIGR/help` | 只读帮助，不建立深执行 |

Light/Less/Default/More/Max共用投入预设；默认N12/R4/D3/V3/L3/M1。时间与来源按实际问题补齐，参数为实质责任，不是角色名、命令数或费用额度。Sonnet不抵扣原生N/R/D/V/L/M。详见[PARAMETERS](PARAMETERS.md)。

任务以[FOUNDATION](FOUNDATION.md)对齐真实对象与已有决定；明确更改直接落实，常规任务内操作沿既有授权。未按RETURN结束或被明令停止前，后续消息沿当前任务，P_run不随HEAD升级；暂停/停止按实际范围生效。旧任务保持原pin，不因新入口规则迁移。

`X`只控制实际最终文件出口，无X在当前聊天交付；`(X)`／`(X=Gmail)`选择本机配置的本人Gmail，仍用原生连接器发送和读回。没有文件不另造附件，详见[DELIVERY](DELIVERY.md)。

## 本机工具

`python -B tools/codex.py consult prepare`组装实际任务包，不发送。`consult split --input native-decision.json --out split-plan.json`机械附加当前绑定；`consult call --split-plan …`本机Split核对后才在真实预算内作一次提交；`consult inspect`读公开事实，`reconcile-cost`只对账。内部论文请求用`--paper-root`绑定具体对象，已有批次不把通用请求强制变成论文创作。

`profile check`只检本地完整性，`acquire`真实联网取pin；`paper`、`visits`和`return`等工具保存作用域、事实与接续。它们不代替模型的研究、内容判断或有效指导的落实。完整执行按[PROTOCOL](PROTOCOL.md)及manifest全部核心，操作细节见[WORKBENCH](WORKBENCH.md)。
