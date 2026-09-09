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
Wiki-to-Agent-Memory/Retrieval/Cortex/runtime path. Private notes are only read to
validate the envelope and explicitly opted-in flat profile. They never feed public
rendering or alter technical ancestry. The public workspace generator accepts no
private-vault input.

Run one projector at a time with a stable source checkout and vault. This is a
local filesystem workflow, not a transaction across concurrent editors or hostile
filesystem mutation. An interrupted multi-file generation can leave drift;
atomic replacement protects individual files, not the whole tree. A first run
interrupted before its manifest may require operator recovery of unowned outputs.
Structural map tests do not claim an interactive Obsidian/Excalidraw plugin test.
RA-3/Bases/derived indexes, corpus migration, Zotero, Work automation, gameplay,
and real input remain outside this leaf.
