# Multiple source workspaces and aggregate t

Suppose S1 and S2 are active together during one SOURCE interval, then S2 continues alone, and S3 is active later. The clock journal records SOURCE state boundaries and each SOURCE state-start is bound to the non-empty set of active source IDs.

Aggregate `t` is the union of those SOURCE intervals. It is **not** the sum of each source's duration, so parallel S1/S2 work cannot double-count time.

An opened SourceWorkspace by itself is not an actual S for completion. To count, the source must participate in real SOURCE-time binding and have a semantic SOURCE evolution/re-entry receipt. Per-source `n`/`r` are then derived from those bound receipts; source `r` references SourceWorkspace before/after revisions rather than a Main Candidate.
