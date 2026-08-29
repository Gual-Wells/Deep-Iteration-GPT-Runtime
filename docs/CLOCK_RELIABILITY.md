# Clock Reliability

Adaptive completion may select soft or hard T/t. A lone duration and `target=` are soft; only `min=` or B/b=1 is hard. B/b without explicit time requires native positive completion.

ClockJournal projects T=MAIN+SOURCE, t=SOURCE, D=D_EXCLUSIVE and V=V_EXCLUSIVE. META/IDLE count nowhere; waiting and sleep never pad time. A trusted session-only monotonic clock can attest one uninterrupted execution. Resume or cross-session claims require provider/boot continuity evidence.

Capability absence does not stop MODEL_NATIVE work. It changes affected actuals to unknown/unattested and prevents canonical time proof. D/V timing in the canonical host path is exclusive; concurrent background D remains deferred until it has an independent noncontaminating ledger.
