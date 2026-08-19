# DIGR 5.0 Alpha 2 Test Matrix

The suite tests protocol invariants rather than merely preserving old implementation behavior.

## Authority, routing and startup

1. exact-uppercase `DIGR` / exact `深度迭代` local candidate capture;
2. immutable same-SHA repository authority and manifest/VERSION binding;
3. four-state repository surface with Native Sovereignty Return;
4. two-stage startup and >=3 compatible monotonic genesis samples;
5. clock failure before task workspace/U0; parameter ambiguity or invalidity only after an EXECUTING run has clock genesis;
6. no substantive task work before MAIN/Strategy Genesis.

## Parameter and commitment integrity

7. full/half-width header punctuation equivalence without U0 rewriting;
8. deterministic unique parameter mapping, typed T/t, legal empty S/D/L markers and ordered D/L tail;
9. single-freeze U0 and Effective Contract; explicit invocation values cannot be silently replaced by semantic completion;
10. SourceDisposition is independent from S numeric minima.

## Mutable native working state

11. Strategy/Candidate/EST/Source/Completion revision chains and latest-state integrity;
12. Strategy schema forbids scheduler fields that would turn the exoskeleton into a planner;
13. Source pivot/close/reopen is revisioned rather than write-once;
14. completion gap open/revise/close/reopen transitions remain explicit.

## Actuals and semantic events

15. MAIN semantic receipts bind an actual MAIN clock state and current Strategy revision;
16. SOURCE receipts bind an actual SOURCE state, active source ID and valid source revision;
17. required Source cannot be satisfied by an empty opened workspace;
18. MAIN R is Candidate-before/after or justified-retention backed;
19. Source r is SourceWorkspace-before/after or justified-retention backed and does not require a Main Candidate;
20. source t uses the union of SOURCE clock intervals, not per-source summation.

## D / L integration

21. D=0 prevents intervention creation and makes L conformance non-blocking;
22. proposal revisions are legal before decree; terminal D sessions reject later mutation;
23. exclusive D execution binds D_EXCLUSIVE, background D binds concurrent MAIN/SOURCE;
24. L target/capability/actual remain distinct;
25. L2/L3 require indexed controlled Input Packet before isolated work and indexed Output Packet on the D result;
26. D reintegration is bound to MAIN clock state and concrete Main consequence;
27. tampered packet/isolation/D references are rejected during recovery.

## Lifecycle, recovery and release

28. RunPhase transition legality, including required return to MAIN for final synthesis before timing closes;
29. artifact-index digest/latest-state drift detection;
30. Run Brief digest **and** derived-field verification after recovery;
31. final run-summary is independently rederived and compared, not trusted because it is indexed;
32. resume requires a fresh same-provider bridge and equal non-empty boot identity for cross-session continuity;
33. JSON schemas validate and workspace layout v2 maps all persisted artifact families;
34. release builder rejects symlinks/traversal/cache artifacts, regenerates tree/hashes, creates deterministic ZIP bytes, cold-extracts and reruns the suite + repository validator;
35. compact and FULL standalone personalization exports are byte-exact copies of their canonical in-package sources.
