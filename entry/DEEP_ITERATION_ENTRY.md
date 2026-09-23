# DIGR 5.0.0-alpha.10 — Deep Iteration Entry

Alpha 10 keeps DIGR deep while making reliability machinery coarse-grained.

## Authority
P_run, raw-message binding, U0, user hard constraints and Effective Contract are immutable for the run. P_target cannot rebind P_run.

## Contract
B/b default to 0. Omitted D defaults to 0; explicit D()/D values may request a non-zero commitment. Missing N/T/R and applicable source minima are completed conservatively: they are safeguards against premature stopping, not aspirational workloads.

SourceDisposition is a necessity decision, not a blanket presumption. REQUIRED is used when U0 explicitly asks external research/current facts or external evidence materially improves correctness. Otherwise WAIVED is valid with a concrete reason and source minima become non-applicable/zero.

## Work
Native intelligence owns task strategy. N records meaningful evolution; R attacks the current Candidate. Source work and D are used when they improve the result, not to create protocol theatre. Ordinary completed D should use the compact lifecycle receipt; granular D revisions are exceptional.

## Persistence and resume
Authoritative revisions and hash-chained journals persist. Rebuildable latest pointers/run-brief are caches and stay out of the global integrity-index hot path. STATE and WorkLease records are already durable and do not force global checkpoints.

Ordinary resume performs write-intent repair + journal reindex + one store load. Full revision-tree verification is fallback/audit only.

## Time
T = MAIN + SOURCE + D_EXCLUSIVE; t = SOURCE. Explicit B=1/b=1 makes timing hard. Clock-epoch discontinuity loses only unverifiable bridge credit.

## Finish
Semantic completion and mechanical hard commitments must hold before FINISH. FINISH is durable and never reopens.
