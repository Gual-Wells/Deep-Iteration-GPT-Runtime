# 5.0.0-alpha.2 Corrected Integration Baseline

Alpha 2 replaces Alpha 1 as the intended mother-base for 5.0 final. Alpha 1's clock journal and authority foundations remain valuable, but the audit found correctness/reliability defects in surrounding integration; preserving those interfaces merely for compatibility would freeze the wrong behavior.

Interfaces intended to freeze after Alpha 2: routing/surface/parameter/run-session/workspace/event semantics described by current manifest schemas, with clock-journal schema retained from Alpha 1. Future pre-final changes should require a concrete bug or contradiction, not cosmetic refactoring.

Change discipline: runtime behavior first, then schema/core/help/examples/tests must converge on the same semantics; no “documentation-only Alpha 2”. Deterministic release and cold validation are mandatory.
