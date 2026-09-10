# Private Research Wiki Projection

RA-1 projects the public Git/YAML Research Atlas into a physically separate private
Obsidian vault. `docs/research-atlas/registry/` remains the authoritative technical
source; generated notes are disposable views. No editable Registry copy is exported.

## Operator setup and CLI

Create the private vault yourself, outside the public checkout. Neither root may
contain the other. The projector requires an existing `.research-wiki-private`
file at the vault root, with this YAML:

```yaml
research_wiki_private_version: "1.0"
project: Planton361/autonomous-game-agent
```

Supply the absolute vault directory through `PRIVATE_VAULT` in your local shell;
the command below contains no actual private location. From the repository root:

```bash
uv run --no-sync python -m fh_agent.research_atlas.private_projection \
  --repo-root . --vault-root "$PRIVATE_VAULT" --source-ref HEAD
```

Append `--check` to validate the exact generated state and declared private
references without writing files, temporary files, directories, or the manifest.
Exit status is `0` for success, `2` for expected configuration/validation/drift
errors; unexpected faults propagate as ordinary failures. Expected errors appear
briefly on stderr. The projector does not create a vault or its marker.

`--repo-root` must be the actual Git worktree root. `--source-ref` resolves locally
to a full 40-character commit and must equal checked-out `HEAD`. Both
`docs/research-atlas/registry/**` and `src/fh_agent/research_atlas/**` must be clean,
including staged and untracked changes. Unrelated repository dirt is permitted
and preserved. Commit the projector before using it against its own checkout.
No network is required for projection.

## Generated ownership

Only `_generated/technical-atlas/` belongs to this generator:

```text
manifest/projection.yaml
records/<ATLAS-ID>.md
evidence/<EVID-ID>.md
system-map/System Anatomy.excalidraw.md
indexes/atlas-id-index.yaml
indexes/Technical Atlas Index.md
```

Paths use stable public IDs; names appear in frontmatter, headings, and aliases.
Internal WikiLinks use vault-relative paths beneath the generated root, including
the System Anatomy element links. The map preserves the public map's semantics.
The ID index resolves current public identities; it is not another Registry.

The deterministic manifest records the source repository, full commit, Atlas
schema `0.2`, exact-byte SHA-256 digests of all three Registry files, record and
Evidence counts, and each owned output's digest. Generated notes carry source
provenance and a digest of the public record's sorted JSON representation; the
map carries the public rendered map's digest. Neither timestamps nor private
absolute paths are included.

Topology, symlinks, marker, source state, prior manifest, authored envelopes, and
all output targets are validated before writes/deletes. Symlinked ownership
boundaries or descendants are rejected. Manifest paths must be normalized,
relative, and contained within the generated root. Unknown files cause an error;
they are never silently overwritten or pruned.

Cleanup considers only obsolete files listed in a valid prior manifest. Their
embedded owner and identity must still match, and their bytes must match the
prior digest before deletion. Edited obsolete files must first be preserved by
the operator. Current generated files with intact owner/identity metadata can be
regenerated to repair content drift. Keep authored content in separate notes.
Each write uses a temporary file in the destination directory and atomic replace;
the manifest is written last. Empty directories are not recursively pruned.
Everything outside the generated root remains authored/unowned and unchanged.

## Minimal private authoring envelope

An authored Markdown note may declare:

```yaml
wiki_schema_version: "0.1"
wiki_id: PROC-EXAMPLE-001
doc_type: process
privacy: private
export_policy: deny
atlas_refs: [CMP-CORTEX]
```

The closed type/prefix mapping is `dossier/DOS`, `process/PROC`, `topic/TOPIC`,
`reading_note/READ`, `synthesis/SYN`, `search_record/SEARCH`,
`journal_entry/JOURNAL`, `paper/WPAPER`, `finding/WFIND`,
`research_question/WRQ`, `experiment_lead/WLEAD`, `research_thread/WTHREAD`,
and `decision_draft/WDEC`. IDs must be unique and match their type's prefix,
followed by uppercase alphanumeric segments separated by hyphens. A private
record cannot declare `atlas_id`; `atlas_refs` resolve only against current public
Atlas IDs. Privacy must be `private` and export policy `deny`.

Notes without a declared Wiki envelope remain unmodeled. Without
`epistemic_schema_version`, an envelope remains **RA-1 legacy only**: other
authored properties stay opaque, with no new scientific requirements, implied
review or automatic migration. Private frontmatter never selects an output
filename. Symbolic links in the authored tree are not followed or modeled.

## RA-2 explicit epistemic profile

To opt in, add these fields to the RA-1 envelope, plus the class-specific
properties from the corresponding [Wiki Templates](Wiki%20Templates/) source:

```yaml
epistemic_schema_version: "0.1"
title: Example
record_version: 1
document_maturity: draft
```

The 13 templates are public-safe copy sources, not operative records. Replace
placeholders in a separately authored private note. Their example YAML is in
code blocks, not active frontmatter. Template properties are flat; scientific
arguments, exact source versions/locators and B0/B1–B13 review sections stay in
the body. No private corpus is imported or populated by these sources.

Both write mode and `--check` validate the closed flat RA-2 contracts through the
existing `validate_wiki_records` call. `record_version` is a strict positive
integer; unknown profile properties, including pseudo-confidence, maturity and
exhaustion scores, fail closed. Legacy notes retain their tolerant behavior.
An opt-in record must still declare its RA-1 envelope: the vault scanner discovers
authored notes through `wiki_schema_version` or `wiki_id`, not a standalone
epistemic property. No-envelope notes remain outside projection validation.

ReadingNotes distinguish source identity, read version/date and actual checked
sections; there is no monotonic reading ladder. Findings separate claim origin
and review state. Only private ResearchQuestion/ExperimentLead carry candidate
stage/state; a non-`none` decision needs Decision refs and `accepted` requires
`candidate`. A recorded Decision needs authority refs. These are structural
checks, not proof that a source was read, a Finding accepted or a Decision made.
Scientific body adequacy, sound inference, actual authority and lifecycle
transitions remain human SCI/Program Owner review responsibilities. `--check`
does not become a scientific acceptance gate and still performs no writes.

Document maturity, reading verification, candidate decisions and public technical
verification remain independent. The five research-role lists imply no other
role, `supports`, `part_of`, causal or implementation evidence. Public Atlas
schema remains `0.2`; its validator allows non-null `research_direction` only on
`ResearchQuestion` and `ExperimentLead`, never Thread or technical records.
There is no automatic private-to-public status mapping or promotion.

Material changes require an explicit new revision and human review; material
Finding changes require human reset of the new revision's review state to draft.
Superseded document maturity needs non-empty `supersedes_refs` lineage, with
predecessor/replacement direction and exact versions explained in the body.
This tooling does not judge that lineage or create an archive. Completed
SearchRecords and recorded Decisions must not be silently rewritten; historical
Public Evidence remains unchanged. A scoped candidate kill never marks a
Component, Topic, Method, Paper area or whole research direction exhausted.

## One-way boundary and limitations

There is no reverse sync, private-to-public export, Canonical/SOT update, or
Wiki-to-Agent-Memory/Retrieval/Cortex/runtime path. RA-1 reads private notes to
validate the envelope and explicitly opted-in flat profile. RA-3B additionally
consumes only the structured reference allowlist for private navigation/audit.
Neither feeds public rendering or alters technical ancestry. The public workspace
generator accepts no private-vault input.

Run one projector at a time with a stable source checkout and vault. This is a
local filesystem workflow, not a transaction across concurrent editors or hostile
filesystem mutation. An interrupted multi-file generation can leave drift;
atomic replacement protects individual files, not the whole tree. A first run
interrupted before its manifest may require operator recovery of unowned outputs.
Structural map tests do not claim an interactive Obsidian/Excalidraw plugin test.
Arbitrary graph traversal, corpus migration, real Zotero integration, Work
automation, gameplay and real input remain outside these projection tools.

## Historical RA-3A direct views and Process navigation

The public Base now calls its unchanged Component/unmapped filter **Atlas Mapping
Incomplete**. This means missing Atlas mapping, not missing literature or a gap.

First generate/check the RA-1 technical projection at the current committed HEAD.
Then, with the same local PRIVATE_VAULT variable and source-ref:

```bash
uv run --no-sync python -m fh_agent.research_atlas.private_views \
  --repo-root . --vault-root "$PRIVATE_VAULT" --source-ref HEAD

uv run --no-sync python -m fh_agent.research_atlas.private_views \
  --repo-root . --vault-root "$PRIVATE_VAULT" --source-ref HEAD --check
```

The separate owner `research-wiki-derived` owns exactly
`_generated/derived/`. Historical RA-3A manifest v1 had these outputs:

```text
manifest/direct-views.yaml
bases/Technical Atlas Views.base
bases/Research Wiki Direct Views.base
indexes/Direct Views Index.md
```

Every invocation first checks the existing RA-1 technical projection without
writing it, including declared RA-2 structural contracts. If it is missing or
stale, regenerate it explicitly first. Marker, non-nested physical roots, source
HEAD and RA-1 clean-source requirements are unchanged. Additionally the committed
public Base, Wiki Views and Process Seeds sources must be clean (staged/untracked
included). Both Base inputs must be tracked regular files without symlink boundaries.
Unrelated dirt is allowed and never modified. No network is needed.

The technical Base preserves the public views and restricts the dataset to
`_generated/technical-atlas`. The direct Wiki Base uses only declared flat RA-2
Properties outside `_generated`: 12 class/status inventories and five independent
role-presence views. Public-safe templates/seeds contain example blocks, not
active frontmatter. Ordinary Markdown, RA-1 legacy records and generated technical
records are excluded. Views display declarations, not verified scientific facts.

The historical v1 manifest pinned source commit, Atlas schema 0.2 and exact-byte
SHA-256 hashes of both source Bases and three payloads. Generated Bases carry an
owner comment; navigation notes carry owner frontmatter. RA-3B extends this same
owner and manifest, as specified below; the two Base payloads retain their behavior.

Before any write, the complete prior manifest, all targets and owner markers are
checked. Symlink boundaries/descendants, traversal and absolute manifest paths
fail closed. Unknown/unowned files block generation rather than being overwritten
or deleted. Cleanup considers only obsolete Base/navigation files in the prior
manifest with matching owner and digest. Empty directories are not pruned.
All writes reuse RA-1's same-directory temporary file plus atomic replace;
the direct-view manifest is last. Authored bytes and the technical projection
remain unchanged. Run only one projector at a time: this is not a multi-file
transaction or protection against concurrent hostile filesystem mutation.

`--check` performs no mkdir, temporary file, replace, unlink or manifest update.
Exit 0 means exact state, 2 means expected configuration/validation/drift failure;
unexpected faults remain non-zero. Following an interrupted first write, preserve
unowned outputs outside the root before retrying; do not erase authored work.

See the [15-view capability matrix](Wiki%20Views/Direct%20View%20Capability%20Matrix.md)
for direct/partial/deferred boundaries and the seven [Process Seeds](Process%20Seeds/)
for optional manual authoring sources extending the RA-2 Process template.
Seeds are drafts, not reviewed, and create no Public part_of or implementation
claim. No automatic seed copying, migration, scientific Body parsing, candidate
promotion, private-to-public sync or Wiki-to-Agent-Memory connection is provided.
Candidate History and Decision Lineage remain deferred; Evidence Profiles are RA-6.
RA-3B supplies only the bounded declared-reference navigation described below.
Direct inventory counts cannot establish absence, coverage, exhaustion, novelty
or evidence independence.

## RA-3B declared reference navigation (manifest v2)

The same `private_views` CLI and `research-wiki-derived` owner now generate
manifest `view_schema_version: "2.0"`, with `reference_index_schema_version: "1.0"`
and a private structured-input fingerprint. No second projector or manifest is
introduced. Exactly two payloads are added to the historical tree:

```text
indexes/declared-reference-index.yaml
indexes/Declared Literature Navigation.md
```

The current tree therefore has five owned payloads plus
`manifest/direct-views.yaml`, six files total. The Direct Views Index retains
both Base links and adds Declared Literature Navigation. It describes the
structured index as navigation/audit with no scientific adjudication.
The historical 17 Direct Views and 15 Capability Matrix dispositions are unchanged.

See the normative [Declared Reference Index Contract](Declared%20Reference%20Index%20Contract.md)
for exact resolution, closed rows, E1–E9 and the finite Component/RQ/Process
recipes. Only existing selected RA-2 reference properties are indexed. There is
no body indexing or heuristic identity resolution. Unknown references remain
valid unresolved audit rows; known wrong types remain their actual types with a
mismatch diagnostic. Neither produces an inferred Paper identity or scientific
validation error. Legacy identities resolve but do not expand.

The fingerprint includes every authored private identity/type/profile/revision
and consumed RA-2 reference sets in deterministic order. It excludes bodies,
titles, paths and unconsumed metadata. Relevant edits cause `--check` drift;
body-only edits without relevant revision/reference changes leave YAML unchanged.
A separate read-only locator scan excludes all `_generated` content and does not
follow authored symlinks. Locators affect Markdown links only: a note move can
change Markdown without changing YAML; a whole-vault move with relative paths
preserved changes neither. Link segments are encoded; unresolved IDs are escaped
plaintext. No private absolute paths or unselected secrets are emitted.

Strict v1 manifests may migrate in place on write. A v1 `--check` returns drift
(exit 2) and never migrates or writes. Unknown versions fail closed. V1 cannot
claim YAML ownership; v2 permits only the exact new index path. YAML owner/schema
markers, existing Base/Markdown markers and all prior ownership/path checks must
pass before writes. Unknown files are never adopted; edited obsolete files are
never deleted. The manifest remains last after per-file atomic writes.

RA-1 exactness, source-ref/HEAD, topology, marker, source cleanliness, Registry
and RA-2 validation remain mandatory preconditions. No automatic RA-1 repair is
performed. `--check` remains strictly write-free, including no temporary files
or cleanup, and unresolved-only/empty output is a valid exact state. Use a single
writer with stable source and vault input. There is no whole-tree transaction;
interruption and concurrent edits retain the recovery limitations above.

The three additional Markdown tables visibly say “declared … paths (derived
navigation)” and each carries the full local warning against support,
implementation evaluation and literature coverage implications. Roles retain
the actual declaring record and revision, never inherit to a Paper anchor, and
`research_method_or_baseline_refs` stays combined. The technical audit retains
all unresolved/wrong-type declarations and every path retains full provenance.
Candidate History and Decision Lineage remain deferred. No acceptance/status
promotion, private-to-public export, scientific adjudication or Wiki-to-Agent
Memory/Retrieval/Cortex path is introduced.

## RA-4A fixture-only Zotero source projection

RA-4A adds an independent offline PoC, with one explicit synthetic JSON fixture
as source. It is not a real Zotero export/API integration. See the normative
[Zotero Source Projection Contract](Zotero%20Source%20Projection%20Contract.md).
No account, SQLite/Data Directory, Zotero application, plugin or PDF is accessed.

```bash
uv run --no-sync python -m fh_agent.research_atlas.zotero_projection \
  --repo-root . --vault-root "$PRIVATE_VAULT" --source-ref HEAD \
  --fixture-export "$SYNTHETIC_ZOTERO_EXPORT"
```

Append `--check` for zero-write exact comparison: 0 means exact/success, 2 means
expected configuration/validation/ownership/drift failure. Unexpected faults
propagate. Use only synthetic fixtures/vaults for this PoC. Source-ref must equal
committed HEAD; the generator package and Zotero contract must be clean. Existing
private marker, physical non-nested roots and symlink/path safety apply.

Owner `zotero-source-projection` owns only `_generated/zotero/`: manifest
`manifest/projection.yaml`, version-addressed source notes at
`sources/<source_id>/<source_version_id>.source.md`, and the two indexes
`indexes/zotero-source-index.yaml` / `indexes/Zotero Source Index.md`. It never
writes authored notes or the technical-atlas/derived roots, and invokes neither
existing writer. Generated notes have no RA-1/RA-2 envelope or scientific status.

Source-family identity binds library context and item key, not title/DOI/citation
key or scholarly Work. Version identity additionally binds explicit version and
attachment identity/digest. Annotation and ordinary metadata updates do not
change version identity. Z1 reimport is deterministic; Z2 changes only its source
payload and global indexes/manifest; Z3 creates a new version with explicit
recoverable predecessor and retains old version bytes. No current-file alias
can retarget an existing reference. Unchanged source records keep their last
material export revision; indexes/manifest record the current export revision.
Without an attachment digest, unchanged key/version cannot detect replacement
bytes. Current/retained is projection presence only, never scientific preference.

Require a single writer and stable inputs. Writes use per-file atomic
flush/fsync/replace, manifest last. There is no whole-tree transaction or lock.
Unknown files are never adopted, even with owner text. An interrupted new-version
write can leave an unmanifested payload: preserve/move it outside the owned root,
then retry. Edited retained history blocks generation; missing non-reconstructible
history cannot be forgotten. Historical versions are not automatically pruned.

All projection data stays private. No public Registry/workspace, Canonical/SOT
or Runtime/Agent Memory/Retrieval/Cortex path is introduced. RA-3B remains
unchanged: zsrc/zsv identifiers stay unresolved there. Intended manual references
are source_refs to a zsrc family and version_read to an exact zsv version;
RA-4A never sets either or any reading/review/Finding/Decision state.

Before merge, TECH safety review and bounded SCI review of family/version/
attachment/predecessor/locator and manual reference semantics remain mandatory,
followed by Anton's explicit merge decision. RA-4B defaults to SKIP. RA-5 remains
blocked until all technical/scientific/CI gates and merge pass; no bulk scientific
record import follows automatically from this PoC.
