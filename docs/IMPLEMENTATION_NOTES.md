# Alpha 3 Implementation Notes

Alpha 3 is a transport hardening release over the Alpha 2 execution model. The real deployment failures `DIGR/help` and `DIGR：返回版本号` showed that Alpha 2 could have all repository/unit tests green while a host skipped repository acquisition and immediately emitted the fixed route-failure message. Source inspection also found an interface mismatch: the local locator named the GitHub Contents API while `runtime/routing.py` consumed raw file bytes.

`runtime/routing.py` remains a version-semantic-free verifier/discovery layer. `runtime/repository_transport.py` now closes the host boundary: it records actual acquisition attempts, rejects search/index/crawl provenance for mutable `stable`, corroborates the Git ref endpoint with the Branches endpoint, pins all later reads, prefers immutable raw SHA URLs, and normalizes GitHub Contents raw/base64 responses. `runtime/invocation_surface.py` still classifies only after pinned startup bytes exist; `runtime/parameter_resolution.py` still acts only after repository-defined clock genesis. None of these chooses task strategy.

The transport module has a concrete standard-library HTTPS fetcher plus a host-supplied fetch-callback interface. ChatGPT/connector hosts may implement the callback, but they must preserve directness/freshness provenance rather than relabel search snippets as live GitHub responses. The fixed route failure has an explicit necessary condition: at least one canonical repository acquisition attempt must have occurred in the current turn.

Below the transport boundary, Alpha 2 semantics remain intentionally stable. `LiveDIGRRun` is the lifecycle/evidence binding layer; raw `.events.append()` is replaced by thin semantic wrappers. Wrappers validate references, not intellectual quality; they also validate phase and foreground clock state.

Strategy/Candidate/EST/Source/D/Completion stores remain revisioned. Source time still has no standalone aggregate helper: formal SOURCE intervals plus source-activity bindings are the one time chain. Main R remains Candidate-backed; source r remains SourceWorkspace-revision-backed.

D/L remains one temporal information-flow lifecycle. L2/L3 controlled Input/Output Packets are indexed around isolated work. Isolation facts describe capability; isolation receipts select target-bounded actual mode.

Recovery still verifies artifact bytes/latest pointers, semantic references, derived Run Brief and rederived FINISHED summary. Resume separately establishes a same-boot clock bridge; integrity alone is not time continuity.
