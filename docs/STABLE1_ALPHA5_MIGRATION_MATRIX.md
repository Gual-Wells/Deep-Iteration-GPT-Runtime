# Stable.1 / Alpha5-r3 / Berta1 Migration Matrix

| Area | Stable.1 base | Alpha5-r3 signal | Berta1 decision |
|---|---|---|---|
| Repository authority | Strong pinned manifest, ref/branch consensus | Retained | Retain unchanged; no cache may bypass live mutable-ref resolution |
| Final bytes | Exact Candidate binding, two-phase fail-closed delivery | Weaker/incomplete in branch comparison | Stable.1 wins |
| Parameter parser | Unique-or-fail but wrapper/order constrained | No V | Add typed-anywhere Berta layer; preserve legacy fallback |
| Timing | T/t plus D state | ClockJournal sole truth, explicit D clock/IDLE | Four projections T/t/D/V; durable-before-memory append |
| D | Revisioned, reintegrated intervention | Better exclusive timing evidence | Retain lifecycle; add opaque D+/D−/Dx semantic directions |
| V | Absent | Supplement proposal only | Implement private persistent VLedger and qualification gate |
| Completion | Free-text assessment plus gaps | Structured completion proposal | Add four structured criteria with migration compatibility |
| Objective/frontier | Native Strategy/Candidate | ObjectiveEnvelope/frontier ideas | Keep lightweight objective/Strategy; do not force frontier overhead |
| Logs | Internal workspace evidence | UI/bridge proposals | Local TOTAL + N/T/R/B/S/D/V/L only |
| MCP/UI/backend | None | Proposed future path | Explicitly excluded in Berta1 |
| Host/model executability | Capability negotiation | M0/C* concern | Capability facts and caps, no hardcoded model brand/tier |

## Deferred

- verified-local artifact cache remains optional future transport acceleration and may be used only after live stable HEAD resolution and exact hash equality;
- client-native dynamic UI remains a separate host project, not protocol semantics;
- stricter mandatory structured-completion gating is deferred until migration evidence shows it does not reject otherwise valid stable.1 work.
