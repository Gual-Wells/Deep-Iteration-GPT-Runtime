# DIGR 5.0 Alpha 4 Test Matrix

The suite covers protocol invariants plus live black-box defects observed through Alpha 3 deployment.

## Repository transport and routing

1. exact-uppercase `DIGR` / exact `深度迭代` local candidate capture;
2. no repository acquisition for non-candidates;
3. actual acquisition evidence precedes route success/failure;
4. search/index/crawl provenance is rejected for mutable `stable`;
5. already-connected connector mode accepts the current `stable` branch HEAD without requiring Git-ref endpoint access;
6. direct REST mode requires Branches/Git-ref full-SHA consensus and permits one bounded live re-observation for a push-between-reads race;
7. pinned resources use immutable SHA URLs and Contents raw/base64 fallback is normalized;
8. manifest/VERSION same-SHA binding and staged startup;
9. NATIVE/HELP/INVALID/EXECUTING surface behavior and >=3 compatible monotonic genesis samples;
10. EXECUTING uses one manifest-declared immutable execution bundle after genesis; bundle members must exactly cover entrypoint/core with verified digests;
11. parameter resolution is blocked until `ExecutingProtocolLoadReceipt` exists; mandatory post-genesis protocol-load failure persists ABORTED.

## Parameter, contract and timing integrity

12. deterministic fixed defaults B=0/b=0/L1 precede semantic completion;
13. typed T/t, unique-or-fail mapping, legal empty S/D/L markers and ordered D/L tail;
14. explicit values cannot be overwritten by semantic completion;
15. SourceDisposition is independent of S numeric minima;
16. N/R/n/r/D lower-bound semantics remain distinct from B/b-governed T/t targets;
17. B/b=0 soft timing does not become a mechanical lower-bound gate; B/b=1 requires verified hard time;
18. initialization/META does not inflate T/t.

## Mutable native state and actuals

19. Strategy/Candidate/EST/Source/Completion revision chains and latest-state integrity;
20. MAIN semantic receipts bind MAIN state/current strategy;
21. SOURCE receipts bind SOURCE state, active source and valid source revision;
22. empty source workspace cannot satisfy required Source;
23. MAIN R is Candidate-backed; source r is SourceWorkspace-revision-backed;
24. source t is SOURCE clock-union time, not per-source summation.

## D / L integration

25. `D(0)` permits quality-driven intervention creation and actual D may exceed target;
26. recovery accepts valid D interventions under a zero D minimum;
27. D actual remains completed+reintegrated intervention count;
28. L target/capability/actual remain distinct;
29. no completed D makes completed-intervention L gating inapplicable;
30. actual completed D under D target zero receives normal L mismatch/gating checks;
31. L2/L3 require indexed controlled Input/Output Packets and correct foreground-state bindings;
32. reintegration binds MAIN state and concrete Main consequence;
33. tampered D/L references are rejected during recovery.

## Proof, Help, lifecycle and release

34. canonical proof floors actual durations to whole seconds and hides hard-unverified time as `?`;
35. canonical zh-CN Help states fixed-default precedence, Source REQUIRED semantics, D(0) lower-bound semantics and timing policies;
36. RunPhase legality including MAIN final synthesis;
37. artifact-index/latest-state drift and derived summary checks;
38. resume continuity rules;
39. schemas/workspace layout cover persisted artifact families;
40. release builder rejects unsafe/case-colliding/Windows-nonportable paths, symlinks, traversal and caches;
41. deterministic ZIP cold-reruns suite + validator;
42. compact/FULL standalone personalization exports are byte-exact package copies.
