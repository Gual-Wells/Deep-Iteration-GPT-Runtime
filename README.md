# Deep Iteration GPT Runtime (DIGR) 5.0.0-alpha.2

**Status:** corrected integration baseline intended to freeze for DIGR 5.0 final.

DIGR 5.0 is a reliability exoskeleton around native model intelligence. It does not replace the model with a planner/search controller. It gives an explicitly invoked high-investment task a pinned protocol authority, early trusted timing, immutable U0/minimum commitments, revisable working strategy, external-source state, candidate-backed re-entry, isolated D interventions, evidence, persistence and recovery.

## Why Alpha 2 exists

Alpha 1 proved the Native Assist substrate and clock-journal foundation, but a full code/rule audit found several interfaces that were internally consistent yet protected behavior no longer suitable for the 5.0 final baseline. Alpha 2 deliberately reopens those interfaces rather than preserving correctness defects for compatibility.

The central correction is:

> **Freeze commitments, never freeze strategy.**

`P_run`, U0, user hard constraints and Effective Contract minimums are immutable. Task representation, decomposition, Strategy, Source direction, validation/tool plan, assumptions, Candidate and D gambits are revisioned working state and may pivot whenever evidence justifies it.

Other Alpha 2 corrections include:

- exact-uppercase local `DIGR` capture + repository `NATIVE` sovereignty return;
- two-stage repository startup so Clock Genesis is close to invocation detection;
- deterministic unique-or-fail parameter resolution with typed T/t and mixed punctuation normalization;
- source research presumed REQUIRED unless explicitly waived for a real reason;
- source t from clock-journal SOURCE intervals bound to active S IDs (no second source-aggregate truth);
- Candidate-backed whole-process R;
- D proposal revisions until Decree, evidence/result revisions and concrete Main reintegration;
- L target/capability/actual split and intervention-linked isolation receipts/packets;
- one RunPhase lifecycle, artifact integrity index, derived run brief and comprehensive workspace recovery;
- strict cross-session clock resume requiring equal non-empty boot identity;
- Event Receipt v2 bound to clock/strategy/candidate/source;
- expanded user-facing help.

## Authority and startup

Local personalization is intentionally thin. It broadly routes exact-uppercase `DIGR` / exact `深度迭代`, pins `stable` to one immutable SHA, validates pinned `manifest.json` + `VERSION`, then loads only the manifest-declared startup slice. The pinned repository returns `NATIVE`, `HELP`, `INVALID` or `EXECUTING`.

`EXECUTING` performs trusted ≥3-sample Clock Genesis **before parameter resolution/U0/task work**, then loads the full pinned entry/core. Failure after genesis is an auditable aborted run, not “nothing happened”.

## Execution shape

```text
USER
  ↓
local broad route → stable→SHA→manifest/VERSION
  ↓
minimal startup slice → NATIVE | HELP | INVALID | EXECUTING
                                      ↓
                                  CLOCK GENESIS
                                      ↓
                              Parameter Resolution
                                      ↓
                                     U0
                                      ↓
                           Effective Contract minima
                                      ↓
                              MAIN / Strategy Genesis
                         ↙             ↓              ↘
                       N              S              D/L
                         ↘             ↓              ↙
                         Strategy ↔ Candidate ↔ Evidence
                                      ↕
                           R whole-process re-entry
                                      ↓
                         Completion / open-gap state
                                      ↓
                         finish clock + recovery audit
                                      ↓
                              RESULT + compact proof
```

See `entry/HELP.md` for user-facing invocation/parameter behavior and `docs/ARCHITECTURE.md` for the engineering model.

## Validation

Run:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python tests/validate_repo.py
```

Deterministic release:

```bash
python tools/build_release.py \
  --output ../Deep-Iteration-GPT-Runtime-5.0.0-alpha.2.zip \
  --personalization-output ../DIGR-5.0.0-alpha.2-CHATGPT-LOCAL-PERSONALIZATION.txt \
  --full-personalization-output ../DIGR-5.0.0-alpha.2-CHATGPT-LOCAL-PERSONALIZATION-FULL.txt
```

The builder regenerates release metadata, runs tests/validator in cold extracted trees and rejects unsafe/symlink ZIP members. Final release validation should build twice and compare byte identity.
