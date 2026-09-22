# Internal D Isolation Baseline

Alpha 8 has no public L parameter or result dimension. Users cannot request L1/L2/L3, the Effective Contract contains no L field, and canonical proof contains no L target/actual pair.

D uses a fixed **internal L1 semantic isolation baseline**:

- disruptive proposal/state is kept semantically separated from ordinary MAIN reasoning while D is active;
- exclusive D execution and D Result production run in D_EXCLUSIVE;
- only explicit reintegration returns selected consequences to MAIN.

IsolationReceipt remains an internal auditable implementation object and its target must be 1. Historical L2/L3 capability fields may remain only as legacy storage compatibility; they are not active Alpha 8 user semantics and must not cause the host to claim a higher public isolation level.

Because isolation is an internal reliability invariant rather than a user contract dimension, it does not participate in parameter resolution, semantic completion, mechanical stop minima or visible proof.

