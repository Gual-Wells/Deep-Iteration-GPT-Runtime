# Invocation Surface and U0

The local router broadly captures only after leading whitespace when the message begins with exact uppercase ASCII `DIGR` or exact `深度迭代`. Lower/mixed-case forms are native messages.

Pinned repository startup returns exactly one surface:

- `EXECUTING`: valid invocation shell with non-empty task;
- `HELP`: exact help command;
- `NATIVE`: broad capture that is discussion rather than invocation;
- `INVALID`: clear invocation attempt with broken invocation structure.

NATIVE/HELP/INVALID never create a run.

For EXECUTING Alpha 9, exact package delivery and complete protocol verification happen before Genesis. Parameter-format resolution happens only after the resulting verified protocol receipt is already bound into the newborn run. Parameter ambiguity therefore never requires a post-Genesis repository fetch.

`U0` is the faithful task text/intention frozen once after parameter resolution and bound to the original message digest. Header normalization must never mutate the task body. Later strategy revisions cannot edit U0.
