# Bounded native Knowledge Graph — Memory Retrieval

Issue #119 implements the native Obsidian Graph pilot released by CONTROL
[5963330134](https://github.com/Planton361/autonomous-game-agent/issues/119#issuecomment-5963330134)
and clarified by
[5963456188](https://github.com/Planton361/autonomous-game-agent/issues/119#issuecomment-5963456188).
It preserves accepted #102/#137 semantics, the exact #121 attachments, #125 RQ
target authority, #123 source inspection and #126 Research Steering. It does not
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

Excluded: Decision/DecisionDraft, Issue/PR/milestone/Project/control/orchestration,
manifest/index/navigation, technical Evidence, raw SourceFamily/SourceVersion,
System/Interface/Contract/DataArtifact/MeasurementPoint anchors, Domain/Function/
Assembly and all presentation duplicates. Exact non-Component technical targets
remain available through the existing detail/attachment inspection routes.
Direct, descendant and related Research retain their existing distinctions;
no ancestor receives a child's Research role.

## Exact semantic edge families

The projection emits authored forward directions, not traversal shortcuts:

| Family | Actual declaring property | Eligibility |
| --- | --- | --- |
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
roles, arbitrary BFS/DFS or transitive closure. No relationships are added to
make a graph denser.

One full vault-relative internal proxy link is emitted per directed identity pair.
Parallel declarations share that link and one audit row retaining every property
and origin. Native Graph may visually collapse reciprocal or parallel links;
the directed proxy-link set and directed audit-pair set are exactly equivalent.
Origins identify the declaring record/revision and DRI row/E-family, or the exact
structured Synthesis/Topic/RQ property. Native Graph has no project-specific typed
edge labels. The companion is the semantic precision layer.

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
One question stays one node. Additional explicitly targeted Components appear
only in the overlay unless already participating in default knowledge. Exact
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
metrics are calculated. An isolated Memory Retrieval anchor is a valid sparse view.

## Ownership, migration and privacy

The existing owner `research-wiki-derived` and strict byte hashes own only the two
companions and the finite one-per-ID node set above. Manifest version **2.16** adds
this path family; DRI 1.2, presentation fingerprint 1.1 and source fingerprint 1.0
remain unchanged. Graph inputs already participate in existing structured input
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
