# Two-stage Run Genesis

Input: `DIGR（R=3）：检查并改进方案`

Required order for the pinned Alpha 4 protocol:

1. local route resolves `stable` → immutable SHA and reads pinned manifest/VERSION plus the manifest-declared startup slice;
2. repository startup surface returns `EXECUTING`;
3. >=3 compatible monotonic samples establish TaskStartupReceipt and clock-journal genesis;
4. `LiveDIGRRun` exists in `GENESIS`;
5. the remaining entry/core protocol is loaded from the **same SHA**;
6. parameter resolution runs (R=3 here), then U0 and Effective Contract freeze;
7. MAIN begins and Strategy Genesis performs the first substantive task work.

If parameter resolution is ambiguous/invalid, the already-born run becomes `ABORTED` and task analysis never starts. If clock genesis fails, no executing run workspace/U0 is created.
