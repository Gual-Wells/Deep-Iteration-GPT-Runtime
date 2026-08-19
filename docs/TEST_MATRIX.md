# DIGR 5.0 Alpha 3 Test Matrix

The suite tests protocol invariants plus the host repository-transport defect exposed after Alpha 2 deployment.

## Repository transport and routing

1. exact-uppercase `DIGR` / exact `深度迭代` local candidate capture;
2. no repository acquisition occurs for non-candidates;
3. a candidate startup bundle begins with actual `stable_ref_primary` and `stable_ref_corroboration` attempts;
4. no-attempt state cannot satisfy the fixed route-failure precondition;
5. search/index transport provenance is rejected for mutable `stable`;
6. Git ref and Branches endpoints must agree on the same full 40-hex SHA;
7. pinned resources use immutable SHA URLs;
8. GitHub Contents API base64 wrappers normalize to real file bytes and raw-response fallback is covered;
9. immutable same-SHA repository authority and manifest/VERSION binding;
10. four-state repository surface with Native Sovereignty Return;
11. two-stage startup and >=3 compatible monotonic genesis samples.

## Parameter and commitment integrity

12. clock failure occurs before task workspace/U0; parameter ambiguity/invalidity only after EXECUTING clock genesis;
13. no substantive task work before MAIN/Strategy Genesis;
14. full/half-width header punctuation equivalence without U0 rewriting;
15. deterministic unique mapping, typed T/t, legal empty S/D/L markers and ordered D/L tail;
16. single-freeze U0 and Effective Contract; semantic completion cannot replace explicit values;
17. SourceDisposition is independent from S numeric minima.

## Mutable native state and actuals

18. Strategy/Candidate/EST/Source/Completion revision chains and latest-state integrity;
19. Strategy schema forbids scheduler fields;
20. Source pivot/close/reopen and completion-gap transitions are revisioned;
21. MAIN semantic receipts bind real MAIN clock state/current Strategy revision;
22. SOURCE receipts bind real SOURCE state, active source ID and valid source revision;
23. empty source workspace cannot satisfy required Source;
24. MAIN R is Candidate-backed; source r is SourceWorkspace-revision-backed;
25. source t is the union of SOURCE clock intervals, not per-source summation.

## D / L integration

26. D=0 prevents intervention creation and makes L conformance non-blocking;
27. proposal revisions are legal before decree; terminal D rejects mutation;
28. exclusive/background D execution binds appropriate formal states;
29. L target/capability/actual remain distinct;
30. L2/L3 require indexed controlled Input/Output Packets;
31. reintegration binds MAIN state and concrete Main consequence;
32. tampered packet/isolation/D references are rejected during recovery.

## Lifecycle, recovery and release

33. RunPhase transition legality including MAIN final synthesis;
34. artifact-index digest/latest-state drift detection;
35. derived Run Brief and final-summary rederivation checks;
36. resume requires fresh same-provider bridge and equal non-empty boot identity cross-session;
37. JSON schemas/workspace layout cover all persisted artifact families;
38. release builder rejects symlinks/traversal/cache artifacts, regenerates tree/hashes, creates deterministic ZIP bytes and cold-reruns suite + validator;
39. compact/FULL standalone personalization exports are byte-exact package copies.
