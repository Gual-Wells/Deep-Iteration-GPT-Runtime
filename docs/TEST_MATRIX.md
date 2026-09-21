# DIGR 5.0 Alpha 6 Test Matrix

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
9. manifest-declared `bootstrap_index` is acquired first, exposes implemented-machine/truth-source/native-intelligence boundaries, and remains non-semantic authority;
10. Plus local-router task-work firewall: reading STARTUP is not execution, EXECUTING is not readiness, and the exact observed regression (task comparison beginning before startup gates) is rejected;
11. NATIVE/HELP/INVALID/EXECUTING surface behavior and >=3 compatible monotonic genesis samples;
12. EXECUTING uses one manifest-declared immutable execution bundle after genesis; bundle members must exactly cover entrypoint/core with verified digests;
13. parameter resolution is blocked until ExecutingProtocolLoadReceipt exists; mandatory post-genesis protocol-load failure persists ABORTED;
14. execute-before-interpret regression: an existing helper cannot be replaced by semantic-equivalent model code/manual receipt;
15. component interrogation requires exact component/operation/executor plus explicit direct-execution / no-substitution / no-manual-result commitment, with at most two re-education rounds;
16. exact-commit runtime artifact names bind to P_run SHA and runtime index members match deterministic_helpers;
17. artifact helper identity is Git-blob/byte-length verifiable against the pinned commit tree; missing bridge + missing/invalid artifact fails closed.

## Parameter, contract and timing integrity

18. deterministic fixed defaults B=1/b=1/L1 precede semantic completion;
19. typed T/t, unique-or-fail mapping, legal empty S/D/L markers and ordered D/L tail;
20. explicit values cannot be overwritten by semantic completion;
21. SourceDisposition is independent of S numeric minima;
22. N/R/n/r/D lower-bound semantics remain distinct from B/b-governed T/t targets;
23. B/b=0 soft timing does not become a mechanical lower-bound gate; B/b=1 requires verified hard time;
24. initialization/META does not inflate T/t.

## Mutable native state and actuals

25. Strategy/Candidate/EST/Source/Completion revision chains and latest-state integrity;
26. MAIN semantic receipts bind MAIN state/current strategy;
27. SOURCE receipts bind SOURCE state, active source and valid source revision;
28. empty source workspace cannot satisfy required Source;
29. MAIN R is Candidate-backed; source r is SourceWorkspace-revision-backed;
30. source t is SOURCE clock-union time, not per-source summation.

## D / L integration

31. `D(0)` permits quality-driven intervention creation and actual D may exceed target;
32. recovery accepts valid D interventions under a zero D minimum;
33. D actual remains completed+reintegrated intervention count;
34. L target/capability/actual remain distinct;
35. no completed D makes completed-intervention L gating inapplicable;
36. actual completed D under D target zero receives normal L mismatch/gating checks;
37. L2/L3 require indexed controlled Input/Output Packets and correct foreground-state bindings;
38. reintegration binds MAIN state and concrete Main consequence;
39. tampered D/L references are rejected during recovery.

## Proof, Help, lifecycle and release

40. canonical proof floors actual durations to whole seconds and hides hard-unverified time as `?`;
41. canonical zh-CN Help states fixed-default precedence, Source REQUIRED semantics, D(0) lower-bound semantics and timing policies;
42. RunPhase legality including MAIN final synthesis;
43. artifact-index/latest-state drift and derived summary checks;
44. resume continuity rules;
45. schemas/workspace layout cover persisted artifact families;
46. release builder rejects unsafe/case-colliding/Windows-nonportable paths, symlinks, traversal and caches;
47. deterministic ZIP cold-reruns suite + validator;
48. Plus deployable/FULL standalone personalization exports are byte-exact package copies; no Free/Go local-personalization copy is shipped.
