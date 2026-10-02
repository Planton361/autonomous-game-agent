# Research Steering projection

Authority: [#126 CONTROL contract](https://github.com/Planton361/autonomous-game-agent/issues/126#issuecomment-5962552494),
using the accepted [RQ Reader Contract](RQ%20Reader%20Contract.md).
This replaces the older top-level dashboard-table proposal. No scientific schema,
public Registry, E1–E9, runtime or canonical source changes are introduced.

The existing `_generated/derived/indexes/Research Landscape.md` is the **Research
Steering** landing page. Its normal reader contains exactly three Markdown tables
and compact inspection links. The old W07 public/private inventories, drafts,
SearchRecords, Findings, Syntheses, Dossiers, DecisionDrafts and history remain
in a collapsed secondary section. W10 Literature Inspection and Source detail /
Audit retain their existing routes. Research Knowledge Home links to Steering.
No separate landing-page identity or duplicate detail page is introduced.

## Derivations

| Inventory | Exact derivation |
| --- | --- |
| Research Questions | Current `in_review` / `domain_accepted` RQs; human `presentation_question`, otherwise title; existing #125 preferred RQ page. Draft/superseded/archived RQs remain secondary navigation only. Legacy current RQs remain visible but have no 0.3 direct binding/analysis. |
| RQ technical subjects | `RQReader.subjects`: opted-in 0.3 RQ-owned `research_direct_subject_refs`, validated by actual Atlas technical type. Multiple subjects remain explicit. No ancestry, Domain, Function, Assembly, adjacency, generic `atlas_refs`, E9 or Paper/Finding attachment joins. |
| RQ Papers | Set of exact existing Paper identities in `literature_rows.paper_ref` and `nearest_work_rows.paper_ref`. Also eligible explicitly selected `establishes` Finding sources, or exact sources of its eligible Synthesis constituent Findings, using existing `statement_ok` gates. SourceFamily-only refs never resolve to Papers. An explicit row counts its existing Paper even when its relevance/comparison prose is unavailable: this is mapped-record membership, not evidence adequacy. Search `result_refs`, corpus pointers, body prose, family similarity and inferred relevance are excluded. |
| RQ Status | Stored `conclusion.gap_state` only when existing `RQReader.conclusion_ok` passes, including exact version/review/dependency gates. Otherwise **Current conclusion unavailable**, never a synthesized `unassessed`. |
| Technical Components | All actual Atlas `Component` entities, linked to existing preferred technical pages. No prefix/name-derived type. |
| Component RQs | Unique current RQs whose exact RQ-owned direct set contains this Component identity. No inherited or adjacent RQs. |
| Component Papers | Union of those RQs' exact Paper sets; each durable Paper counts once per Component. Reuse across Components is legitimate. |
| Component Gap-analysis status | Counts of eligible stored RQ gap states, in fixed five-state order, plus unavailable conclusions separately. No score or operational recommendation. Empty = **No directly mapped current RQs**; no assertion about absence of research or gaps. |
| Papers | Every existing authored Paper identity once, preserving W10's inventory scope (including historical records). No Zotero corpus import. |
| Paper Area / Components | Paper → explicit current RQ Paper membership → exact RQ-owned direct subjects whose actual type is Component; unique Components, ordered by human name/identity. |
| Paper Used in RQs | Unique current RQs containing the exact Paper identity in the same Paper-membership set. |
| Paper Read state | Exact Paper-referencing ReadingNotes, each with its existing `reading_depth` and maturity. No highest-depth synthesis or new reading vocabulary. No mapped note is explicit; no family-level retargeting. |
| Paper Source status | Existing G4 Paper family, declared related/preferred version resolution, and exact mapped ReadingNotes' `version_read` resolution, with G4 version warnings. Preferred version is navigation, never substituted for version read. Read depth and resolution remain separate. |
| Paper Zotero | Existing `RQReader.zotero` rule: exactly one accepted item pointer bound unambiguously to the resolved Paper family. Missing/ambiguous stays unavailable. |

Counts describe mapped records only, never completeness, saturation, novelty,
quality, feasibility, project fit, value, confidence or automatic priority. No
Decision/Claim acceptance or Experiment/Protocol authorization is produced.
GitHub Project retains operational priority authority; `next_scientific_work`
is scientific guidance only and is not reproduced as execution permission.

## Bases, Markdown and ownership

One additional fixed payload, `bases/Research Steering.base`, has exactly three
focused table views: **Research Questions**, **Technical Components**, **Papers**.
Each view filters exact preferred page paths. Snapshot formulas render the same
projection cells as Markdown, including human links, numeric counts and status
text. No row notes, scientific master, extra identities or duplicate projection
infrastructure are created. Missing locators in standalone sparse renderer calls
stay unavailable in Markdown and cannot create a guessed Base route; supported
workspace scanning supplies locators for every actual authored record.

Markdown tables are always visible; each links to its focused Base view for
optional filtering/sorting. This avoids showing two copies of each table and
keeps core navigation usable with Bases disabled. Generated values require
regeneration after authoring. Bases use documented
[formulas and view filters](https://obsidian.md/help/bases/syntax) and
[`if` / `link` functions](https://obsidian.md/help/bases/functions).
Native visual behavior is reserved for later exact-head human G6.

Manifest **2.15**, presentation fingerprint **1.1**, reference and G4 fingerprints
remain unchanged in meaning/schema: all consumed scientific fields already
participate in these contracts. The new Base uses the existing semantic ownership
and Obsidian normalization rules. Existing strict-byte index ownership, intact
old-manifest migration, unknown/unowned/edited-path rejection, preflight,
manifest-last writes and zero-write check remain unchanged. No new ownership root
or wildcard is added. Private absolute locators fail closed through the existing
presentation path validator. Authored records/catalog remain untouched.

## Synthetic acceptance mapping

`tests/test_research_steering.py` is required by `.github/fast-tests.txt`; existing
RQ, W07/W10, G4, workspace and ownership tests remain required with the unchanged
60,000 ms CI gate. Fixtures are fictional and never applied to the private Vault.

| Required cases | Proof |
| --- | --- |
| 1–8: exact single/multi-subject RQs, multiple RQs, reused Papers, dedup, no inheritance/Domain/Function/adjacency leakage | Reuse/set tests; actual Atlas parent/child exclusion; wrong-type targets; structured statement sources; no-row generic attachments excluded. |
| 9–12: five states, unavailable conclusion, distribution, sparse Component | Five independent state parametrizations; stale/absent/legacy/draft/historical cases; mixed distribution and empty Components. |
| 13–15: read/source distinction, unresolved version, global Paper uniqueness | Exact note/version test; verified-source/no-note case; reused Paper global row assertion. |
| 16–19: preferred RQ/Component/Paper and eligible Zotero navigation | Base exact-path filters, human Markdown targets, full synthetic tree, accepted/ambiguous Zotero checks. |
| 20–22: deterministic Bases/Markdown and rich-view absence | Shuffled records yield equal inventories/Base bytes/Markdown; every Base formula cell matches Markdown's shared inventory; fallback retains three tables and preferred links after rich-view links are removed. |
| 23–25: finite ownership, zero-write, privacy | Existing lifecycle/normalization/negative-path coverage also exercises the new Base; new intact 2.15 migration, edited-Base rejection, authored-byte and filesystem snapshots, unsafe locator fail-closed. |
| 26–27: counts do not change conclusions or authorization | Unused and explicitly consumed Paper additions preserve stored gap states and Decision state; guidance absent from dashboard; no scientific mutations. |
| 28–29: set-like determinism vs authored order | Shuffled snapshots; existing RQ authored rows untouched and order-sensitive presentation fingerprint retained. |

Implementation does not perform real Research, populate production RQs/literature,
access Zotero/hidden game state, enter Live, run publication work, apply the private
Vault, perform human G6 or merge. Later CONTROL authorization must name the exact
reviewed PR head before actual-vault apply/check or human G6.
