# Local Audit Logs

Berta1 has no MCP, UI, PWA, remote bridge or backend requirement. The runtime materializes local user-facing logs at delivery: `TOTAL.ndjson` plus independent `N`, `T`, `R`, `B`, `S`, `D`, `V`, and `L` logs.

N/R/S/n/r behavior receipts remain individually inspectable. T includes the four-clock projection; D/V include successful and unsuccessful recorded work and aggregate exclusive duration; B records timing policy and verification; L records target/actual isolation. TOTAL is a deterministic union. Logs disclose behavior and evidence without exposing private chain-of-thought.
