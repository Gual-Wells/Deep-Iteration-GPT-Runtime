# Invocation and Parameter Resolution — Alpha 10

Normative behavior is in `entry/HELP.md` and manifest core authority.

Public order remains `N < T < R < B < S < D`; S uses `n < t < r < b`.

- B/b omitted → 0.
- D entirely omitted → 0.
- explicit `D()` → D may be semantically completed.
- bare numeric tokens never become T/t without duration semantics.
- mixed positional/labeled syntax must resolve uniquely or fail.
- missing N/T/R and applicable source minima are completed conservatively, as minimum sufficient safeguards rather than workload targets.
- SourceDisposition is chosen before source-minimum completion.

Parameter resolution happens after verified package/protocol readiness and Clock Genesis, but does not perform repository transport.
