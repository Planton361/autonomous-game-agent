# READ — Reading Note

Public-safe template source — not an active private record. Copy the example
properties into a separately authored private note and replace placeholders.
No reading, review, result or decision is asserted by this template.

## Required properties (example only)

```yaml
wiki_schema_version: "0.1"
epistemic_schema_version: "0.1"
wiki_id: "READ-<UNIQUE-ID>"
doc_type: reading_note
title: "<TITLE>"
record_version: 1
document_maturity: draft
privacy: private
export_policy: deny
atlas_refs: []
paper_refs: ["<PAPER-REF>"]
# Alternatively use source_refs: ["<SOURCE-REF>"]; remove paper_refs entirely.
version_read: null
read_date: null
reading_depth: lead_only
checked_sections: []
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
finding_refs: []
search_refs: []
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

## Source identity/version/check protocol

Paper is source identity; ReadingNote is our processing of a concrete version. Multiple notes per Paper/version are allowed, not independent evidence. Choose exactly one paper_refs OR source_refs identity. lead_only has no checked sections or read date. A checked depth needs a version, actual date and its named section; relevant_fulltext_checked needs explicit scope/omissions. methods_checked does not imply abstract_checked or results_checked.

| Source/version | Section/locator | Checked by/on | Actual depth | Omissions |
| --- | --- | --- | --- | --- |
| `<SOURCE/VERSION>` | `<LOCATOR>` | not checked | lead_only | `<UNKNOWN>` |

`<TO BE AUTHORED; NOT REVIEWED>`

## Research question and actual approach

Report what the source actually investigates, not an inferred project match.

`<TO BE AUTHORED; NOT REVIEWED>`

## Population/task/environment

Use unknown for unchecked/unclear information, not_reported only within a checked source scope.

`<TO BE AUTHORED; NOT REVIEWED>`

## Treatment/comparison/fixed factors

Separate the compared conditions and what is held fixed.

`<TO BE AUTHORED; NOT REVIEWED>`

## Agent information/Memory/training/weights

Document each where relevant; absence of reporting does not establish absence of a feature.

`<TO BE AUTHORED; NOT REVIEWED>`

## Resources/budgets/experimental unit

Document actual source information; never infer independence from run counts alone.

`<TO BE AUTHORED; NOT REVIEWED>`

## Outcomes/measurement/analysis

Locate the relevant measures/results and methods.

`<TO BE AUTHORED; NOT REVIEWED>`

## Authors' findings with locators

Only the authors' reported findings, with concrete passages.

`<TO BE AUTHORED; NOT REVIEWED>`

## Authors' explicit limitations with locators

Only explicit author statements; our suspected limitations belong below.

`<TO BE AUTHORED; NOT REVIEWED>`

## Our interpretation/inference

Separate our inference and its premises from author findings.

`<TO BE AUTHORED; NOT REVIEWED>`

## Applicability/transfer limits

Explain bounded project relevance, not demonstrated transfer by association.

`<TO BE AUTHORED; NOT REVIEWED>`

## Unknown/not-reported/open verification questions

unknown = unchecked/unclear; not_reported = absent in named checked sections; not_applicable requires a reason. Reading is not replication.

`<TO BE AUTHORED; NOT REVIEWED>`
