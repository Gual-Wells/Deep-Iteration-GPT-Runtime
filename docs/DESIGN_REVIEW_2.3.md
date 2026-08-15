# 2.3.0 Design Review — Why 2.2.0 Under-scaled T

## Observed 2.2.0 failure

A parameterized `T=15min` task could finish after a very small amount of real work while still claiming the budget was satisfied. The root cause was not merely tool speed. The protocol weakened T in three stages:

1. T was defined relative to human task time rather than the executing reference model.
2. Continuous time was collapsed into coarse buckets (`>10–30m` etc.).
3. The stop rule allowed diminishing-return termination without first proving that the requested T-scale work had actually been explored.

The parser also stored T as a string without any runtime contract explaining that semantic interpretation belongs to ChatGPT. This made T easy to treat as a display label.

## 2.3.0 correction

### A. Reference frame
T now means GPT-5.6 Sol / High task scale. This makes `15min` a model-relative execution-scale instruction rather than an analogy to human work.

### B. Semantic ownership
The parser is intentionally syntax-only. It extracts `complexity_budget_raw`; ChatGPT owns interpretation. No minute normalization, tier mapping, token conversion or workload table is present.

### C. Continuous scale
No fixed buckets. `11m`, `15m`, `20m` and `29m` remain distinct semantic signals.

### D. Dual stop gate
Stopping requires both:
1. T budget adequacy — the effective work is commensurate with T, or remaining work is genuinely low-value/unavailable.
2. Result adequacy — no major correctness, evidence or deliverable gap remains.

### E. Early convergence without padding
Wall-clock time may be shorter than T because tools can parallelize and machine work can be dense. Early convergence is accepted only after a semantic check that high-value remaining work is exhausted. Waiting, repeated search and output inflation are forbidden.

### F. Multi-deliverable coverage
T is allocated adaptively, not evenly. However every core deliverable must receive risk-proportionate execution and validation so breadth cannot hide omissions.

### G. Protocol version pinning
A mutable `stable` ref is resolved to one commit where possible, and all modules in the run use that immutable commit. This avoids the 2.2-era ambiguity where a release window or cache could mix versions.

### H. Observability
Runtime reports add `t_budget_adequacy` and optional resolved version/commit. Prompt iteration may expose only high-level focus labels, never hidden chain-of-thought.

## Explicit non-goals

2.3.0 does not attempt to force exact wall-clock runtime; it does not map T to token budgets; it does not guarantee that larger T always improves output; and it does not replace native model planning with a workflow engine.

## Regression protections

`tests/test_t_semantics.py` checks raw-T preservation, reference model identity, absence of tiering in the parser, and the ordering of the T stop gate. `tests/test_protocol_pin.py` checks immutable commit references. `tests/validate_repo.py` performs static semantic regression checks in active protocol files.
