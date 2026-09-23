# DIGR 5.0 Alpha 9 Test Matrix

The suite protects both safety and liveness invariants. Tests are regression guards; the release architecture remains defined by pinned manifest/entry/core.

## Repository authority and preflight

1. exact-uppercase DIGR / exact 深度迭代 routing remains intact;
2. stable resolves to immutable P_run and binds manifest/VERSION;
3. bootstrap_index precedes startup;
4. NATIVE/HELP/INVALID do not create a run;
5. EXECUTING requires exact implementation delivery;
6. runtime-distribution schema 3 packages helpers plus the execution bundle;
7. RUNTIME-INDEX schema 2 binds commit, manifest, VERSION, helpers and protocol bundle;
8. complete protocol verification and ExecutingProtocolLoadReceipt exist before Genesis;
9. missing/mismatched preflight prevents Genesis rather than aborting a born run;
10. post-Genesis protocol rebinding is forbidden.

## Parameter and contract surface

11. public order remains N<T<R<B<S<D;
12. B=0 and b=0 are the fixed defaults;
13. explicit B=1/b=1 remains hard timing;
14. missing N/T/R/n/t/r/s remain semantic-completion fields;
15. L remains absent from the public parameter/contract/proof surface;
16. D uses internal L1.

## Formal time and liveness

17. T = MAIN + SOURCE + D_EXCLUSIVE; t = SOURCE;
18. work leases require an active formal state;
19. same-epoch leased resume may bridge formal time;
20. unleased same-epoch resume records an ordinary CoverageGap;
21. lost clock continuity creates EPOCH_ANCHOR/PROBE/READY rather than killing the run;
22. cross-epoch bridge duration is never guessed or counted;
23. prior and later hard-verifiable intervals remain independently valid;
24. a leased semantic state may restart at the new epoch;
25. coverage completeness is diagnostic, not a stop gate.

## Hot-path persistence

26. append-only journals and immutable revisions remain authoritative;
27. semantic evolution/R/source/D events do not require synchronous run-brief refresh;
28. lifecycle transitions, lease boundaries, resume and finalization may checkpoint derived cache;
29. stale run-brief/latest pointers remain rebuildable after authoritative verification;
30. write-intent and journal-chain recovery remain fail-closed on irreconstructible state.

## Actuals, finalization and proof

31. MAIN/SOURCE semantic events retain clock/strategy/candidate/source bindings;
32. R/r cannot move backward to superseded revisions;
33. D execution/result/reintegration preserve state and isolation bindings;
34. SourceDisposition REQUIRED/WAIVED semantics remain enforced;
35. finalization admission occurs before FINISH;
36. explicit hard minima remain strict;
37. FINISH is durable and FINISHED requires delivery_ready=true;
38. canonical proof omits L and hard actuals are verified counted lower bounds.

## Release convergence

39. manifest/interface versions identify Alpha 9;
40. generated execution bundle exactly matches current entrypoint/core bytes;
41. runtime artifact includes the exact generated bundle;
42. Python/JSON/UTF-8 release hygiene remains enforced;
43. deterministic generated metadata converges before stable promotion.
