# Native production and file I/O

The model/controller performs semantic work. `runtime/codex_preprint.py` is a standard-library file helper with no model calls, scheduler, automatic truth checker or learner diagnosis. Use `tools/codex.py preprint --help` for exact CLI arguments.

## Source

`init --spec scene.json --out new-book` requires a new root, `id`, `title`, `public_scene`, and at least two actors. Each actor has unique `id`, `name`, `outward`, `inner`, optional `own_background` and `public_role`. `directors` have unique IDs and their own territories; `initial_state` is explicit fictional world truth. `sources` preserve material identities. Per-person background isn't automatically public; never feed the raw spec to an actor or phone.

`genesis_brief` can preserve actual target domains, scene domain, their concrete generalization relation and meaningful differences; unresolved personal relevance remains unresolved. `language_brief` preserves before-generation opportunities or an explicitly later retrospective. Both stay in source/creator material, not actor packets or phone files. They are native creative judgements, not automatically checked user value.

An actor's optional `materials` contains owned props/excerpts (`title`, `text`, `origin`). Set `initially_read:true` only for material genuinely already known at genesis, such as that person's own notes or the CV/JD already received before the call; its text is then present in that actor's first packet. Other available material requires an actual outward submission with `reads:[material-id]`. A shared file name or action saying "I share it" does not automatically deliver another actor's private material: the recipient must really receive a public utterance or a sourced visible excerpt. Establishing sensible initial knowledge avoids mechanical opening rounds without fabricating later reading or transfer.

Both `packet` and `director` accept `--out <new-private-file.json>` to save the exact bounded view as UTF-8. These input files belong outside the phone upload. `archive --root <book> --source-base <explicit-base> --out <new-creator-archive>` preserves selected event source/input files and the unchanged snapshot; `audit-sources --root <archive>` verifies it without the original base. Actual missing inputs remain gaps, not reconstructed delivery evidence.

`packet --actor ID --channel outward|inner` returns a visible `view` and its SHA. It includes only the relevant persona, own background, cast's public profiles, observed public/directed events and the person's own pair exchanges. Hidden events don't produce visible sequence-number gaps or a global revision. A packet SHA is an operator-side consistency binding, not authenticated proof of what an agent read.

Send precisely this bounded view to a real isolated context. Retain its actual output and origin. For continued contexts send actual new observations, or the latest view if necessary; never ask a context that already saw a future to pretend to forget it. If using a fresh context, label that execution change and supply the needed bounded history.

## Recorded operations

`record --root book --input event.json --expected-revision R --operation-id stable-ID` accepts an actual sourced event. Native `speech`/`action`/`inner`/`inner_reply` identify `actor`, `text`, `executor`, `source_ref`, and the delivered current `packet_sha256`. Inner channels are creator-only. Public speech/actions default to the public audience. Avoid folding unsupported world changes into an utterance.

World decisions have `kind:world`, `decision:apply|retain|decline`, `proposal`, `reason`, `changes`, `percepts:[{to:[public|creator|actor-ID],text}]`, and `source_ref`. Only adopted effects change world state; retain/decline cannot deliver perceptions. Public perception text is not the hidden proposal/cause. Store source proposal and controller handling separately enough to audit.

There is one controller writer. A stable operation ID retries the same payload without duplicating it; a different payload with the same ID is rejected. Revision conflicts require reloading actual state. Never relabel an old actor output with a new packet SHA after a real view change; deliver the new input to the actor and obtain its actual next submission. Unexpected `.writer.lock` requires process inspection before manual recovery.

`annotate` binds resources to actual public utterance spans with `event_id`, `surface`, `meaning`, `function`, `register`, `frequency_status`; optional source notes state their actual scope. It creates no learner evidence. Prefer a few useful expressions with context over turning every line into vocabulary entries.

For connected listening, resources can name `related_event_ids`; only public speech is projected. Explicit `public_sources:[{label,url}]` supplies selected web references, while private `source_notes` stays in the creator source. Optional `listening_threads:[{id,label,text,event_ids}]` connects actual public turns into a short look-back; non-public anchors are rejected. None of these fields is read aloud during the scene or becomes a learner assessment.

## Publication

`publish --root book --out new-edition` verifies the source snapshot and creates public phone files plus a physically separate creator file. `verify --root book --edition edition` reports whether source and edition still match. A book revision or a modified output needs deliberate new publication; do not call an old export current merely because the product VERSION is unchanged.

Use public outputs when preparing a phone text-performance probe; don't feed creator files and then claim secrecy. A generation trace, a text enactment, actual mobile Voice observation and learning benefit are distinct claims.
