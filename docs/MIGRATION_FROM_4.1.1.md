# Migration from 4.1.1 to the 5.0 Alpha 8 baseline

The 5.0 line evolved through several correction passes: Alpha 2 established the current execution/state mother-base, Alpha 3 hardened repository transport, Alpha 4 corrected live integration, Alpha 5 made B/b hard by default, Alpha 6 added implementation-identity execution, Alpha 7 added cross-host time attribution, and Alpha 8 converges crash recovery and public semantics.

Current public parameters are N/T/R/B/S/D. Public L is removed; D uses internal L1.

Current timing is T=MAIN+SOURCE+D_EXCLUSIVE and t=SOURCE. B/b=1 proves a lower bound over counted hard-verifiable intervals. Unleased gaps receive no time credit but do not invalidate the whole run.

Current recovery treats immutable revision history and verified journals as authoritative, while latest pointers/run-brief are derived. FINISH is a durable commit point.

Historical 4.x/early-5.x L2/L3, D-not-in-T and complete-coverage stop rules must not be imported into the current pinned protocol.

