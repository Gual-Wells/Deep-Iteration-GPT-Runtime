# 本任务用量与费用返回

外部模型费用与 Codex 额度都返回，但保留真实分母与账目状态。百分比不由模型正文自报，不由消息次数或effort名称换算。

## 原生聚合事件

宿主显式选择本任务Main及实际D/V/其他代理的rollout路径、actor及turn或起止边界，运行 `usage collect`。同一聊天内旧任务不因共用文件进入新账目；默认不扫描其它聊天。只投影`turn_context`的实际模型/effort/speed与`token_usage_record`、`token_count`、`thread/tokenUsage/updated`及额度通知中的聚合字段，不提取或保存正文、隐藏思考、任意工具输出或凭据。

`token_usage_record`按thread+response去重，并保留`thread_token_usage`累计端点。它只替换累计区间中能够证明覆盖的部分，部分精确response不能代表整个turn；未覆盖的累计残差仍保留。重复导入和跨actor导入不重复加账。类别无法从局部重叠中识别时，保留可确定的残差总tokens，分类及加权份额留未知。安全原始聚合与实际加总视图分别保存，不能因晚到一条精确记录删除其余真实消耗。

只有旧式通知时用有据累计差或单次last aggregate。start/turn边界穿过两次累计观测之间时，不把整个区间差归入任务；可单独保留标明“末次响应在边界后完成”的last归属假设，其余列累计归因缺口，last自身跨边界的可能性也不隐去。精确response及真实turn成员关系可消除对应别名的不确定性。跨累计计数倒退另开覆盖epoch，不相减。

输入已包含cached input，输出已包含reasoning output时，各子集只列分解。逐响应明报的model/effort/speed优先于同一thread和turn的上下文。缺失字段留未知，明确的调用方填充使用较低等级的标签。迟到事件按原turn取上下文，晚到的旧turn累计别名沿用原覆盖epoch。累计两端属于同一turn时，按该turn内的改道和实报冲突判断字段覆盖；跨turn时核对活动线程跨度内的字段变化。同等强来源矛盾时，相应字段及依赖它的加权归因保持未知。

旧投影的回合上下文归属可以用原明示rollout和任务边界重新采集。同一响应重新出现时更新上下文标签，能从旧记录识别的逐响应明报字段仍保留，聚合总量不因标签更新而重复加账。保存旧快照及其观测截止。先前来源不全或聚合边界有疑义时，以已有授权选定的文件全量重投影，并报告仍无法复核的覆盖。

```text
python tools/codex.py usage collect --root TASK --rollout SELECTED.jsonl --actor Main --turn-id ACTUAL_TURN_ID
python tools/codex.py usage collect --root TASK --rollout AGENT.jsonl --actor V-usage --start 2026-11-18T06:18:25+00:00
python tools/codex.py usage collect --root TASK --rollout ACCOUNT_A.jsonl --actor Main --turn-id ACTUAL_TURN_ID --account ACTUAL_ACCOUNT_SCOPE --limit-id ACTUALLY_ELIGIBLE_LIMIT_ID
python tools/codex.py usage snapshot --root TASK --input ACTUAL_RATE_LIMIT_READ.json --at ACTUAL_ISO_TIME --baseline
python tools/codex.py usage body --root TASK
```

真实rate-limit读取可由`snapshot`投影；不会由工具暗发模型请求或取得新费用授权。`root/usage/observations.json`仅保存选中聚合；return绑定这一文件，不依赖持续增长的原始聊天文件。持续工作后再次导入，得到新的可封存观测。

## 三种分母

1. **账户窗口变化**：每个真实account/limitId/windowDuration分别返回起止`usedPercent`和百分点Δpp。多桶兼容别名不再加一次，primary/secondary槽位变化不自动改变桶身份。套餐改变、读数回退、已跨重置时刻或大幅重置标记变化均分段，不能硬减整条聊天首尾。`resetsAt`小幅漂移本身不证明重置。
2. **本任务占套餐额度**：服务账户变化不自动等于任务账单。默认并发状态未知，只返回账户段变化；主任务或独占活动有明确依据时，`account_activity=primary_task/exclusive`可返回带假设身份的该观测段近似。读数粒度和入账延迟未知时不称严格上界；0pp只称读数未变化，不能声称0消耗或`<1pp`。
3. **各模型/effort/speed占本任务份额**：已导入总tokens占比有明确聚合分母；任务边界归属的假设与缺口另列，不能混称完整任务实测。另以公开credits相对费率或显式校准给加权用量代理占比，后者不是官方订阅换算。按同一观测段分配pp时，事件必须属于同一account且明确有该limitId的计量资格，再用该段组权重。只看到单桶兼容视图不证明服务只有该桶；未知eligibility不分档pp，跨账户事件不进入本桶。未知模型/缓存数不能编费率；原始token占比仍可用。速度未知时明确Standard代理假设。

内置代理依据[官方定价](https://learn.chatgpt.com/docs/pricing)，读取日期2026-11-18。官方明确credits价格本身不能确定套餐内消耗。实际计量字段依据[App Server](https://learn.chatgpt.com/docs/app-server)。未来费率变化需更新或用task内`usage/config.json`显式校准及来源。不能用代理费率宣称额度换算已精确测得。

## 外部模型账目

逐 exchange 读取实际 attempt 并按当前任务汇总。保留 Sonnet、Hydrogen、Grok 的实际身份和各层共用费用。请求服务等级与供应商已报告等级各自读取。保留`consult_guidance`或`council_member`及member/cycle/round身份。`reconciled_at`且KNOWN为已核对；服务usage已报但未metadata核对为服务已报；有依据的estimated独列；UNKNOWN未决预留独列。未决预留不是已发生账单，不与已知费用合称账单总额。尚未尝试与费用未知分开。

返回快照注明观测截止与覆盖actor。Main、D/V、重试按真实导入纳入；未导入者保持覆盖缺口，不能报未调用。真正未调用的档位才写“未调用”。当前最终回复、迟到usage与未知费用可能在快照之外；不能声称测到了尚未发生的完整尾部。

新pin的return自动附本节用量片段；未导入原生数据时明确未知，不能封存成0。旧pin维持原返回规则。
