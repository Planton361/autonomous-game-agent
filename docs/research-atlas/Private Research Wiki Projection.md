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

Actual private-vault application uses the restore-point harness from the
repository root:

```bash
uv run --no-sync fh-agent workspace apply
uv run --no-sync fh-agent workspace check
```

The lower-level projector modules remain implementation stages and test
surfaces; do not run them as a manual sequence against the actual private vault.
The harness resolves the local-only `PRIVATE_VAULT` setting or accepts an
explicit `--vault-root` argument.

`--repo-root` must be the actual Git worktree root. `--source-ref` resolves locally
to a full 40-character commit and must equal checked-out `HEAD`. Both
`docs/research-atlas/registry/**` and `src/fh_agent/research_atlas/**` must be clean,
including staged and untracked changes. Unrelated repository dirt is permitted
and preserved. Commit the projector before using it against its own checkout.
No network is required for projection.

## Workspace apply/check harness

For a reviewed source checkout, use the stable local operator surface instead of
running the two projectors manually:

```bash
uv run --no-sync fh-agent workspace apply --vault-root "$PRIVATE_VAULT"
uv run --no-sync fh-agent workspace check --vault-root "$PRIVATE_VAULT"
```

`--vault-root` is explicit; when omitted, both commands use the local-only
`PRIVATE_VAULT` environment variable. They require the canonical repository
origin, the actual Git worktree root, a clean supported projector checkout, the
exact local `HEAD`, and the marker at precisely the supplied vault root. They
never search parent directories or scan for a vault. Paths with spaces are
ordinary path arguments. No private absolute path is committed or sent to GitHub.

`workspace apply` first runs no-write ownership/precondition checks over both
generated roots. After both pass, it creates a timestamped, never-overwritten restore point
outside both the vault and the repository. By default it is a sibling
`.research-wiki-restore-points/` directory; `--restore-root` can select another
safe external directory. A restore point copies only the pre-apply generated
roots (`_generated/technical-atlas/` and `_generated/derived/`) plus local
relative metadata; it does not copy authored notes or `.obsidian/**`. The command
prints its restore-point location locally, then runs technical projection, direct
views, and both zero-write checks against the resolved full `HEAD` SHA. It exits
zero only if every stage passes. A failed preflight has no restore point because
no Workspace files have been changed; a failure after the restore point reports
its location. There is deliberately no automatic rollback.

`workspace check` creates no restore point and delegates only to both existing
`--check` paths. It makes no directories, temporary files, manifests or other
vault writes. Both commands preserve the existing owner, manifest, marker and
semantic validation; unknown or authored content is never removed to force
success. Use one writer and avoid concurrent Obsidian/editor changes: the
harness is a recovery aid, not a whole-tree transaction or locking system.

## Cross-platform recovery and plugin fallback (W12)

The supported operating model is Linux generation from one clean, exact source
revision, followed by the operator's existing Obsidian Sync and Mac read/use.
The Mac is not a second generation source. Generated paths are POSIX-relative,
NFC-normalized and checked for Windows-invalid components, case-fold collisions
and Unicode-normalization collisions. Durable links use vault-relative Obsidian
targets or encoded POSIX-relative Markdown links; generated files contain no
machine-specific vault path.

Obsidian Markdown is the durable navigation layer. The core Bases plugin renders
the two generated `.base` tables, the core Canvas support opens native `.canvas`
views, and the optional Excalidraw community plugin opens the rich anatomy maps.
Losing any of those views reduces presentation only: Research Knowledge Home,
Technical Hierarchy, Component Hub pages, Research Landscape, Literature
Inspection and the linked technical records remain Markdown entry points. No
operator-local plugin or UI settings are generated authority.

For missing or drifted manifest-owned output, `workspace check` reports drift
without writing. With the same clean source revision and valid ownership state,
`workspace apply` preflights both generated roots, records the prior generated
roots in its external restore point, regenerates the expected output and runs
both checks. Repeating apply at the same source and authored inputs reproduces
the same generated bytes. A generated Workspace is therefore recoverable from
its committed Registry/views plus the current authored records that its accepted
views consume.

Unknown/unowned files, a lost owner marker, or an unsupported/corrupt manifest
block apply before either generated root is changed. Preserve those files and
the restore point for inspection; never move authored notes into a generated
root or let the generator adopt them. If ownership cannot be proven, preserve
the affected generated root outside the vault before rebuilding it from an
empty root. An interruption during an existing generation is detected by
`workspace check`; apply can rewrite paths still covered by the prior valid
manifest. A first generation interrupted before its manifest leaves unowned
outputs, which must be preserved outside the root before retrying.

Generated output can be reconstructed by the generator. Authored private
Research content cannot: recover it through the operator's existing private
backup/recovery process. Obsidian Sync is not treated as a verified backup.
W12 does not recover authored notes, `.obsidian` UI state, Sync conflict copies,
or outputs for future gated Workspace leaves. Actual Linux-to-Mac G6 remains a
separate operator acceptance after CONTROL approves the exact PR head.

## Generated ownership

Only `_generated/technical-atlas/` belongs to this generator:

```text
manifest/projection.yaml
records/<ATLAS-ID>.md
evidence/<EVID-ID>.md
system-map/System Anatomy.excalidraw.md
system-map/Agent Anatomy.excalidraw.md
domain-maps/Evidence, Memory & Retrieval.excalidraw.md
indexes/atlas-id-index.yaml
indexes/Technical Atlas Index.md
```

Paths use stable public IDs; names appear in frontmatter, headings, and aliases.
Internal WikiLinks use vault-relative paths beneath the generated root. W03 makes
Agent Anatomy the primary rich Home and adds one Evidence, Memory & Retrieval
Domain slice. System Anatomy remains a separate reference/rollback map. Region
sequence cues are explicitly presentation-only; the Domain slice shows selected
Registry-backed relations and keeps `presented_in_domain` separate from technical
`part_of` ancestry. The maps preserve public visual semantics while routing Home
navigation to the generated Research Knowledge Home.
The ID index resolves current public identities; it is not another Registry.

W03 advances the technical projection manifest from `1.0` to `1.1`. A finite
`1.0` manifest remains readable so the two new owned paths can be added without
replacing or deleting the prior System Anatomy. The output set, path, owner and
digest checks remain closed; unknown files still fail closed.

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

The historical v1/v2 manifests pinned source commit, Atlas schema 0.2 and
exact-byte SHA-256 hashes of both source Bases and generated payloads. The
generator emits an owner comment in each Base and owner frontmatter in navigation
notes. Obsidian legitimately reserializes an opened Base as YAML: it may remove
comments, reorder mapping keys, normalize quoting/indentation and replace
`note.property` with its documented `property` shorthand in view property selectors.
The [Obsidian Bases syntax](https://help.obsidian.md/bases/syntax) defines `.base`
files as YAML and documents both note-property spellings as equivalent.

Current manifest v2.1 therefore classifies workspace artifacts explicitly:

| Class | Scope | Ownership behavior |
| --- | --- | --- |
| A — authored | Everything outside the generated roots | Never generator-overwritten. |
| B — strict deterministic generated output | Generated Markdown, YAML indexes and manifests | Owner/schema checks remain fail-closed; `--check` compares exact bytes. |
| C — Obsidian-managed projection/config | Only the two manifest-owned `.base` payloads | The manifest records reconstructable emitted-byte and canonical semantic digests; validation accepts only narrow YAML serialization equivalence. |
| D — operator-local UI state | Obsidian workspace/layout state such as `.obsidian/workspace*.json`, outside the generated roots | Neither read nor written by this projector and never technical, scientific or architecture authority. |

Base semantic canonicalization ignores YAML comments, key order, quoting and
indentation, and normalizes the documented `note.` shorthand only for `properties`
keys and view `order`, `groupBy.property` and `sort[].property` selectors. Filters,
view names, view/list ordering, configuration values, added/removed views and every
other Base semantic remain exact. A meaningful Base edit therefore still fails
closed. The repository source templates remain committed strict inputs; deterministic
generator bytes remain reconstructable even when Obsidian later serializes an
equivalent local form.
Obsidian Sync may transport either serialization, but it supplies no ownership or
semantic authority and is not needed to explain the observed deterministic rewrite.

Before any write, the complete prior manifest, all targets and ownership evidence
are checked. Symlink boundaries/descendants, traversal and absolute manifest paths
fail closed. Unknown/unowned files block generation rather than being overwritten
or deleted. For v2.1 Bases, prior semantic digests replace volatile comments as the
ownership proof; strict outputs retain their marker/schema rules. Existing v1/v2
Bases migrate only when their recorded emitted-byte digest is intact or when the
manifest-recorded current payload is semantically identical under the narrow Base
rules above. This bridge cannot adopt an unmanifested Base. Cleanup considers only
validated obsolete generated files. Empty directories are not pruned.
All writes reuse RA-1's same-directory temporary file plus atomic replace;
the direct-view manifest is last. Authored bytes and the technical projection
remain unchanged. Run only one projector at a time: this is not a multi-file
transaction or protection against concurrent hostile filesystem mutation.

`--check` performs no mkdir, temporary file, replace, unlink or manifest update.
Exit 0 means exact state for class B and semantic equivalence for class C; exit 2
means expected configuration/validation/drift failure. Unexpected faults remain
non-zero. Following an interrupted first write, preserve unowned outputs outside
the root before retrying; do not erase authored work.

Use the supported `workspace apply` / `workspace check` harness described above
for the complete current Workspace. The lower-level projector commands remain
implementation and test surfaces; W12 adds no separate manual write sequence.

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

## RA-3B declared reference navigation (manifest v2 family)

The same `private_views` CLI and `research-wiki-derived` owner now generate
manifest `view_schema_version: "2.1"`, with `reference_index_schema_version: "1.0"`,
a private structured-input fingerprint and explicit per-payload ownership class.
No second projector or manifest is introduced. Exactly two payloads were added to
the historical tree:

```text
indexes/declared-reference-index.yaml
indexes/Declared Literature Navigation.md
```

The RA-3B reference-navigation payload set before the K3 extension had five
owned payloads plus `manifest/direct-views.yaml`, six files total. The Direct
Views Index retains both Base links and adds Declared Literature Navigation. It
describes the structured index as navigation/audit with no scientific
adjudication.
The historical 17 Direct Views and 15 Capability Matrix dispositions are unchanged.

The same v2.1 manifest also owns the bounded K3 first visual Knowledge Map slice:

```text
indexes/Research Knowledge Home.md
workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL.md
workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER.md
```

These three payloads extend the existing `research-wiki-derived` writer; they do
not introduce a second renderer, owner or manifest. Their content is generated
from the fixed public K2 selections and a privacy-safe authored-record count.
The workbenches preserve exact Registry typed edges, explicitly separate
presentation grouping from `part_of`, label historical technical Evidence as
implementation provenance, and keep the Independent Verifier Interface lane
empty when no `IF-*` record exists. Empty private research/source panels are
navigation state, not scientific absence or exhaustion.

W01 versions the three K3 payloads with `k3_view_schema_version: "1.1"` while
retaining manifest v2.1, the same owner and a finite owned path set. Home and both
workbenches begin with the same plain-Markdown orientation pattern: human-readable
title first, secondary stable ID where applicable, Home, exact Registry-backed
parent and presentation context where available, Research/fallback navigation,
and concise projection/authority cues. Workbench status remains split into target
architecture, implementation declaration, technical verification, measurement
presence, measurement validity, scientific evidence and accepted-claim axes; no
overall status is derived. Wikilinks emitted inside Markdown table cells escape
their alias delimiter for Obsidian table parsing; ordinary non-table Wikilinks
remain unchanged. These links, lists and tables are the durable fallback and do
not require Breadcrumbs, Canvas, Excalidraw, CSS or another plugin. The manifest
continues to hash and own the changed bytes; no new writer or ownership subtree
is introduced.

The W01 G6 repair changes only the two workbench filenames to the human-first
paths shown above. A prior v2.0/v2.1 manifest may name the exact retired ID-first paths
`workbenches/CMP-MEM-RETRIEVAL — Memory Retrieval.md` and
`workbenches/CMP-INDEPENDENT-VERIFIER — Independent Verifier.md` solely so the
existing owner-marker and recorded-digest cleanup can remove intact generated
outputs while writing the current paths. Edited, unowned, unknown or unmanifested
files still fail closed; the retired names are never emitted as compatibility
files.

At W01, the K3 extension brought the tree to eight owned payloads plus
`manifest/direct-views.yaml`, nine files total. The Direct Views Index links the
Research Knowledge Home entry. K3 does not write authored
private records, source identities, scientific evidence or claims.

## W02 technical hierarchy navigator (manifest v2.2)

The `research-wiki-derived` owner now adds `indexes/Technical Hierarchy.md` and
one `hierarchy/<stable technical ID>.md` note per current technical Registry identity.
The same manifest owns each output with a strict byte digest. The generated notes
link to their corresponding `_generated/technical-atlas/records/<ID>.md` notes;
they do not edit those notes or any authored note. Existing v1/v2.0/v2.1 manifests
are read for bounded migration. A v2.2 manifest can claim only the fixed entry
path and stable-ID-shaped Markdown paths under `hierarchy/`; unknown files remain
unowned and block application. Obsolete hierarchy files require the prior owner
marker and recorded byte digest before cleanup.

The entry starts at declared System roots and expands only `part_of` edges in
their Registry direction (child → parent). Each node note lists every rooted path,
all direct parents, all direct children, and a link back to the entry. Multiple
parents produce multiple paths. Technical records without a `part_of` path to a
System appear in a separate unconnected section; interfaces, contracts, data,
measurements and environments are not given invented parents. A separate Domain
section uses only `presented_in_domain` and states that it is presentation
grouping, never ancestry. Labels lead in all navigation text; IDs remain visible
and provide stable filenames and frontmatter identity. Sorted labels with ID
tie-breaks make the output independent of Registry enumeration order. Cycles,
self-parent edges, missing endpoints and duplicate output paths fail before writes.

Generated frontmatter includes `technical_parents`, `technical_children`, and
`presentation_domains` for derived navigation consumers. Nodes with declared
parents also carry an `up` list of links to those generated parent notes. This
matches the optional Breadcrumbs typed-link field described in its
[hierarchy guide](https://breadcrumbs-docs.michaelpporter.com/guides/getting-started-with-hierarchies/)
and supports multiple parents without choosing one. These fields are
reconstructable from the Registry; no plugin setting or private `.obsidian` state
is written. An operator who uses Breadcrumbs may need to enable its typed-link
builder and rebuild its graph; this is optional configuration. Plain Markdown
paths and parent/child lists are the complete navigation fallback. Research
Knowledge Home and the two existing K3 workbenches link into the hierarchy while
retaining their W01 status and Interface
lane semantics. Real-vault application remains a separate G6 step after CONTROL
reviews an exact PR head; use only `uv run --no-sync fh-agent workspace apply`
with the #82 restore-point harness.

## W03 Agent Anatomy and Domain slice

The `public-research-atlas` projection owns the two additional finite Excalidraw
paths listed above. The private Research Knowledge Home prominently links to
Agent Anatomy, the representative Domain slice, W02 Technical Hierarchy, and the
existing Memory Retrieval workbench. System Anatomy remains directly reachable
for W03 G6 comparison and rollback. Markdown navigation stays usable if the
Excalidraw plugin is unavailable.

The `research-wiki-derived` Home advances from K3 view schema `1.1` to `1.2`;
its existing `2.2` ownership manifest and finite output paths remain in place.

Agent Anatomy groups selected technical landmarks into operator-facing regions
and uses dashed sequence cues labelled as presentation only. Functional regions
do not create Registry ancestry or technical relations. Between-run candidate
work is outside the in-run boundary; the independent Verifier is shown outside
Cortex decision authority; the optional bridge remains behind the No-Spoiler
Firewall.

The Evidence, Memory & Retrieval slice selects current `presented_in_domain`
members for navigation, then shows a curated set of exact Registry relations to
the shared System parent, interface, retrieval snapshot and Cortex context.
Memory and Memory Retrieval remain separate technical siblings under `SYS-AGA`;
the Domain is not their technical parent. Both surfaces use deterministic
semantic/layout element IDs and inspectable parsed Excalidraw Markdown. They
consume no private scientific content, and the private projector rewrites only
vault-relative destinations.

See the normative [Declared Reference Index Contract](Declared%20Reference%20Index%20Contract.md)
for exact resolution, closed rows, E1–E9 and the finite Component/RQ/Process
recipes. Only existing selected RA-2 reference properties are indexed. There is
no body indexing or heuristic identity resolution. Unknown references remain
valid unresolved audit rows; known wrong types remain their actual types with a
mismatch diagnostic. Neither produces an inferred Paper identity or scientific
validation error. Legacy identities resolve but do not expand.

## W04 Component Synthesis Hubs (manifest v2.3)

W04 keeps the human-first Memory Retrieval and Independent Verifier workbench
paths as each Component's Overview entry. One shared renderer builds the same
three views for both stable Component identities:

```text
workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL.md                 # Overview
workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL/Technical.md
workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL/Research.md
workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER.md       # Overview
workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER/Technical.md
workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER/Research.md
```

The Overview distinguishes Registry `part_of` parentage from
`presented_in_domain` navigation context, preserves the separate architecture,
implementation and verification axes, and links to Technical and Research.
Technical lanes are populated only from directly related, typed Registry
records; selected edges keep their Registry direction. Component children are
shown only when a direct `part_of` edge declares them. The Verifier Interface
lane remains explicitly empty when no directly related Interface is registered;
other relationship types do not fill it.

At W04, Research views exposed the private-snapshot availability count and
source-projection state and linked to declared-reference navigation. The W04
Research-view behavior was extended by W06; current behavior is described in
the W06 section.

The generated direct-view manifest advances to schema `2.3`; Hub Markdown uses
K3 view schema `1.3`. Ownership is limited to the four exact child paths above
and the existing fixed paths. No wildcard owns a Hub folder. Prior `2.0`–`2.2`
manifests may claim only their previously declared fixed paths and the two
finite retired W01 workbench names; applying them adds the W04 children. A
`2.3` manifest may additionally own only the four declared Hub child paths.
Unknown or unowned files still block generation, authored notes remain outside
the generated tree, and `--check` remains zero-write. W02 Component hierarchy
notes link to the Hub Overview; the W03 Domain slice routes through Research
Knowledge Home. Actual-vault G6 remains a separate acceptance gate after
CONTROL reviews the exact PR head.

## W05 precise technical detail maps (manifest v2.4)

W05 adds one shared endpoint detail renderer and one native JSON Canvas renderer for the
finite technical records directly exposed by the two W04 Technical Hub lanes:

```text
IF-MEM-CORTEX
CON-CORTEX-CONTEXT
DAT-RETRIEVAL-SNAPSHOT
MEAS-RETRIEVAL-DELIVERY-001
CON-VERIFIER-RESULT
DAT-OBSERVATION
DAT-VISIBLE-OUTCOME
```

For each ID, `workbenches/Technical Details/<ID>.md` and the matching `.canvas` are
separately listed strict-byte owned payloads. The manifest adds no wildcard folder
ownership. The Hub Overview retains its W04 contract; W06 later extends Research.
The Technical lanes link each present exact endpoint to its Markdown workbench and Canvas.
The Verifier lane remains empty for Interface and MeasurementPoint because no directly
related records of those types exist in the current Registry.

Each workbench preserves the endpoint title, stable ID and exact Registry type, originating
Hub links, direct Component context, separate architecture/implementation/technical-
verification axes, exact source → relation → target rows, accepted historical technical
Evidence links, Canvas link and low-friction return navigation. MeasurementPoint pages
state that measurement validity, scientific evidence/effect and accepted claims are not
established by the relation or view.

Each Canvas is valid JSON Canvas 1.0 JSON. It is endpoint-centered and contains only the
curated direct technical relation set shared with its Markdown workbench. Arrows preserve
Registry source and target, and labels retain the exact relation name. Historical
implementation provenance is limited to the same accepted `EVID-48-*` implementation
Evidence selected by W04. Cards use a type marker plus a readable type label and stable ID;
their relative Atlas-record links resolve in the workspace. Presentation grouping, return
navigation and layout cues do not create semantic edges. Node and edge IDs are stable
hashes of Registry identities or exact relation triples. JSON key/order/coordinates are
deterministic; no machine-specific Canvas configuration is written.

Manifest v2.4 may add only the fourteen exact W05 files derived from the seven IDs above.
Prior v1.0–v2.3 manifests retain only their previously declared finite paths and may
migrate to v2.4 on write after the existing owner, digest, path and authored-content checks
pass. Unknown or unowned files still block writes; edited obsolete owned files are not
deleted. `--check` remains zero-write. These generated workbenches/maps are presentation
only and do not establish technical authority, measurement validity or scientific claims.
Actual-vault G6 remains a separate acceptance gate after CONTROL reviews the exact PR head.

## W06 Component-scoped Research views

W06 updates the existing Memory Retrieval and Independent Verifier `Research.md`
pages using one shared model. It adds no generated path or Base. Each page shows
only the exact current Registry `related_to_research_question` edges declared by
its Component, with the actual direction, both stable identities, the human
Research Question name and a link to the public technical projection record.
The Registry relationship lane remains distinct from private literature
navigation and does not imply literature coverage or a scientific result.

The literature section filters the existing Declared Reference Index to
eligible N-C `navigation-path` rows ending at the exact public Component.
The index remains the path authority; this view adds no traversal, parent or
Domain rollup, role inheritance, ranking, top-k or truncation. Every selected
row shows its Paper/source identity, direct/derived path kind, recipe, complete
ordered `via` edges, actual declaring record/type/revision, originating
property and verbatim role, exact Component target, prerequisite references
and row ID. These fields keep the role on the record that declared it and make
each navigation path traceable to its source declaration.

Unresolved and wrong-type declarations stay visible in the existing Direct
Reference Audit through the page's Declared Literature Navigation link; they
are not promoted into eligible Component paths. The current Component-specific
empty state is `No matching declared Component literature paths are present in
this snapshot.` It makes no claim about literature absence, research absence,
novelty, a gap, completeness or priority. Private record bodies remain
unprojected; generated links use relative, encoded locators only.

W06 changes only the bytes of the four already-owned Hub child pages. The
manifest remains v2.4 and adds no ownership entries; the K3 Markdown view
schema advances to `1.5`. Deterministic selection and rendering use the
current Registry and existing structured index rows. `--check` remains
zero-write. Actual-vault G6 remains gated on CONTROL approving the exact PR head.

The fingerprint includes every authored private identity/type/profile/revision
and consumed RA-2 reference sets in deterministic order. It excludes bodies,
titles, paths and unconsumed metadata. Relevant edits cause `--check` drift;
body-only edits without relevant revision/reference changes leave YAML unchanged.
A separate read-only locator scan excludes all `_generated` content and does not
follow authored symlinks. Locators affect Markdown links only: a note move can
change Markdown without changing YAML; a whole-vault move with relative paths
preserved changes neither. Link segments are encoded; unresolved IDs are escaped
plaintext. No private absolute paths or unselected secrets are emitted.

Strict v1/v2.0 manifests may migrate in place to v2.1 on write. Their `--check`
returns drift (exit 2) and never migrates or writes. Unknown versions fail closed.
V1 cannot claim YAML ownership; v2.x permits only exact schema-versioned paths. Prior
versions can name only their previously declared fixed paths, with W02 hierarchy, W04 Hub
children and W05 detail paths added by their respective manifest versions. YAML
owner/schema markers, Markdown owner markers, Base ownership-class validation and
all prior ownership/path checks must pass before writes. Unknown
files are never adopted; edited obsolete files are never deleted. The manifest
remains last after per-file atomic writes.

RA-1 exactness, source-ref/HEAD, topology, marker, source cleanliness, Registry
and RA-2 validation remain mandatory preconditions. No automatic RA-1 repair is
performed. `--check` remains strictly write-free, including no temporary files
or cleanup, and unresolved-only/empty output is a valid state. Use a single
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
