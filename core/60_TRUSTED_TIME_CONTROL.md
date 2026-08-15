# 60 — Trusted Time Control

3.0 的 T/t 是**实际运行时间目标**，不再是 2.x 的参考模型语义任务规模。

hard 时间必须优先使用可重复读取且具有连续性身份的可信时钟。参考实现：`runtime/clock_probe.py`。

理想强验证：
- monotonic timestamp；
- 可跨调用确认相同 clock identity（Linux 可使用 boot ID）；
- wall clock 作为旁路 sanity check。

若无法可靠确认 hard 时钟连续性，必须 fail closed：`unverifiable` 不等于 `satisfied`。

Global T：
- 本次 DIGR 当前 user turn 正式启动后建立 clock anchor；
- elapsed 为可信当前快照与 anchor 的单调时钟差；
- B=hard 且 elapsed<T：正常停止禁止；
- elapsed>=T：仅表示时间下限满足，不覆盖结果质量门。

真实工具等待若是完成任务必需的正常执行过程，可以属于总 wall-clock elapsed；但不得故意制造等待，且长等待本身不能替代后续质量检查与有效进化。

Aggregate source t：记录 S 的 source-active 时间区间并求并集。并行 S 不重复累计。若时钟身份失效，hard source time 同样不能伪称满足。

Hard time 强制的是“在这段真实运行窗口中持续寻找并执行仍有价值的任务提升”，不是承诺每一秒都可被解释为隐藏推理时间。协议只报告可验证 wall/monotonic elapsed，不宣称不可测的内部神经计算时长。
