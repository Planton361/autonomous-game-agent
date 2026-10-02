# Human-first reader and G3 presentation

Authority: [#122](https://github.com/Planton361/autonomous-game-agent/issues/122)
with [Program Owner amendment 5938665528](https://github.com/Planton361/autonomous-game-agent/issues/122#issuecomment-5938665528),
accepted [G3 #106](https://github.com/Planton361/autonomous-game-agent/issues/106)
and [conceptual model #137](https://github.com/Planton361/autonomous-game-agent/issues/137).
Exact attachment truth remains the accepted #121 / PR #144 baseline.

## Preferred technical reader

The same preferred pages now read in this order:

1. What this is.
2. Responsibility / why it exists.
3. How it works.
4. Inputs / outputs / important connections.
5. Subcomponents / go deeper (System and Component only).
6. Current implementation state.
7. Important limitations.
8. Research Questions.
9. Relevant Research / Literature.
10. Gap-assessment status.
11. Sources & verification; collapsed Sources & audit.

Perception, Observation Builder and UI State Classification have bounded public
reader copy in `technical_reader.py`, authored from the existing builder, OCR,
spatial-producer and UI source inspections at `main@80b6b122`. It describes the
current orchestration, not a new capability. Other subjects retain their Registry
description and explicit unavailable mechanism/limitation states; missing copy
never implies completeness. Technical inspection is not a scientific result.

Direct child cards contain human responsibility, implementation state, explicit
public question count when present, a Research availability cue and Open component.
Only `part_of` creates these children. Parent and related Research sections show
original destination links and distinct record counts, not descendant Paper prose.
Function membership/order/role remain exactly authored, non-containment context.
No Research is inherited through Function or Domain.

Research Questions come only from the existing explicit public subject relations.
No private RQ target field is introduced. Empty means: “No explicit Research
Question is currently attached to this subject.” Gap assessment remains unassessed.

Human role labels are Direct subject, Method / baseline, Measurement relevance,
Project transfer and Adjacent context. They change display only, not literal
backend predicates. Sources expose compact links with exact commits, Registry,
Evidence, row IDs, recipes, ownership and fingerprints inside one native collapsed
`aga-audit` callout. Research Map page decisions stay there, separate from runtime
algorithm rationale. Native Markdown remains the semantic fallback.

## Opt-in private RA-2 0.2

Existing 0.1 records and templates remain valid, with no bulk migration.
Only a record using G3 fields must explicitly declare
`epistemic_schema_version: "0.2"`. The closed contracts permit:

| Owner | Field | Value |
| --- | --- | --- |
| Paper / ReadingNote / Finding | `presentation_contexts` | List of exact context blocks, default empty |
| Finding | `presentation_statement`, `presentation_limitation` | Optional nonblank authored text |
| Synthesis | `presentation_summary`, `presentation_limitation` | Optional nonblank authored text |
| Dossier | `presentation_overview` | Optional nonblank authored text |
| ResearchQuestion | `presentation_question` | Optional nonblank authored text |
| Topic | `presentation_summary` | Optional nonblank authored text |

Each context contains `role` (one existing literal Research property), `target_ref`,
`why_relevant` (nonblank authored text), optional singular `finding_ref` and optional
singular `reading_note_ref`. The same owner must already declare that exact
role/target. Duplicate owner/role/target contexts fail closed. Contexts do not create
an attachment, a role, a new target class, or an RQ target authority.

Scientific text is escaped literally, without truncation, whitespace stripping,
body extraction, paraphrase, generated summaries or inference. Bodies, Journal
prose and annotations remain outside presentation. Missing selections never cause
replacement or best-Finding selection. One Paper identity can carry separate
contexts for multiple subjects.

## Literal Paper and Finding preview

A preview joins a direct attachment to its Paper through the existing finite path
ending in that same terminal owner/role/target, or a directly declaring private
Paper. It displays human bibliography, authored relevance, explicitly selected
Finding, limitation/read provenance and source/detail links. A public Paper anchor
without a private RA-2 Paper has no G3 structured preview; exact navigation remains
in audit. Sparse bibliography is shown once per Paper when no eligible context is
available. Distinct explicitly authored contexts are preserved.

Paper and context owner must be domain-accepted or in-review for rich context.
In-review is visibly qualified. Draft/superseded/archived records remain
historical/detail navigation, without current scientific prose.

Finding default rich display requires both domain-accepted document maturity and
domain-accepted review. An in-review document with checked/domain-accepted review
is explicitly qualified; draft review or historical maturity suppresses the prose.
A selected Finding must explicitly name that Paper in `source_refs`; a selected
ReadingNote must explicitly name that Paper as its single Paper/source. Unavailable,
wrong-type or unmatched selections are reported without substitution or source-family
resolution. Reading provenance may be displayed at any maturity, including draft,
with its actual maturity, version/date, depth and checked sections visible.

Finding origin determines attribution: Source-reported finding, Author-reported
limitation, Project inference or Project empirical result. A source-origin Finding's
limitation is labeled Author-reported limitation / applicability; a project-origin
Finding's limitation is labeled Project-authored limitation / applicability.
Project-authored relevance is separately labeled and links its actual owner.
These labels never promote an authored record into an accepted project Claim.

Independent Synthesis/orientation previews appear in the existing global Research
Landscape, using only literal fields and eligible maturity. Synthesis requires all
Finding references to resolve to private Findings. No Component-specific Synthesis
relevance, inferred consensus, source resolution or G4/G5 expansion occurs.

## Fingerprints, ownership and privacy

Direct-view manifest **2.13** adds `presentation_fingerprint_version: "1.0"` and
`presentation_input_fingerprint`. The closed reference index remains **1.2**, and
its existing `private_input_fingerprint` and all E1–E9/N-C/N-T meanings remain intact.
Structured audit inputs use deterministic JSON with literal recoverable values.
The projection computes the presentation hash once and reuses it across pages and
the manifest; individual page rendering computes the same hash independently.
The separate presentation hash uses sorted record identities and canonical JSON
for consumed structured identity/title/state/reference, bibliography, read metadata
and G3 fields. Bodies, aliases/tags, filenames, local paths, mtimes and annotations
are excluded. Locator moves can change links without changing either input hash.

Generated path sets, owner and Identity Page metadata version remain unchanged.
Intact historical manifests through 2.12 migrate through the existing bounded
writer. Edited/unowned files still fail closed; authored notes are untouched;
workspace check still performs zero writes. Private values stay export-deny and
never enter public Atlas rendering. Fixtures are entirely synthetic.

## Reader Markdown and PDF

Normal native Obsidian PDF with the managed optional stylesheet omits `aga-audit`
under `@media print`, even when the disclosure is open. Screen/native audit stays
complete. No tiny fonts, fixed-height clipping or external resource is introduced.
Stylesheet installation is still a separate exact-head G6 action.

For CSS-off/generic Markdown/PDF engines, create a private read-only derivative:

```bash
uv run --no-sync python -m fh_agent.research_atlas.reader_export \
  --vault-root "$PRIVATE_VAULT" \
  --page '_generated/derived/identity-pages/Perception.md' \
  --output 'reader-exports/Perception.md'
```

The command validates the private root, generated ownership and physical paths.
It removes the complete audit block and hidden owner metadata, retaining technical
explanation, navigation, question state, literal previews, limitations and source
links. It writes only a new `reader-exports/*.md` derivative inside that same private
vault, rejects existing output and never writes an editable master or an external
public export. Render that derivative with the chosen Markdown/PDF reader. The
original preferred page remains the audit-complete projection. Generic rendering
of the original audit-complete Markdown can expand blockquotes; use the derivative
when the print stylesheet is unavailable.

## Task-based human G6 after CONTROL acceptance

Implementation never applies to the synced private vault. After exact-head source/CI
acceptance, use supported apply/check for truthful real state and the separately
physical disposable synthetic vault for positive examples. The committed
`tests/test_g2_interface_attachment.py::reader_records()` provides three unmistakably
fictional, human-titled Papers, explicit contexts/Findings/limitations/read provenance,
and one independent Synthesis. Do not put these in the actual Research corpus.

G6 tasks: explain Perception and what is missing within roughly 30 seconds; open
Observation Builder; understand question availability, Paper relevance, attributed
Finding/limitation/read state; open Sources & audit; produce one concise reader
PDF/Markdown export. No screenshot marathon. Real Research, private RQ targeting,
Gap computation, Graph, actual-vault application and merge remain separate gates.

## Accepted #125 RQ reader overlay

The later [RQ Reader Contract](RQ%20Reader%20Contract.md) supersedes the Component
reader's inline Paper previews and unassessed gap placeholder with compact exact
RQ cards. G3 presentation functions, attribution and historical 0.1/0.2 validation
remain intact. Manifest 2.15 and presentation fingerprint 1.1 implement the later
accepted opt-in 0.3 inputs; the historical 2.13 description above remains the G3
baseline, not the current manifest version.
