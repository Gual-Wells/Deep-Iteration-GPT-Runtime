# Deep Iteration GPT Runtime (DIGR) 5.0.0-Berta2

**Status:** Berta-series integration candidate; not a stable release.

DIGR is a pinned-protocol reliability exoskeleton around native model intelligence. Berta2 repairs the two central Berta1 regressions: host proof is no longer execution permission, and no-parameter invocations are task-adaptive again.

## Authority and distribution

The local configuration only captures exact-uppercase `DIGR`/`深度迭代` candidates and transports repository authority. It resolves current `stable` to a full SHA, verifies pinned `manifest.json` against pinned `VERSION`, then loads the manifest startup slice. Only pinned STARTUP classifies NATIVE/HELP/INVALID/EXECUTING. The untouched task and all later reads remain pinned to one SHA.

`manifest.json` is navigation authority. `runtime-descriptor.json` is loaded later and integrity-binds generated model protocol, Help and execution bundle. It cannot replace manifest navigation.

## Berta2 behavior

Public parameters are `N,T,R,B,S(n,t,r,b),D(s),V(o),L(e)`. Typed labels may move when remaining bare values keep one unique interpretation; flat `n/t/r/b/s/o/e` are accepted. Conflicts and ambiguity fail visibly.

No group is adaptive and source-required by default. Native intelligence fills missing task-scale N/T/R/S/D/V values once after the full pinned protocol is available. Only explicit `standard` selects fixed N2/T0/R1/S0/D0/V0/L1/source-auto. A lone duration remains Alpha4 soft T; `min=` is hard and `target=` soft. `B=1`/`S(b=1)` can request positive native T/t completion.

V is a persistent distant-view channel with private ledger, semantic distance, nonredundancy and Main sovereignty. D keeps one public surface while D+/D−/Dx remain opaque native directions. D(0)/V(0) are zero minima, not off switches. Candidate is created only after meaningful output exists.

Clock projections are `T=MAIN+SOURCE`, `t=SOURCE`, `D=D_EXCLUSIVE`, `V=V_EXCLUSIVE`. Recommended reporting is `T目标/T真实（+D真实时间，+V真实时间）`; unknown facts are `?`.

## Execution versus attestation

Berta2 separates:

- `ExecutionMode=MODEL_NATIVE|HOST_ENFORCED`;
- `AttestationLevel=NONE|PARTIAL|CANONICAL`.

Missing native host integration never prevents full DIGR execution. It only prevents claims that require unavailable clocks, persistence, tools or final-output interposition. A session-only monotonic clock can support one uninterrupted task; semantic V is not blocked by a host viewpoint count.

The Python HostAdapter is a reference enforcement/attestation implementation, not an automatically installed ChatGPT tool, MCP server or plugin. Canonical host delivery binds exact current Candidate primary bytes, summary, proof, audit logs and a terminal semantic-state digest, then seals DELIVERED/INCOMPLETE/ABORTED workspaces against further API mutation.

## Logs and UI scope

Berta2 contains no MCP, dynamic UI, PWA, remote bridge or backend service. Each execution returns or persists TOTAL plus independent N/T/R/B/S/D/V/L behavior logs. Successful and unsuccessful D/V work is retained; observed D/V owned time is aggregated. Logs expose decisions and evidence summaries, not hidden chain-of-thought.

## Local configuration

`local-personalization/PERSONALIZATION_TEMPLATE.txt` is the only editable local-shell source. Generated compact, FREE_GO and root standalone files are byte-identical and end in `<!-- DIGR_LOCAL_PERSONALIZATION_END -->`.

```bash
python tools/build_release.py --prepare-only
```

## Validation and packaging

```bash
python -m unittest discover -s tests -p 'test_*.py'
python tests/validate_repo.py
python tools/build_release.py \
  --output ../Deep-Iteration-GPT-Runtime-5.0.0-Berta2.zip \
  --personalization-output ../DIGR-5.0.0-Berta2-CHATGPT-LOCAL-PERSONALIZATION.txt \
  --full-personalization-output ../DIGR-5.0.0-Berta2-CHATGPT-LOCAL-PERSONALIZATION-FULL.txt
```

The builder regenerates derived artifacts, rejects cache/symlink/path hazards, fixes ZIP timestamps, cold-extracts, revalidates and checks hashes. Promotion to mutable `stable` additionally requires fresh iOS/Web/Desktop black-box evidence; this candidate package does not claim that external gate has run.
