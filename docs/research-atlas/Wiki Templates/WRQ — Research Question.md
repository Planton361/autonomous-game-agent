# WRQ — Research Question

Public-safe template source — not an active private record. Copy the example
properties into a separately authored private note and replace placeholders.
No reading, review, result or decision is asserted by this template.

Intake and maintenance: [operator workflow](../Research%20Intake%20and%20Maintenance.md).
Keep this record’s durable identity when reused or renamed; creation/validation
never means scientific acceptance.

## Required properties (example only)

```yaml
wiki_schema_version: "0.1"
epistemic_schema_version: "0.1"
wiki_id: "WRQ-<UNIQUE-ID>"
doc_type: research_question
title: "<TITLE>"
record_version: 1
document_maturity: draft
privacy: private
export_policy: deny
atlas_refs: []
question_stage: idea
decision_state: none
```

## Optional properties (example only)

Omit unused properties. These are flat lists or short bibliographic scalars;
complex scientific conditions and arguments belong in the body.

```yaml
aliases: []
tags: []
wiki_refs: []
supersedes_refs: []
review_refs: []
research_direct_subject_refs: []
research_method_or_baseline_refs: []
research_measurement_relevance_refs: []
research_project_transfer_refs: []
research_adjacent_context_refs: []
search_refs: []
synthesis_refs: []
finding_refs: []
experiment_lead_refs: []
decision_refs: []
```

## B0 — Provenance and revision/review record

| Field | Value |
| --- | --- |
| Responsible author/editor | `<EDITOR>` |
| Creation date | `<ACTUAL-CREATION-DATE>` |
| Revision date | `<ACTUAL-REVISION-DATE>` |
| Origin including LLM/chat assistance | `<ORIGIN/ASSISTANCE-OR-NONE>` |
| Record revision | `<RECORD-VERSION>` |
| Change reason | `<REASON>` |
| Exact source/object versions | `<VERSIONED-REFS>` |
| Concrete source/object locators | `<LOCATORS>` |
| Review actor | not reviewed |
| Review role | not reviewed |
| Review date | not reviewed |
| Review scope | not reviewed |
| Review result | not reviewed |

Placeholders are not evidence. Material changes require a new revision and human
review; no automatic semantic diff or acceptance occurs. Preserve earlier
SearchRecords/Decisions and historical Public Evidence. For superseded document
maturity, supply explicit supersedes_refs lineage and explain predecessor and
replacement direction/version in the body; the field alone proves neither.
The five research-role lists imply neither each other nor supports, part_of,
causality or implementation evidence. No automatic private-to-public promotion
and no Wiki-to-Agent-Memory connection exist.

## Exact question/claim revision and scope

Pin the question, version and scope, not a whole field's alleged exhaustion.

`<TO BE AUTHORED; NOT REVIEWED>`

## Knowledge target/estimand

Define the knowledge target and estimand where applicable.

`<TO BE AUTHORED; NOT REVIEWED>`

## Closest relevant comparison

Record closest competing explanation or method; open at idea, concrete for researchability.

`<TO BE AUTHORED; NOT REVIEWED>`

## Search/literature state and limitations

literature_mapped means documented scope, not proven novelty.

`<TO BE AUTHORED; NOT REVIEWED>`

## Discriminating/falsifiable test idea

Describe a testable distinction, not execution authorization or a protocol freeze.

`<TO BE AUTHORED; NOT REVIEWED>`

## Validity/resource risks

Separate scientific adequacy and program resource decisions.

`<TO BE AUTHORED; NOT REVIEWED>`

## Closure points

Identify unresolved evidence/comparison/identification issues.

`<TO BE AUTHORED; NOT REVIEWED>`

## Stage history

Record previous/new question_stage, revision/date/reason and stage-gate review; no automatic transitions.

`<TO BE AUTHORED; NOT REVIEWED>`

## Decision history

Every accepted/deprioritized/killed/superseded state needs a versioned Decision ref; accepted requires candidate. Kill is limited to exact candidate revision and then-current search/review state, never Component/Topic/Method/Paper area. SCI reviews bounded candidates; Anton decides program/study/resource changes. Preserve old states; reopening is explicit new review, not history rewriting.

`<TO BE AUTHORED; NOT REVIEWED>`

## Optional RQ reader profile (RA-2 0.3)

Opt in explicitly; retain this same `wiki_id`. This is the RQ's sole authored
scientific input, not a second analysis note. See the
[RQ Reader Contract](../RQ%20Reader%20Contract.md) for eligibility and exact fields.
Only 0.3 gives this RQ's own `research_direct_subject_refs` exact technical-target
semantics. Unbound questions remain valid. No old authored records are migrated.

```yaml
epistemic_schema_version: "0.3"
research_direct_subject_refs: []
presentation_question: null
presentation_analysis:
  subject_contexts: []
  literature_rows: []
  nearest_work_rows: []
  establishes: []
  conclusion: null
  zotero_corpus: null
```

Empty selections mean no literature explicitly curated or compared, not no
relevant literature or prior art. Author a conclusion only under its explicit
comparison/evidence/review contract. `next_scientific_work` is guidance, never
execution authorization. The complete bibliography, PDFs and reading stay in Zotero.

### Author the accepted closed analysis shapes

Merge only explicitly authored selections into the opt-in object above. Keep
`conclusion: null` until authorized analysis supplies it. Do not copy placeholder
prose into a scientific conclusion. The exact [#124 accepted package](https://github.com/Planton361/autonomous-game-agent/issues/124#issuecomment-5959565974)
and [acceptance](https://github.com/Planton361/autonomous-game-agent/issues/124#issuecomment-5959667108)
govern; [RQ Reader Contract](../RQ%20Reader%20Contract.md) gives eligibility.

| Array/object | Exact entry fields |
| --- | --- |
| subject_contexts | target_ref, why_matters |
| literature_rows | paper_ref, context_owner_ref, context_role |
| nearest_work_rows | paper_ref, approach, already_covers, remaining_difference, competitive_relevance, evidence_refs |
| establishes | record_ref, use (`knowledge` or `adverse_evidence`) |
| zotero_corpus | kind (`collection` or `saved_search`), ref |
| conclusion required | question_version, gap_state, authored_conclusion, prior_work_covers, remaining_distinction, strongest_uncertainty, next_scientific_work, as_of, author |
| conclusion optional | evidence_refs, reviewed_by, reviewed_inputs, falsifiable_test_concept, contribution_potential, feasibility_risks, project_fit |
| reviewed_inputs entry | ref, record_version |

Each technical subject needs its own exact binding and reason. A multi-component
question reuses the same RQ, Paper and ReadingNote identities. Literature context
must already belong to the selected Paper/ReadingNote/Finding and target this RQ;
selection does not create relevance. `context_role` uses one of the existing five
research-role property names. Nearest-work evidence selects exact source Findings.
The RQ must separately declare selected `finding_refs` and `synthesis_refs`.

No new search counts, technical-practice fields, analysis identity or disposition
schema exists. Allowed gap states are `unassessed`, `insufficient_evidence`,
`covered_by_prior_art`, `narrowing_required`, `candidate_gap`. Candidate requires
all four rationale fields and current reviewed evidence. Review pins each consumed
private dependency’s exact revision; actors and RQ `review_refs` attest human
review, never validation success. Operational decisions remain separate.
