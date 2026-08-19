# Invocation and Parameter Resolution

See `entry/HELP.md` for user-facing behavior and `core/11_PARAMETER_FORMAT_AND_RESOLUTION.md` for normative details.

Engineering rule: surface classification is syntax-only and happens in the minimal startup slice. Parameter resolution happens only after EXECUTING Clock Genesis. Natural-language semantic classification may identify count/duration categories, but deterministic constraints must yield exactly one legal mapping. Bare numeric T/t is forbidden.
