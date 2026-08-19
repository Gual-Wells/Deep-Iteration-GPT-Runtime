# Migration from 4.1.1 to 5.0.0 Alpha 2

Alpha 2 is the corrected integration baseline for the 5.0 final line. The migration is intentionally not a compatibility wrapper around every intermediate pre-release interface: where audit found a correctness or reliability defect, the surrounding interface was reopened rather than preserved.

## What remains conceptually stable

- local personalization is a thin routing/authority transport layer, not a copy of versioned DIGR semantics;
- each routed turn resolves `stable` to one immutable commit and binds `manifest.json` + `VERSION` + all protocol reads to that same commit;
- `P_run`, U0, user hard constraints and Effective Contract minima are commitments;
- Result Sovereignty, semantic completion, Formal Active Time, trusted monotonic clock facts, `?` for unverifiable actuals, compact visible proof, deterministic releases and non-sticky activation remain foundational;
- the deterministic runtime constrains integrity, lifecycle and evidence. It does not choose the model's task strategy.

## What changed for the 5.0 integration baseline

### Routing and startup

The local candidate router now captures exact uppercase ASCII `DIGR` or exact `深度迭代` after leading whitespace only. The repository startup surface has four outcomes: `NATIVE`, `HELP`, `INVALID`, `EXECUTING`. A routed discussion such as `DIGR是什么？` can therefore return unchanged to ordinary ChatGPT without creating a run.

Repository loading is staged. The pinned startup slice is sufficient to classify the surface and establish Run Genesis. An `EXECUTING` call starts trusted clock/journal state before parameter resolution, then loads the remaining protocol from the same pinned commit.

### Parameter surface

The invocation header is punctuation-normalized before deterministic mapping, so mixed full/half-width parentheses, comma and colon forms are equivalent without rewriting U0. Time slots require duration semantics; a bare number can never be invented into T/t. `S`, `S()`, `D`, `D()`, `L`, `L()` are legal structural markers. A mapping is accepted only when the constraints leave exactly one interpretation.

### Frozen commitments versus mutable work

5.0 separates immutable commitments from revisioned current understanding. Strategy, Candidate, EST, Source direction, D proposals before decree and Completion gaps can all change as evidence or failure demands. Strategy snapshots are external memory, not a planner: no scheduler score, priority or deterministic `next_step` decides what GPT should think next.

### Source research and re-entry

Normal execution presumes `SourceDisposition=REQUIRED` unless a concrete U0/host reason records a waiver. This obligation is independent of the numeric `S(n,t,r,b)` minima. An actual S requires a real SourceWorkspace, a formal SOURCE-time binding naming that source, and a semantic SOURCE receipt; opening an empty source object does not satisfy the obligation.

MAIN R is Candidate-backed whole-process re-entry. Source `r` is independently SourceWorkspace-result/revision backed and does not require a global Main Candidate. This keeps source research independently revisable while preserving auditable before/after state.

### D and L

D is now a revisioned intervention session. Proposal revisions remain mutable until Decree binds one revision. D execution is tied to its actual clock state; reintegration is MAIN work and records its MAIN clock binding plus concrete Main consequence. Terminal interventions cannot be silently mutated.

`L_target`, `L_cap` and `L_actual` are distinct. L2/L3 use indexed controlled Input/Output Packet artifacts: input exists before isolated execution, output is produced by the isolated work and bound to the result. Capability alone never proves an actual isolation mode.

### Recovery

Workspace v2 has one authoritative RunPhase lifecycle and one artifact index. Recovery verifies not only file hashes but cross-store semantics: clock/source bindings, Strategy/Candidate/Source revisions, D isolation packets and clock states, EST references, derived Run Brief fields and the final summary. `LiveDIGRRun.resume()` must then establish a fresh same-provider, equal-nonempty-boot clock bridge; file integrity alone is not clock continuity.

## Intermediate pre-release note

5.0.0-alpha.1 was an important Native Assist and clock-journal substrate. Alpha 2 deliberately keeps the reliable foundation while replacing integration behavior that the later audit showed should not be frozen for final 5.0.
