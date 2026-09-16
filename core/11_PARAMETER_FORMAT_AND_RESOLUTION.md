# Parameter Format and Unique Resolution

Public order is `N < T < R < B < S < D < L`; inside S it is `n < t < r < b`. Omitted positions do not reorder the remaining values. The deterministic resolver's structural partial defaults remain `B=0`, `b=0`, `L(1)`; missing `N/T/R/n/t/r/s` remain unresolved for the later contract-completion layer. A higher-precedence all-omitted rule is defined in `core/15_SEMANTIC_DEFAULT_COMPLETION.md`: when the invocation supplies no parameter token and no S/D/L marker at all—`DIGR：task`, `DIGR()：task`, or alias equivalents—the effective contract is fixed to `DIGR(3,3min,5,1,S(3,1min,5,1),D(3),L(1))`.

Before deterministic resolution, normalize only invocation-header punctuation: `（→(`, `）→)`, `，→,`, `：→:`. Full-width/ASCII pairs may therefore mix. Task text is untouched.

Semantic classification may recognize natural duration/count language (`10分钟`, `half hour`, `三轮`). The deterministic resolver then searches for **one and only one** mapping satisfying scope/order/type constraints. A token cannot bind two parameters. A bare number can never become `T/t` and the model may not invent a time unit.

Positional main/S segments:

- 0 items: all semantic fields missing; structural B/b remains 0. If the whole invocation also contains no S/D/L marker, the later all-omitted contract rule takes precedence.
- 1 item: duration uniquely anchors T/t; bare count is ambiguous between N/R (or n/r).
- 2 bare counts: uniquely N,R (or n,r), because T/t cannot consume a bare number and B/b defaults.
- 3 items: must occupy N,T,R (or n,t,r); therefore `1,10min,1` works and `1,1,1` is invalid.
- 4 items: N,T,R,B (or n,t,r,b).

`S`, `S()`, `D`, `D()`, `L`, `L()` are legal strong markers. Empty S means n/t/r missing and b=0; empty D means s missing; empty L means L1. D/L tail order is D then L; an otherwise unanchored single trailing count is ambiguous, while two can uniquely occupy D,L. Any explicit marker means the invocation is not the all-omitted case.

Examples: `DIGR(1,1):task` ⇒ N=1,R=1; `DIGR(1):task` ⇒ AMBIGUOUS; `DIGR(1,1,1):task` ⇒ INVALID; `DIGR(1,10min,1,S()):task` ⇒ valid; `DIGR(1,1,S,D,L):task` ⇒ valid.
