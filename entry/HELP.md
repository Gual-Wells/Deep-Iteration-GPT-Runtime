# DIGR 5.0.0-alpha.2 Help

DIGR is an explicit high-investment execution mode. It is turn-scoped (non-sticky): a later message is ordinary ChatGPT unless that later message invokes DIGR again.

## 1. Calling DIGR

```text
DIGR：<task>
DIGR(<parameters>)：<task>
深度迭代：<task>
深度迭代(<parameters>)：<task>
```

`DIGR` is exact uppercase ASCII. `digr`, `Digr`, etc. do not route. Chinese/ASCII parentheses, comma and colon are interchangeable in the invocation header and may be mixed. `DIGR/help` and `深度迭代/help` open this help without starting a task run.

The local router intentionally captures some DIGR-prefixed discussion too. The pinned repository then returns that message to ordinary ChatGPT as NATIVE, e.g. `DIGR是什么？` or `DIGR(R=3)这种格式怎么样？`.

## 2. Parameters

| Parameter | Meaning | Default when omitted |
|---|---|---|
| N | minimum meaningful MAIN evolutions | semantic completion |
| T | Formal Active Task Time target | semantic completion |
| R | minimum whole-process candidate re-entries | semantic completion |
| B | T policy: 0 soft / 1 hard | 0 |
| S(n,t,r,b) | source-research evolution / aggregate source time / source re-entry / t policy | n/t/r semantic completion, b=0 |
| D(s) | minimum completed disruptive-gambit interventions | s semantic completion |
| L(e) | D isolation implementation target | L1 |

N/T/R/n/t/r/s are minimums, not caps. Meeting them does not force an early stop if result quality can still materially improve.

## 3. Format, omission and ambiguity

Canonical relative order is `N,T,R,B,S,D,L`; inside S it is `n,t,r,b`. Omitted fields do not reorder what remains. T/t must contain recognizable duration semantics; a bare number can **never** be invented into minutes/seconds.

`S`, `S()`, `D`, `D()`, `L`, `L()` are valid markers. Empty S leaves n/t/r to semantic completion and fixes b=0; empty D leaves s to semantic completion; empty L means L1.

Examples:

```text
DIGR(1,1)：task                 # valid -> N=1, R=1; T omitted
DIGR(1)：task                   # ambiguous -> no unique N vs R mapping
DIGR(1,1,1)：task               # invalid -> middle item would have to be T but has no time unit
DIGR(1,10min,1)：task           # valid -> N=1, T=10min, R=1
DIGR(1,10min,1,S())：task       # valid; S numeric minima omitted
DIGR(1,1,S,D,L)：task           # valid strong markers
DIGR（1,10min,1)：task          # valid mixed punctuation
DIGR是什么？                    # not an invocation; returned to native ChatGPT
```

If the outer shell is clearly EXECUTING, DIGR establishes trusted Clock Genesis **before** resolving the inside parameters. An ambiguous/invalid parameter set then aborts that born run without starting task analysis.

## 4. What execution does

A successful run follows this conceptual chain:

```text
pinned repository authority
→ minimal startup classification
→ trusted clock genesis
→ parameter resolution + U0
→ frozen minimum contract
→ MAIN / revisable Strategy Genesis
↔ N evolution
↔ source S research (normally presumed required)
↔ candidate-backed R re-entry
↔ optional D non-local intervention under L isolation
→ completion/open-gap assessment
→ timing + workspace verification
→ result + compact proof
```

Only P_run, U0, user hard constraints and contract minimums are frozen. Strategy is explicitly mutable: new evidence, failed tests, R, S or D can redirect the task model, decomposition, research/tool/validation plan and assumptions. The runtime records this state but never scores routes or chooses the model's next thought.

S means external information broadly: web, official docs, code/repository, files, data, papers, community material, tools and test results. Normal DIGR runs presume a real source strategy unless U0 or host reality justifies an explicit source waiver. `S(0,0s,0,0)` lowers numeric minimums; it does not itself disable research.

R is a whole-process re-entry into an existing candidate, not a final proofreading pass. It may challenge the candidate, representation, strategy, decomposition, evidence, source plan, tool route or validation method; after a substantive independent challenge, retaining the original candidate is allowed.

D is a disruptive non-local intervention. Its proposal can evolve until Decree; completion requires execution/result evidence and reintegration into Main. L1/L2/L3 describe the isolation actually used for D, separately from what the host is capable of.

## 5. Time and stopping

T counts useful MAIN+SOURCE active time; t counts SOURCE only. META/IDLE and exclusive D do not count. Background isolated D does not count T/t while Main may continue independently.

B=1 or b=1 makes the corresponding time a hard lower bound. Hard elapsed time is claimed only with verifiable monotonic continuity; after a process boundary, equal non-empty boot identity is required. If continuity cannot be proved, DIGR uses `?` rather than guessing.

Padding is forbidden: waiting, sleeping, repeated searches, logging and mechanical rewrites do not become useful task time. Reaching all minimums only opens the stop gate; Result Sovereignty still asks whether more useful work would materially improve the result.

L mismatch is reported honestly. It blocks delivery only when the user's U0 explicitly makes the requested isolation mode mandatory. With D(0), L is non-blocking because no D intervention exists to isolate.

## 6. Return format

The task result comes first. The final line is a compact run proof using the existing DIGR proof shape, conceptually:

```text
DIGR(N/actualN, T/actualT, R/actualR, B,
     S_i(n/actualn, t/actualt, r/actualr, b),
     D(s)/D(actuals), L(e)/L(actuale))
```

`?` means an actual value cannot be reliably verified. The normal response does not dump Strategy/EST, hidden reasoning, query logs, clock journal, schemas or repository audit files.
