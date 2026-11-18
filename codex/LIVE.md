# 可见过程与公开流：来源、正文和显示声明

本节修复中间过程退成普通摘要、逐token JSON过长截断、断线后遗漏正文的问题。**实际commentary仍是用户可见入口。** 工具生成的display_text、stdout、文件或ACK不能自己证明消息已被用户看到；宿主必须实际发出，工具只记录其显示声明。

## 原生责任进度

每个实际N/R/n/r有具体问题与有意义方法后报告开始，结束报告所得和后果；D/V的形成、再入、返回与Main处理分别可辨。标题标真实actor及N/R/D/V/S单位，另行标阶段：▶开始、⋯进展、↻再入、↩返回、◆主线处理、✓完成、■线路关闭或⏸受阻。按真正发生合并相邻边界，不按命令凑单位，不预编未启动人物。

独立返回的公开原文或标明概括放引用块，Main中心主张处理另行说明采用/拒绝/待落实和实际后果。普通摘要可以承载实质发现，不能抹掉这些来源和阶段。发生漏报就承认漏报、从当前真实状态恢复；没有记录到的开始保持缺口，不倒填为当时已通知。

`live work --root TASK --input work.json`保存一次真实公开工作事件，字段为actor、kind、unit、stage、text、operation_id、source_ref。kind支持U0/N/R/D/V/S/M/SIDECAR；RETURN/HANDLED须指向实际返回或处理依据。operation_id只重放同一事实，不能改写为新内容。若没有START，记录missing_start，不补造历史。

## Claude公开正文

0.16 `consult call`和`council run-round`默认按exchange/成员无损合并相邻正文，保留换行；段落到达、长度上限或短延迟即发送`public_text`，不等整稿。正文不做摘要、不机械删尾；未完、连接、异常与完整状态分别显示。`--raw-events`仅用于诊断，不替代可读commentary。结束事件只打印小摘要，完整交换用inspect读回，避免结果元数据淹没正文。

原始公开事件与正文仍持久保存；不保留隐藏思考或任意服务字段。中断恢复先读同一exchange，不新发推理，不用“重试一次”补正文。不把本轮普通Consult冒称子议会实际已运行。

## 断点读取与待转播

```text
python -B tools/codex.py live read --root TASK --reader commentary --exchange-id ACTUAL_ID --max-chars 8000
# 实际将display_text/segments原文发到用户commentary后：
python -B tools/codex.py live ack --root TASK --delivery-id ID --evidence-ref ACTUAL_COMMENTARY_REFERENCE --compact
```

省略exchange-id读取原生工作事件。read本身不前移游标，未ACK会重读相同正文。同一exchange和成员的相邻公开增量合并为一段，只标一次来源，宿主连接与结束状态仍单列。大段按字符分批，`segments`保留精确原文及在原事件流中的起止位置，拼接可以还原正文。`from`、`to`沿用原事件下标、段内偏移和哈希。ACK需要宿主真实显示引用，记录为HOST_REPORTED_DISPLAYED。旧ACK不能将游标移回，来源内容改动或截断会报错。`--compact`只打印ACK元数据，持久收据仍保留完整批次、原文及显示引用。省略此选项仍返回完整收据。

宿主须持续取流，不等待整包。收到公开段落及时原文转播；如工具输出被截断，明确说明，使用同一exchange的live read补取尚未报告部分，称补转而非伪造实时。停止、撤销与真实预算按原协议；可见过程修复不新增外部费用授权。
