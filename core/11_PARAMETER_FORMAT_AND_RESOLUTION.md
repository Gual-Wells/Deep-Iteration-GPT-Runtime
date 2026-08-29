# Parameter Format and Resolution

Public order:

```text
N < T < R < B < S(n,t,r,b) < D(s) < V(o) < L(e)
```

Deterministic code resolves structure; native intelligence chooses only missing task-scale values. No group, empty group, `adaptive` or `profile=adaptive` leaves missing N/T/R/S/D/V for one task-aware completion and defaults source policy to `required`. Only explicit `standard` fixes `N=2,T=0,R=1,B=0,S(0,0,0,0),D(0),V(0),L(1),source=auto`.

Typed labels may appear outside canonical order. Flat `n,t,r,b` identify S; `s`/D identify D(s); `o`/V identify V(o); `e`/L identify L(e). Wrapper forms remain canonical. D(0) and V(0) are zero lower bounds, never disable switches.

After typed values are removed, bare values are mapped only to remaining slots by type and relative order. Parentheses balance, duration tokens carry units, and duplicate definitions fail even when equal. No mapping is INVALID; multiple mappings are AMBIGUOUS with candidates. Never guess.

A lone duration preserves Alpha4 soft-T meaning (B=0). `target=<duration>` is explicit soft; `min=<duration>` is hard. Explicit `B=1` or `S(b=1)` may omit T/t; native completion must then choose a positive value. Source policy tokens compose with V and typed labels. Explicit values cannot be overridden by completion.
