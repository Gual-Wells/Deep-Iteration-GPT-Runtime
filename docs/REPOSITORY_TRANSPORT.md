# Repository Transport — Alpha 10

Mutable stable authority remains connector branch HEAD or direct REST branch/ref consensus. After pinning, every read uses the same immutable SHA.

EXECUTING no longer verifies helpers one by one. Startup obtains:
1. one recursive Git tree for the pinned SHA;
2. the exact pinned `runtime/runtime_package.py` verifier;
3. the exact-commit runtime archive.

The verifier checks manifest, VERSION, every helper, execution bundle, and every bundle member against the Git tree in one operation. The verified bundle then yields ExecutingProtocolLoadReceipt before Genesis.

There is no mandatory repository transport after Genesis. Search/index snapshots are never mutable-ref authority.
