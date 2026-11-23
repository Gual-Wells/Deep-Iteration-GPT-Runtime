# DIGR Codex Stable 1.4 使用说明

| 调用 | 工作方式 |
| --- | --- |
| `DIGR：核对这组设计的机制并完成约定修改` | Codex 研究和交付。在能影响成品的取舍定案前，请 Claude 作一次独立首发。第一层累计 0.20 美元内直接使用。 |
| `DIGR：：请 Claude 就这份稿件的结构给建议` | 第二层指导。Main 落实有效建议。 |
| `DIGR：：让 Claude 制作一份可用的解释` | 第二层正式产出。原生 L3 和 Claude 独立完成同范围候选，Claude 对两份成品终裁，Main 落实并交付。 |
| `DIGR：：用 Sonnet 完整讲通这篇论文` | 对完整论文读物执行双边产出与裁决，接入同 pin 的[论文增量](../paper/PROTOCOL.md)。 |
| `DIGR(Less)(X)：任务` | 参考 Less 投入偏好推断各项参数，最终文件按配置交付至本人 Gmail。 |
| `DIGR(More,N=20)：任务` | 参考 More 投入偏好，按显式 N 声明和实际任务推断完整配置。 |
| `DIGR(Less,F=3)：设计离线阅读器的批注同步方案` | 先研究至少 3 个来自相关公开社区的高评价、有特色的项目，再将所得用于相关方案的取舍。 |
| `DIGR/help` | 只读帮助。 |

一处原生议会负责初议和再议。Claude 成员可发起 Codex 支持工作，收到实际结果后继续研究。两层每次提交均有本机 Split、费用预留和公开原文转播。单冒号直接开放第一层，双冒号直接开放两层。第一层每任务累计 0.20 美元，第二层内容指导、候选及终裁共用 1.00 美元。钱包及更窄限额同时约束真实发送。详见 [PROTOCOL](PROTOCOL.md)、[COUNCIL](COUNCIL.md)、[CONSULT](CONSULT.md)、[SPLIT](SPLIT.md)。

Main 主动找 Claude 能影响的开放取舍。Claude 可选择或改划议题并先给出立场，原生议会读原文后再议，由 Main 落实。追加请教要有当前仍值得解决的具体问题。取舍已经确定、超过实际决定窗口或已有材料足够时，原生议会据实际所得推进。

ASCII `:` / `::` 与全角等价。真实获取 Codex 分支、固定同 SHA 协议后解析，双冒号整体消费。三枚以上分隔冒号和空任务无效。完整只读/询问调用也可深执行，操作范围按实际委托。讨论和引用有原来的含义。DIGRC、DIGRP 兼容拼写沿相同角色和费用条件。

Light、Less、Default、More、Max 是五档投入偏好基准，`standard` 兼容为 Light。裸调用以 Default 为参考（N12/R4/D3/V3/L3/M1）。Main 在正式 INIT 前主动考虑能改善交付的加深做法，按真实工作逐项推断。若一次更深入的整体重开可能改变方案，Less 也可以将 R 定得更高。推断值可以越过 Light 或 Max 的参考值，用户逐项声明的值按其适用范围生效。Codex 沿当前模型和推理设置工作。只有预见超巨量批任务才按实际收益考虑多档协作。两层 Claude 的研究与内容工作均另记来源，原生 N/R/D/V/L/M 仍由 Codex 承担。详见 [PARAMETERS](PARAMETERS.md)。

F 是任务级去重项目数，支持 `F=3`、`F(3)` 和 `F（3）`。默认 F0。每个项目须有社区高评价的来源、实际研究的项目原件及一项具体取舍记录。缺额按实际报告，受影响的方案保持暂定。[F 的完整规则](PARAMETERS.md#f-公开社区项目先研)。

F 达额不结束已采用内容的持续生产责任。使具体原件、构造与条件进入实际生产者的工作，在相关候选、反馈和恢复中继续使用、重研或放弃。通用规范复述与“已借鉴”声明不能单独充抵；不增加知识卡、评分或每项目代理门槛。

任务以[FOUNDATION](FOUNDATION.md)对齐真实对象与已有决定；明确更改直接落实，常规任务内操作沿既有授权。未按RETURN结束或被明令停止前，后续消息沿当前任务，任务按原 P_run 接续。精确 `DO：` 或 `DO:` 把本条原话接入当前任务。新完整单／双冒号与用户明确更改更新相应许可，其他补充沿用仍适用的决定。暂停与停止按实际范围生效。

执行与更新均遵循[原语宪法](CONSTITUTION.md)，包括证据与主张相称、决定及动作有真实来源，以及同时满足更新要求与稳定性的版本化义务。

`X`只控制实际最终文件出口，无X在当前聊天交付；`(X)`／`(X=Gmail)`选择本机配置的本人Gmail，仍用原生连接器发送和读回。没有文件不另造附件，详见[DELIVERY](DELIVERY.md)。

## 本机工具

`python -B tools/codex.py consult prepare` 组装实际任务包。第二层用 `--guidance` 或正式对象和阶段参数声明实际目的。`consult split --input native-decision.json --out split-plan.json` 绑定当前计划，`consult call --split-plan …` 通过本机 Split 核对后在真实预算内作一次提交。`consult inspect` 读公开事实，`reconcile-cost` 负责对账。`consult budget-preview` 用于估算，`consult budget-limit` 登记用户给出的更窄限额。`production` 记录实际派发、候选及裁决进入成品的后果，论文请求用 `--paper-root` 绑定对应对象。

`profile check`只检本地完整性，`acquire`真实联网取pin；`live work/read/ack` 保存真实阶段和无损公开流，宿主实际转播后再确认显示。 `usage` 返回真实 Claude 美元及 Codex 模型和档位的用量证据。 `paper`、`visits` 和 `return` 保存作用域、事实与接续。它们不代替模型的研究、内容判断或有效指导的落实。完整执行按[PROTOCOL](PROTOCOL.md)及manifest全部核心，操作细节见[WORKBENCH](WORKBENCH.md)。
