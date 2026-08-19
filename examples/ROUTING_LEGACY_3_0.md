# Legacy routing without semantic contamination

Assume `stable` pins to a legacy 3.0 commit whose manifest has no `bootstrap_entry` but declares `entrypoint` and `core`.

The 5.x local router may use that manifest only to locate files. It must then delegate DIGR semantics to the loaded 3.0 repository protocol. It must **not** require 5.0 task-clock readiness, L defaults, D/L semantics or 5.0 proof before 3.0 has loaded.
