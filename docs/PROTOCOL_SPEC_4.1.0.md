# Protocol Specification — DIGR 4.1.0

## Routing plane (non-version semantic)
Candidate route key -> `stable` -> immutable commit -> pinned `manifest.json` -> manifest-declared protocol paths -> explicit semantic-authority delegation. Route failure means no P_run and no DIGR execution.

## Repository 4.1 bootstrap
Repository P_run classifies task/help/off. Help/off do not start task runtime. Executing task requires trusted two-snapshot monotonic clock readiness before U0 or substantive work. P_target cannot rebind current P_run.

## Invocation
`DIGR(N?,T?,R?,B?,S(n?,t?,r?,b?),D(s?),L(e?)): U0` with Chinese alias. Fixed defaults: B=0, b=0, L1. Missing N/T/R/n/t/r/s are jointly semantically completed. No special AUTO mode.

## Execution
N/R/n/r/s are minima; hard T/t are verified floors; L is exact. S may instantiate multiple times; positive source contract requires at least one actual S. D(0)=off. D(s>0) requires a mature non-local gambit plus Decree/Execution/Result/Reintegration. L1/L2/L3 report actual isolation facts, not API names.

## Formal Active Time
MAIN=>T; SOURCE=>T+t; D_EXCLUSIVE/META/IDLE=>neither. Routing is outside task runtime. 4.1 task-clock readiness is META startup evidence and not formal T/t. Observed duration and hard continuity verification are separate facts.

## Stop/proof
Normal completion requires mechanical minima + Result Quality Gate. Unverified hard actual cannot pass. Canonical proof:
`DIGR（N/actualN，T/actualT，R/actualR，B，Sᵢ（n/actualn，t/actualt，r/actualr，b），D（s）/D（actuals），L（e）/L（actuale））`.
Unknown hard actual is `?`; no version/provenance/logs/EST/D-State by default.
