# RQ-centered scientific reader

Authority: accepted [#124 package](https://github.com/Planton361/autonomous-game-agent/issues/124#issuecomment-5959565974),
[#125 amendment](https://github.com/Planton361/autonomous-game-agent/issues/125#issuecomment-5959688598)
and [CONTROL release](https://github.com/Planton361/autonomous-game-agent/issues/125#issuecomment-5959747816).
This supersedes the older #125 separate technical-best-practice request.

Research Question is the scientific unit. Zotero remains primary for the full
bibliography, PDFs, attachments, annotations and normal reading. The private
reader consumes curated structured analysis; it performs no Research and has no
real Zotero API/SQLite/PDF access. Dossier behavior and E1–E9 stay unchanged.

## Opt-in and authoring

RA-2 0.3 is explicit. Old 0.1/0.2 records remain valid and untouched. Only 0.3
ResearchQuestions use their own `research_direct_subject_refs` as exact private
bindings to actual Atlas System, Component, Interface, Contract, DataArtifact or
MeasurementPoint identities. Type comes from the snapshot, never the ID prefix.
No binding comes from generic `atlas_refs`, ancestors, Function, Domain, adjacency,
Paper/Finding attachment, source similarity or E9. Unbound RQs get independent
pages. Multiple questions and subjects are supported.

`rq_schema.py` defines the closed objects; unknown fields, bad primitive types,
blank text, unsafe refs/pointers, duplicate selections and illegal combinations
fail before generated writes. The single RQ-owned `presentation_analysis` has:

| Field | Closed shape / meaning |
| --- | --- |
| subject_contexts | Ordered `{target_ref, why_matters}`; exact directly bound targets only, unique target |
| literature_rows | Ordered `{paper_ref, context_owner_ref, context_role}`; one row per exact private Paper |
| nearest_work_rows | Ordered `{paper_ref, approach, already_covers, remaining_difference, competitive_relevance, evidence_refs}`; unique Paper, nonempty exact source Finding set |
| establishes | Ordered `{record_ref, use}`; exact Finding/Synthesis, unique record/use; `knowledge` or `adverse_evidence` |
| conclusion | Optional closed authored assessment below |
| zotero_corpus | Optional `{kind, ref}`; `collection` or `saved_search`, exact supported pointer |

Conclusion requires `question_version`, `gap_state`, `authored_conclusion`,
`prior_work_covers`, `remaining_distinction`, `strongest_uncertainty`,
`next_scientific_work`, `as_of` and `author`. Optional sets: `evidence_refs`,
`reviewed_by`; optional `reviewed_inputs` is one `{ref, record_version}` per
consumed private dependency. Optional rationale texts are `falsifiable_test_concept`,
`contribution_potential`, `feasibility_risks`, `project_fit`; all four are required
for `candidate_gap`. Dates are ISO dates; versions are strict positive integers.

Gap states: `unassessed`, `insufficient_evidence`, `covered_by_prior_art`,
`narrowing_required`, `candidate_gap`. Covered/narrowing/candidate require an
explicit eligible comparison and evidence. Candidate also requires current review.
Domain-accepted conclusions require exact current reviewed inputs, actors and RQ
`review_refs`. In-review conclusions without review are visibly provisional;
attempted stale reviews cannot degrade silently into provisional prose.

Review refs are explicit eligible JournalEntries identifying this RQ in
`resulting_object_refs`, or exact GitHub Owner/reviewer issue-comment references
in this repository. External authority is not fetched. A human attestation is
required; structural validation certifies neither adequacy nor truth. Changed
pinned revisions, missing/extra dependencies, historical or wrong selections
make the current reviewed conclusion unavailable. Historical input remains in
collapsed audit; no successor is auto-selected. Decisions remain separate,
audit-only navigation in this reader; no gap state authorizes operational action.

Finding's optional 0.3 `presentation_source_locations` is an ordered array of
`{reading_note_ref, page?, section?}` with at least one locator. The note must
already be declared by the Finding, bind the exact source Paper or matching
family, and resolve its own exact same-family version read with date and checked
non-abstract/metadata scope. Paper-specific notes cannot be exchanged merely
because another Paper shares a family. The reader never infers claim adequacy
or locators from body/PDF text. Historical G3 previews do not require these fields.

## Normal reader

Component Research contains only exact RQ cards: literal human question, that
Component's authored reason, eligible gap cue and Open Research Question.
Existing public RQ navigation remains distinct. Draft/historical questions have
navigation only. No Paper lists, conclusions, counters or audit rows appear here.
G3 preview functions remain available independently; E9 provenance stays in audit.

Each private RA-2 RQ has one preferred generated page, in this order:

1. Research Question — literal `presentation_question`, otherwise title.
2. Why this matters — literal reasons for exact subjects.
3. Most relevant literature — Paper / Why relevant / Key finding used here /
   Important limitation / Read state / Zotero.
4. Nearest work / closest prior art — Work / Approach / What it already covers /
   Remaining difference / limitation / Competitive relevance.
5. What the literature currently establishes — selected literal statements with
   source finding, author limitation, inference/synthesis and adverse-use attribution.
6. Research conclusion — one authored block with coverage, distinction, uncertainty,
   gap cue and applicable authored rationale; no generated connective prose.
7. Next work — stored recommendation once, only when current conclusion eligible.
8. Zotero / Sources & audit — corpus link, collapsed provenance/diagnostics.

Literature membership/order is authored, with no ranking, selection, truncation
or Paper-count inference. Exact G3 contexts must already belong to their owner
and target this RQ. The owner is the Paper, its exact ReadingNote or a Finding
explicitly sourced to that Paper. Relevance requires eligible Paper/owner maturity;
ReadingNote metadata remains inspectable at any maturity. Selected Findings
must also be declared by the RQ and meet G3 review plus source-location gates.
Missing cells are unavailable/not explicitly selected; no replacements occur.
Synthesis must explicitly target the RQ and all Finding dependencies must qualify.
Own empirical results are outside this literature reader.

Nearest-work rows use only explicit eligible source Findings from that exact
Paper, with checked passage provenance. In-review comparison is qualified;
domain-accepted or attempted-reviewed comparison additionally needs current review.
A comparator need not be in the literature table. Empty rows do not imply no
prior art. SearchRecords appear only as dated exact-RQ provenance in audit;
no count, coverage, saturation, competition or gap is derived from `result_refs`.
Source corrections/retractions are visible warnings, never gap-state mutations.

Corpus pointers accept only Zotero library/group collection/search links, or
Zotero web group collection links, with positive group ID and eight uppercase
ASCII alphanumeric key, without query/fragment/extra path. Per-Paper item links
require one distinct accepted Zotero item pointer bound exactly to the Paper's
resolved G4 family by an unambiguous opaque/url binding. Version/other-family
bindings do not qualify. No source URL is relabeled Zotero.

## Fingerprints and ownership

Presentation fingerprint 1.1 uses the existing domain, adding opt-in, RQ analysis,
Finding source locations, review/search/Synthesis/Decision/Journal dependencies
and their exact consumed fields. `presentation_inputs()` is the allowlist and
canonicalization source. Set-like refs/review actors/sections/pins sort;
authored rows/statements/locations preserve order. Bodies, aliases/tags, filenames,
mtimes, annotations and arbitrary Zotero content stay excluded. Reference
fingerprint 1.0 and source-resolution fingerprint 1.0 definitions are unchanged.
No fourth fingerprint exists.

Manifest 2.15 retains the same owner/root/single writer and source payloads,
adds presentation 1.1 and the finite `research-questions/<human title>.md` route. Naming reuses the portable technical-page rules; ambiguous/reserved titles receive a durable identity suffix. Hidden metadata binds each exact path to its RQ identity.
Only 2.15 may own these safe exact manifested paths. Old manifests remain readable;
unknown/unowned/edited files and lost/invalid ownership fail before writes.
Generated metadata does not declare an authored Wiki envelope. Authored records
remain the sole scientific masters. All replacements remain atomic per-file,
manifest-last; no concurrent-editor lock or whole-tree transaction is claimed.
Check remains zero-write. Existing source-history/read-retarget safeguards remain.

## Fictional proof and G6 plan

`tests/rq_reader_fixtures.py` supplies fictional positive states and exact checked
provenance. `tests/test_rq_reader.py` proves reader layout, strict schema, stale
reviews, wrong refs, sparse/unbound/legacy states, multi-subject binding without
inheritance, body independence, source-status neutrality, Zotero ambiguity,
no uncurated comparator selection, no count-derived science and no authorization.
The compact [prototype](../../tests/fixtures/rq-reader/Reader.md) is a generated
reader derivative, not a production RQ or scientific finding.

Implementation never touches the actual synced vault. After CONTROL exact-head
source/CI acceptance, apply/check the actual vault using the supported harness;
verify no fictional records and truthful no-RQ/sparse states. Then create a separate
physical `/private/tmp/aga-rq-g6-vault` from the fictional fixture only, serialize
records with `model_dump(mode="json", exclude_unset=True)`, write the existing
private marker and fictional source catalog, and use the supported harness there.

One human journey: Component → RQ card → RQ page → literature → nearest work →
established statements → conclusion → Zotero → back. Understand the scientific
state without opening Audit. No screenshot marathon. Human G6, CONTROL review,
Program Owner merge and Issue completion remain later gates.
