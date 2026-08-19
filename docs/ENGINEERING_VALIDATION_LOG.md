# Engineering Validation Log — DIGR 5.0.0 Alpha 2

Release role: corrected integration baseline intended to freeze the interfaces used by the later 5.0 final release.

This file records the acceptance procedure, not historical chat status messages. A release is accepted only from commands run against the final frozen tree. Previous “completed” messages are not evidence.

## Final-tree acceptance gates

The final source tree must pass, in this order:

1. full `unittest` discovery over `tests/test_*.py`;
2. `tests/validate_repo.py` repository-contract validation;
3. Python 3.10 grammar parsing, JSON/schema metadata checks, UTF-8/LF sweep and stale-current-semantics checks performed by the validator;
4. regeneration and verification of `FILE_TREE.txt` and `SHA256SUMS.txt`;
5. deterministic ZIP creation with fixed metadata and sorted members;
6. ZIP CRC/path/symlink/cache safety checks;
7. cold extraction into a new directory, followed by hash verification, the full unit suite and repository validation from that extracted copy;
8. a second independent release build from the unchanged source tree; both ZIPs and both standalone personalization exports must be byte-identical;
9. an additional final cold extraction/revalidation of the delivered ZIP;
10. byte equality between the standalone compact/FULL personalization files and their corresponding files inside the delivered ZIP.

## Correctness areas required by this baseline

Acceptance specifically covers the issues that motivated Alpha 2: staged startup and clock genesis, Native Sovereignty Return, unique typed parameter resolution, mutable Strategy/Candidate/Source state, Source Presumption, Candidate-backed MAIN R, SourceWorkspace-backed source r, D/L isolation packet and clock-state binding, comprehensive recovery, derived Run Brief verification, final-summary rederivation, and deterministic release.

The exact test count and delivered SHA-256 digests are intentionally reported by the release command/final delivery record rather than embedded here. Embedding the final ZIP hash inside the ZIP would create a self-referential artifact and make deterministic verification meaningless.
