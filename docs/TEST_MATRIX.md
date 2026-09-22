# DIGR 5.0 Alpha 7 Test Matrix

The suite covers the prior authority/execution-integrity baseline plus live formal-time defects observed on multi-tool ChatGPT hosts.

## Repository transport, authority and execution integrity

1. exact-uppercase DIGR / exact 深度迭代 candidate capture;
2. no repository acquisition for non-candidates;
3. mutable stable requires real current acquisition evidence;
4. immutable P_run binds manifest/VERSION at one commit;
5. bootstrap_index precedes startup and remains structural rather than semantic authority;
6. NATIVE/HELP/INVALID/EXECUTING surface behavior;
7. >=3 compatible monotonic Genesis samples;
8. full execution bundle verification before parameter resolution;
9. post-Genesis protocol-load failure persists ABORTED;
10. existing helpers cannot be replaced by semantic-equivalent model code;
11. component interrogation binds exact component/operation/executor;
12. accepted execution commitment constrains the next relevant action;
13. same-commit runtime artifact verifies helper identity against the pinned tree;
14. missing identity-preserving delivery fails closed.

## Alpha 7 parameter and contract surface

15. public order is N<T<R<B<S<D;
16. B=1 and b=1 are the only fixed parameter defaults;
17. missing N/T/R/n/t/r/s are semantic completion fields;
18. bare numbers never become T/t;
19. L/L()/L= inputs are INVALID;
20. parameter-resolution schema contains no L_e;
21. Effective Contract contains no L field or L mismatch policy;
22. D internally receives fixed L1 isolation.

## Formal time and cross-host continuity

23. T = MAIN + SOURCE + D_EXCLUSIVE;
24. t = SOURCE only;
25. META/IDLE do not count;
26. D_EXCLUSIVE contributes to T;
27. a work lease requires active MAIN/SOURCE/D_EXCLUSIVE;
28. leased same-boot resume restores the semantic state;
29. leased SOURCE resume restores active_source_ids;
30. leased external SOURCE time contributes to T and t;
31. unleased formal resume produces a CoverageGap;
32. an unleased gap is never silently dropped;
33. coverage gaps invalidate hard T/t verification;
34. hard verification still requires trusted clock continuity;
35. soft timing remains non-blocking;
36. parallel source work uses clock-union time rather than per-source multiplication.

## Actuals, D and state integrity

37. MAIN evolution/re-entry receipts require valid MAIN bindings;
38. SOURCE receipts require real SourceWorkspace plus active SOURCE binding;
39. empty source workspace cannot satisfy SourceDisposition REQUIRED;
40. D(0) means zero minimum, not disabled;
41. D actual counts completed/reintegrated interventions;
42. D execution/reintegration remains clock/state bound;
43. internal isolation target is L1;
44. artifact-index/latest-state drift is detected;
45. recovery independently re-derives timing/state facts.

## Finalization and proof

46. finish_time requires MAIN;
47. semantic completion readiness is required before finalization;
48. finish_time projects actuals before mutating the live ledger;
49. unmet hard time denies finalization and leaves phase EXECUTING;
50. incomplete coverage denies hard finalization;
51. admitted finish closes ledger then enters FINALIZING;
52. FINISHED requires delivery_ready=true;
53. canonical proof omits L;
54. hard-unverified or coverage-incomplete actual time renders ?;
55. visible actual durations floor to whole seconds.

## Release and cold validation

56. every persisted artifact family conforms to its schema;
57. manifest/interface versions match Alpha 7;
58. execution bundle exactly matches current entrypoint/core bytes and SHA-256 digests;
59. Python sources parse under the declared minimum grammar;
60. UTF-8/LF release hygiene is enforced;
61. deterministic runtime artifact build reruns the unit suite and repository validator;
62. protocol spec, Help, core and manifest agree on work leases, D time and public-L removal.

