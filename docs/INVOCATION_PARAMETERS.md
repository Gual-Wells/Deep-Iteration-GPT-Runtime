# Invocation Parameters — 3.0

Canonical:
```text
深度迭代（N，T，R，B，S（n，t，r，b））：<任务>
```

ChatGPT 是语义解释器，canonical 语法不是硬 parser 合同。

## Main / S isomorphism
- `N ↔ n`: minimum effective evolution cycles
- `R ↔ r`: minimum whole-process result re-entry evolution cycles
- `B ↔ b`: soft/hard time-policy semantics
- `T ↔ t`: both are actual time targets, but T belongs to the whole run while t belongs to the union of all S source-active intervals

## Example
```text
深度迭代（3，15m，2，hard，S（2，6m，1，hard））：分析某技术问题
```

Meaning:
- Main N >= 3
- Main R >= 2
- Total run hard minimum 15m, verified by trusted clock
- Every actual S: n>=2, r>=1, b=hard
- Aggregate source-active time across all S: >=6m
- all minimums are floors, never ceilings
