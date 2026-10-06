# Bounded native Knowledge Graph — scoped Component profiles

Current generated routes and supported global ownership migration are specified in
[Final Research Map](Final%20Research%20Map.md) (#159, accepted #158 target).
Older path/pipeline descriptions below are retained as implementation history;
the final operator workflow supersedes those presentation routes. Actual-vault
migration still requires CONTROL exact-head review and separate G6 authorization.

## Current #127 profile contract

Native Obsidian Graph remains the only renderer. The primary orientation is the
explicit Registry System / Component skeleton with exact Research attachments.
There is no default vault-wide mega-graph. Every current Registry Component gets
three disposable profiles, including nested Components and scopes with no mapped
knowledge. The retained `memory-retrieval` pilot below is a compatibility route;
preferred Component pages now open the scoped `architecture` profile.

```text
_generated/derived/knowledge-graph/components/<CMP-ID>/
  architecture/
    Graph Profile.md
    Edge Audit.md
    nodes/<Class> - <label> — <durable-ID>.md
  knowledge-detail/
    Graph Profile.md
    Edge Audit.md
    nodes/<Class> - <label> — <durable-ID>.md
  rq-overlay/
    Graph Profile.md
    Edge Audit.md
    nodes/<Class> - <label> — <durable-ID>.md
    optional-rq-overlay/<Class> - <label> — <durable-ID>.md
```

For example, the primary nested Facts scope uses:

```text
path:"_generated/derived/knowledge-graph/components/CMP-MEM-FACTS/architecture/nodes/"
```

Optional epistemic detail uses:

```text
path:"_generated/derived/knowledge-graph/components/CMP-MEM-FACTS/knowledge-detail/nodes/"
```

The explicit optional question profile uses:

```text
(path:"_generated/derived/knowledge-graph/components/CMP-MEM-FACTS/rq-overlay/nodes/" OR path:"_generated/derived/knowledge-graph/components/CMP-MEM-FACTS/rq-overlay/optional-rq-overlay/")
```

Use only one scoped expression at a time. Profile companions and authored pages
stay outside these expressions. Follow the manual native Graph instructions below;
the generator never creates `.obsidian/graph.json` or changes operator settings.
Switch profiles from their generated instructions, and restore the architecture
expression to turn questions OFF. Orphans ON keeps disconnected selected nodes
visible. Filenames explicitly carry classes; optional colors are only aids.

### Selection and closure

The selected Component owns its explicit `part_of` descendant subtree. Only this
subtree seeds knowledge selection; ancestors are orientation context. Selection
reuses the accepted finite N-C prefixes terminating at exact scoped Components,
and one explicit Synthesis `finding_refs` or Topic `paper_refs` / `finding_refs`
join to the frozen core. No recursive scientific traversal or inferred attachment
is introduced. Exact participating Components declared by selected knowledge add
their own required ancestry but do not select their other Research or siblings.

Only Registry `part_of` creates technical depth. Every displayed skeleton edge is
an authored Registry declaration between included identities. Function, Domain,
Assembly, folder and Graph proximity never create ancestry. Research attached to a
child is still attached only to that child; parent/child relevance is never inherited.

| Profile | Node classes | Semantic edge families |
| --- | --- | --- |
| Architecture (primary) | System root context, Component, eligible current Paper / ReadingNote / Finding / Synthesis / explicitly linked Topic | Registry `part_of`; accepted E9 exact attachment properties; minimal declared knowledge links incident to otherwise unanchored selected knowledge |
| Knowledge detail (optional) | Same classes and same technical skeleton | Architecture families plus all accepted selected E1–E5 declarations and explicit Synthesis/Topic joins |
| RQ overlay (explicit optional) | Architecture classes plus ResearchQuestion and exact overlay-only Component targets / ancestry | Architecture families plus current RA-2 0.3 RQ-owned `research_direct_subject_refs`; multi-target questions allowed |

The architecture profile suppresses knowledge-detail pairs when both endpoints
already have exact Component attachments. It retains explicit links needed to
orient unanchored selected knowledge without pretending those links establish an
E9 attachment. The knowledge-detail profile preserves all eligible selected
relations, their source property, direction, version and structured origin.
Questions are labeled ResearchQuestion and remain OFF in both ordinary profiles.
RQ targets never expand knowledge selection and never create inherited targets.

System, Interface, Contract, DataArtifact and MeasurementPoint exact Research
attachments retain preferred-page inspection routes and property/version audit
information. Non-Component attachment edges are detail only. This Delivery does
not accept a dedicated deep-endpoint or SourceFamily/SourceVersion topology
profile. Technical Evidence also remains detail inspection.

### Navigation and audit

Anatomy reaches nested preferred Component pages through existing technical
navigation. Every preferred Component page links to its scoped architecture
profile, Edge Audit, Anatomy, Research Landscape / Steering and generated detail.
Profile pages switch among the three modes. Graph nodes state their durable ID
and the exact companion audit path in plain text: open that companion outside the
filtered node folders for preferred knowledge detail and exact affected Component
routes. Return from preferred Component pages to Anatomy. The audit provides the
complete Markdown fallback with technical skeleton and research/knowledge edge
families separated, even if the native force layout is difficult to read.

Generated Source Details provides the reverse record → exact affected identity →
scoped profile/audit routes. Generated preferred RQ detail pages also offer their
exact Component profiles and the explicitly optional RQ overlay. Authored private
pages remain unchanged; when reading authored knowledge, its reverse routes live
in these generated companions. No navigation links are added to proxy topology.

Every directed proxy link has exactly one directed identity-pair Edge Audit row.
Parallel declarations share that link, retaining every relation/property, exact
origin, source version and direction in the row. Native Graph cannot draw typed
project edges or guarantee a literal hierarchy layout; labels, Markdown inventory
and audit preserve meaning. Position, centrality, distance and density have none.

Excluded nodes: Decisions, Issues, PRs, milestones, Project/control artifacts,
indexes, manifests, presentation duplicates, Function/Domain/Assembly, technical
Evidence and unaccepted deep/source topology classes. Excluded edge origins:
navigation, backlinks, return links, folder placement, Domain/Function/Assembly
membership, tags, title/DOI/embedding similarity, proximity, inherited Research
roles, ancestor rollups, generic BFS/DFS and transitive scientific closure.

### Ownership, privacy and sparse states

Manifest 2.17 adds the finite scoped path grammar; Graph metadata 1.1 applies to
those files. Historical manifest versions, including 2.16's pilot, retain their
existing path authorities and cannot claim new scoped files. Existing migration,
restore, strict digests, zero-write checks, edited-generated and unknown/unowned
fail-closed behavior remain in force. One durable identity has one node per
profile and one preferred page overall. Proxies remain disposable. All profile
outputs are private / export deny; public workspace generation receives none.

No mapped knowledge still yields the selected technical skeleton, instructions,
Markdown inventory and neutral diagnostic. Sparse, disconnected, unresolved and
large inventories use the same deterministic scope contract, never silent
truncation or arbitrary densification. A large selected subtree can still have
many nodes; choose a nested scope to bound the view further. Counts and missing
content imply no literature absence, gap, novelty, completeness, exhaustion,
priority, quality, evidence strength or scientific weakness.

Tests retain the #119 regressions and add nested multi-branch scope, exact
cross-component attachment, duplicate identity, no inheritance, profile/RQ
filtering, deterministic reordered input, proxy/audit parity, migration from
2.16, private isolation, sparse/large inventories and navigation coverage within
`tests/test_knowledge_graph.py`. The existing required module remains in the
58-module fast manifest; no tier or timing gate changes are made.

Actual private-vault apply/check and human G6 are deferred until CONTROL reviews
the exact source/CI head and separately authorizes those actions. G6 must confirm
the technical skeleton is recognizable in native Graph, both navigation directions,
profile switching, exact attachments, Edge Audit, sparse state, Markdown fallback
and unchanged global settings.

## Retained #119 Memory Retrieval pilot

Issue #119 implements the native Obsidian Graph pilot released by CONTROL
[5963330134](https://github.com/Planton361/autonomous-game-agent/issues/119#issuecomment-5963330134)
and clarified by
[5963456188](https://github.com/Planton361/autonomous-game-agent/issues/119#issuecomment-5963456188).
The Component skeleton repair follows CONTROL
[5968367667](https://github.com/Planton361/autonomous-game-agent/issues/119#issuecomment-5968367667).
It preserves accepted #102/#137 semantics, the exact #121 attachments, #125 RQ
target authority, #123 source inspection and #126 Research Steering. That pilot alone does not
implement #127. These are generated navigation views, never scientific masters,
a graph database, an accepted Claim or a literature completeness assessment.

## Projection and durable identity

The existing private workspace harness generates this finite extension inside
its existing `_generated/derived/` owner:

```text
knowledge-graph/memory-retrieval/
    Graph Profile.md
    Edge Audit.md
    nodes/<sanitized human title> — <durable ID>.md
    optional-rq-overlay/<sanitized human title> — <durable ID>.md
```

One proxy represents one durable identity. Registry records, preferred Identity
Pages, Component Hubs, Technical/Research children, indexes, workbenches, Canvas
and Excalidraw never create additional identities. Filenames carry the identity
suffix; titles are presentation, never identity resolution. Titles are escaped
in bodies and sanitized in filenames/link aliases. Proxies contain generated
owner/path/class/identity metadata, disposable-projection wording and their
outgoing semantic links. They have no RA-2 authored-record envelope.

Sources are the actual public Registry and validated private RA-2 structured
records. Eligible knowledge records have `in_review` or `domain_accepted`
document maturity, following the existing reader eligibility contract. This
eligibility is not scientific acceptance, source verification or evidence quality.
Private Paper records are supported; public Paper records are not automatically
expanded into this private pilot. No real literature is included in the repository.

The default inventory includes the Memory Retrieval Component (also in an empty
snapshot), eligible Paper/ReadingNote/Finding in its exact direct attachments or
existing accepted N-C K0–K3 prefixes, and one explicit Synthesis/Topic join to
that frozen core. Synthesis joins through its `finding_refs`; Topic joins through
its `paper_refs`/`finding_refs`. A join does not expand their other targets or
create a research role. Only explicit Component targets of selected records become
additional participating default Component anchors.

Component hierarchy provides orientation. Research objects remain attached only
through explicit scientific declarations. Tree position does not infer scientific
relevance. Each participating Component includes its complete explicit Registry
`part_of` ancestor path, including System root context. Only these ancestors are
added: no siblings or unrelated descendants. The default skeleton is computed
before optional RQ targets; overlay-only targets and their ancestors remain in
the overlay unless already in the default skeleton. Every ancestor has one proxy.

Current Registry truth: Memory Retrieval and Cortex each point directly to
`SYS-AGA`; Semantic Facts points to Memory, which points to `SYS-AGA`. The
committed fictional baseline therefore has three default skeleton nodes/two
edges; the overlay adds two Component nodes/two skeleton edges. Memory Retrieval
is not a child of Memory. These are navigation counts, not scientific metrics.

Excluded: Decision/DecisionDraft, Issue/PR/milestone/Project/control/orchestration,
manifest/index/navigation, technical Evidence, raw SourceFamily/SourceVersion,
Interface/Contract/DataArtifact/MeasurementPoint anchors, Domain/Function/
Assembly and all presentation duplicates. Exact non-Component technical targets
remain available through the existing detail/attachment inspection routes.
Direct, descendant and related Research retain their existing distinctions;
no ancestor receives a child's Research role.

## Exact semantic edge families

The projection emits authored forward directions, not traversal shortcuts:

| Family | Actual declaring property | Eligibility |
| --- | --- | --- |
| Technical skeleton | Component `part_of` → Component/System | Exact public Registry relationship; selected ancestor closure only |
| E1 | ReadingNote `paper_refs` or `source_refs` → Paper | Existing resolved typed declaration |
| E2 | Paper `reading_note_refs` → ReadingNote | Existing exact ReadingNote source back-reference prerequisite |
| E3 | Finding `source_refs` → Paper | Existing resolved typed declaration |
| E4 | ReadingNote `finding_refs` → Finding | Existing resolved typed declaration |
| E5 | Finding `reading_note_refs` → ReadingNote | Existing resolved typed declaration |
| E9 | Paper/ReadingNote/Finding five research-role properties → Component | Existing exact terminal resolver, Component class only |
| Structured membership | Synthesis `finding_refs` → Finding | Explicit current schema field; target in frozen core |
| Structured membership | Topic `paper_refs`/`finding_refs` → Paper/Finding | Explicit current schema field; target in frozen core |
| Optional RQ | ResearchQuestion `research_direct_subject_refs` → Component | Eligible current RA-2 0.3 question explicitly targets Memory Retrieval; current exact target resolver |

E9 preserves `research_direct_subject_refs`, `research_method_or_baseline_refs`,
`research_measurement_relevance_refs`, `research_project_transfer_refs` and
`research_adjacent_context_refs` verbatim. Shared membership is not a shortcut
Paper–Finding or Synthesis–Component edge. Source catalog objects remain
inspection-only. Unresolved, wrong-type, unsupported or outside-slice references
produce diagnostics and no edge.

No edge comes from navigation/backlinks, folder membership/co-location, Domain,
Function, Assembly, title/DOI similarity, tags, embeddings, geometry, inherited
roles, arbitrary Research BFS/DFS or transitive semantic closure. The only
ancestry closure is explicit Registry `part_of` for technical orientation.
No relationships are added to make a graph denser.

One full vault-relative internal proxy link is emitted per directed identity pair.
Parallel declarations share that link and one audit row retaining every property
and origin. Native Graph may visually collapse reciprocal or parallel links;
the directed proxy-link set and directed audit-pair set are exactly equivalent.
Origins identify the declaring record/revision and DRI row/E-family, or the exact
structured Synthesis/Topic/RQ property. Skeleton origins identify the exact public
Registry source–`part_of`–target declaration. The audit has an Edge class column:
`technical skeleton` versus `research / knowledge`. Native Graph has no
project-specific typed edge labels. The companion is the semantic precision layer.

## Native Graph activation

The [native Graph documentation](https://obsidian.md/help/plugins/graph) describes
nodes, internal-link edges, Search files, Groups, Tags, Attachments, Existing files
only and Orphans. Its search box uses the
[Search query syntax](https://obsidian.md/help/plugins/search), including `path:`
and grouped `OR`. The reproducible default filter is:

```text
path:"_generated/derived/knowledge-graph/memory-retrieval/nodes/"
```

Enable the explicit RQ overlay by replacing it with:

```text
(path:"_generated/derived/knowledge-graph/memory-retrieval/nodes/" OR path:"_generated/derived/knowledge-graph/memory-retrieval/optional-rq-overlay/")
```

Open the native global Graph from the ribbon, then Graph settings → Filters →
Search files. Paste the default filter. Set Tags OFF, Attachments OFF, Existing
files only ON and Orphans ON (so an empty snapshot still shows its Component).
Arrows may be enabled for declared direction. Restore the default expression to
disable questions. Use global Graph, rather than Local Graph's distance filter.

Questions have `Research Question` filenames and explicit classes, distinguishable
without colors. An optional presentation Group is:

```text
path:"_generated/derived/knowledge-graph/memory-retrieval/optional-rq-overlay/" file:"WRQ-"
```

Color carries no scientific meaning. The overlay uses only eligible RA-2 0.3
RQ-owned exact `research_direct_subject_refs`, preserving many-to-many targeting.
One question stays one node. Additional explicitly targeted Components
and their required ancestors appear
only in the overlay unless already in the default skeleton. Exact
deep endpoint targets remain on the RQ reader/detail routes. Paper/Finding,
nearest-work, ancestry and proximity never infer question targets.

No global Graph settings or `.obsidian/**` file is generated or changed. A saved
project-local profile is not imposed on user-owned Graph settings; activation is
manual. Operator excluded-file patterns can hide expected notes and require
manual inspection. Actual native rendering/filter behavior is reserved for human
G6; automated parity does not certify an interactive journey.

## Companion, navigation and sparse states

`Edge Audit.md` contains `Knowledge Graph — Memory Retrieval`, Graph profile,
Nodes, Edge Audit, Navigation / inspection and Sparse state sections. Human titles
precede stable IDs. Graph Profile documents classes, exclusions, filters, settings
and limitations. The pair is a sufficient Markdown fallback when Graph is ignored.

Memory Retrieval's preferred Identity Page and Component Research link to both
companions. Existing Anatomy links resolve to that preferred identity. Companion
navigation returns to exact preferred technical pages, authored knowledge detail
(or preferred RQ reader), Agent Anatomy, exact attachment audit, Source Details
and complementary Research Steering. Proxies contain no such links. Both filters
include only the node folders, excluding companions and all external navigation
notes; therefore return/Home/index/source links cannot contaminate topology.

A Graph node opens its proxy; read its stable identity and inspect that identity
in the companion navigation inventory. No new URI mechanism or plugin is required.
Unavailable authored detail is explicit rather than a fabricated link.

Supported states: no matching documented knowledge, unresolved reference,
unsupported/excluded relation, unavailable detail route, knowledge at another
exact technical scope and no eligible questions in the overlay. These do not
imply literature absence, novelty, gap, completeness, saturation, scientific
weakness, evidence strength, research value or priority. No scientific graph
metrics are calculated. A Memory Retrieval/System skeleton without knowledge
is a valid sparse view.

## Ownership, migration and privacy

The existing owner `research-wiki-derived` and strict byte hashes own only the two
companions and the finite one-per-ID node set above. Manifest version **2.16** adds
this path family, including Component/System identity suffixes; DRI 1.2,
presentation fingerprint 1.1 and source fingerprint 1.0 remain unchanged. Graph inputs already participate in existing structured input
fingerprints. Historical owners cannot claim Graph paths. Intact historical
manifests migrate through the existing bounded process; obsolete owned proxies
can be disposed of, while edited or unowned files fail closed. No persistent
Graph store is introduced. `workspace check` remains zero-write.

All outputs have `privacy: private` and `export_policy: deny`. Authored private
bytes and public export boundaries remain intact. Fixtures live only in tests;
the public workspace export never receives private proxy records, names or IDs.
No actual private vault is read/applied as part of implementation acceptance.

## Committed fictional acceptance and deferred human G6

`tests/knowledge_graph_fixtures.py` is the bounded fictional private dataset.
`tests/test_knowledge_graph.py` independently asserts intended inventories/pairs,
proxy identities/links and companion inventory/audit parity, duplicate reuse,
parallel declarations, optional multi-target RQ, exclusions, sparse diagnostics,
reordered-input byte determinism, migration, edited/unowned rejection, authored
preservation, private export isolation and untouched global Graph settings.
The required fast manifest includes the new tests without removing older tests.

After CONTROL exact-head source/CI review, human G6 is a separate authorization:

1. Actual synced vault: reviewed workspace apply/check, no fictional records,
   truthful sparse state and unchanged operator-global settings.
2. Disposable non-synced physical vault `/private/tmp/aga-graph-g6-vault`:
   serialize only the committed fixture factory into private authored notes,
   with the existing private marker; apply/check from a reviewed clean exact-head
   checkout. Never copy the fixtures into the actual vault.
3. Open actual native Graph. Activate the default expression; inspect the bounded
   classes and one-per-ID identity, with RQ absent. Enable overlay and distinguish
   its single multi-target RQ, then disable it. Compare one visible edge pair with
   its exact relation/origin in Edge Audit. Follow companion preferred detail,
   Component and Anatomy routes. Demonstrate sparse state and Markdown fallback;
   confirm no Decision/control/manifest/index nodes.

These steps are acceptance instructions, not claimed executed evidence. Layout,
position and density cannot count as semantic or scientific evidence.
