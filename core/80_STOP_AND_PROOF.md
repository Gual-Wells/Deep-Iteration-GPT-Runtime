# 80 — Stop Gates & Canonical Minimal Proof

正常成功结束至少满足：
- `N_actual >= N`、`R_actual >= R`；
- source contract 激活时至少一个 S，且每个实际 S 的 n/r 达标；
- `B=1` 时 **hard-verified** `T_actual >= T`；
- `b=1` 时 **hard-verified** `t_actual >= t`；
- `D(s>0)` 时 `D_actual >= s`；
- L target/actual 不虚报；
- Result Quality Gate：没有仍明显值得处理、足以实质提高 U0 核心结果的重大质量缺口。

每一个执行型 DIGR run 都必须在首个 substantive/formal work 前通过 Universal Clock Readiness Gate；这与 B/b 无关。若 B=1/b=1，hard T/t 还必须对用于证明的 formal intervals 具备 hard-verification fact。一个看似达标但没有 hard-verification fact 的 observed 数字不能通过 hard stop，也不能直接进入 visible hard proof。

soft T/t 可在真实收敛时提前停止；hard minimum 达标也不是强制到点停。禁止 padding。

## Mechanical vs semantic gates
确定性 runtime 只检查数值 minimum、source 数量、hard verification 与 L exact match；不能判断一次 N/R/D 是否语义有效，也不能替代 Result Quality Gate。

## Canonical proof
任务结果后默认只附：

`DIGR（N/实际N，T/实际T，R/实际R，B，Sᵢ（n/实际n，t/实际t，r/实际r，b），D（s）/D（实际s），L（e）/L（实际e））`

- i 渲染为实际 S 总数数字下标；
- 多 S：`n_actual=min(n_i)`、`r_actual=min(r_i)`；t_actual 为所有 formal source-active 区间并集；
- hard verification 不成立时 visible actual 写 `?`，即使内部有 observed 数字；
- compact actual duration 不得向上取整跨 target；
- 不显示版本、AUTO、参数来源、箭头、H/S、✓✗、S×k、SHA 或重型状态。

默认不返回 final prompt、EST、D-State、每轮过程、自评分、完整 workflow、查询日志副本或 hidden reasoning。
