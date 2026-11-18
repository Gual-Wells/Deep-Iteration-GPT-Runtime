# DIGR Codex Stable 1.0 使用说明

| 调用 | 工作方式 |
| --- | --- |
| `DIGR：核对这组设计的机制并完成约定修改` | Codex 研究和交付。外部视角有价值时，可请 Claude 作第一层子议会成员，按共享钱包可用余额使用。 |
| `DIGR：：让 Claude 一起研究并制作这篇解释` | 可用两层。付费前先向用户说明实际角色、费用上界和范围。按委托让 Claude 指导实质内容取舍或出稿。 |
| `DIGR：：用 Sonnet 完整讲通这篇论文` | 第二层为完整论文读物，接入同 pin 的[论文增量](../paper/PROTOCOL.md)。 |
| `DIGR(Less)(X)：任务` | Less 研究投入，最终文件按配置交付至本人 Gmail。 |
| `DIGR/help` | 只读帮助。 |

一处原生议会负责初议和再议，Claude 第一层是其内部研究成员。第二层的正式内容来源按实际对象登记。两层每次提交均有本机 Split、费用预留和公开原文转播。费用许可、作品决定和调用发生事实分别记录。机器上有凭据或已经准备请求时，仍须满足任务适用的角色和费用条件。详见 [PROTOCOL](PROTOCOL.md)、[COUNCIL](COUNCIL.md)、[CONSULT](CONSULT.md)、[SPLIT](SPLIT.md)。

ASCII `:` / `::` 与全角等价。真实获取 Codex 分支、固定同 SHA 协议后解析，双冒号整体消费。三枚以上分隔冒号和空任务无效。完整只读/询问调用也可深执行，操作范围按实际委托。讨论和引用有原来的含义。DIGRC、DIGRP 兼容拼写沿相同角色和费用条件。

Light/Less/Default/More/Max共用投入预设；默认N12/R4/D3/V3/L3/M1。时间与来源按实际问题补齐，参数为实质责任，不是角色名、命令数或费用额度。Codex 沿当前的模型和推理设置工作。只有预见超巨量批任务才按实际收益考虑多档协作。两层 Claude 的研究与内容工作均另记来源，原生 N/R/D/V/L/M 仍由 Codex 承担。详见[PARAMETERS](PARAMETERS.md)。

任务以[FOUNDATION](FOUNDATION.md)对齐真实对象与已有决定；明确更改直接落实，常规任务内操作沿既有授权。未按RETURN结束或被明令停止前，后续消息沿当前任务，任务按原 P_run 接续。精确 `DO：` 或 `DO:` 把本条原话接入当前任务。新完整单／双冒号与用户明确更改更新相应许可，其他补充沿用仍适用的决定。暂停与停止按实际范围生效。

`X`只控制实际最终文件出口，无X在当前聊天交付；`(X)`／`(X=Gmail)`选择本机配置的本人Gmail，仍用原生连接器发送和读回。没有文件不另造附件，详见[DELIVERY](DELIVERY.md)。

## 本机工具

`python -B tools/codex.py consult prepare`组装实际任务包，不发送。`consult split --input native-decision.json --out split-plan.json`机械附加当前绑定；`consult call --split-plan …`本机Split核对后才在真实预算内作一次提交；`consult inspect`读公开事实，`reconcile-cost`只对账。双冒号使用 `consult budget-preview` 和 `consult budget-approve` 记录已说明的费用范围与真实答复。内部论文请求用 `--paper-root` 绑定具体对象。

`profile check`只检本地完整性，`acquire`真实联网取pin；`live work/read/ack` 保存真实阶段和无损公开流，宿主实际转播后再确认显示。 `usage` 返回真实 Claude 美元及 Codex 模型和档位的用量证据。 `paper`、`visits` 和 `return` 保存作用域、事实与接续。它们不代替模型的研究、内容判断或有效指导的落实。完整执行按[PROTOCOL](PROTOCOL.md)及manifest全部核心，操作细节见[WORKBENCH](WORKBENCH.md)。
