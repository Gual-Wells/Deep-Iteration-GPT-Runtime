# Internal D Isolation Baseline

Alpha 7 removes L from the public DIGR parameter and result surface. Users cannot request L1/L2/L3, the Effective Contract contains no L field, and canonical proof contains no L target/actual pair.

D internally uses a fixed **L1 semantic isolation baseline**:

- disruptive proposal/state is kept semantically separated from ordinary MAIN reasoning while D is active;
- exclusive D work runs in D_EXCLUSIVE;
- only explicit reintegration returns selected consequences to MAIN.

IsolationReceipt remains an internal auditable implementation object. Its target for Alpha 7 must be 1. Existing capability evidence fields may remain for backward-compatible internal structure, but host capability must not silently upgrade the actual intervention above the fixed public-independent L1 baseline.

Because isolation is now an internal reliability invariant rather than a user contract dimension, it does not participate in parameter resolution, semantic completion, mechanical stop minima or visible proof.

