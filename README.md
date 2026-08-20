# Deep Iteration GPT Runtime (DIGR) 5.0.0-alpha.4

**Status:** black-box corrected integration baseline intended to converge toward DIGR 5.0 final.

DIGR 5.0 is a reliability exoskeleton around native model intelligence. It does not replace the model with a planner/search controller. An explicitly invoked high-investment task receives pinned protocol authority, early trusted timing, immutable U0/contract commitments, revisable strategy/source/candidate state, disruptive interventions, evidence, persistence and recovery.

## Why Alpha 4 exists

Alpha 3 closed the host repository-transport gap exposed by route failures that occurred before any repository acquisition. Live Alpha 3 deployment then supplied a second round of black-box evidence:

- once GitHub was connected, the ChatGPT GitHub connector resolved the real current `stable` HEAD and read pinned files successfully, but the deterministic transport adapter still modeled connector and REST acquisition as the same two-endpoint workflow;
- `D(0)` had been partially encoded as “D disabled”, contradicting the project-wide lower-bound semantics and the lower-level D store/actuals implementation;
- L applicability was keyed to the frozen D minimum rather than actual completed D;
- documentation blurred unconditional count/D minima with B/b-governed soft/hard time targets;
- user-visible ChatGPT proofs leaked raw fractional seconds instead of the canonical deterministic renderer's whole-second actual format;
- `entry/HELP.md` was English despite `language=zh-CN`, and model translation weakened normative wording such as SourceDisposition `REQUIRED`.

Alpha 4 corrects these defects while preserving the Alpha 3 authority/clock/state architecture.

## Alpha 4 corrections

### Transport capability split

Mutable `stable` has explicit transport-specific authority:

- an **already-connected GitHub repository connector** may read the public repository's `stable` branch resource and accept its current 40-hex HEAD SHA;
- a genuine **direct REST client** reads both Branches and Git-ref resources and requires SHA consensus;
- search/index/crawl snapshots remain inadmissible mutable-ref authority;
- no new GitHub OAuth connection is required solely to bootstrap this public repository.

After one SHA is accepted, all manifest/VERSION/startup/core reads remain pinned to that immutable commit.

### D/L lower-bound correction

`D(s)` is a minimum completed/reintegrated intervention count. `D(0)` means “no completed D is mechanically required”, not “D is disabled”. Quality-driven D remains permitted and actual D may exceed target. L continues to preserve `L_target`, `L_cap` and `L_actual`; L stop applicability follows **actual completed D**, not the D minimum.

### Timing target terminology

`N/R/n/r/D` are unconditional lower bounds. T/t are frozen **targets** governed by B/b:

- B/b=0: soft target, not a mechanical lower-bound stop gate;
- B/b=1: hard lower bound requiring trusted timing evidence.

Initialization/repository/META work remains outside T/t unless it becomes substantive MAIN/SOURCE task work.

### Canonical proof and Help

The protocol now explicitly requires the same user-visible proof semantics as `runtime/proof.py`: actual durations floor to whole seconds; hard-unverified time is `?`; raw float/nanosecond values do not leak. The canonical Help is now a professional zh-CN reference with explicit default precedence, timing policy, SourceDisposition, D/L and proof rules.

## Authority and startup

```text
candidate message
  ↓
ACTUAL direct repository acquisition
  ↓
connector branch HEAD
  OR direct REST branch+ref consensus
  ↓
immutable 40-hex SHA
  ↓
pinned manifest/VERSION
  ↓
manifest startup_slice
  ↓
NATIVE | HELP | INVALID | EXECUTING
                           ↓
                       CLOCK GENESIS
                           ↓
              pinned execution bundle
                           ↓
             verified entrypoint/core[]
                           ↓
            ExecutingProtocolLoadReceipt
```

## Validation

Run:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python tests/validate_repo.py
```

Deterministic release:

```bash
python tools/build_release.py \
  --output ../Deep-Iteration-GPT-Runtime-5.0.0-alpha.4.zip \
  --personalization-output ../DIGR-5.0.0-alpha.4-CHATGPT-LOCAL-PERSONALIZATION.txt \
  --full-personalization-output ../DIGR-5.0.0-alpha.4-CHATGPT-LOCAL-PERSONALIZATION-FULL.txt
```

The builder regenerates release metadata, rejects cross-platform path collisions/symlinks/traversal/cache artifacts, cold-extracts the ZIP, verifies all hashes and reruns the full suite + repository validator.
