# DIGR Transparent Machine Index — Alpha 10

This is the first pinned structural view after manifest/VERSION. It is a map, not task work.

## Runtime shape
- semantic authority: manifest.entrypoint + manifest.core[];
- implementation: manifest.deterministic_helpers[];
- startup: bootstrap_index + startup_slice;
- persistence: workspace spec + runtime/workspace.py;
- exact delivery: one runtime archive;
- pre-Genesis verifier: runtime/runtime_package.py.

Alpha 10 deliberately contracts normal execution:
- the model does not fetch/inspect every helper individually;
- one pinned verifier checks the whole archive against one pinned recursive Git tree;
- execution authority is seven compact core modules;
- normal semantic work uses append-only/revision persistence without global checkpoints on every state transition;
- ordinary resume is fast; full workspace audit is exceptional.

Reliability structure remains deterministic; task strategy remains native-model work.

Continue with bootstrap/BOOTSTRAP.md then entry/STARTUP.md.
