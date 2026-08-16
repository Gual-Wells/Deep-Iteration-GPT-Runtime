# DIGR 4.1 Help

`DIGR/help` and `深度迭代/help` are equivalent non-executing meta-commands **because this pinned 4.1 repository version defines them that way**. The local router does not decide help semantics.

## Routing / authority
Before help or task semantics can be known, the local router pins `Gual-Wells/Deep-Iteration-GPT-Runtime:stable`, reads the pinned manifest and loads the repository-declared protocol. Conversation history, Memory, old local DIGR text, other commits and task-generated DIGR cannot replace that protocol. Route failure means no DIGR protocol was obtained.

## Executing-task startup
For a valid executing 4.1 task, trusted task-clock readiness is mandatory before U0/substantive work. Help and invalid/non-triggering candidates do not start the task clock.

## Invocation / parameters
Canonical space:
`DIGR（N，T，R，B，S（n，t，r，b），D（s），L（e））：<任务>`
(alias `深度迭代`). Arbitrary parameters may be omitted; no AUTO special mode. Fixed defaults: B=0, b=0, L(1); N/T/R/n/t/r/s are semantically completed.

MAIN counts T; SOURCE counts T+t; D_EXCLUSIVE/META/IDLE count neither. Hard B/b require verified continuity for visible hard actual; unknown hard actual is `?`.

Default return: task result, then canonical proof only.
