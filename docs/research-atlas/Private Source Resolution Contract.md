# Private SourceFamily / SourceVersion resolution

Authority: [Delivery #123](https://github.com/Planton361/autonomous-game-agent/issues/123),
accepted [G4 #107 / Program Owner 5840663686](https://github.com/Planton361/autonomous-game-agent/issues/107#issuecomment-5840663686),
and [CONTROL release 5942152560](https://github.com/Planton361/autonomous-game-agent/issues/123#issuecomment-5942152560).
This extends source inspection only. RA-2 fields, G3 scientific presentation
eligibility, RA-3B index 1.2/E1–E9, technical hierarchy and public Registry stay
unchanged. The Human-First Reader remains the normal reading surface.

## One private authored input

The supported Workspace harness optionally reads precisely
`<private-vault>/.research-source-catalog.json`. It never searches directories,
reads another filename, substitutes a Zotero projection, or populates a catalog.
Absent input means **Project source catalog unavailable**. An explicitly empty
catalog means no families declared in this snapshot. Neither implies literature
absence, evidence quality, novelty, a gap or search completeness.

The catalog is private/export-deny, operator-authored structured source metadata.
It is not a second bibliographic/PDF manager or another editable Paper identity.
Public repository fixtures are fictional acceptance inputs only. Real catalog
contents must never be committed or supplied to public rendering/export.
The catalog and all generated projections are separate from RA-4A adapter data.

All models are strict, closed and versioned. Reject unknown keys/types, duplicate
JSON keys, nonfinite values, duplicate project IDs, dangling binding targets,
missing/dangling family membership and malformed/self/cross-family/duplicate
version relations before derived writes. Reject symlinks/nonregular inputs,
control/format text, absolute paths, file URIs and traversal. Errors do not echo
private paths/values. No arbitrary metadata/body/annotation dictionary exists.

| Model | Exact fields |
| --- | --- |
| Catalog | `source_catalog_schema_version: "1.0"`, `privacy: private`, `export_policy: deny`, `families`, `versions`, `bindings` (default empty) |
| SourceFamily | `source_family_id`, `title`, optional `bibliographic_label`, optional `preferred_version_ref` |
| SourceVersion | `source_version_id`, exactly one `source_family_ref`, `label`, `kind`, `status` (default unknown), `availability` (default unknown), optional `locator`, `relations` (default empty) |
| VersionRelation | `relation`, `target_version_ref` |
| ExactBinding | `scheme`, `value`, `target_ref` |
| SourceLocator | optional `url`, `page`, `section`; at least one required |

IDs use `srcf-` or `srcv-` followed by lowercase alphanumeric segments separated
by hyphens. They are opaque **persisted authored identities**; the generator
never allocates or derives them. Metadata, title, authors, DOI, URL, date,
citation/Zotero keys, attachment identity, filenames, file bytes and mtime never
establish identity or membership. Labels can change without changing identity.
Each version directly declares an existing `srcf-*`; an alias is not membership.

Kinds: `preprint`, `revised_preprint`, `accepted_manuscript`, `published`,
`correction`, `erratum`, `other`. Directed relations: `revision_of`,
`published_from`, `corrects`, `erratum_for`, `supersedes`. They point from the
version declaring the relation to a distinct, existing, same-family version.
No date or bibliographic similarity creates a relation. The reader preserves
that direction, e.g. Published version — published from → Preprint v1.
Supersession establishes no scientific invalidation.

`status`: `available`, `unknown`, `withdrawn`, `retracted`.
`availability`: `available`, `not_locally_available`, `attachment_unavailable`,
`unknown`. Availability is separately authored; it is not tested by opening files
or requesting URLs. Locators are human positions and/or explicit HTTP(S) URLs
without credentials. A source link opens precisely that declared locator; it
never chooses another file/version. No local attachment path is accepted.

## Exact resolver and provenance

Direct project ID lookup and external bindings share an exact lookup index:

- zero exact matches → `unresolved`, no target;
- exactly one match of the requested type → `resolved`;
- multiple exact matches → `conflict`, no selected target;
- wrong type or contradictory contextual family → `rejected`, no target.

Duplicate bindings conflict even when both name the same target. Candidate refs
are sorted for audit only. A version from another family cannot become a read or
related version. Missing/unresolved versions remain explicit diagnostics.
Malformed catalog structure blocks import; valid conflicting alias declarations
remain inspectable diagnostics and cannot authorize a resolved binding.

Binding schemes are `doi`, `arxiv`, `openreview`, `url`, `citation_key`, `opaque`.
For the first five, the lookup literal is exactly `scheme:value`; for `opaque`,
it is exactly `value`. No trimming, casefolding, DOI/URL normalization, fragment
stripping, title matching, fallback chain, first/newest/nearest choice or Zotero
ancestry occurs. `doi:10.9999/example` is distinct from `10.9999/example` and
`doi:10.9999/EXAMPLE`. An authored Paper's DOI/URL is not automatically a binding.
Opaque aliases cannot shadow scheme namespaces, project IDs or adapter IDs.

Paper's existing `source_refs` binds one exact family. More than one distinct
family reference is diagnosed and rejected, without changing RA-2 authoring
validation. `related_version_refs` binds exact same-family known versions; it
never means that those versions were read. The source resolver adds no Research
edges to the existing Declared Reference Index.

ReadingNote keeps its exact-one `paper_refs XOR source_refs` relationship.
A Paper reference resolves only to the exact existing RA-2 Paper and that Paper's
explicit family binding. `source_refs` can also bind an exact family directly;
its existing exact Paper-reference usage remains supported. `version_read`
resolves separately to one exact same-family version, never to a preferred
version. No reading provenance or authored bytes are rewritten. An unresolved
legacy version literal is retained in Audit with an explicit reader diagnostic,
without inventing a resolved identity. Existing checked reading requirements,
read depth/date/sections and scientific eligibility remain unchanged.

Optional `preferred_version_ref` is solely an explicitly authored default for
Workspace navigation/presentation. Missing preference, unresolved/conflicting
lookup, wrong type or cross-family version produce visible diagnostics and no
fallback. A resolved retracted/withdrawn preference remains explicitly authored
and warned, with no silent replacement or endorsement. No `current_known_version`,
chronological default, best evidence or inferred publication-of-record exists.
Preference never changes the version read or automatically invalidates a note.

Correction/erratum kinds and explicit incoming correction/erratum/supersession
relations create metadata diagnostics. Retractions/withdrawals preserve historical
navigation. No status edit changes Finding review state, Finding/Claim status,
Decision, publication wording or source substitution. Scientific consequences
remain a separate authorized Review/Evaluation/claim-authority action.

## Human-first reader and audit

The existing Paper preview and W10 Literature Inspection use human Paper titles,
source-family labels, exact **Version read**, compact other-known-version links,
separate **Preferred for navigation**, status/warnings and declared exact locators.
The source family and exact version links open **Source details**, where human
headings show lineage, preferences, status and reciprocal Paper/ReadingNote
navigation. The older version remains reachable without opening raw Audit.
Duplicate human headings are disambiguated with a secondary stable identity;
labels never decide resolution. No additional Paper or editable master is created.

W10 retains every accepted literal RA-2 structured field inside collapsed native
record audit. Source details retain the full normalized catalog, exact IDs,
aliases, resolver outputs, source commit and fingerprint in a collapsed native
`aga-audit` block. Normal Component pages contain no new alias tables or resolver
metadata wall. The private reader derivative retains human source/version links
and excludes the complete audit. Native Markdown is sufficient; no plugin or
Graph is required. These source displays are not scientific summaries.

## Separate fingerprint and finite ownership

`source_resolution_fingerprint_version: "1.0"` versions the separate
`source_resolution_input_fingerprint`. Canonical sorted-key compact UTF-8 JSON
contains the normalized closed catalog actually consumed by the source
resolver/index/inspection and the selected Paper/ReadingNote binding inputs:

- Paper: `wiki_id`, `doc_type`, sorted distinct `source_refs`,
  sorted distinct `related_version_refs`;
- ReadingNote: `wiki_id`, `doc_type`, sorted distinct `paper_refs`/`source_refs`,
  literal nullable `version_read`.

Catalog families/versions sort by opaque ID; relations sort by relation/target;
bindings sort by scheme/value/target. Duplicate aliases are retained so conflicts
cannot disappear through deduplication. Equivalent reordering gives identical
fingerprints/index/generated bytes. Catalog labels, status, membership, bindings,
relations, preference, availability and locators are structured consumed source
projection inputs. Relevant edits change this fingerprint and/or exact view
bytes. Bodies, annotation prose, RA-2 bibliography/title/review state, unrelated
metadata, local paths, filenames and mtimes are excluded. Unknown catalog extras
are rejected rather than silently hashed. Existing `private_input_fingerprint`
and `presentation_input_fingerprint` retain exactly their old definitions.

Direct-view manifest **2.14** adds only the two source fingerprint fields and
these two fixed strict-byte payloads under the existing `research-wiki-derived`
owner, root and single writer:

```text
indexes/source-resolution-index.yaml
indexes/Source Details.md
```

The closed source index includes normalized private catalog, exact record
bindings, family preferences and exact alias resolutions. Only 2.14 may own
these two paths; an older manifest cannot adopt them. No wildcard source folder,
public Registry schema/relationship or new writer exists. Historical accepted
1.0–2.13 generated ownership migrates through the existing bounded checks.
`workspace check` reports migration/input drift with zero writes. Edited source
payloads, lost owners, unknown/unowned files, unsafe paths and malformed prior
source indexes block before derived writes. Authored notes/catalog bytes stay
untouched. Per-file atomic replacement and manifest-last behavior are unchanged;
there is no whole-tree transaction or concurrent-editor lock.

Prior catalog families/versions must remain explicitly catalogued. A version
cannot silently move to another family. Removing a prior catalog, family or
version blocks rather than pruning historical provenance. Status/preference/
labels can be explicitly edited. Missing history index may be rebuilt only when
its bytes exactly reproduce the prior manifested digest; otherwise restore it.
This is historical source navigation safety, not automatic scientific review.
The Workspace harness still restores only generated roots, not authored inputs.

## RA-4A and privacy boundary

RA-4A is unchanged, fixture-only, offline, and supplies no fallback catalog.
`zsrc-*`, `zsv-*`, `zatt-*` remain adapter/projection identities. This Delivery
supports no adapter binding or real Zotero integration. A future adapter needs
its own accepted explicit binding contract. No real API, SQLite, credentials,
PDFs, annotations, source import or Research execution is performed.
Public Atlas/workspace rendering receives no private catalog; no public export
path is added. No canonical/protocol, runtime, Component/Function, RQ/gap, Graph,
W12, Claim or publication work is authorized.

## Synthetic proof and safe human G6

Committed `tests/fixtures/source-resolution/catalog.json` and
`tests/source_resolution_fixtures.py` supply fictional human-readable sources,
two families/four versions, exact aliases, a deliberate collision and cross-family
preference, one older-version ReadingNote, a different preferred version,
correction/retraction/withdrawal/supersession, and unresolved Paper references.
They are technical acceptance data, never scientific evidence.

Implementation never applies these fixtures to the actual synced Research vault.
After CONTROL exact-head source/CI acceptance and human G6 authorization:

1. Actual synced vault: supported `workspace apply` then `workspace check`.
   Where no real project catalog is authored, inspect truthful unavailable/empty
   source state. Confirm no synthetic source titles or IDs appear.
2. Disposable synthetic vault: use a new physical path such as
   `/private/tmp/aga-source-resolution-g6-vault`, outside the repository and synced
   vault. Copy only the committed fictional catalog and the helper's synthetic
   records (serialize `model_dump(mode="json", exclude_unset=True)` to Markdown
   frontmatter), plus the existing private marker. Then use the same supported
   harness with that explicit `--vault-root`. Do not copy actual private data.
3. One human journey: Paper preview on Observation Builder → source family →
   Preprint v1 actually read → Published version explicitly preferred → directed
   lineage/status/correction/retraction warning → return to Paper/ReadingNote.
   Confirm **Version read** differs visibly from **Preferred for navigation**
   without opening raw Audit. No screenshot marathon; no real reading claim.

G6, CONTROL acceptance, user merge and Issue closure remain subsequent gates.
