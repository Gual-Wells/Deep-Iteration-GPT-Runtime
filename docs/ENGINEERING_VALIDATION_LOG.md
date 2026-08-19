# Engineering Validation Log — DIGR 5.0.0 Alpha 3

Release role: transport-hardened integration baseline over the Alpha 2 corrected execution model.

This file records the acceptance procedure, not historical chat status messages. The post-deployment Alpha 2 failures are treated as black-box evidence: both candidate turns returned the fixed route-failure message without observable repository acquisition. Source inspection then established the missing host transport bridge and Contents/raw-byte mismatch.

## Final-tree acceptance gates

The final source tree must pass, in this order:

1. full `unittest` discovery over `tests/test_*.py`;
2. `tests/validate_repo.py` repository-contract validation;
3. explicit repository-transport regressions: actual attempt receipts, direct mutable provenance, ref/branch consensus, raw-SHA pinning and Contents wrapper decoding;
4. Python 3.10 grammar parsing, JSON/schema metadata checks, UTF-8/LF sweep and stale-current-semantics checks;
5. regeneration and verification of `FILE_TREE.txt` and `SHA256SUMS.txt`;
6. deterministic ZIP creation with fixed metadata and sorted members;
7. ZIP CRC/path/symlink/cache safety checks;
8. cold extraction followed by hash verification, full unit suite and repository validation from that extracted copy;
9. a second independent release build from the unchanged source tree; both ZIPs and both standalone personalization exports must be byte-identical;
10. an additional final cold extraction/revalidation of the delivered ZIP;
11. byte equality between standalone compact/FULL personalization and package copies.

Alpha 3 acceptance does not claim that an external ChatGPT product exposes a hard pre-message hook. It proves that the shipped transport contract and host adapter no longer permit the package-level ambiguities found in Alpha 2, and that the personalization explicitly makes a current-turn acquisition action a prerequisite for route failure.

Exact test counts and final SHA-256 digests are reported by the final release run rather than embedded here.
