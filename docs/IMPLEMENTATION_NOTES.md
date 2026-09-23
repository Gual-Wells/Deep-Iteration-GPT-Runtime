# Alpha 9 Implementation Notes

Alpha 9 is a liveness-convergence release over Alpha 8.

- Runtime distribution embeds the generated execution bundle; RUNTIME-INDEX schema 2 binds manifest, VERSION, helper identities and bundle.
- Full protocol verification occurs before LiveDIGRRun.start creates Genesis. Post-Genesis protocol bind/abort paths are retired.
- Resume first tries same-epoch continuity; on failure ClockJournal opens EPOCH_ANCHOR / EPOCH_PROBE / EPOCH_READY rather than aborting.
- Cross-epoch time is uncredited; prior/later verified intervals remain usable.
- run-brief is derived cache state and no longer rewrites synchronously after each semantic evolution/source/R/D event.
- B/b return to 0; explicit B=1/b=1 remains strict.

Exact implementation identity, P_run/U0/contract, Source/R/D semantics and FINISH durability remain unchanged.
