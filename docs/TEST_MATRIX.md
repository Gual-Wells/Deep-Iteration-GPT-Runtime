# DIGR 4.1 Contract Test Matrix

## Routing / authority
1. local personalization contains routing/discovery/delegation only, not versioned DIGR semantics;
2. stable must pin to full immutable SHA; route receipt binds repository/ref/commit/manifest digest;
3. legacy manifest without bootstrap_entry routes to its declared entrypoint/core without importing 4.1 semantics;
4. 4.1 manifest discovers bootstrap/entry/core from the same pinned commit;
5. P_run identity must match route receipt repository + commit;
6. context/local/other-commit/P_target cannot be represented as P_run semantic authority;
7. route failure is distinct from DIGR task startup failure.

## Invocation / startup
8. repository 4.1, not local router, classifies task/help/off;
9. help/off do not instantiate task-clock startup;
10. executing 4.1 task requires two-snapshot trusted clock readiness before U0/substantive work.

## Defaults / contract
11. B missing=>0; b=>0; L=>1;
12. N/T/R/n/t/r/s remain model-native semantic completion;
13. hard shorthand cannot use degenerate T/t evasion;
14. Effective Contract freezes targets; runtime rejects bool/NaN/Infinity.

## N/R/S/EST
15. N/R/n/r substantive; EST is memory not search/CoT;
16. positive source contract forces >=1 S;
17. multi-S n/r=min per-S; t=source-active union;
18. R/r whole-process challenge + ABG.

## D/L
19. D(0) disables; D(s>0) requires Mature Gambit + Decree/Execution/Result/Reintegration;
20. no numeric ambition/disturbance/novelty/coup controller;
21. L1 semantic only; L2/L3 require real facts; API names cannot self-certify; L exact.

## Time / proof / release
22. MAIN=>T; SOURCE=>T+t; D_EXCLUSIVE/META/IDLE=>neither;
23. observed duration distinct from hard verification;
24. unverified hard number cannot satisfy stop or visible proof;
25. canonical proof exact form; unknown=`?`; no legacy markers;
26. primary and Free/Go routers are byte-identical and contain no protocol copy;
27. standalone personalization export is byte-identical to ZIP-internal primary;
28. Python >=3.10 syntax, UTF-8/LF/control and local-link checks;
29. release rejects symlink/path traversal/self-inclusion/incomplete hashes;
30. deterministic ZIP bytes, CRC, exact tree/SHA and cold validation;
31. property tests cover source union, interval duration, hard proof and isolation monotonicity.
