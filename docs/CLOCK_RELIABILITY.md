# Clock Reliability — Alpha 2

Clock journal format remains the stable Alpha 1 core: ≥3 readiness samples, provider/session/boot identities, monotonic and wall readings, sequence/hash chain, state and formal-ledger parity.

Alpha 2 changes *where and how continuity is used*:
- repository startup is staged so EXECUTING reaches Clock Genesis before full core loading and before parameter resolution;
- cross-process/session observed time now requires equal non-empty boot identity, not provider equality alone;
- resume verifies the persisted workspace, probes ≥3 fresh samples, proves the persisted-last→new-anchor bridge, appends `RESUME_*`, and drops any unclosed semantic tail rather than charging an unknown process gap; the resumed live session therefore has no inferred foreground work state until the caller explicitly re-enters MAIN/SOURCE/D_EXCLUSIVE/META/IDLE with a fresh STATE receipt;
- hard time still fails closed; `?` is preferred to an invented duration.

T/t remain formal active time, not wall occupancy. MAIN+SOURCE count T, SOURCE counts t, D_EXCLUSIVE/META/IDLE do not.
