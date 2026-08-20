# Invocation Surface and U0

The local router broadly captures only after leading whitespace when the message begins with exact uppercase ASCII `DIGR` or exact `深度迭代`. Lower/mixed-case `digr`, `Digr`, etc. are ordinary native messages.

Pinned repository startup then returns exactly one surface state:

- `EXECUTING`: `DIGR：task`, `DIGR(...):task`, and Chinese alias equivalents with non-empty task;
- `HELP`: exact `DIGR/help` or `深度迭代/help` after outer whitespace;
- `NATIVE`: broad captures that are discussion rather than invocation, e.g. `DIGR是什么？`, `DIGR(R=3)这种格式怎么样？`;
- `INVALID`: a clear invocation attempt whose invocation shell is broken, e.g. empty task after colon or an unfinished parameter group containing the task separator.

Only `EXECUTING` creates Run Genesis. Parameter ambiguity belongs *inside* the born run and is resolved only after clock genesis plus verified full-protocol readiness. If parameter resolution is AMBIGUOUS/INVALID, abort before U0/task analysis.

For an executing run, `U0` is the faithful task text/intention frozen once, bound to the original message digest. Header punctuation normalization must never mutate the task body. Later strategy revisions cannot edit U0.
