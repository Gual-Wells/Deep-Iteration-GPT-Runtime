# 一个实际请求怎样接入 Split

以下为合成示例，不是已发生的 Claude 调用、节省率或用户材料。所有任务文件放在调用者自己的 D 盘私有工作目录；不要把真实任务、原件、分工计划或凭据提交到协议仓库。

设当前任务用双冒号委托 Claude 参与解释一篇论文的队列稳定性与学习策略。本机已提取原文、复核符号，发现漂移界不能单独证明某个学习策略稳定。Claude 应得到有关原式、假设、读者疑问和当前解释，决定怎样贯通这组关系；不必再让它做 PDF 提取、查路径或运行复算。

本机复算还可能发现原件自身的疑点。例如合成原文把服务变量定义为“实际完成工作”，附录又要求稳态严格负的到达减服务余量；不能默默改成“可提供的服务容量”后把修正讲法当原文定理。任务包应同时提供原段和标明本机身份的疑点、推导及其适用前提，让Claude据此自行发展或改变解释。最小充分材料在这种情境可以就是完整短论文；内容选择与讲法仍交给协作者。

先根据本次原生研究准备 `claude-task.txt`、`original-excerpt.md`、必要图像；这些是实际发出的材料，不是本机索引。2.0+ 按同一真实委托准备整篇导读，并按 [Paper Pool](../../PAPER_POOL.md) 履行学术任务工作。旧论文增量沿原 pin 绑定。

```text
python -B tools/codex.py consult prepare --root D:/work/task --guidance --input D:/work/claude-task.txt --material D:/work/original-excerpt.md --exchange-id explain-stability
python -B tools/codex.py consult split --root D:/work/task --exchange-id explain-stability
```

第二条只读取绑定，不执行模型研究。推荐把本次原生判断写为`native-decision.json`，由工具附加当前绑定，避免手工复制不透明字段。决定和结果只适用于这里的构造情境，真实任务须由Codex自己形成。

```json
{
  "decision": "本机完成原式定位、符号核对与漂移界复算；本次请 Claude 发展完整解释并处理读者混淆。保留原式和假设以便它改变当前讲法。",
  "local_work": [
    {
      "task": "核对原文漂移界与稳定性论断的适用前提",
      "result": "原文只给出该界；对学习策略的稳定性结论还需要对应策略条件。原文主张与补充推导在材料中分别标识。",
      "evidence": []
    }
  ],
  "claude_value": "让原式、条件和读者问题形成一条有说服力的解释；可替换现稿的进入点、结构或例子，也可要求必要原件。",
  "context_decision": "提供决定性原段与相关现稿；不重放 PDF 提取日志。原式、定义、反例和当前用户要求完整保留，图像只补不能可靠文字化的局部。"
}
```

`local_work`只记录真实已完成工作。所选文件证据可写为 `{"path":"checks/calculation.txt","sha256":"实际观察的64位SHA256"}`；本例相对路径基于原生判断文件目录。纯概念研究可用公开结果摘要，不要求为了填字段造文件。确无有价值的本机先做工作时，用空列表并给 `local_work_reason`，说明为什么当前任务应直接交给Claude；不制造无用工序。

```text
python -B tools/codex.py consult split --root D:/work/task --exchange-id explain-stability --input D:/work/native-decision.json --out D:/work/split-plan.json
```

该命令不生成上例的判断文字，只附加当前绑定并检查实际证据。相对证据按`native-decision.json`的目录解析；即使输出到另一目录，所指原件也不改变。输入带旧`format`或`binding`会被拒绝；输出已有文件时不覆盖。仍可手工使用绑定预览，但不能将旧计划重新盖成当前研究。

此处使用第二层内容协作。按 [WORKBENCH](../../WORKBENCH.md) 核对双冒号的当前层内余额、保守费用上界及实际作用域。当前费用事实须覆盖完整请求和图片、实际模型及共享钱包。1.3 的当前双冒号在额度内直接运行：

```text
python -B tools/codex.py consult call --root D:/work/task --exchange-id explain-stability --split-plan D:/work/split-plan.json --facts D:/work/current-cost-facts.json --ceiling-usd <当前真实授权内的本次额度>
python -B tools/codex.py consult inspect --root D:/work/task --exchange-id explain-stability
```

`call`在本机执行一次Split再经过既有费用和单次尝试边界；公开分工记录保存在该交换的私有`split.json`，不传给Claude。它检查身份和所选文件字节，不认证摘要陈述或研究质量。下一次续调仍准备新的实际问题、获取新的绑定并形成新Split；不能复用本例或旧请求的计划。

请求内容、模型、effort、输出上限、公开历史、论文作用域或用户输入变化后，重做受影响的本机判断并绑定新请求。若使用`--continue-from`，统计和预算包含实际重放的全部消息；需要有来源的摘要接续时，明确另开交换并提供仍有效指导与原件，不能把摘要称作逐字历史。公开历史、本机材料和API实际传入范围分别记录。
