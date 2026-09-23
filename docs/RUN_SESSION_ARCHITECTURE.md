# Run Session Architecture — Alpha 9

Preflight occurs before the live lifecycle:

`PINNED → PACKAGE_ATTESTED → PROTOCOL_READY`

No live run exists yet. Only after preflight succeeds does the persistent lifecycle begin:

`GENESIS → PARAMETER_RESOLVED → U0_FROZEN → CONTRACT_FROZEN → EXECUTING → FINALIZING → FINISHED`

ABORTED is terminal.

During EXECUTING, work may span multiple trusted clock epochs. A same-epoch work lease may receive bridge credit. If clock continuity changes, the bridge receives no time credit, a continuity gap is retained, and a leased semantic state may restart at the new trusted epoch. The run itself survives.

Authoritative journals and immutable revision state remain on the persistence path. Derived run-brief/latest views are rebuildable caches and may lag between coarse checkpoints such as lifecycle transitions, work-lease boundaries, resume and finalization.

FINISH is the durable formal-time commit. Recovery may repair FINISH→FINALIZING and valid-summary→FINISHED crash windows, but never reopens timing.
