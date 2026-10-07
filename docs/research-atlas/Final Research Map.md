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

## Supported migration and recovery

Final manifests now use product schema `1.1` with one closed ownership class per
file: `strict-bytes`, `obsidian-base-semantics`, `obsidian-canvas-semantics` or
`obsidian-excalidraw-semantics`. Every row keeps the emitted-byte SHA-256; managed
formats additionally keep a semantic SHA-256. The finite inventory and two logical
owners are unchanged. Ordinary Markdown, indexes, Registry projections, manifests,
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

The automated empty-private synthetic baseline has 696 legacy files and 520 final
files: 176 fewer (25.3%). This is not an actual private-vault count. Populated
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
head. Architecture Tree, Ablaufdiagramm and Interaction Map remain future work,
not part of this presentation repair.
