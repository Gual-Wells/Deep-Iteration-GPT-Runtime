# DIGR 5.0.0-Berta2 帮助

DIGR 是显式调用、仅对本条任务生效的高投入执行模式，不会自动延续到下一轮。

## 1. 调用与仓库路由

```text
DIGR/help
深度迭代/help
DIGR：<非空任务>
DIGR(<参数>)：<非空任务>
深度迭代：<非空任务>
```

英文别名必须精确大写。本地层只做宽候选捕获和仓库传输：命中后先取得当前 `stable` 的完整 SHA，再从同一 SHA 校验 manifest/VERSION 并加载完整 startup slice；它不在本地猜测 help、task、参数或标点。Pinned STARTUP 才分类 NATIVE/HELP/INVALID/EXECUTING。`digr`、`Digr` 不捕获；`DIGR是什么`、`DIGRAPH` 会在真实获取后作为 NATIVE 交回普通 ChatGPT。

## 2. 两条执行路径

DIGR 的执行与证明是两个维度：

- `MODEL_NATIVE`：没有原生 HostAdapter 也完整运行协议；不能观测或机器证明的 actual 写 `?`，不得伪造 receipt。
- `HOST_ENFORCED`：宿主真实提供仓库绑定、持久工作区、适用时钟和最终输出闸门，可进一步取得 `PARTIAL` 或 `CANONICAL` attestation。

缺少宿主能力只降低相关证明，不得把任务降成“不执行的提示词模式”。语义 V 是模型原生认知机制，不受 `viewpoint_max=0` 阻断。单次不中断任务可使用可信 session-only monotonic clock；跨 session 的连续性必须另行证明。

## 3. 参数与自适应补全

公开顺序是：

```text
N,T,R,B,S(n,t,r,b),D(s),V(o),L(e)
```

普通 `DIGR：任务`、空参数组、`adaptive`/`自适应` 使用自适应模式：确定性解析器只映射语法，模型依据精确 U0、任务规模和可用环境一次性补全缺失的 N/T/R/S/D/V；默认来源政策为 `source=required`。只有显式 `standard`/`标准`/`profile=standard` 才固定：

```text
N=2,T=0,R=1,B=0,S(0,0,0,0),D(0),V(0),L(1),source=auto
```

显式值绝不允许补全阶段修改。`B=1` 或 `S(b=1)` 可以不同时给 T/t，此时由模型选择与任务相称的正值；硬时间不能为 0。

裸 duration 保留 Alpha4 语义，是 soft T（B=0）。`target=15min` 明确表示 soft；`min=15min` 才表示 hard。`source=auto|required|off` 可显式指定；`off` 强制 S 数值为 0。

显式类型标签可以乱序，`n/t/r/b/s/o/e` 可直接表示 S/D/V/L 内部参数，不必写包装括号。删去显式项后，无标签值必须仍然只有一种合法的类型与相对顺序解释；重复、无解或多解均返回错误/候选，不猜测。

## 4. N、R、Candidate 与停止

N 只计实质改变方案、表示、验证方法或证据结论的演化。MAIN 先建立可修订 Strategy；只有出现有意义的结果时才建立 Candidate，不为凑 R 过早制造半成品。R 必须已有 Candidate，再把它送回整个解决过程挑战任务理解、假设、策略、来源、工具路线和验证；保留原 Candidate 也必须有实质挑战证据。

达到最低值只打开停止资格。仍有高价值改进时应继续；停止还需评估目标覆盖、证据完整性、对抗韧性和剩余风险。

## 5. S、D、V、L

自适应默认来源为 REQUIRED。显式 `source=auto` 才允许依据任务给出有理由的 REQUIRED/WAIVED 选择；“模型已经知道”不是 waiver。`source=off` 是用户明确关闭。

`D(0)` 与 `V(0)` 都只是零下限。D 经 proposal、Decree、执行、结果与 MAIN reintegration；D+/D−/Dx 是内部不透明方向，不增加公开参数。V 是持久远距视角：每个 V 有私有 ledger、语义距离与非冗余证据，不进行 V-to-V 通信，Main 保有最终决策权。

L1/L2/L3 是 D 的隔离目标；实际等级必须绑定具体 intervention evidence，不能由宿主 capability 自动升级。Berta2 的 canonical host runtime 目前使用 D_EXCLUSIVE；background D 的独立并发计时仍列为后续接口扩展，不伪装成已实现。

## 6. 四时钟

```text
T = MAIN + SOURCE
t = SOURCE
D真实时间 = D_EXCLUSIVE
V真实时间 = V_EXCLUSIVE
```

META、IDLE 不计，D/V 不污染 T/t，等待和 sleep 不填充时间。推荐返回：

```text
T目标/T真实（+D真实时间，+V真实时间）
```

不可观测或不可信的实际值写 `?`。

## 7. 日志与交付

每次执行返回或持久化 `TOTAL` 总日志，以及 N、T、R、B、S、D、V、L 独立日志。它们记录面向用户的行为、阶段、证据引用、计数与时间摘要；成功和不成功的 D/V 都保留，其所有已观测专属时间进入 D/V 时间汇总。日志不泄露隐藏推理。

有 canonical host 时，最终 exact bytes 必须等于 current Candidate 的首要 content-addressed payload。交付还绑定 terminal semantic/audit digest、summary、proof、envelope，并在 DELIVERED/INCOMPLETE/ABORTED 后封印工作区；任何终态修改均拒绝。只有验证后的 DELIVERED 才是 canonical proof。

MODEL_NATIVE 路径仍返回完整作品、参数目标/实际报告、attestation level 和九类日志，但必须标明哪些 actual 是自报、可观测或未知，不得冒充 canonical。

## 8. 发布身份

5.0.0-Berta2 是 Berta 系列候选，不是 stable。代码/Schema/ZIP 自洽验证是包发布门；将其推进 mutable `stable` 之前，还必须补做真实 ChatGPT iOS/Web/Desktop 的同任务 black-box 回归并保存原始证据。
