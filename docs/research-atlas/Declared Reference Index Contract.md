# Declared Reference Index Contract

RA-3B adds deterministic private navigation over existing declarations. It changes
neither RA-2 semantics nor the historical 17 Direct Views / 15 capability
dispositions. This contract implements the bounded Issue #58 leaf. All examples
and test inputs are synthetic.

## Identity and input

Run the existing `fh_agent.research_atlas.private_views` CLI. Its read-only authored
scan uses RA-1 envelope discovery, skips the entire `_generated` subtree and all
authored file/directory symlinks, and must fail on unreadable input rather than
index a partial snapshot. RA-1 and RA-2 validation precede field selection.

Resolution is exact membership in `Atlas.entities` or the validated private
`wiki_id` table. The closed statuses are:

| Status | Type / revision / profile |
| --- | --- |
| `resolved-public` | Actual Atlas entity `type`; null revision/profile |
| `resolved-private` | Actual `doc_type`; RA-2 actual `record_version` / `ra2`, or null / `legacy` |
| `unresolved-external-or-missing` | Null type/revision/profile |

Duplicate private identities and public/private collisions are hard preflight
errors. Legacy targets remain visible but cannot participate in navigation.
Unknown identifiers never acquire a type from a prefix, filename, title, alias,
tag, DOI, URL or Wikilink. After existing RA-2 whitespace validation, there is no
case folding, URL/DOI normalization, fragment/version stripping or alias matching.
Two records sharing a DOI/source string are not thereby the same Paper.

Only the following existing properties on each actual RA-2 type are consumed:
`paper_refs`, `reading_note_refs`, `finding_refs`, `rq_refs`, `process_refs`,
`source_refs`, `research_direct_subject_refs`, `research_method_or_baseline_refs`,
`research_measurement_relevance_refs`, `research_project_transfer_refs`,
`research_adjacent_context_refs`. `source_refs` is consumed only for Paper,
ReadingNote and Finding. Other types' source metadata is not a literature edge.
The five roles on other RA-2 types remain audit-only.

`atlas_refs`, `wiki_refs`, `supports_refs`, `contradicts_refs`, `qualifies_refs`,
`supersedes_refs`, `overrules_refs`, `ordered_refs`, `related_version_refs`,
`decision_refs`, `search_refs`, `synthesis_refs`, `measurement_refs`, `input_refs`
and `output_refs` are not consumed. No Public Atlas relation is traversed.

Each unique source/property/validated reference produces one direct audit row.
Same-property duplicate references normalize to a sorted set; distinctions
between sources, properties, roles, directions and prerequisites remain.
RA-2 structural errors still fail before normalization can hide them.

Type checks are `match`, `mismatch`, `unresolved`, `not-constrained`.
Expected namespaces are `public:Paper` / `private:paper` for `paper_refs`,
`private:reading_note` for `reading_note_refs`, `public:Finding` /
`private:finding` for `finding_refs`, `public:ResearchQuestion` /
`private:research_question` for `rq_refs`, and `private:process` for `process_refs`.
Source and role references are not type-constrained in the audit; navigation
applies the narrower edge rules below. For example, `paper_refs: [CMP-CORTEX]`
resolves as actual public Component with `mismatch`, never Paper or unresolved.
Wrong-type and unresolved references remain valid audit data, with no expansion
and no automatic global RA-2 validation error.

Unsafe selected literals fail generically before writes: NUL/control/format
characters, absolute POSIX paths, Windows drive/UNC paths, `file:` URIs and `..`
path segments. Errors must not echo private literals or paths. HTTP(S), DOI and
URN strings stay opaque; there is no network or file lookup.

## Fixed edges and finite navigation

P means actual public Paper or private RA-2 paper; R/F/S mean private RA-2
reading_note/finding/process; Q means public ResearchQuestion or private RA-2
research_question; C means public Component. No legacy record expands.

| Edge | Actual declaration | Allowed traversal |
| --- | --- | --- |
| E1 | R `paper_refs` or `source_refs` → P | Inverse P → R |
| E2 | Private P `reading_note_refs` → R | Forward P → R, only with exact R source identity back to P |
| E3 | F `source_refs` → P | Inverse P → F |
| E4 | R `finding_refs` → F | Forward R → F |
| E5 | F `reading_note_refs` → R | Inverse R → F |
| E6 | R/F `rq_refs` → Q | Forward R/F → Q |
| E7 | Private Q `finding_refs` → F | Inverse F → Q |
| E8 | S `rq_refs` → Q | Inverse Q → S |
| E9 | Private P/R/F one of the five research roles → C/Q/S | Forward, terminal |

E2 requires the ReadingNote's validated single `paper_refs`/`source_refs` value
to resolve exactly to its Paper. Its confirming E1 forward declaration remains
in `prerequisite_refs`; failure yields `reading-source-not-matched`. It does not
make the Paper's listing authoritative over an unrelated ReadingNote.

Prefixes are exactly K0=P; K1=P→R via E1 inverse or E2 forward; K2=P→F via E3
inverse; K3=K1→F via E4 forward or E5 inverse. Recipes are exactly:

| Family | Permitted suffix |
| --- | --- |
| N-C | K0/K1/K2/K3 + terminal E9 to C |
| N-Q | K1 + E6; K2/K3 + E6 or E7; K0/K1/K2/K3 + terminal E9 to Q |
| N-P | An N-Q ending in E6/E7 + inverse E8; K0/K1/K2/K3 + terminal E9 to S |

Maximum path is P→R→F→Q→S, four traversed edges. There is no recursive walker,
BFS/DFS, transitive closure, fifth hop, cycle, Q/Process role expansion,
Component-parent rollup or expansion after E9. Co-occurring Paper/Process lists
on a Dossier/Topic/Thread never authorize a join. No ranking, top-k, sampling or
silent truncation is permitted.

Every edge preserves the actual declaring identity, revision, type, property,
role and direct target. Inverse E8 still says **Process declares `rq_refs` to Q**;
it never invents a Q `process_refs` declaration. Roles belong to the declaring
P/R/F record, never to the Paper anchor by inheritance.
`research_method_or_baseline_refs` remains the combined role verbatim; it cannot
classify Method, Baseline, context or evaluated comparator.

No path asserts reading, checking, support, scientific relevance, authorship,
implementation evaluation, causality, coverage, novelty, gap, exhaustion,
evidence quality, Finding acceptance or Decision acceptance.

## Closed YAML schema and provenance

Private payload: `indexes/declared-reference-index.yaml`. Top-level keys are
exactly `index_schema_version: "1.0"`, `generated_by: research-wiki-derived`,
`source_repository: Planton361/autonomous-game-agent`, `source_commit` (40 lower
hex characters), `source_atlas_schema`, `private_input_fingerprint` (64 lower
hex characters), and `rows`. `source_atlas_schema` is exactly `"0.2"` or
`"0.3"`, copied from the shared validated Registry version envelope; the three
Registry files must agree. The current public Registry uses `"0.3"`; legacy
`"0.2"` content remains valid only without Function nodes or
`contributes_to_function` relations. This provenance field is independent of
private Research record schemas and fingerprints, so a source-version change
alone requires no private-record migration.

Each closed row has exactly:

```text
row_id, row_kind, source_wiki_id, source_record_version, source_doc_type,
originating_property, originating_role, navigation_start, navigation_view,
recipe, target_identifier, target_resolution_status, resolved_target_type,
target_record_version, target_profile, expected_target_types, type_check,
path_eligible, diagnostic_codes, path_kind, via, prerequisite_refs
```

`row_kind` is `declared-reference` or `navigation-path`. Audit rows are retained
in addition to navigation rows. Audit `navigation_start`, `navigation_view` and
`recipe` are null; navigation views are `component`, `rq`, `process`. Recipes
serialize family/prefix/ordered edge IDs and directions. `path_kind` is `direct`
only for a single forward edge, otherwise `derived`. `source_*` and
`originating_*` refer to the final edge's actual declarer. For inverse navigation,
`target_*` describes the traversal destination, while `expected_target_types`
and `type_check` describe the final **declared** reference preserved in `via`.

An identity descriptor contains exactly `identifier`, `resolution_status`,
`resolved_type`, `record_version`, `profile`. `navigation_start` and each
traversal endpoint use this descriptor.

Each `via` and `prerequisite_refs` edge contains exactly:

```text
edge_id, declaring_wiki_id, declaring_record_version, declaring_doc_type,
property, role, declared_target_identifier, declared_target_resolution_status,
declared_target_type, declared_target_record_version, declared_target_profile,
traversal_direction, traverse_from, traverse_to
```

Directions are `forward` or `inverse`. Edge IDs are E1–E9, or `A:<property>` for
an audit-only declaration from the closed property allowlist. Prerequisites use
the same representation, retain their direction and are not traversed hops.
Closed diagnostics are `unresolved-reference`, `wrong-target-type`,
`legacy-target-not-expandable`, `outside-path-allowlist`,
`reading-source-not-matched`.

`row_id` is lowercase SHA-256 of the full row without `row_id`, using compact,
sorted-key, UTF-8 JSON with `ensure_ascii=False` and no trailing newline. Do not
include a global fingerprint, timestamp or path in the row ID. Distinct full
rows with the same hash fail before writes; sort final rows lexically by hash.
No titles, authors, body snippets, timestamps or scientific scores are emitted.

## Structured fingerprint and locators

Fingerprint schema `1.0` hashes the following canonical JSON (same encoding as
row IDs): `{"fingerprint_schema_version":"1.0","records":records}`. Records
sort by `wiki_id`. Each includes `wiki_id`, `doc_type`, `profile`,
`record_version`; legacy uses null revision and has no reference map. Each RA-2
record additionally includes `references`, containing its consumed properties,
including empty arrays, each `sorted(set(validated_values))`.

Body, title, aliases, tags, filenames, paths, mtime, `atlas_refs`, maturity,
review state, question stage, decision state and unconsumed bibliography are
excluded. Relevant identity/type/profile/revision/reference changes and record
addition/removal change the fingerprint. A body-only edit without revision/ref
changes leaves fingerprint and YAML bytes unchanged. Validation still runs over
the full RA-2 record, including excluded properties.

The separate validated `wiki_id` → vault-relative Markdown locator map is for
rendering only. Public links use the RA-1 ID-only `private_path` mapping. Link
segments are percent-encoded; references never become raw link targets.
Unresolved identifiers remain escaped plaintext, without automatic HTTP/file
links. Escape Markdown table/link/backtick and HTML-sensitive syntax. No private
absolute path is serialized. Moving a private note changes Markdown links and
manifest digests but not fingerprint/YAML; moving the whole vault with relative
locators unchanged changes no bytes.

## Owner, migration and safety

`private_views.py` remains the only writer/CLI, owner `research-wiki-derived`,
root `_generated/derived/`, manifest `manifest/direct-views.yaml`.
`private_reference_index.py` is pure typed logic/rendering with no writes or CLI.
V2.1 owns exactly eight payloads plus its manifest:

```text
bases/Technical Atlas Views.base
bases/Research Wiki Direct Views.base
indexes/Direct Views Index.md
indexes/declared-reference-index.yaml
indexes/Declared Literature Navigation.md
indexes/Research Knowledge Home.md
workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL.md
workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER.md
```

That is the original v2.1 payload set. W02 extends the manifest to v2.2 for the
finite Technical Hierarchy; W04 extends it to v2.3 for the shared Component Hub
views; W05 extends it to v2.4 for the finite technical detail maps. The two
human-first workbench paths remain the Overview entries. W04 adds only these
four exact child paths:

```text
workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL/Technical.md
workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL/Research.md
workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER/Technical.md
workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER/Research.md
```

The current writer accepts manifest `view_schema_version` `1.0`, `2.0`,
`2.1`, `2.2`, `2.3` and `2.4`. V2 adds
`reference_index_schema_version: "1.0"` and `private_input_fingerprint`; v2.1 adds
an explicit ownership class and semantic digest for each Obsidian-managed Base,
while retaining source repository/commit/Atlas schema, Base source digests and
owned-file byte digests. The manifest never owns itself. Valid v1/v2.0/v2.1/v2.2/
v2.3 states regenerate in place as v2.4; their `--check` reports drift/exit 2
with zero writes. Unknown versions fail closed. V1 cannot own YAML or K3
workbench payloads. V2.0–v2.2 may own only the exact declared-reference YAML
path and the original fixed K3 paths; v2.2 also owns the fixed hierarchy entry
and its stable-ID-shaped hierarchy notes. V2.3 additionally accepts only the
four W04 Hub child paths listed above; it never owns an arbitrary Hub subtree.
V2.4 additionally accepts only the fourteen W05 detail-map files for the seven
bounded technical IDs; it never owns an arbitrary detail subtree. Prior v2
manifests may additionally name only the two retired W01 ID-first workbench
paths for owner-and-digest-validated cleanup. Those paths are never emitted as
compatibility files. Historical prior-owned Base/Markdown paths remain eligible
only for the same fail-closed cleanup.

Before the first write: validate derived boundary/symlinks and prior manifest;
run RA-1 `technical_projection(..., check=True)` for topology, marker, source-ref
== HEAD, relevant source cleanliness, Registry/RA-2 validity and exact projection;
scan authored inputs; build all output in memory; validate every target, owner,
unknown file and path. Never repair RA-1 implicitly. Markdown owner frontmatter
remains mandatory; YAML requires the exact owner and index schema `1.0`. The two
`.base` paths are explicitly Obsidian-managed projections: v2.1 validates their
manifest-recorded semantic digests while normalizing only YAML presentation and
documented note-property shorthand in property selectors. Meaningful Base edits,
lost strict-output owners and unknown/unowned files fail closed and are never
adopted. Edited obsolete files are not deleted. Cleanup uses only validated prior
ownership.

`--check` compares class-B payloads byte-exactly and the two class-C Bases by their
narrow canonical semantics, without mkdir, temporary files, replace, unlink,
cleanup or manifest rewrite. Accepted state is 0; drift/configuration/validation
is 2. Empty or unresolved-only indexes are valid.
Writes use per-file atomic replacement and manifest last. Require one writer
and stable inputs; there is no whole-tree transaction or concurrent-editor lock.
Interrupted first generation may require preserving unowned outputs before retry.

## Views, privacy and deferred work

The private Markdown renders all navigation rows in exactly three tables:

- Literature by Component — declared role paths (derived navigation)
- Literature by RQ — declared reference paths (derived navigation)
- Literature by Process — declared reference paths (derived navigation)

Each table carries this local warning:

> Declared reference paths only. Roles belong to the named declaring record and are not inherited by the paper. These paths do not establish support, implementation evaluation or literature coverage. An empty view means no matching declared paths in this snapshot.

Display Paper identity/resolution, target/type, actual declarer/revision,
property/role, direct/derived kind, complete via/prerequisites and row ID. A
Direct Reference Audit displays every audit row, including wrong-type and
unresolved declarations. No scientific deduplication or aggregate Paper evidence
count. The existing Direct Views Index links the navigation and describes the
structured index as navigation/audit without scientific adjudication.

These are technically resolved navigation views for the finite recipes, not
scientifically complete Literature Coverage. Historical Direct Base and
Capability Matrix remain unchanged. Candidate History and Decision Lineage are
explicitly deferred: `record_version`, scan/file order, `supersedes_refs` and
`overrules_refs` do not create authoritative history or “latest decision wins”.
No new RA-2 history property or status promotion is provided.

All selected private identities and rows remain only in the private vault.
No body/title, legacy opaque extras, ordinary note content or attachments enter
outputs. No private rows are committed. Public Repository contains only code,
synthetic tests and public definitions/docs. Public Atlas/Registry, Canonical/SOT,
Runtime and Agent Memory/Retrieval/Cortex remain isolated. No network dependency,
new dependency, Zotero, corpus population, RA-4, D7, gameplay or input is involved.

Acceptance coverage is A01–A20/A27 in the pure-index tests, A14–A26 in writer
integration tests, a synthetic committed-repo CLI lifecycle, and A28 through the
unchanged RA-1/RA-2/RA-3A/Atlas regression suites. No real private vault is tested.

## RM-3 G2 Interface pilot — current index 1.1 / view manifest 2.11

Issue #120 and CONTROL amendment
[5932696558](https://github.com/Planton361/autonomous-game-agent/issues/120#issuecomment-5932696558)
supersede the historical Component-only terminal boundary above only for this
pilot. Accepted #105 disposition
[5839496369](https://github.com/Planton361/autonomous-game-agent/issues/105#issuecomment-5839496369)
provides the semantics. No public Registry, Atlas schema 0.3, RA-2 field or
canonical/protocol change is needed.

### Terminal eligibility and finite representation

E1–E8 and existing N-C/N-Q/N-P recipes remain unchanged. E9 additionally admits
exact public identity `IF-MEM-CORTEX` only when its resolved Registry type is
`Interface`. Another Interface is outside this pilot; an identifier prefix does
not establish type. A wrong actual type at the pilot ID fails closed. Unresolved
references remain diagnostic audit data. The existing role-reference audit type
check remains unconstrained; unsupported resolved role targets retain
`outside-path-allowlist`, never an eligible N-T path.

The closed generated index advances to `index_schema_version: "1.1"`, adding
only `navigation_view: technical` and family `N-T`. No row/edge/identity fields
are added. Exactly these finite recipes are accepted:

| Prefix | N-T recipe suffix |
| --- | --- |
| K0 | E9 forward |
| K1 | E1 inverse or E2 forward; then E9 forward |
| K2 | E3 inverse; then E9 forward |
| K3 | E1 inverse or E2 forward; E4 forward or E5 inverse; E9 forward |

Every suffix ends at the exact Interface. The maximum N-T path has three hops;
the existing global maximum remains four. Typed prefix declarations, ordered
contiguous endpoints, actual terminal owner/role/type/target, cycle rejection and
E2's exact E1 confirmation are validated. Invalid finite N-T recipes fail before
projection. E9 cannot be extended even through the internal path builder. There
is no recursive walker, arbitrary BFS/DFS, transitive Research closure, role
inheritance or semantic traversal after E9.

All five existing roles remain literal and complete: `research_direct_subject_refs`,
`research_method_or_baseline_refs`, `research_measurement_relevance_refs`,
`research_project_transfer_refs`, `research_adjacent_context_refs`. In particular,
method/baseline remains combined and measurement relevance establishes no
measurement validity. No role is inferred from another role or from navigation.

### Primary direct presentation and bounded related display

The existing preferred Interface Identity Page displays **Directly attached
Research**. It selects every eligible exact authored E9 audit declaration from
private Paper/ReadingNote/Finding, independently of Paper-anchor resolution.
Thus an unresolved source does not hide an otherwise exact Interface declaration
or fabricate a literature path. Matching N-T navigation paths are separately
shown with their full ordered provenance and prerequisites. A derived Paper
navigation path does not change the directly authored attachment's owner.

Each displayed attachment preserves the declaring private record, its type and
revision (the exact role owner), verbatim role/property, original target
`IF-MEM-CORTEX`, type `Interface`, resolution, terminal declaration and audit row
ID. Each matching N-T path preserves recipe, path kind, row ID, every ordered
`via` descriptor and E2 prerequisite. Authored body/editor metadata is not mined
to invent an owner or a scientific claim.

The existing Memory Retrieval preferred page displays the same declarations only
as **Related technical-scope Research**, gated by the independent exact Registry
triple `CMP-MEM-RETRIEVAL --supplies--> IF-MEM-CORTEX`. It displays that relation
separately, links to the same preferred Interface, and retains the original
Interface target and role. Removing that triple removes the related display but
changes neither E9 nor the private reference fingerprint. No Research record →
Memory Retrieval attachment is generated. No second preferred page is created;
W05 and existing Hub child views remain auxiliary.

No parent Component, `part_of` ancestry, Function membership, Domain, legacy
Assembly, folder, backlink or graph proximity propagates Research relevance.
Unrelated preferred pages retain their neutral Research state and existing
routes. Native Markdown preserves the complete facts and links without CSS or
Mermaid. Empty states describe only this snapshot, never literature absence,
novelty, gap, completeness or scientific weakness.

ResearchQuestion ↔ technical-subject many-to-many targeting from accepted #137
remains a separate RM-3 contract. This pilot adds no RQ target field and does not
satisfy or infer that requirement. Technical existence, implementation provenance
and Research declarations remain separate from accepted scientific evidence.

### Ownership, fingerprints and privacy

The current manifest is `view_schema_version: "2.11"`, with
`reference_index_schema_version: "1.1"`. It owns precisely the same finite paths
as 2.10; there is no new file, subtree, preferred route, writer or owner. Valid
historical 1.0–2.10 manifests retain their original closed reference-version and
path checks. Index owner markers accept only historical 1.0 or current 1.1;
Identity Page v1.1 owner markers likewise admit those two reference versions,
retaining exact path/ID/type binding. Unknown versions/owners fail closed.
Write mode regenerates validated generated output; check mode reports migration
drift without directories, temporary files, replacement, cleanup or writes.
Authored records require no migration and remain byte-preserved.

The structured private fingerprint remains schema 1.0 and hashes the same
validated identity/type/profile/revision/reference sets. New terminal eligibility
changes generated rows, not authored input selection or fingerprint semantics.
Relevant role/target/revision changes affect the fingerprint; body/title-only
edits do not. Locator changes affect Markdown/manifest bytes, not YAML or the
fingerprint. Input/Registry order does not affect bytes. Public technical
relations affect the related view through existing Registry revision provenance,
never by entering private Research edges or the private fingerprint.

Only synthetic private fixtures prove this pilot; they assert no real reading,
literature evidence, scientific claim or gap. Private projection remains
export-denied. Public rendering has no private input path. No private vault was
applied during implementation; actual-vault G6 requires subsequent CONTROL
exact-head review and authorization. Registry hierarchy, Function identities and
memberships, `part_of`, `contributes_to_function`, engineering-provenance panels,
compatibility routes and canonical/protocol sources remain unchanged.
