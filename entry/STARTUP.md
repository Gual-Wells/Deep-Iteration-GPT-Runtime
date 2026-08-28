# DIGR 5.0.0-Berta1 — Self-contained Pinned Startup

This file is authoritative only after the adapter has resolved `stable`, pinned one immutable SHA, verified that pinned `manifest.json.version` equals pinned `VERSION`, and loaded the complete `manifest.startup_slice` from that SHA. Classification always uses the untouched original user message; repository transport and setup text are not part of the message.

## 1. Surface classification

Remove leading whitespace only, then select the exact leading alias `DIGR` or `深度迭代`. Preserve the original bytes/hash and all text after the alias.

1. **HELP** — after the alias, the remainder stripped of surrounding whitespace is exactly `/help`.
2. Otherwise, remove leading whitespace from the remainder. If its first character is ASCII `(` or full-width `（`, consume one balanced parameter group. For group structure only, ASCII/full-width opening and closing parentheses are equivalent and nesting is allowed. An unclosed or prematurely closed group is **INVALID**. After the group, remove leading whitespace.
3. **EXECUTING** — the next character is ASCII `:` or full-width `：`, and the following task contains at least one non-whitespace character. Preserve `task_raw` exactly as the text after that single separator; do not normalize task punctuation.
4. A balanced parameter group without a task separator, or a separator with an empty task, is **INVALID** and receives local correction without Run Genesis.
5. Every other broad-prefix capture is **NATIVE**. Return the complete untouched original message to ordinary ChatGPT. Thus `DIGR是什么？`, `DIGR 协议...` and `DIGRAPH` are NATIVE, but only after this pinned startup was actually obtained.

`digr` and `Digr` never reach this protocol because the local candidate router does not capture them.

## 2. Navigation by classification

- NATIVE: load no HELP or execution content; return the original message.
- HELP: load pinned `manifest.help` and return it without Run Genesis.
- INVALID: return a concise structural correction; create no run.
- EXECUTING: resolve parameters below, then load pinned `manifest.entrypoint` and `manifest.core[]`, or a bundle verified to contain exactly those members in that order. A manifest-declared `runtime_descriptor` may describe and integrity-bind generated execution/release artifacts, but does not override these paths.

## 3. Parameter-resolution navigation

Parameter meaning is resolved only after EXECUTING classification. Pass the preserved optional parameter group to the deterministic Berta1 parser described by `core/11_PARAMETER_FORMAT_AND_RESOLUTION.md` and implemented by the manifest-declared parameter helper.

- no group, an empty group, `standard`/`标准`, or `profile=standard` selects the standard profile: `N=2`, `R=1`, no time requirement (`T=0`), `source=auto`, `D=0`, `L=1`;
- a lone explicit duration or `min=<duration>` selects a positive hard time minimum; `target=<duration>` selects a soft target;
- `source=auto|required|off` is explicit policy input;
- other positional/labeled surfaces use the `legacy-alpha4` unique-or-fail parser automatically and emit a visible compatibility warning; no explicit legacy profile token is required;
- invalid mappings remain INVALID; ambiguous mappings return NEEDS_CORRECTION. The model must not guess or complete parameter values.

Only a resolved EXECUTING surface may proceed to trusted monotonic Clock Genesis, immutable U0 binding and the Effective Contract. Any startup failure before Genesis creates no run.
