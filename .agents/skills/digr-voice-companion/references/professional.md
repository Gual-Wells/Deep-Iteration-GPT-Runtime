# Practice material

These are agreed, fictional engineering histories for English practice, not the user's verified employment or measurements from this machine. Introduce that status once, then let the user say “I built,” “I measured” and “I decided” naturally. The user may borrow a later stage before studying it. Give enough explanation and content to participate; do not turn the facts into an entrance exam.

The worlds support interviews, colleague conversations, design arguments, explanations to a product teammate and creative work. Choose a live purpose. You need not ask all the questions below, recite every number or stay inside these two projects. When actual source material is supplied, use its real facts. A new imagined project or paper can be agreed openly.

## LeaseRun: a result must stay alive while someone reads it

### The world

The user built a small, self-owned C++ runner around an already integrated **synchronous CPU adapter**. Its calls finish their computation before returning, and independent contexts can run concurrently. This is not a claim about the interfaces or defects of a real framework.

The model has 48 MiB of shared, read-only constants. Each execution slot has its own context and 16 MiB of writable workspace. The output is a float32 feature map of shape 1 × 256 × 32 × 32: 1 MiB. The application later reduces that map to four float32 scores: 16 bytes.

At first, eight slots were reserved. An early experiment shared one writable arena between two contexts and produced mismatches during overlapping execution, so that branch was discarded. Separate wrapper objects had not created separate underlying memory.

The final result object holds a ticket for its slot. While a result lease is alive, that slot cannot be overwritten. A span or pointer alone is only a view and does not own the ticket. Execution errors return the slot too. When both slots are held, a third runner call returns `Busy`; the application can separately queue up to six requests. The user chose two slots for ordinary use and documented the burst trade-off.

An asynchronous device adapter would need a different release condition: the device's completion event as well as the consumer's lifetime. That port is a possible next responsibility, not a secretly completed part of this history.

### Fixed simulated comparison

Both versions use the same model, synchronous adapter, thread configuration and input shape. Ordinary traffic lasts 60 seconds at 12 requests per second; consumers release results within 20 ms. The burst is eight simultaneous arrivals with the application queue described above. Latency ends when the result is readable and includes waiting and execution, not its later holding time.

| Measurement | Eight slots | Two slots |
|---|---:|---:|
| Reserved workspace | 128 MiB | 32 MiB |
| Shared read-only constants | 48 MiB | 48 MiB |
| Ordinary result-ready p95 | 9.7 ms | 9.5 ms |
| Eight-request burst p95 | 24 ms | 96 ms |

This saves 96 MiB of **reserved workspace**, not 75% of the whole process or a reduction in the workspace one execution needs. The small ordinary-latency difference is not a speed claim. The burst gets worse.

### Sayable opening

> I first thought this was a memory-pool problem, but the important decision was who owned the output. A model call can finish while someone is still reading its result. I made the result hold a ticket for its slot, so the memory stays valid. That avoids a copy, but a slow reader can hold up the pool. For long-term storage, the caller can copy the data it needs and release the ticket.

A shorter borrowed thought is enough: “The computation had finished, but the result was still in use. I had to protect both lifetimes.”

### Make a conversation happen

- A teammate needs the four scores for a minute. Keeping their 16 bytes need not reserve a 16 MiB slot: discuss copying the aggregate and releasing the lease.
- Another library author prefers always returning an owned vector. Take that alternative seriously: simpler ownership may be worth allocation and copying. Zero-copy is not the predetermined winner.
- A product teammate asks why “less memory” made burst waiting worse. Explain that there are fewer places to run and hold results, rather than reciting a definition of RAII.
- An interviewer asks what changed the user's mind. The abandoned shared arena and the slow consumer are different useful stories.
- The team wants the asynchronous port. Agree a new hypothetical implementation task, explain completion plainly, and explore it together. Do not demand knowledge of a named GPU API before lending a usable reply.

## PocketDecode: the first word and the rest of the answer

### The world

The user built the generation loop, numerical comparison scripts and cache-selection experiments for a fictional single-request decoder. A teammate supplied the model and checkpoint. This project did not train a model, write an attention kernel, build a multi-user server or implement cross-request prefix caching.

The fictional model has 24 layers, 32 query heads, four KV heads and head dimension 64. K/V uses BF16, two bytes per element, batch size one. Weights occupy about 1.50 GiB. All measurements use the same 8 GiB GPU and software image. These are supplied simulation facts, not specifications of a released model.

The prompt is processed once in prefill, which also produces the first output token. The loop then feeds only the new token each step while reusing earlier K/V. A fixed 128-token output therefore has 127 decode steps after the first token. The last predicted token has not yet been fed back into the model.

The user initially advanced positions incorrectly using only the current input length. After fixing the loop, they compared logits under teacher forcing on 64 fixed sequences, including lengths 32, 128, 512 and 2048 and left-padding cases. The same next token was supplied to each version at every step. The maximum absolute logit difference was 0.0078125, below this experiment's preselected 0.01 BF16 tolerance; the greedy next-token choices agreed on these cases. The tolerance is local to this experiment, not a universal standard. “The answers looked similar” was not the check.

### Fixed simulated timing

Each row uses a loaded model, prepared token IDs, 512 prompt tokens and exactly 128 output tokens, no early EOS exit. Results are means of 30 warmed, sequential runs. Timing includes the loop, required device synchronization and getting each token ID visible to the host; it excludes tokenization, loading, network and multi-request queues.

| Version | First token | Time per later token | Whole output |
|---|---:|---:|---:|
| Recompute full prefix, no persistent KV | 160 ms | 184.0 ms | 23,528 ms |
| Dynamic KV, eager decode | 164 ms | 14.2 ms | 1,967 ms |
| Static capacity 2048 + compiled decode | 165 ms | 11.7 ms | 1,651 ms |

Whole output is first-token time plus **127** later-token intervals, rounded. The first token did not get faster. The later static result combines fixed-shape caching with compilation; do not attribute every gain to ordinary KV caching.

For this model, K/V bytes per cached token are:

`2 × 24 layers × 1 batch × 4 KV heads × 64 × 2 bytes = 24 KiB`.

A static capacity of 2048 reserves 48 MiB for K/V. Capacity 16384 reserves 384 MiB. In this particular implementation, the larger capacity raised warm time per later token to 17.8 ms because unused masked positions still incurred work. It is a local counterexample to “bigger is always better,” not a universal claim about every attention backend.

Compilation costs 4.8 seconds cold. Compared with the dynamic path, the warmed saving is roughly 0.316 seconds per common request, so about sixteen such requests are needed to recover that compile cost under these assumptions. A resident demo can prewarm; a tool that runs once and exits may prefer dynamic. Capacity checks consider prompt **plus planned output**, not just prompt length. A 2048-token prompt followed by 128 outputs does not fit a 2048 static capacity.

### Sayable opening

> Adding a KV cache made the later tokens much faster because we stopped repeating work on the whole prefix. It didn't really improve the first token: we still had to process the original prompt. I then tried a static cache with compiled decoding as a separate change. That helped our warm workload, but it introduced a cold cost. I kept the dynamic path for unusual input lengths and short-lived runs.

To explain without jargon: “We waited about as long for the first word, but there was much less waiting between the later words.”

### Make a conversation happen

- A colleague asks why a response feels faster when the first word is not faster. Explain a timeline with the first word, gaps and last word.
- A teammate changes the use case to one command-line call followed by exit. Reconsider compilation instead of defending the old choice at all costs.
- An interviewer wants one number that changed the user's mind. First-token time, the oversized cache and cold cost support different answers.
- A reader wants to understand one decode step. Use three familiar tokens and show what is new and what remains, rather than beginning with a terminology test.
- A team suggests reusing a common instruction prefix across requests. That is a new proposed experiment. Lend the responsibility and any new simulated records explicitly before using them as completed history.

## Bring in the learning material without building another syllabus

If the user names a chapter, source, paper or knowledge-pool entry that is actually accessible, pick one consequential object from it: a result's lifetime, the boundary of a timing measurement, a changed tensor shape, a model-quality loss, or a deployment choice. Put people around that object with different needs. A colleague may explain; an interviewer may be curious; the user can disagree or ask for a full model answer. Do not require a knowledge audit or completion of that chapter first.

Without the source, do not pretend to retrieve a local library, a full book or an unseen paper. Use these agreed worlds, create a fresh clearly imagined one, or work from a passage the user provides. Keep a real paper's unknown results unknown. The purpose is professional English that can generalize to new exchanges, not a fixed bank of answers or a new prerequisite study program.
