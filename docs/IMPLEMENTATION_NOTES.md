# Alpha 2 Implementation Notes

`runtime/routing.py` is transport-only. `runtime/invocation_surface.py` classifies the pinned startup surface. `runtime/parameter_resolution.py` performs deterministic unique mapping after clock genesis. None of these chooses task strategy.

`LiveDIGRRun` is the lifecycle/evidence binding layer. The old raw `.events.append()` path is replaced by thin semantic wrappers because a syntactically valid receipt in the wrong work state is not a valid actual. Wrappers validate references, not intellectual quality; specifically they also validate phase and foreground clock state.

Strategy/Candidate/EST/Source/D/Completion stores are revisioned. Source time has no standalone aggregate helper: formal SOURCE intervals plus source-activity bindings are the one time chain. An actual S additionally needs semantic source work, so creating an empty workspace cannot satisfy Source Presumption. Main R is Candidate-backed; source r is SourceWorkspace-revision-backed.

D/L is one temporal information-flow lifecycle. An L2/L3 controlled Input Packet is indexed before isolated execution; Output Packet is indexed after isolated work and attached to its result. D execution and reintegration bind formal clock states. Terminal D sessions reject mutation. Isolation facts describe capability while isolation receipts select the target-bounded actual mode.

Recovery first verifies artifact bytes/latest pointers, then cross-checks semantic references against clock/source/Strategy/Candidate/D state, verifies the derived Run Brief, and rederives a FINISHED run summary. Resume separately establishes a new same-boot clock bridge; integrity alone is not time continuity.
