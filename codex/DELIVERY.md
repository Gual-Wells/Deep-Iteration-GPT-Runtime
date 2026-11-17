# X：通过 Gmail 交付最终文件

X 是统一DIGR的独立文件交付栏；旧C/P写法兼容。本版只支持已连接的原生 Gmail，发送到本人邮箱；文字答复始终留在当前聊天。没有 X，文件也在当前聊天交付。没有最终文件就跳过，不为交付另造报告、附件或测试文件。

## 调用与任务范围

- `DIGR(X)：任务`：最终文件发送到本人 Gmail。
- `DIGR()(X=Gmail)：任务`：默认投入，显式选择同一本人 Gmail。
- `DIGR(N=12,R=4)(X)：任务`：常规参数后接独立的最后一组 X。

`(X)` 与 `(X=Gmail)` 等价。X 不能混入投入参数组；正文、引文和工具结果中的 X 不启用交付。空值、重复 X、未知或非 Gmail 目标明确报错，不猜目标或回退。

同一任务接续保留选择，新任务重置。任务创建时冻结本人邮箱；随后本机配置变化不重定向进行中的任务。用户撤销 X 后，余下文件只在本聊天交付，既往发送及未决结果仍保留并如实报告。旧任务继续使用其实际 pin 的交付语义。

## 原生 Gmail 操作

1. 从任务记录取得冻结的 `policy`。用当前 Gmail `get_profile` 读取实际邮箱，核对账号与本人收件地址都匹配该快照；不从姓名或正文猜地址。
2. 选择真正的最终文件，每次一份文件、一封邮件；多文件逐个执行相同步骤。保存文件名、字节数与 SHA256。用 `delivery prepare` 冻结候选，再用 `mark-sending` 保存本次身份依据及发送意图。只有新返回的 `send_allowed:true` 才发送一次；重放、inspect、resume 都不授予第二次发送。
3. 调用现有原生 `send_email`，`to` 使用已核对的本人邮箱，`attachment_files` 使用单个原文件的 Windows 绝对路径字符串；不附加 CC/BCC。保存实际发送结果及 message ID。附件不手工编码进 MIME 正文。
4. 用 `read_email` 的 `format:"full"` 读回该 message ID，核对 From、To、SENT 及每个附件的文件名、字节数。保存原生完整结果，再 `reconcile` 记录真实读回。邮件总 `size_estimate` 不是附件大小。
5. 在当前聊天交付成品入口和实际发送结果。API 接受与附件元数据匹配不代表用户已打开邮件；只有实际取回原始附件并比对 SHA256 时才说明远端字节一致。

原生 `send_email` 的可用参数结构如下；to 和文件路径须来自本次实际 profile 与候选，不复制占位值。`attachment_files` 是单一路径字符串，不是 JSON 数组或对象列表：

```json
{
  "to": "<已核实的本人邮箱>",
  "subject": "最终文件",
  "payload": {"mime_type": "text/plain", "body": {"content": "最终文件见附件。"}},
  "attachment_files": "D:\\work\\output\\complete.pdf"
}
```

`get_profile` 使用空对象 `{}`；`read_email` 使用 `{"message_id":"实际发送返回的ID","format":"full"}`。需要附件字节时，先从真实读回结果选择支持读取的附件，再按完整 attachment ID 或插件规定的精确文件名调用 `read_attachment`，不猜 ID。

## 记录命令与依据

使用与本轮协议匹配的分发：`python -B <distribution>/tools/codex.py delivery --help`。已安装技能从 `CODEX_HOME/digr-codex/toolchain.json` 定位实际工具；它不是新调用的协议获取或送达证明。以下文件均为私有任务数据，公开仓库不保存真实邮箱、邮件或回执。

| 命令（在 `delivery` 后） | 输入与作用 |
| --- | --- |
| `prepare --root TASK --input prepare.json --operation-id OP` | `{candidate_id,policy,files,authorization_source_ref}`，files 是实际最终文件路径；返回 delivery_id，无 X/无文件直接跳过 |
| `mark-sending --root TASK --input sending.json --operation-id OP` | `{delivery_id,identity,identity_evidence}`；先保存本次发送意图，再返回 attempt_id 和一次发送许可 |
| `reconcile --root TASK --input outcome.json --operation-id OP` | `{delivery_id,attempt_id,outcome,receipt}` 记录 sent；uncertain/not_sent 则提供实际 evidence 与 evidence_path |
| `inspect --root TASK`（或 `resume`） | 查看已保存状态和未决尝试，不发送 |
| `completion --root TASK --input final-files.json` | `{files,policy?,candidate_id?}`，核对实际最终文件的交付覆盖 |

写入命令可带 `--expected-revision N`。同一 operation ID 只重放相同内容，且不再次发送。文件改变后需重新审阅候选，旧回执不能满足新版。

`identity` 使用实际 account/recipient、`account_confirmed:true`、`recipient_confirmed:true` 及 `binding_basis:"stable-identifiers"`。身份 JSON 保存 `{"identity":实际identity对象,"source_evidence":[实际profile结果路径]}`。发送依据直接保存原生 send_result；读回依据直接保存原生 full 结果，或包在 `readback_result` 下。回执包含候选/尝试 ID、冻结 policy 的 target/channel/account/recipient/transport、`evidence_kind:"gmail-api"`、实际 message_id、identity、`readback:{completed:true,attempt_correlated:true}`、三个依据路径和真实 readback_result。工具从保存的原生 MIME 和标签（label_ids 或 labelIds）核对事实，不以自写“成功”替代服务结果。

发送超时或中断时先检查同一消息/本人邮箱，再决定结果；未找到一次搜索结果不证明没有发送。未决尝试先对账，不能盲重试。已经验证的文件不因恢复或最终收口重复发送。当前依据丢失时，可重新读回同一实际消息并以相同归一回执补证；补证保存新的 current_proof、保留历史缺口，不新建发送尝试。

## 论文对象与父任务共用交付记录

新批次用 `paper init --task-root PARENT` 关联同一 P_run。每篇先生成并审阅一份完整 PDF；不拆章节或生产职责文件交付。

- 无 X：本篇为 `READY_LOCAL` 后直接 `paper return`。
- 有 X：所有 `delivery` 操作的 `--root` 用 PARENT，candidate_id 使用本篇已审候选 ID，files 只含该篇完整 PDF。
- 父账本验证后，`paper delivery --root PAPER --input receipt-link.json --expected-revision N --operation-id OP` 只登记 `{candidate_id,delivery_id}`，不再次发送；随后 `paper return`。其他论文和父任务继续。

父任务最终 RETURN 声明实际最终文件并复用已有有效交付记录，不能遗漏已声明的成品，也不把内部笔记或 QA 自动变成附件。未来可增加适配器；本版只实现 Gmail，配置内容不执行命令或代码。
