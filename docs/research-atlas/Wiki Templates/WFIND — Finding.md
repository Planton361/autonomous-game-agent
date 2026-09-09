# WFIND — Finding

Public-safe template source — not an active private record. Copy the example
properties into a separately authored private note and replace placeholders.
No reading, review, result or decision is asserted by this template.

## Required properties (example only)

```yaml
wiki_schema_version: "0.1"
epistemic_schema_version: "0.1"
wiki_id: "WFIND-<UNIQUE-ID>"
doc_type: finding
title: "<TITLE>"
record_version: 1
document_maturity: draft
privacy: private
export_policy: deny
atlas_refs: []
claim_origin: our_inference
review_state: draft
source_refs: ["<SOURCE-REF>"]
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
reading_note_refs: []
supports_refs: []
contradicts_refs: []
qualifies_refs: []
rq_refs: []
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

## Atomic proposition

`<ONE SCOPED PROPOSITION, NOT AN ESTABLISHED RESULT>`. Split independently supportable/refutable claims.

`<TO BE AUTHORED; NOT REVIEWED>`

## Population/task/environment

State the relevant subject and environment; not_applicable requires justification.

`<TO BE AUTHORED; NOT REVIEWED>`

## Compared/reference conditions

Specify the actual comparison/reference.

`<TO BE AUTHORED; NOT REVIEWED>`

## Outcome/measurement

Name outcome and operational measurement; do not invent an experiment for theoretical claims.

`<TO BE AUTHORED; NOT REVIEWED>`

## Scope/conditions

Include necessary qualifications in the proposition itself.

`<TO BE AUTHORED; NOT REVIEWED>`

## Source evidence table with version and concrete locator

| Source ref | Source type | Exact version | Concrete locator | Proposition part supported |
| --- | --- | --- | --- | --- |
| `<SOURCE-REF>` | `<PROVENANCE-TYPE>` | `<VERSION>` | `<PAGE/SECTION/TABLE/DATA-LOCATOR>` | `<CLAIM-PART>` |

A source link alone is insufficient. Source type is provenance, not a truth score.

`<TO BE AUTHORED; NOT REVIEWED>`

## Limitations/applicability/counterevidence

Include contrary evidence and limits. No subjective numeric confidence.

`<TO BE AUTHORED; NOT REVIEWED>`

## supports/contradicts/qualifies assessment

Pin target claim revisions and justify the relation, or explain not_applicable. A difference alone is not contradiction.

`<TO BE AUTHORED; NOT REVIEWED>`

## Origin-specific reasoning

authors_result: checked primary result and relevant method via ReadingNote. authors_limitation: explicit primary passage via ReadingNote, not our suspicion. our_inference: premises, inference, alternatives. own_empirical_result: actual versioned data/run/analysis/protocol, measurement unit, integrity and admissibility evidence; no planned test as result.

`<TO BE AUTHORED; NOT REVIEWED>`

## Review record

not reviewed. checked requires a documented source/claim check; domain_accepted requires scoped SCI review, not universal truth. Record actor/role/date/revision/scope/result and reservations. Material changes require a new revision and human reset to draft; prior acceptance remains historical.

`<TO BE AUTHORED; NOT REVIEWED>`
