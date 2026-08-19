# Deep Iteration GPT Runtime (DIGR) 5.0.0-alpha.3

**Status:** transport-hardened integration baseline intended to freeze for DIGR 5.0 final.

DIGR 5.0 is a reliability exoskeleton around native model intelligence. It does not replace the model with a planner/search controller. It gives an explicitly invoked high-investment task pinned protocol authority, early trusted timing, immutable U0/minimum commitments, revisable working strategy, external-source state, candidate-backed re-entry, isolated D interventions, evidence, persistence and recovery.

## Why Alpha 3 exists

Alpha 2 corrected the 5.0 execution/state architecture and passed its full deterministic release suite. Real deployment then exposed a different boundary defect: both `DIGR/help` and `DIGR：返回版本号` returned the fixed route-failure message **without any observable repository acquisition action**. Source audit also found that the local locator named GitHub's Contents API while the deterministic routing loader expected raw file bytes.

Alpha 3 keeps Alpha 2 execution semantics and hardens only the host repository-transport edge. The key rule is:

> **No acquisition attempt is not an acquisition failure.**

A candidate route must cause a real repository read before the fixed failure response is admissible.

## Alpha 3 transport corrections

- new `runtime/repository_transport.py` host bridge with actual acquisition receipts;
- mutable `stable` rejects search/index/crawl provenance;
- direct REST mode corroborates Git-ref and Branches endpoints and requires one identical full 40-hex SHA;
- standard-library direct fetcher asks mutable requests to revalidate (`Cache-Control: no-cache` / `Pragma: no-cache`);
- every later resource is pinned to that SHA;
- primary pinned transport is immutable `raw.githubusercontent.com/{SHA}/{PATH}`;
- GitHub Contents API remains a fallback using `application/vnd.github.raw+json`;
- ordinary Contents JSON/base64 responses are normalized into real file bytes instead of being mistaken for `manifest.json`/`VERSION`;
- compact local personalization explicitly requires an actual repository action before any user-visible route result;
- repository transport schema 1 + routing schema 3 record the reopened deployment boundary;
- fresh-chat smoke guidance now distinguishes router non-execution from a genuine repository failure.

## What stays from Alpha 2

`Freeze commitments, never freeze strategy` remains the execution/state baseline. `P_run`, U0, hard user constraints and Effective Contract minima are immutable; Strategy, Candidate, EST, Source direction, validation/tool plan, assumptions, Candidate and pre-Decree D proposals are revisioned working state.

Source Presumption, clock-bound source time, Candidate-backed R, D/L isolation receipts/packets, RunPhase, artifact index, derived Run Brief, comprehensive recovery, strict cross-session clock continuity and Event Receipt v2 are unchanged except for version labels and transport integration.

## Authority and startup

```text
candidate message
  ↓
ACTUAL direct repository acquisition
  ↓
stable ref API + branch API → same 40-char SHA
  ↓
immutable pinned manifest/VERSION bytes
  ↓
manifest startup_slice
  ↓
NATIVE | HELP | INVALID | EXECUTING
                           ↓
                       CLOCK GENESIS
                           ↓
                 pinned entrypoint/core[]
```

Search results and crawled/indexed GitHub pages are useful for human research but are not mutable-ref authority. Once a SHA is pinned, cached content at that exact SHA is semantically safe because the Git object is immutable.

A connected GitHub connector may implement the direct-current branch-head acquisition instead of REST. The package cannot turn a ChatGPT personalization field into a platform-level hard hook; Alpha 3 therefore makes the host obligation explicit and provides a deterministic transport adapter for hosts that can execute it.

## Validation

Run:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python tests/validate_repo.py
```

Deterministic release:

```bash
python tools/build_release.py \
  --output ../Deep-Iteration-GPT-Runtime-5.0.0-alpha.3.zip \
  --personalization-output ../DIGR-5.0.0-alpha.3-CHATGPT-LOCAL-PERSONALIZATION.txt \
  --full-personalization-output ../DIGR-5.0.0-alpha.3-CHATGPT-LOCAL-PERSONALIZATION-FULL.txt
```

The builder regenerates release metadata, runs tests/validator in cold extracted trees and rejects unsafe/symlink ZIP members. Final release validation should build twice and compare byte identity.
