# Alpha 10 Implementation Notes

Alpha 10 contracts reliability cost rather than weakening semantic guarantees.

- execution authority reduced from 18 core modules to 7;
- one package verifier + recursive Git tree replaces per-helper verification;
- omitted D defaults to 0; explicit D() can still request semantic completion;
- SourceDisposition is chosen by task necessity, not blanket presumption;
- ordinary resume skips full workspace audit;
- journal reindex is batched;
- STATE/WorkLease no longer trigger global checkpoint;
- latest Strategy/Candidate/Source/D/EST/phase/run-brief files are unindexed rebuildable caches;
- ordinary completed D can persist as one compact lifecycle revision.

Full recovery, granular D revisioning and full workspace audit remain available when they have real value.
