# Internal D Isolation Baseline

Alpha 9 has no public L parameter or result dimension. Users cannot request L1/L2/L3, the Effective Contract contains no L field, and canonical proof contains no L target/actual pair.

D uses a fixed internal L1 semantic-isolation baseline:

- disruptive proposal/state remains semantically separated from ordinary MAIN reasoning while active;
- exclusive D execution and D Result production run in D_EXCLUSIVE;
- only explicit reintegration returns selected consequences to MAIN.

IsolationReceipt remains an internal auditable implementation object and its active target is 1. Historical L2/L3 capability/storage fields may remain only for compatibility; they are not active Alpha 9 user semantics and must not create a public isolation claim.

Because isolation is an internal reliability invariant rather than a user contract dimension, it does not participate in parameter resolution, semantic completion, mechanical stop minima or visible proof.
