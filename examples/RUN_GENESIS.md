# Contracted Run Genesis — Alpha 10

Input: `DIGR（R=3）：检查并改进方案`

Required order:

1. resolve stable → immutable SHA and bind manifest/VERSION;
2. read INDEX + startup slice;
3. classify EXECUTING;
4. obtain one pinned recursive Git tree, the pinned runtime-package verifier, and the exact-commit runtime archive;
5. execute one package attestation covering helpers + compact protocol bundle + bundle members;
6. construct ExecutingProtocolLoadReceipt;
7. establish trusted monotonic readiness and create Genesis;
8. resolve R=3 and defaults, freeze U0/contract;
9. enter MAIN.

No execution-bundle acquisition remains after Genesis.
