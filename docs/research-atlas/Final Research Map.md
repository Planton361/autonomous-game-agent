# Final Research Map operator contract

Issue #159 implements the revised information architecture accepted in #158,
Program Owner comment 6018075117. This is generated presentation and ownership
migration; Registry, scientific schemas, fingerprints and authored Research
remain their existing authorities.

## Current generated tree

```text
Research Map Home.md
Research Map/
  System/
  Components/                 # exact single System containment chain
    Identities/               # reserved ambiguous/no-System-chain flat route
  Functions/
  Interfaces/
  Contracts/
  Data Artifacts/
  Measurements/
  Environments/
  Program/
    Research Questions/
    Research Threads/
  Project/Decisions/
  Research/Question Readers/
  Views/
    Research Steering.md
    Literature Inspection.md
    Graphs.md
  Graphs/<CMP-ID>.md
  Diagrams/
    Architecture Tree.md
    Architecture Tree.canvas
    Execution Flow.md           # Ablaufdiagramm: Mermaid + Markdown fallback
    Agent Anatomy.excalidraw.md
    Evidence, Memory & Retrieval.excalidraw.md
    Technical Relations/      # seven native Canvas endpoints
  Tables/                     # three Bases
  Guides/Using the Research Map.md
_Research Map Internals/
  Registry/Records/
  Registry/Evidence/
  Indexes/
    atlas-id-index.yaml
    declared-reference-index.yaml
    source-resolution-index.yaml
  Audit/
    Declared References.md
    Source Details.md
  Graphs/<CMP-ID>/
    Edge Audit.md
    Architecture/Nodes/
    Knowledge Detail/Nodes/
    Questions/Nodes/
    Questions/Question Overlay/
  Assets/Agent Anatomy Hero.svg
  Manifests/
    technical-atlas.yaml
    research-map.yaml
  Migration/routes.yaml
```

Empty reserved families need no placeholder files. Internal storage has no
landing page. Open or bookmark **Research Map Home** manually; the generator
never writes `.obsidian` startup, bookmark, graph or plugin state.

Navigate System → Component → subcomponent through Registry `part_of` only.
Functions and other typed contexts create no Component ancestry. Ambiguous or
missing unique System ancestry uses
`Research Map/Components/Identities/<human title> — <CMP-ID>.md`, while the page
shows every actual structural path. Stable-ID order selects no parent.

Preferred technical pages share Home, Technical / Research / Sources navigation,
state and limitations, typed content, compact verification, collapsed complete
audits and return navigation. Retired Technical Detail Markdown and Hub auxiliary
content is retained in collapsed preferred-page audits. Raw Registry pages are
internal inspection surfaces. Agent Anatomy and the Domain diagram are secondary.
Markdown readers and mode-specific audits remain usable without rich plugins.

Home presents task-oriented entry points before collapsed complete identity
inventories. System/Component pages start with compact exact structural navigation;
large child-card inventories are collapsed. Function participant tables expose
technical types. Research Steering presents scientific inventories before one
Graph catalog route; source/history detail remains secondary.

Agent Anatomy is a selective explanatory overview of roles and safety boundaries,
not complete architecture, exact Function membership or strict runtime order.
Its explanatory placements do not change Registry memberships. Executive Control
is the accepted Function wording; a bounded Skill Contract remains a Contract.
Between-run learning remains conditional on an authorized future protocol.

Graph mode links target the distinct Architecture, Knowledge Detail and Questions
headings in each consolidated guide/audit. Identical guide instructions are shared,
while filters, nodes, directed pairs, origins and diagnostics remain mode-specific.
Canvas technical cards open preferred identity pages first, with raw Registry
records behind audit disclosure. Evidence cards are explicitly provenance/audit
destinations, not invented preferred technical identities. Canvas relations are
unchanged.

Public program questions/threads, private RQ reading projections and public
project Decisions have separate routes. Private RQ masters remain editable at
their authored locations. Every other private scientific class retains its exact
authored preferred page; no generic generated scientific-reader family exists.

Each Component has one Graph guide and one Edge Audit. Architecture, Knowledge
Detail and Questions have distinct sections and proxy directories. Audit identity
is `(Component, mode, directed pair)`. Every origin, node, detail-only endpoint,
inspection route and sparse-state diagnostic survives consolidation. Filters
select only the corresponding internal proxy folders, never guides or audits.

## Architecture Tree

Issue #162 adds the first visualization step at
`Research Map/Diagrams/Architecture Tree.md`. Reach it from Home's **Start here**,
the navigation guide, or the Home/orientation row on every System and Component
preferred page.

The primary page includes a native Obsidian Canvas embed, a direct **Open
Architecture Tree Canvas** link and the complete linked Markdown hierarchy.
Canvas requires no community plugin. The embed is a shape overview;
[Obsidian displays card text only in the opened Canvas](https://obsidian.md/help/embeds).
Use the direct link for labels and identity navigation. If Canvas rendering or embedding is
unavailable, read **Linked Markdown tree** on the same page. Each visual card and
Markdown entry opens the existing preferred identity page; neither creates a new
technical identity or duplicates a scientific reader.

The visual reads parent → contained Component from left to right. Unarrowed
`contains` lines invert the Registry's child `part_of` parent declaration for
presentation. Markdown indentation expresses exactly the same ancestry.
Only `part_of` contributes edges. Siblings sort by human title with stable ID as
a tie-breaker, without architectural priority or runtime ordering. Multiple
containment paths repeat the same identity under all actual parents, retaining
one preferred page. Components without a System chain appear as detached roots;
the generator invents no System attachment.

Cards and Markdown entries show Registry implementation status, including
target-only and partial identities. The tree is composition, not proof of
capability, execution order or scientific results. Identity pages retain the
responsibility, verification and limitations. **Context outside ancestry** links
to Functions and other typed inventories, preferred pages and existing Component
Graph guides. Functional participation, Domain grouping, control, evidence and
Research relations never become tree ancestry.

Both new files use existing `research-wiki-derived` ownership. Markdown remains
strict-byte owned; Canvas uses the existing closed Canvas semantic rules. No
ownership, migration, recovery, save-stability or `.obsidian` policy changes.
The #162 empty-private synthetic output was **522 files**, adding these two
artifacts to the accepted #159 **520-file** baseline; #164 adds one page (523 total).
Actual-vault rollout and #161's on-hold disposition remain separate; this Delivery does not apply or
repair the installed vault and does not establish Linux/Mac G6.

Architecture Tree is the first of the three visualization steps. Issue #164 adds
only step 2 below. Interaction Map remains a later bounded contract.

## Ablaufdiagramm / execution flow

Issue #164 adds one first-class generated Markdown page:
`Research Map/Diagrams/Execution Flow.md`, display title **Ablaufdiagramm**.
Reach it from Home's **Start here**, **Using the Research Map**, or the Home row
on the System, Cortex, Manager, Body, Independent Verifier and Executive Control
preferred pages. Its linked identity/status table opens existing preferred
System/Component/Function/Contract/DataArtifact pages; navigation does not depend
on Mermaid click handlers. No new identity, Registry relation or technical
ancestry is inferred from a process arrow.

The native Obsidian Mermaid flowchart shows normative authority prerequisites:
admissible observation/evidence → event-driven Cortex intention → Manager
validation → bounded Skill Contract → Body/eligible Reflex proposal → separate
SafetyFilter/InputExecutor gate → visible outcome → independent Verifier →
Manager evaluation. Rejection records no executed action. Continued execution
requires a valid active contract; a meaningful replan follows contract
closure/suspension. Death closes a Life Episode; permitted restart preserves the
Mission Run's frozen identities and Body weights. Optional future
replay/training/held-out validation/certification is outside the running Mission
Run and requires a separately authorized protocol.

These arrows explain intended control, not a deterministic per-frame schedule or
strict order for asynchronous internals. The complete numbered **Markdown
fallback** covers every gate and branch with canonical source locators and the
accepted `ALIGN-2026-09-19-v1.0` overlay. It remains readable with Mermaid disabled.
Native visual rendering remains **unverified until inspected in Obsidian**.
No community plugin, new backend, parser, Canvas or external media is added.

The implementation table reads individual Registry statuses, including
`target-only` Temporal State, Reflex and Body certification. Functions have no
implementation-status field. Current bounded hierarchical/replan code and guarded
input are linked separately; neither those code surfaces nor the drawing proves
a demonstrated full live loop, a Phase-D/H exit or a scientific result. Missing
Registry mappings imply no omitted capability or scientific weakness.

With frozen identical synthetic inputs, the independent exact-main baseline
comparison adds only this page and changes Home, the generated guide, six
orientation pages and the derived manifest. Empty-private output is **523 files**.
The page uses existing `research-wiki-derived` **strict-byte** ownership; the
manifest updates normally. Architecture Tree Markdown/Canvas, seven Technical
Relations Canvases, Bases, Excalidraw, Graph modes, Registry projections, source
indexes, migration routes and the technical manifest remain byte-identical.
Actual-vault ownership/save/recovery and #161's ON HOLD state are separate;
#164 authorizes no vault apply/check/repair or Linux/Mac G6.

## Supported migration and recovery

Final manifests now use product schema `1.1` with one closed ownership class per
file: `strict-bytes`, `obsidian-base-semantics`, `obsidian-canvas-semantics` or
`obsidian-excalidraw-semantics`. Every row keeps the emitted-byte SHA-256; managed
formats additionally keep a semantic SHA-256. The two logical owners and ownership
classes are unchanged; the finite inventory includes the two Architecture Tree
artifacts. Ordinary Markdown, indexes, Registry projections, manifests,
ledger and the illustration remain exact-byte owned.

Bases retain the accepted YAML and note-property shorthand equivalences, including
removed owner comments; the manifest's finite path, owner and matching semantic
digest prove ownership. Canvas accepts object-key/formatting changes and the
documented `fromEnd=none` / `toEnd=arrow` defaults and equivalent JSON numeric
spellings (`40` / `40.0`). Nodes, edge order, endpoints,
sides, labels, metadata, preferred links, geometry and styling remain protected.

Excalidraw accepts YAML/JSON object reserialization, plain or LZ-string Base64
compressed drawing sections, cache section spacing, equivalent JSON numeric
spellings and element `version`, `versionNonce`, `updated` bookkeeping counters.
Restored fractional `index` keys are accepted only when all keys are valid and
strictly increasing in the unchanged element/stacking order (or all are absent).
Exact restore defaults are normalized: `created=null`, `hasTextLink=false`, empty
`boundElements` (`null` / `[]`), text `labelPosition=null` / `baseFontSize=null`,
and image `crop=null`. Non-default values, bindings and ordering changes stay
protected. These rules follow the pinned [ordering](https://github.com/zsviczian/excalidraw/blob/6a4e51cc8e343f484f47d306ac9c09e1db515cb0/packages/element/src/fractionalIndex.ts)
and [restore implementation](https://github.com/zsviczian/excalidraw/blob/6a4e51cc8e343f484f47d306ac9c09e1db515cb0/packages/excalidraw/data/restore.ts)
in the plugin's `@zsviczian/excalidraw` dependency `0.18.140`.
The finite save-time editor/viewport/tool preference keys in `EDITOR_FIELDS`,
plugin release exporter URL and previous editor text mode are normalized. These
are verified against the [plugin's save implementation](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/f30b4c5d3dcb66ac76ced8f05d9e95409ee94c79/src/view/ExcalidrawView.ts).
No wildcard appState stripping is allowed: the scene background and every unknown
field remain protected; frame visibility is also protected if a future generated
scene contains frame elements. The Anatomy illustration may be inline or externalized
only with its exact image identity, strict generated SVG digest and embedded-file
route. It preserves all other scene fields, element/stacking order, geometry,
styles, image semantics, links, customData, Registry triples, visible labels,
Markdown text/link/embedded-file caches, project prose and every frontmatter,
provenance and privacy field. Unknown
churn is not silently discarded. A semantic edit or missing owner/schema fails
closed; adding authored prose to a generated diagram is not an allowed save.

Historical product manifest `1.0` remains readable. Rewritten old Canvas/Excalidraw
may migrate only when regeneration with the recorded source revision produces
bytes matching the old emitted SHA-256, then the current file matches that trusted
reference semantically. If prior inputs cannot be reproduced, migration blocks;
the current file is never its own ownership oracle. `check` detects an outdated
manifest; supported `apply` advances it without manual deletion.

Historical reference resolution does not execute manifest-selected code. The
recorded `8e544d2e05180306a9580b5475c03e0bd91601ac` public/empty-input lineage
uses pinned original emitted data independently produced by that exact historical
code and assets. Its local immutable Git tree, original manifests, emitted hashes
and admissible-input provenance must agree. Current rendered bytes with an old
commit label are not a historical oracle. Other revisions require byte-identical
renderer code/assets in local Git; unsupported or unreproducible inputs block.
The reference's generation record is in
`src/fh_agent/research_atlas/historical_references/README.md`. Resolving historical
bytes does not accept new semantic differences or authorize an actual-vault apply.

Checks remain zero-write. Apply proves ownership before restore-point creation,
validates the copied snapshot, then restores canonical emitted bytes. External
receipt schema `2.0` records exact before/after digests and ownership/semantic
records. Recovery verifies exact saved before bytes and receipt metadata before
mutation, accepts only proven equivalent managed current output, restores the
original plugin-written bytes, and blocks real edits. Historical exact receipts
remain readable and retain their exact current-output guard.

Use a clean, reviewed exact checkout and the existing marked external vault.
Under #159, actual-vault use requires later CONTROL G6 authorization on an exact
reviewed PR head. Implementation tests use temporary synthetic vaults only.

```bash
uv run --no-sync fh-agent workspace apply --vault-root "$PRIVATE_VAULT"
uv run --no-sync fh-agent workspace check --vault-root "$PRIVATE_VAULT"
```

The harness inventories both old roots and every final destination before any
write. It validates finite old manifests/owners/hashes, final manifests, semantic
Base ownership, collision and portability boundaries, symlinks, immutable source
history and exact read-version protections. Edited, unowned, owner-lost, corrupt,
ambiguous or colliding content fails closed. It never adopts authored content.

An external never-overwritten restore point covers both old roots, both final
namespaces and root Home, including absence. Its `migration-plan.json` records
exact before/after path digests and source head. Replacements are per-file atomic,
read back before legacy retirement, and the two owner manifests commit last.
The logical owners remain `public-research-atlas` and `research-wiki-derived`.
There is no whole-tree atomicity or concurrent-editor lock: use one writer and
pause concurrent edits/Sync during generation. Check remains zero-write.

A successful apply retires the old owned tree and emits the migration ledger.
There are no permanent redirects. The older projector renderers remain pure
intermediate/test surfaces and bounded legacy readers, not the operator workflow;
they reject direct regeneration after final Home exists. Unsupported historical
routes fail closed instead of acquiring wildcard ownership.

After interruption, check/apply fail closed on uncommitted output. Recover
explicitly from the reported external receipt, from the same clean source head:

```bash
uv run --no-sync fh-agent workspace recover \
  --vault-root "$PRIVATE_VAULT" --restore-point "$RESEARCH_MAP_RESTORE_POINT"
```

Recovery validates every existing generated byte against before/after receipts
and every restored byte against its owned backup digest before mutation. The receipt
must match the same source head and frozen authored/catalog inputs. Operator edits,
unknown outputs, corrupt backups and source-head mismatch block recovery. It
restores generated files only, verifies the restored inventory, then apply/check
can be retried. It never restores or edits authored Research/catalog or `.obsidian`.
Keep external restore points private. Optional Zotero ownership stays independent.

Missing ordinary generated payloads can be reconstructed from intact manifests.
Missing immutable source-history indexes require restoration of manifested bytes.
Both generated namespaces and `_generated` are excluded from authored discovery;
Direct Views Base filters exclude them too. Technical Base routes select internal
Registry records. All WikiLinks, relative Markdown links, Canvas routes, Graph
filters and source/reference routes use final destinations.

## Evidence and remaining gate

The #159 automated empty-private synthetic baseline had 696 legacy files and 520
final files: 176 fewer (25.3%). With #162's two Architecture Tree artifacts, synthetic
output was 522 files, 174 fewer than the legacy baseline. With #164, current
output is 523 files, 173 fewer than that baseline. These are not actual
private-vault counts. Populated
synthetic tests prove no duplicate non-RQ readers, exact per-mode Graph parity,
portable links, source protections, deterministic/idempotent generation, authored
preservation, zero-write checks and bounded interruption recovery.

Stop at CONTROL exact-head PR/diff/CI review. Actual-vault hard-path compatibility
inventory and Linux → existing Sync → Mac G6 remain later authorized work. Do not
inspect/populate authored Research to manufacture examples. Authored hard-path
references may require separately authorized repair; this Delivery provides no
unproven redirects and no authored migration. User merge remains gated on G6 and
explicit M0 authorization.

Presentation repairs change generated bytes. A previous actual-vault apply/check
does not certify the repaired head; do not apply it until CONTROL reviews that exact
head. The Ablaufdiagramm is the bounded #164 Delivery described above. Interaction
Map remains future work; no later diagram or actual-vault rollout is authorized here.
