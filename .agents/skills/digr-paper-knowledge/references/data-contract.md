# Data and command contract

Implementation: `runtime/codex_knowledge.py`, `tools/codex_knowledge.py`. Standard library plus `pypdf` only when importing PDF sources. No model calls or background service.

`pool.json` schema 2 is one private authority. An atomic replace commits a complete revision. A short exclusive lock prevents competing writers; expected revisions prevent lost updates; operation receipts support same-content retries. The snapshot integrity digest detects inconsistent edits, not malicious authorship or semantic correctness. A machine crash can leave the lock; inspect the recorded PID and token before recovery. Power-loss durability has not been established.

Responsibilities within that snapshot:

| Field | Responsibility |
|---|---|
| `binding` | Runtime repository/ref and earlier protocol pin; private data repository |
| `concepts`, `concept_history` | Current shared definitions and explicit corrections |
| `papers.sources` | Immutable PDF/text versions and extraction representation identities; local/relative file locators |
| `occurrences` | Content-addressed paper usage, role, assumptions, quote/page, frozen concept definition |
| `use_corrections` | Explicit source-checked replacement links; historical questions and evidence stay frozen |
| `sessions.questionnaire` | Frozen offered wording, occurrence contexts and response identity |
| `pool_members` | The uses already admitted to the shared pool and their historical question snapshots |
| `explanations`, `evidence` | Delivered content and scoped user/agent observations; not a mastery score |
| `receipts` | Operation ID, request digest, committed revision and result |

The pool is not a general-purpose event platform. Evidence and old question objects are retained because their historical meaning matters. Concept corrections do not rewrite them. Synonyms are not merged by a search index.

## Start and inspect

```text
python -B <cli> --pool <root> init --runtime-pin 0.7.0@<actual40sha> --repository owner/private-repo
python -B <cli> --pool <root> validate
python -B <cli> --pool <root> card
python -B <cli> --pool <root> check-sources
python -B <cli> --pool <root> resume --session paper-a-s1
python -B <cli> --pool <root> questionnaire --session paper-a-s1 --out choices.md
python -B <cli> --pool <root> search --query backlog
```

Paths inside the private pool are stored relatively and survive a clone to another directory. External source paths work only while that location exists. `check-sources` checks actual bytes. Source versions, extractor representations, questionnaire identity, data revision and runtime pin serve different purposes.

`search` returns candidate meanings from names, aliases, definitions and observed paper usage. It never merges records or assigns learning credit. Result and use limits report when more matches exist; `show-use --id <occurrence>` reads a complete selected use and its evidence. `resume --items A1,A4 --related-limit 3` limits the selected context, not the stored data. `card` derives a short current navigation view from the authoritative continuation/selection records.

## Native analysis input

Create an analysis JSON from actual source reading. This shortened synthetic shape illustrates fields, not paper facts:

```json
{
  "session_id": "paper-a-s1",
  "paper": {"id": "paper-a", "title": "Example", "file": "sources/paper.pdf", "source_sha256": "<actual64sha>", "pages": 1},
  "concepts": [
    {"id": "queue.ready-work", "label": "Ready-work queue", "definition": "Shared meaning.", "aliases": ["backlog"], "prerequisites": []}
  ],
  "occurrences": [
    {"key": "local-queue", "concept_id": "queue.ready-work", "page": 1, "section": "System model", "quote": "Exact source words", "usage": "This paper's meaning and limitation.", "role": "local computation", "assumptions": ["slot-start arrivals"], "claim_kind": "author_usage"}
  ],
  "questions": [
    {"item_id": "A1", "group": "Dynamic system", "label": "How ready work changes over a slot", "occurrence_keys": ["local-queue"]}
  ]
}
```

`ingest` verifies source SHA, page count and normalized exact quote containment using the actual PDF/text. This does not validate that the concept, implication or chosen teaching path is correct; native reading must do that. Visual-only anchors need a verifiable text anchor for this initial implementation; retain the visual source separately and describe the limitation rather than inventing a quote. Formula numbers and model assumptions belong in `usage`, not in a global canonical formula.

A new source SHA under the same paper ID requires `new_source_version: true` and a new session ID. Old sources/questions remain present. Redefining an existing concept during ingestion is rejected. Use a distinct sense/role ID or an explicit `revise-concept` operation with old content SHA, replacement, reason and source reference.

```text
python -B <cli> --pool <root> ingest --input analysis.json --expected-revision 0 --operation-id intake-a
```

## One multi-selection response

```json
{
  "session_id": "paper-a-s1",
  "questionnaire_sha256": "<from resume>",
  "selected_ids": ["A1", "A4"],
  "response_text": "The actual user's batch reply",
  "response_ref": "Actual chat/message or user-edited file location"
}
```

```text
python -B <cli> --pool <root> select --input response.json --expected-revision 1 --operation-id actual-response-1
python -B <cli> --pool <root> select-md --input choices.md --source-ref <actual-user-edited-file> --operation-id actual-response-1
```

`select-md` reads the frozen session/hash/revision headers and checked IDs. It does not authenticate who edited the file. Native Codex must use the actual user's response and must distinguish fixtures. Revision conflict and changed-question errors leave the authority unchanged.

## Teaching and evidence

All mutation inputs include `session_id` and `questionnaire_sha256`. An `explanation` additionally includes requested `item_id`, `delivered: true`, complete `text`, and `source_ref`. A prepared draft cannot be recorded as delivered. An `evidence` input contains `item_id`, `kind`, `statement`, `ability`, `representation`, and `source_ref`; optional fields can preserve observed time, unresolved parts and the agent's explicitly attributed interpretation.

Evidence kinds: `self_report`, `application_observation`, `needs_review`, `declined_check`, `legacy_unverified_claim`. The operator supplies observations; the CLI does not authenticate the user or certify understanding. `resume` exposes the full scoped records and labels derived only as `unassessed`, `explained_not_assessed`, or `evidence_recorded_for_scoped_ability`. Read the statement and scope; that last label is not “mastered.”

For a grouped question, `explanation` and `evidence` can specify a nonempty `occurrence_ids` subset of that question. Omission attributes the record to the whole offered item and must only be used for full coverage. A partial explanation leaves the other uses unassessed, reports `partially_explained_not_assessed`, and exposes `explained_occurrence_ids`/`unexplained_occurrence_ids`. Evidence still reports only a scoped ability, never full-group or permanent mastery. The CLI text/JSON interface is UTF-8, including in Windows subprocesses.

```text
python -B <cli> --pool <root> explanation --input delivered.json --expected-revision 2 --operation-id explanation-1
python -B <cli> --pool <root> evidence --input observed.json --expected-revision 3 --operation-id evidence-1
python -B <cli> --pool <root> finish --input close.json --expected-revision 4 --operation-id close-1
python -B <cli> --pool <root> checkpoint --input cursor.json --expected-revision 4 --operation-id pause-1
```

`finish` also requires the actual close instruction in `source_ref`. It adds requested occurrences to the same pool without upgrading learning evidence. Read a finished session by its session ID.

`checkpoint` needs `summary`, `next_action` and the actual context `source_ref`, plus the session/questionnaire identity. Additional attributed user words, lesson reference and unresolved notation can be retained. It records navigation, not a learning judgment. The file lock does not coordinate distinct clones: private Git uses a single writing checkout with explicit fast-forward handoff; a rejected push is a conflict to reconcile, not a reason to force or auto-merge state.

A cursor binds the session's frozen questionnaire and actual selection record. A later selection or close retires it into history; closed sessions reject new current cursors. Unrelated pool revisions do not invalidate a cursor. The card distinguishes an explicit empty answer, no answer, and a historical source version even if those old bytes still match.

## Explicit correction and legacy import

`revise-concept` requires `concept_id`, `expected_content_sha256`, complete five-field `replacement`, `reason`, and `source_ref`. Historical occurrences and answers retain their original snapshots and are marked as differing from the current definition when reopened.

`revise-use` requires `occurrence_id`, `replacement`, `reason`, and `source_ref`. Replacement fields can include `usage`, `role`, `assumptions`, `concept_id`, `page`, `section`, `quote`, `claim_kind`, and `supporting_quotes: [{page,quote}]`. It verifies all supplied quotes against the same original source bytes. It adds a replacement occurrence and correction link, preserving the original question and learning evidence. If the old use was pooled, the corrected use also enters the pool without inheriting learning credit. `show-use` and `resume` expose corrections; ordinary search omits superseded interpretations. A different paper or source version needs a new intake, not this correction command.

The `migrate-v1` command imports only the documented old flat prototype shape: `{schema_version:1, concepts:[{concept_id,names,definition,aliases,prerequisite_ids,learner,...}]}` into an empty destination. It preserves the complete original, including claimed states, as an unverified legacy import; it creates no verified evidence or fabricated source occurrences. It is a migration fixture/interface, not a claim that the user had an earlier implemented pool.

Before publishing data, verify current private visibility and remote identity. Public runtime changes are separate from private corpus commits. New precise DIGR invocations still perform their normal live protocol acquisition; the data binding must not replace routing authority.
