# Deep Iteration GPT Runtime (DIGR) 4.1.0

DIGR 4.1 is a task-commitment/runtime-control protocol for preventing premature under-allocation of effort while preserving the model's native freedom to reason, research, use tools, test, redesign and synthesize.

**4.1's architectural correction:** local personalization is no longer a pre-protocol. It is a minimal **Reliable Routing Plane**. All versioned DIGR semantics live in the pinned repository protocol.

## First design axiom

> **本地负责叫醒、找到、钉住、交权；仓库负责定义、启动、执行、停止和证明。**

Formally:

`Local Config = Candidate Response + Repository Routing + Immutable Pin + Authority Delegation`

`Pinned Repository Protocol = All Versioned DIGR Semantics`

`Runtime Helpers = Evidence / Verification, not Semantic Authority`

## Control plane

```text
user message begins with DIGR / 深度迭代
        ↓ candidate route only
local personalization router
        ↓
stable → immutable 40-char commit SHA
        ↓
pinned manifest.json
        ↓
manifest discovery: bootstrap_entry (4.1+) or legacy entrypoint+core
        ↓
explicit authority delegation to pinned repository protocol
──────────── semantic authority boundary ────────────
repository version classifies task/help/off
        ↓ executing 4.1 task only
mandatory trusted task-clock readiness
        ↓
U0 → Semantic Completion → Effective Contract
        ↓
MAIN / SOURCE / R / D-L / validation
        ↓
Stop Gates → Result → Canonical Proof
```

### Why this matters
4.0.0 accidentally let the local loader define root-gate, clock, no-fallback and P_target behavior while also claiming that the local loader was “not protocol”. That created two semantic authorities and allowed the anti-contamination mechanism itself to contaminate an older repository version. 4.1 removes the pre-protocol gate completely.

The local router may know only discovery facts: candidate route keys, repository/ref, immutable pin requirement, manifest location and manifest-declared protocol paths. It cannot define invocation validity, help behavior, defaults, clock rules, N/R/S/D/L, stop gates or proof.

## Routing and legacy cleanliness
The router reads `Gual-Wells/Deep-Iteration-GPT-Runtime:stable` on every candidate invocation and pins it to an immutable commit. It then reads **that commit's** `manifest.json`.

- 4.1+ manifest: follow `bootstrap_entry`, then repository entry/core.
- legacy manifest without `bootstrap_entry`: follow its declared `entrypoint` + `core`.

This compatibility rule only decides **where to read**. It does not import 4.1 semantics into a legacy P_run. Therefore a pinned 3.0 repository can be routed and then run strictly by 3.0's own semantics instead of being rejected by a future 4.1 startup rule.

A route failure happens before P_run exists and is not a DIGR execution. The router reports that no repository protocol was obtained; it does not reconstruct DIGR from conversation memory or a local protocol copy.

## Repository-delegated semantic authority
Once a pinned repository protocol is loaded, it is the DIGR semantic source for that user turn, subject to higher-priority instructions and current user hard constraints. Protocol decisions must be provenance-clean:

`Context !-> ProtocolSemantics`

but ordinary task continuation remains allowed:

`Context -> U0 / Evidence`

The goal is protocol authority isolation, not conversation amnesia.

If a task modifies DIGR, the generated/edited protocol is `P_target`; it cannot rebind current `P_run`. A later user turn must route and pin again before a new repository version can become P_run.

## 4.1 task startup
After 4.1 itself classifies a candidate as an executing task, it requires trusted monotonic task-clock readiness **before U0 freeze or substantive work**. Help/invalid candidates do not start a task clock. This rule belongs to repository P_run=4.1; it is deliberately absent from local personalization.

The timer substrate separates:
- observed monotonic duration;
- hard continuity verification.

Soft T/t may use honest observed duration. Hard T/t must carry continuity-verification facts for the formal intervals they claim.

## Invocation
Canonical form:

`DIGR（N，T，R，B，S（n，t，r，b），D（s），L（e））：<任务>`

Alias: `深度迭代`.

4.1 has no special AUTO mode. Any subset may be supplied. Fixed defaults are only `B=0`, `b=0`, `L(1)`; missing N/T/R/n/t/r/s are jointly completed by native semantic calibration.

## Execution semantics retained from 4.0
- Result Sovereignty and Task Commitment;
- Effective Contract freeze;
- EST as lightweight evolution-state memory, not a search algorithm;
- N and whole-process R/r re-entry + ABG;
- multi-instance S with per-S n/r and aggregate source t;
- D(s) Disruptive Gambit, with D(0)=off;
- exact L1/L2/L3 isolation semantics;
- MAIN/SOURCE/D_EXCLUSIVE/META/IDLE Formal Active Time;
- hard-verification-aware stop checks and canonical proof;
- strict deterministic helpers, schemas, property tests and deterministic release validation.

## Time states
| State | T | t |
|---|---:|---:|
| MAIN | yes | no |
| SOURCE | yes | yes |
| D_EXCLUSIVE | no | no |
| META | no | no |
| IDLE | no | no |

Routing happens before task runtime and is not Formal Active Time.

## D and L
D performs non-local, plausibly high-upside interventions. A valid D requires Decree + Execution + Result + Reintegration. Disturbance/ambition/coup propensity remain semantic and non-numeric.

L is exact, not a minimum:
- L1: semantic isolation in the same context;
- L2: separate LLM history/context + controlled telemetry + state firewall;
- L3: L2 plus independent agent identity/instructions/execution loop/tool execution.

API names such as handoff, nested run, sandbox or worktree do not self-certify L2/L3.

## Canonical proof
`DIGR（N/实际N，T/实际T，R/实际R，B，Sᵢ（n/实际n，t/实际t，r/实际r，b），D（s）/D（实际s），L（e）/L（实际e））`

Unknown/unverified hard actual is `?`. Version/provenance/logs/EST/D-State are not included by default.

## Local personalization
Use `local-personalization/CHATGPT_LOCAL_PERSONALIZATION.txt`. The Free/Go compatibility file is byte-identical to the primary router, preventing semantic drift. The FULL file is explanatory reference only.

The release builder can export the standalone direct-copy text from the **same internal source bytes**, so ZIP and standalone configuration cannot silently diverge.

## Repository layout
- `bootstrap/BOOTSTRAP.md`: repository-version startup semantics after routing;
- `entry/`: invocation/help execution entry;
- `core/`: normative DIGR semantics;
- `runtime/routing.py`: version-semantic-free route/provenance validation;
- `runtime/protocol_authority.py`: P_run binding to route receipt;
- `runtime/task_startup.py`: 4.1 executing-task clock readiness;
- `runtime/*`: time/contract/source/isolation/stop/proof helpers;
- `schemas/`: closed machine-readable records;
- `tests/`: control-plane, runtime, property, hygiene and release tests;
- `tools/build_release.py`: deterministic ZIP + cold validation + personalization export.

## Validation
Run:

```bash
python -m unittest discover -v
python tests/validate_repo.py
python tools/build_release.py --output ../Deep-Iteration-GPT-Runtime-4.1.0.zip --personalization-output ../DIGR-4.1.0-CHATGPT-LOCAL-PERSONALIZATION.txt
```

The build is local and does not require Git automation.
