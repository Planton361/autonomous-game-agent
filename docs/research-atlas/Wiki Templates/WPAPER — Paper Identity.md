# WPAPER — Paper Identity

Public-safe template source — not an active private record. Copy the example
properties into a separately authored private note and replace placeholders.
No reading, review, result or decision is asserted by this template.

## Required properties (example only)

```yaml
wiki_schema_version: "0.1"
epistemic_schema_version: "0.1"
wiki_id: "WPAPER-<UNIQUE-ID>"
doc_type: paper
title: "<TITLE>"
record_version: 1
document_maturity: draft
privacy: private
export_policy: deny
atlas_refs: []
source_refs: ["<SOURCE-IDENTITY>"]
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
doi: "<DOI-IF-KNOWN>"
url: "<SOURCE-URL-IF-KNOWN>"
authors: []
publication_year: null
venue: "<VENUE-IF-KNOWN>"
reading_note_refs: []
related_version_refs: []
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

## Identifying metadata/source locator

Identify title/authors and a recoverable source identity; unknown metadata stays unknown. DOI is optional.

`<TO BE AUTHORED; NOT REVIEWED>`

## Publication/preprint character

Document bibliographic character, not a quality score.

`<TO BE AUTHORED; NOT REVIEWED>`

## Version list/date/locator/relationships

Identify corrections and related versions. Do not overwrite the version read in existing ReadingNotes.

`<TO BE AUTHORED; NOT REVIEWED>`

## ReadingNote links

Multiple notes may process the same version; reading_depth is not a Paper property.

`<TO BE AUTHORED; NOT REVIEWED>`

## Identity uncertainties/corrections

Record ambiguity, corrections or retractions with provenance. Multiple versions are not independent studies.

`<TO BE AUTHORED; NOT REVIEWED>`
