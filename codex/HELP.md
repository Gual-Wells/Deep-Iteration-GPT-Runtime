# DIGR Codex 0.8.5 使用说明

普通任务采用轻量交付偏好；显式 DIGR 启动高投入的问题研究、方案探索与实际制作。默认 N12/R4/D3/V3/L3/M1，只自主上调和改变方法；时间按任务补齐为软目标，来源默认 REQUIRED。

0.8.3接入社区[反防御性写作规则](../docs/CODEX_ANTI_DEFENSIVE_UPGRADE.md)：先陈述有依据的主张，删除重复辩护和叠加保留，保留实际影响结论与使用的限定。核心规则已进入必读执行正文，完整技能随分发提供，可按写作用途调用。

0.8.5接通[ DIGRP 0.2.0 论文解构增量](../paper/PROTOCOL.md)的直接调用：`DIGRP：完整处理这篇论文……`，兼容`DIGR：按 DIGRP 完整处理……`。每篇完整M，内部职责综合为自然的阅读章节；桌面标准单页、每篇一份完整PDF、一次经授权Gmail返回。完整调用才选择增量执行，`DIGRP/help`只看说明。全部论文和公共工作完成后再统筹结束。`python -B tools/codex.py paper --help`提供文件工具，原生宿主承担阅读、证明、教学、代理与发送。

任务未按RETURN明确结束或被明令停止/取消前，后续消息沿当前DIGR作为补充处理；NEW_TURN、纠正、追问或技术中断不使它降级、重开前置或丢失投入。暂停保留任务，普通补充不自动恢复。再次命中前缀仍先获取仓库，当前P_run不变。已结束后的普通讨论也不复活DIGR。

现实中数据不齐时，用已有来源和有据中心估计推进，保留相关不确定性；只问会改变当前决定且不能合理替代的少量信息。不要把未知一律判成坏情况、把可逆试用挂在理想数据之后，或擅自换成更慢目标。[0.8.2行为与兼容说明](../docs/CODEX_REAL_WORLD_CONTINUITY_UPGRADE.md)。

新任务先按[FOUNDATION](FOUNDATION.md)独立研究用途、成品、处理粒度、已有基础、依赖与投入，展示可纠偏说明并问答；用户明确决定后才正式初始化并全面执行。前置独立预算/计时，调用参数留给正式任务，前置没有固定高投入下限。已确认续做只讨论重要变化，常规操作不重新审批。

| 调用 | 行为 |
| --- | --- |
| `DIGR：任务` / `深度迭代：任务` | 先取得真实仓库 pin，读启动切片及完整执行协议，再动态初始化。 |
| `DIGR：只问原因，别推送` | 完整显式调用，仍为深执行；动作限于询问/研究，不获得推送授权。 |
| `DIGR(N=18,R=5,D(4),V(4))：任务` | 显式配置；数值是实质责任，不是工具调用数。 |
| `DIGR(M(2))：任务` | 两条完整独立 Main，各自初始化参数、推进、使用自己的D/V、收敛并比较，不能平分同一份总量。 |
| `DIGR(target=60min)：任务` | 软时间目标，不改变其它责任，也不表示到点就结束。 |
| `DIGR(min=60min)：任务` | 有效工作硬下限；无真实计时证据时未验证，不靠等待凑。 |
| `DIGR(standard)：任务` | 用户主动选择 N2/R1/D0/V0/L3/M1、时间0、来源AUTO的低档；模型不会自主切入。 |
| `DIGR/help` | 帮助，不建立执行契约。 |
| `DIGR是什么？` | 精确前缀仍先获取，再按启动协议进入普通讨论。 |
| `digr：任务` / `Digr：任务` | 不命中精确前缀。 |

初始化显示 `N（12）` 这样的生效值，结尾显示 `N（12/实际）`，B/b始终单值。中途使用色块、粗体身份和独立阶段行，显示真正的研究、返回与主线处理；不预编全部名册，不输出隐藏思维链。多个M分别展示，详细责任与格式见 [PARAMETERS](PARAMETERS.md)。

- **D** 先自主找到攻击口，成熟后以真实研究/作品挑战整条路线，Main处理其中心主张。
- **V** 先研究形成分域，在有距离的材料世界持续工作；默认由Main忠实转交必要质疑与新事实，同线可因候选进展或自己新发现再入。
- **M** 各自完整推进。文件目录和脚本不会自动替代真正独立的Main。
- **授权** 延续已有任务与资源决定；能力、预算、执行效果分别看，不为常规任务内操作反复申请。

[PROTOCOL](PROTOCOL.md)、[FOUNDATION](FOUNDATION.md)、[CHARACTER](CHARACTER.md)、[PARAMETERS](PARAMETERS.md)、[COLLABORATION](COLLABORATION.md)、[PERMISSIONS](PERMISSIONS.md)、[RETURN](RETURN.md)为执行正文，可从同pin聚合包一次读取。默认返回在response正文固定五段，以正文时间／工作表显示过程，禁用内嵌页或附件替代；T计所有参与者工作并集、t计来源并集，近似补点与缺口明确说明。结束后普通纠错不再启动DIGR，真正未完成的补充沿用原任务。[WORKBENCH](WORKBENCH.md)是按需工具手册。

## 实际使用工具

从仓库根目录运行，无需安装第三方依赖：

```text
python -B tools/codex.py --help
python -B tools/codex.py profile check
python -B tools/codex.py acquire --stage startup --out D:/task/acquired
python -B tools/codex.py workbench --help
python -B tools/codex.py task --help
python -B tools/codex.py line --help
python -B tools/codex.py clock --help
```

`acquire`进行真正联网获取；profile check只检查本地分发。其它工具协助保留原目标、取回材料、接续本线产物、按真实活动边界算时长；不调用模型、不启动代理或扩大权限。原有 `tools/codex_profile.py`、`tools/codex_workbench.py` 与 `tools/codex_experience.py` 仍可用。

本分支不自动改宿主采样参数或模型权重；新语义和工具能否在后续任务持续改善结果，仍需实际使用观察。
