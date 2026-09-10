# Zotero Source Projection Contract

RA-4A / Issue #60 is a fixture-only, offline source-projection PoC. It demonstrates
source identity, explicit version binding and safe reimport, not compatibility
with a real Zotero exporter. It uses no account, API, plugin, SQLite database,
Zotero Data Directory, Zotero process or attachment file. Only synthetic fixtures
are authorized. No new dependency is required.

## Input and closed adapter schema

The only source input is an explicitly supplied regular UTF-8 `.json` file.
Reject symlink boundaries, duplicate JSON keys, non-standard/non-finite numbers,
unknown fields, wrong types and duplicate item/attachment keys in one library or
annotation keys within an attachment. All nested models are closed and strict;
there is no raw metadata dictionary passthrough. Input is never inferred from a
directory. No attachment is opened: tests compute digests from synthetic bytes.

The fixture builder lives only in `tests/test_research_wiki_zotero_projection.py`;
there is no committed export asset. Its baseline has exactly three synthetic
families Z1/Z2/Z3 in `fixture-library-alpha`.

| Model | Fields |
| --- | --- |
| Fixture | `fixture_schema_version: "1.0"`, `export_revision`, `library_context`, `items` |
| Item | `zotero_item_key`, `persistent_ids`, `source_version`, `primary_attachment`, `predecessor`, `metadata`, `annotations` |
| Persistent ID | `kind: doi / arxiv / isbn / other`, `value` |
| Attachment | `zotero_attachment_key`, optional `sha256` (64 lowercase hex or null) |
| Predecessor | `source_version`, `zotero_attachment_key`, `attachment_digest` (hash or null); entire descriptor may be null |
| Metadata | `item_type`, `title`, ordered `creators`, positive integer/null `publication_year`, nullable `container_title`, optional nullable `citation_key`, nullable HTTP(S) `url` |
| Annotation | `annotation_key`, `text`, `locator` |
| Input locator | optional `page`, `section`, `attachment_relative`; at least one must be non-null |
| Attachment-relative locator | `kind: pdf-page`, `value` |

Text is nonempty, single-line opaque text. Control/format characters, file URIs,
absolute paths, drive/UNC paths, traversal segments and storage locations fail
before writes, including when supplied as metadata. Locators are structured
source positions, never filenames. HTTP(S) metadata is displayed as escaped text
and never dereferenced. No casefolding or bibliographic normalization generates
identity. `page` may be nonnumeric; location validity is only syntactic.

Normalize item order by item key, persistent IDs by `(kind, value)`, annotations
by annotation key; preserve creator order. Canonical JSON uses sorted keys,
`ensure_ascii=False`, compact separators, `allow_nan=False`, UTF-8, no newline.

## Independent identities

All identities use full lowercase SHA-256, with the following exact canonical
JSON fields (object keys shown in braces):

| Identity | Prefix and hash inputs |
| --- | --- |
| Source family | `zsrc-`, `{library_context, zotero_item_key}` |
| Attachment | `zatt-`, `{library_context, zotero_attachment_key}` |
| Source version | `zsv-`, `{source_id, source_version, attachment_identity, attachment_digest}` |
| Annotation | `zann-`, `{source_version_id, attachment_identity, annotation_key}` |

The nullable version-hash key is literally `attachment_digest`. A Source family
is a Zotero-like item in a library context, not automatically a scholarly Work.
Title, creators, DOI/arXiv/ISBN, citation key and URL never merge items or create
aliases. Metadata, annotations and export revision never change source/version
identity. An explicit version-label, attachment-key or present attachment-digest
change creates a new version ID. Without a digest, replacement bytes behind the
same key are undetectable unless version label or key changes explicitly.

`annotation_set_digest` hashes the normalized input annotation models, including
text and locator fields (optional fields materialized as null). The annotation
key is version-bound: reuse on a new version produces a new annotation ID.
`source_record_digest` hashes the entire generated frontmatter except itself.
`fixture_semantic_sha256` hashes the normalized fixture, never its pathname.

## Version retention and predecessor

For a previously known family, a newly introduced version requires an explicit
predecessor descriptor. Recompute its version ID with the same family and require
that exact version to exist in the prior manifest and be physically recoverable.
A supplied predecessor for a first import must also resolve to prior history;
dangling/self predecessors fail. No chronology, DOI, title, date or citation-key
heuristic is permitted. Store only `new -> predecessor`; never add a successor
to the old source. A recorded predecessor cannot be changed on metadata reimport;
omitting it on the same existing version preserves its recorded value.

Prior-owned versions no longer current are retained with exactly their existing
bytes after owner, identity and prior digest validation. No historical pruning.
Removed families retain their versions with current ID null. Missing history
that the current fixture cannot reconstruct fails closed. A missing current
payload can be reconstructed from that fixture only when its bytes reproduce
the prior manifest digest; otherwise restore it explicitly. A retained version cannot be
rewritten when selected again; restoration of an identical version is allowed.

Unchanged source payloads keep their last material `fixture_export_revision`.
The manifest/index record the current export revision globally. This prevents
an export revision change from rewriting unrelated Z1/Z3 source payloads during
Z2 metadata/annotation updates. Current payloads with intact identities may be
regenerated to repair content drift; retained payloads require the prior digest.

## Generated records, index and manifest

Owner: `zotero-source-projection`. Only root: `<vault>/_generated/zotero/`.

```text
manifest/projection.yaml
sources/<source_id>/<source_version_id>.source.md
indexes/zotero-source-index.yaml
indexes/Zotero Source Index.md
```

No `current.source.md`, symlink or hardlink alias is generated. Filenames use
only validated hash IDs; existing version references never silently retarget.
The projector writes no authored files and does not call RA-1 or RA-3B writers.

Source frontmatter is closed, with exactly these fields:

```text
zotero_source_schema_version, generated_by, source_id, source_version_id,
library_context, zotero_item_key, persistent_ids, source_version,
attachment_identity, attachment_digest, annotation_set_digest,
import_schema_version, fixture_schema_version, fixture_export_revision,
source_locator, source_metadata, predecessor_source_version_id,
source_record_digest, annotations
```

Source/import/fixture schema versions are `1.0`. Metadata remains the closed
adapter metadata model. The source locator binds adapter `zotero-fixture-json`,
library context, item key, source version ID and attachment identity.
Projected annotations contain key, annotation ID, text and locator; each locator
binds exact version, attachment identity and annotation key alongside the human
location fields. A locator's existence establishes no reading or correctness.

Manifest v1 is closed:

```text
projection_schema_version, generated_by, source_repository,
generator_source_commit, import_schema_version, fixture_schema_version,
fixture_export_revision, fixture_semantic_sha256,
current_source_versions, retained_source_versions, owned_files
```

Schema versions are `1.0`; repository is `Planton361/autonomous-game-agent`.
Current/retained inventories are lists of `{source_id, source_version_id}`;
current has at most one version per family. Inventories must exactly partition
owned source versions. Duplicate paths/version IDs/current family IDs fail.
Each owned entry has `path`, `kind`, nullable source/version IDs and `sha256`.
Kinds are `source_version`, `source_index`, `source_index_markdown`. Source paths
must match embedded IDs exactly; index kinds allow only the two fixed paths.
The manifest never owns itself; unknown versions/fields/owners fail closed.

The YAML index has schema `1.0`, owner, generator commit, fixture export revision,
fixture semantic digest and `sources`. Each family has its ID, nullable current
version ID and all recoverable versions. Each version includes its ID,
`projection_presence: current / retained`, exact generated path, source label,
attachment identity/digest, predecessor, persistent IDs and `source_file_sha256`.
Models are closed. The Markdown index navigates these same versions and states:

> Generated Zotero source projection only. Current/retained describes projection presence, not reading, review, scientific validity, preferred version, Finding support, candidate status or Decision acceptance.

Only projection presence is modeled. No scientific preferred-version selection.
Markdown escapes link/table/HTML syntax; generated links use fixed hash-ID paths.
No timestamp, random ID, local path, export pathname or attachment path is emitted.

## CLI and safety

With caller-supplied shell variables pointing to a separate synthetic vault and
fixture, from the repository root:

```bash
uv run --no-sync python -m fh_agent.research_atlas.zotero_projection \
  --repo-root . --vault-root "$PRIVATE_VAULT" --source-ref HEAD \
  --fixture-export "$SYNTHETIC_ZOTERO_EXPORT"
```

Append `--check` for exact comparison. Exit 0 is success/exact state; 2 is expected
configuration/validation/ownership/drift failure. Unexpected faults propagate.
Errors are generic and do not echo private input values or paths.

Preflight requires existing non-nested physical repo/vault roots, the existing
private marker version `1.0` and project, local full commit equal to HEAD, and
clean generator package plus this contract path (staged/unstaged/untracked).
Unrelated repo dirt is permitted. Validate fixture regularity and all symlink
boundaries before reading. Parse and resolve in memory. Inspect only the owned
subtree, validate prior manifest and unknown files, owner/identity and history
digests, then construct all expected payloads before any mutation.

All paths must be normalized relative POSIX paths, with no absolute/drive/UNC,
backslash, NUL, doubled separator, dot/traversal segment or escaping target.
Reject symlinked boundaries/descendants and occupied nonregular output targets
or nondirectory parents. Unknown/unowned files are never adopted or deleted,
even if their text contains the owner. Lost-owner/identity files block writes.

Cleanup is prior-manifest-only for unchanged owner-and-digest-validated obsolete
non-source payloads. V1 expects both fixed index paths, so normal v1 reimports
have no obsolete non-source payload; the cleanup guard does not admit extra
index paths. Source versions are always retained, never cleanup candidates.

`--check` compares exact file set and bytes without mkdir, tempfiles, writes,
replace, unlink, cleanup or manifest update. Write mode uses a **single writer**,
stable inputs, **per-file atomic** same-directory temporary writes with
flush/fsync/replace and **manifest last**. Unchanged source bytes are preserved.
There is no **whole-tree transaction**, lock or protection against hostile
concurrent editors. After interruption, a new version may be **unmanifested**:
retry must fail unknown/unowned. Preserve/move that file outside the owned root
explicitly, then rerun; never auto-adopt it. The same applies to an interrupted
first run. Existing prior-owned current payload drift can be regenerated.

## Scientific/privacy boundaries and gates

Generated source notes contain no RA-1/RA-2 envelope, reading/review/candidate/
decision fields, scientific status synonyms, Finding/Decision refs or generated
READ/WFIND/WDEC identities. They cannot become authored Paper/ReadingNote records.
All authored bytes and `_generated/technical-atlas` / `_generated/derived` remain
unchanged. Public Registry/workspace, Canonical/SOT and Runtime/Agent
Memory/Retrieval/Cortex receive no fixture data or writes.

Intended manual authoring, subject to bounded SCI review: `source_refs: [zsrc-…]`
names a family; ReadingNote `version_read: zsv-…` names the exact read version.
RA-4A never writes either field, read date/depth/sections, Findings or Decisions.
RA-3B is unchanged and continues to leave zsrc/zsv identifiers unresolved.
No Candidate History/Decision Lineage or Zotero-to-RA-3B resolver is added.

Before merge: green focused/full CI, TECH ownership/path/recovery/isolation
review, then bounded SCI review of family-vs-Work identity, version/attachment
basis, explicit predecessor, syntactic locator limits and manual family/version
reference separation. Anton alone decides merge. No general RA-2 reopening.

RA-4B default is **SKIP** without demonstrated recurring manual cost, a verified
real export/API contract, idempotency/recovery/no-overwrite evidence and clear
value. RA-5 remains blocked until Z1/Z2/Z3, bounded SCI, TECH safety, full CI and
explicit merge pass; any later RA-5 plan is separate and scientific/editorial.
No bulk ReadingNote/Finding/Decision import, real Zotero integration, corpus
migration, Work automation, dependency change, D7, gameplay or input is authorized.

Acceptance A01–A45 is implemented in the single synthetic test module: strict
schema/identities; Z1/Z2/Z3; authored/other-owner invariance; ownership/history/
path/recovery/check/Git gates; privacy/no-DB/no-network; locator binding and docs.
