# Deep Iteration GPT Runtime (DIGR) 5.0.0-Berta1

**Status:** Berta-series integration candidate; not a stable release.

DIGR is a reliability exoskeleton around native model intelligence. An explicitly invoked high-investment task receives immutable protocol identity, early trusted timing, frozen U0/contract commitments, revisable strategy/source/candidate state, disruptive interventions, evidence, persistence and recovery.

## Berta1 contract

The local shell broadly captures exact-uppercase `DIGR`/`深度迭代` prefixes and performs live transport before classification. An existing connector reads the current `stable` branch HEAD; direct REST reads branch and Git-ref in the same attempt and requires matching full SHAs. At that SHA, `manifest.json` is the navigation authority: its version must equal pinned `VERSION`, and its sole startup slice is the self-contained `entry/STARTUP.md`.

The protocol version is `5.0.0-Berta1`; Python packaging uses the PEP 440 mapping `5.0.0.dev1+berta1`, recorded as descriptor `package_version`. `runtime-descriptor.json` is loaded only through manifest navigation as an execution/release artifact description, never as the first read or a replacement for manifest navigation.

The runtime descriptor integrity-binds three deterministic distribution artifacts:

- `dist/MODEL_PROTOCOL.md`: compact model protocol generated from one author source;
- `dist/HELP.zh-CN.md`: generated canonical Chinese help;
- `dist/EXECUTION_PROTOCOL.json`: generated member-order, byte-length and SHA-256 bundle.

The logical source files remain reviewable under `bootstrap/`, `entry/` and `core/`. Generation changes transport shape, not semantics.

## Berta1 additions: V, four clocks and local logs

The public parameter order is `N,T,R,B,S(n,t,r,b),D(s),V(o),L(e)`. Clearly typed labels may be reordered; remaining unlabeled values must still have one unique mapping. Flat `n/t/r/b/s/o/e` labels are supported. D(0) and V(0) are zero minima, not off switches.

V is a persistent isolated viewpoint channel with a private VLedger, semantic-distance and nonredundancy evidence, positive owned time, and no V-to-V communication. Main remains sovereign. D internally uses opaque D+/D−/Dx mechanisms while its public syntax remains D.

The four clock projections are `T=MAIN+SOURCE`, `t=SOURCE`, `D_time=D_EXCLUSIVE`, and `V_time=V_EXCLUSIVE`; META/IDLE count nowhere. Canonical presentation groups them as `T目标/T真实（+D真实时间，+V真实时间）`.

The standard profile is N2/R1/no-time/source-auto/D0/V0/L1. Explicit `min=<duration>` is a hard lower bound and `target=<duration>` is soft.

Berta1 closes new runs as `DELIVERED` or `INCOMPLETE`. Delivery writes local `TOTAL` plus independent N/T/R/B/S/D/V/L NDJSON audit logs. MCP, dynamic UI, PWA, remote bridge and backend code are deliberately absent. An incomplete run cannot claim a canonical proof.

## Host integration and client boundary

`digr.preflight` and `digr.commit_delivery` are logical protocol API names. In this package they map to `runtime.host_adapter.HostAdapter.preflight` / `.start` and `runtime.run_session.LiveDIGRRun.commit_delivery`. The package does not install a ChatGPT tool, MCP server, plugin, or native iOS/Web/Desktop host binding.

Local personalization can enforce candidate routing and repository handoff only to the extent supported by the client. Without a host integration that actually exposes the Python-equivalent preflight, persistent workspace, trusted continuous clock and final-output interposer, execution is `DIGR~` ADVISORY and cannot claim mechanical actuals or canonical proof. Therefore identical personalization text alone cannot guarantee identical enforced behavior across ChatGPT clients.

## Local personalization

`local-personalization/PERSONALIZATION_TEMPLATE.txt` is the single editable source for compact, FREE_GO, expanded and root standalone configurations. Generated configurations end with `<!-- DIGR_LOCAL_PERSONALIZATION_END -->` so truncated copies fail visibly.

Prepare generated artifacts without creating a ZIP:

```bash
python tools/build_release.py --prepare-only
```

## Validation and release

```bash
python -m unittest discover -s tests -p 'test_*.py'
python tests/validate_repo.py
```

The optional schema test dependency is declared as `test`; repository structural validation remains standard-library-only.

To build a deterministic release after validation:

```bash
python tools/build_release.py \
  --output ../Deep-Iteration-GPT-Runtime-5.0.0-Berta1.zip \
  --personalization-output ../DIGR-5.0.0-Berta1-CHATGPT-LOCAL-PERSONALIZATION.txt \
  --full-personalization-output ../DIGR-5.0.0-Berta1-CHATGPT-LOCAL-PERSONALIZATION-FULL.txt
```

The builder regenerates descriptor-declared artifacts, rejects symlinks/path traversal/cross-platform collisions, excludes Python and test caches, fixes ZIP timestamps, verifies hashes after cold extraction and reruns validation. DEFLATE byte reproducibility is guaranteed only within the same Python/zlib build environment.
