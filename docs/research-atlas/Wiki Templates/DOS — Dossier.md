# DOS — Dossier

Public-safe template source — not an active private record. Copy the example
properties into a separately authored private note and replace placeholders.
No reading, review, result or decision is asserted by this template.

## Required properties (example only)

```yaml
wiki_schema_version: "0.1"
epistemic_schema_version: "0.1"
wiki_id: "DOS-<UNIQUE-ID>"
doc_type: dossier
title: "<TITLE>"
record_version: 1
document_maturity: draft
privacy: private
export_policy: deny
atlas_refs: []
subject_refs: ["<SUBJECT-REF>"]
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
process_refs: []
rq_refs: []
finding_refs: []
paper_refs: []
decision_refs: []
```

## B0 — Provenance and revision/review record

| Field | Value |
| --- | --- |
| Responsible author/editor | <EDITOR> |
| Creation date | <ACTUAL-CREATION-DATE> |
| Revision date | <ACTUAL-REVISION-DATE> |
| Origin including LLM/chat assistance | <ORIGIN/ASSISTANCE-OR-NONE> |
| Record revision | <RECORD-VERSION> |
| Change reason | <REASON> |
| Exact source/object versions | <VERSIONED-REFS> |
| Concrete source/object locators | <LOCATORS> |
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

## Purpose / exact subject

Identify the precise subject; at least one atlas_refs or subject_refs entry is required.

<TO BE AUTHORED; NOT REVIEWED>

## Scope / non-responsibilities

State what is and is not covered.

<TO BE AUTHORED; NOT REVIEWED>

## Technical projection references and source state

Link public technical records and their source commit. Do not author implementation_status, verification_status or architecture_authority copies.

<TO BE AUTHORED; NOT REVIEWED>

## Interfaces/data/process context

Distinguish public facts from proposed interpretation.

<TO BE AUTHORED; NOT REVIEWED>

## Research roles

Justify each link's exact role. A Component link does not establish evaluation of our exact implementation.

<TO BE AUTHORED; NOT REVIEWED>

## Open questions / limits

Record unresolved questions without a maturity/exhaustion score.

<TO BE AUTHORED; NOT REVIEWED>
