# Security, Authority and Intelligence Boundaries

Repository pinning prevents context from redefining protocol semantics. Workspace path validation, atomic writes, release path/symlink checks, hash-chained journals and artifact digests address accidental/host-level state corruption; they are not a cryptographic trust system against a malicious host.

The model's hidden reasoning is never persisted as required protocol state. Strategy/Candidate/EST store concise external working state only. Deterministic helpers validate lifecycle, types, references and timing facts, not “good ideas”.
