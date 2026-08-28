# Parameter Format and Deterministic Resolution

After pinned STARTUP classifies EXECUTING, `digr.preflight` resolves the preserved parameter surface before Run Genesis. The public order is:

```text
N < T < R < B < S(n,t,r,b) < D(s) < V(o) < L(e)
```

The Berta1 standard profile is `N=2, T=0/no-time, R=1, B=0, source=auto, S(0,0,0,0), D(0), V(0), L(1)`. Both `D(0)` and `V(0)` are zero lower bounds, not disable switches.

Explicitly typed parameters may appear outside canonical order. Flat nested labels are valid without wrapper syntax: `n,t,r,b` identify S; `s` or `D` identify D(s); `o` or `V` identify V(o); `e` or `L` identify L(e). `S(...)`, `D(...)`, `V(...)`, and `L(...)` remain canonical spellings.

After typed values are removed, every unlabeled value is mapped only against remaining slots by type and relative order. Parentheses must balance, durations must carry units, duplicates are invalid even when equal, and the mapping must have exactly one solution. No solution returns INVALID; multiple solutions return AMBIGUOUS with candidate slots. The model cannot guess or repair silently.

A lone duration or `min=<duration>` creates a hard T minimum; `target=<duration>` creates a soft target. Legacy alpha4/stable.1 forms remain accepted only when uniquely resolvable and are visibly diagnosed as compatibility input.
