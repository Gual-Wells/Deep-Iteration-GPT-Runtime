# Stop, Delivery and Proof

Mechanical minima open stop eligibility; they never compel low-quality output. Completion assesses objective coverage, evidence integrity, adversarial resilience, residual risk and remaining high-value work.

Every path returns an honest execution report using:

```text
DIGR（N目标/N实际，T目标/T真实（+D真实时间，+V真实时间），R目标/R实际，B，Sₛ（n目标/n实际，t目标/t实际，r目标/r实际，b），D（s目标）/D（s实际），V（o目标）/V（o实际），L（e目标）/L（e实际））
```

Unknown/unattested actuals are `?`, and the report names NONE/PARTIAL/CANONICAL attestation. A noncanonical report is not a failed execution.

Canonical delivery additionally requires `digr.commit_delivery`: exact final bytes must equal the current Candidate primary payload; logs and semantic terminal digest bind summary/proof/envelope; verification precedes DELIVERED and the terminal seal. Any gate failure closes INCOMPLETE. Only verified DELIVERED may call its report canonical proof.
