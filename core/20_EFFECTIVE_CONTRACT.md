# 20 — Effective DIGR Contract

Effective Contract 包含：`N,T,R,B,S(n,t,r,b),D(s),L(e)`。

- `N`：主体最低有效进化次数。有效变化可发生在理解、Prompt/行为、拆解、流程、方法、验证、研究策略、工具、测试、考虑维度或综合；纯措辞改写不算。
- `T`：Formal Active Task Time 目标。
- `R`：形成可评估结果后，最低 whole-process result re-entry 次数。
- `B`：T 的 soft/hard 策略，0=soft，1=hard。
- `S(n,t,r,b)`：可多实例发生的外源研究进化模板；n/r 是每个实际 S 的最低有效进化/回代数，t 是全部正式 source-active 区间并集目标，b 是 t 的 soft/hard 策略。
- `D(s)`：最低有效 Disruptive Gambit Intervention 数；`D(0)` 是显式关闭，不是 minimum 0。
- `L(e)`：D 的隔离实现等级；e∈{1,2,3}，且是精确目标等级而非 minimum。

N/R/n/r/s 与 hard T/t 是 floors, never ceilings。一个真实动作若同时满足多种语义条件，可以同时推动多个计数，不要为了形式计数重复劳动。

若 `n>0 or t>0 or r>0 or b=1`，至少必须实际产生一个 S；否则不能用“零个 S”真空满足 source contract。
