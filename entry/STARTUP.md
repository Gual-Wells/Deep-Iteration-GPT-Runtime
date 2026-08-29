# DIGR 5.0.0-Berta2 — Self-contained Pinned Startup

This file becomes authoritative only after `stable` is resolved to one immutable SHA, pinned `manifest.json.version` equals pinned `VERSION`, and the complete `manifest.startup_slice` is loaded from that SHA. Classification uses the untouched original message.

## 1. Surface classification

Remove leading whitespace only, then select exact leading alias `DIGR` or `深度迭代`.

1. **HELP**: the remaining text, stripped at both ends, is exactly `/help`.
2. Otherwise remove leading whitespace from the remainder. If it begins with ASCII `(` or full-width `（`, consume one balanced group. Full-width/ASCII parentheses are equivalent for structure; nesting is allowed. Unclosed or prematurely closed structure is **INVALID**. Remove leading whitespace after the group.
3. **EXECUTING**: the next character is `:` or `：`, followed by a task containing a non-whitespace character. Preserve `task_raw` exactly after that one separator.
4. A parameter group without a task separator, an empty task, or malformed group is **INVALID** and creates no run.
5. Every other broad-prefix capture is **NATIVE**. Return the complete original message to ordinary ChatGPT. `DIGR是什么？`, `DIGR 协议...`, and `DIGRAPH` are NATIVE only after pinned startup acquisition.

Lower/mixed-case `digr` and `Digr` never reach this protocol because the local router does not capture them.

## 2. Navigation

- NATIVE: load no HELP/execution content; return the original message.
- HELP: load pinned `manifest.help`; create no run.
- INVALID: return concise structural correction; create no run.
- EXECUTING: structurally resolve the parameter group, then load pinned `manifest.entrypoint` and `manifest.core[]`, or a verified bundle containing exactly those members in order. A manifest-declared runtime descriptor may integrity-bind generated artifacts but never overrides manifest navigation.

## 3. Berta2 parameter startup

Structural parsing is deterministic and unique-or-fail; task-scale calibration is model-native.

- no group, an empty group, `adaptive`/`自适应`, or `profile=adaptive` selects adaptive completion;
- only explicit `standard`/`标准`/`profile=standard` fixes `N=2,T=0,R=1,B=0,S(0,0,0,0),D(0),V(0),L(1),source=auto` (equivalently D=0 and V=0 minima);
- normal adaptive source policy defaults to `required`; `source=auto|required|off` overrides it explicitly;
- a lone duration preserves Alpha4 meaning: soft `T` with `B=0`; `target=<duration>` is explicitly soft and `min=<duration>` is hard;
- explicit `B=1` or `S(b=1)` may leave T/t absent for native completion, which must choose a positive value;
- uniquely resolvable Alpha4/stable.1 positional forms follow a visible `legacy-alpha4` syntax-compatibility path while retaining missing-value completion;
- public order is `N,T,R,B,S,D,V,L`; clear typed labels may move, including flat `n,t,r,b,s,o,e`, only when remaining bare tokens retain one unique interpretation;
- invalid mappings are INVALID; multiple mappings are NEEDS_CORRECTION with candidates. Never guess.

Before monotonic Clock Genesis (Run Genesis), deterministic preflight may reject malformed/ambiguous syntax and verify pinned execution artifacts. After the full protocol is bound, native completion fills every missing task-scale value exactly once; explicit values cannot be changed. The completed receipt is persisted before U0 and Effective Contract freeze.

Host capability gaps affect attestation, not permission to execute the DIGR task. `MODEL_NATIVE` execution remains valid; only claims requiring absent evidence become unknown/non-canonical.
