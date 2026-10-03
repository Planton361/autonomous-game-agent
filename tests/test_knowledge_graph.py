"""Native Graph identity/link/audit parity and fail-closed private ownership."""

import re
from pathlib import Path, PurePosixPath

import pytest
import yaml
from knowledge_graph_fixtures import fictional_graph_records
from projection_test_cache import cached_full_projections  # noqa: F401
from test_research_wiki_projection import filesystem_state, git, write_note
from test_research_wiki_views import outside_owned, setup  # noqa: F401
from test_rq_reader import cached_lifecycle_setup  # noqa: F401

from fh_agent.research_atlas import knowledge_graph as graph
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.private_projection import ProjectionError, yaml_text
from fh_agent.research_atlas.private_reference_index import build_index, make_snapshot
from fh_agent.research_atlas.rq_presentation import RQReader
from fh_agent.research_atlas.source_presentation import SourceReader
from fh_agent.research_atlas.source_resolution import SourceResolver
from fh_agent.research_atlas.validator import Atlas, load_registry
from fh_agent.research_atlas.workspace import workspace_tree


@pytest.fixture(scope="module")
def atlas():
    return load_registry(Path(__file__).resolve().parents[1] / "docs/research-atlas")


# This module alone reuses immutable pure outputs. Never cache filesystem/Vault state.
_PROJECTION_CACHE = {}


def projection_key(atlas, records):
    # Keep record/ref order and explicit fields: exclude_unset consumes fields_set.
    # Include complete Atlas contents so a changed technical fixture cannot hit.
    return (
        atlas.source_atlas_schema,
        tuple((identity, node.model_dump_json()) for identity, node in atlas.entities.items()),
        tuple(edge.model_dump_json() for edge in atlas.relationships),
        tuple(
            (type(record), record.model_dump_json(), tuple(sorted(record.model_fields_set)))
            for record in records
        ),
    )


def projection(atlas, records):
    key = projection_key(atlas, records)
    if key in _PROJECTION_CACHE:
        model, entries = _PROJECTION_CACHE[key]
        return model, dict(entries)
    snapshot = make_snapshot(
        [r.model_dump(mode="json", exclude_unset=True) for r in records], atlas
    )
    reference = build_index(atlas, snapshot, "a" * 40)
    reader = RQReader(atlas, records, SourceReader(SourceResolver(None)))
    model = graph.project_graph(atlas, reference, reader)
    locators = {r.wiki_id: PurePosixPath("authored") / (r.wiki_id + ".md") for r in records}
    tree = graph.render_graph(
        model, "a" * 40, atlas, records, locators, views.identity_page_paths(atlas)
    )
    # Projection/Node/Declaration are frozen, with tuple/string fields. Tree payloads
    # are bytes; store immutable entries and return a fresh dict even on first build.
    entries = tuple(tree.items())
    _PROJECTION_CACHE[key] = (model, entries)
    return model, dict(entries)


def inventory(text):
    block = text.split("## Nodes\n", 1)[1].split("## Edge Audit", 1)[0]
    return {
        line.split(" | ")[1]
        for line in block.splitlines()
        if line.startswith("| ") and not line.startswith(("| Node", "| ---"))
    }


def audit_pairs(text):
    block = text.split("## Edge Audit\n", 1)[1].split("## Navigation", 1)[0]
    return re.findall(r"\| ([A-Z0-9-]+) → ([A-Z0-9-]+) \|", block)


def proxy_pairs(tree):
    paths = {
        str(graph.DERIVED / p.with_suffix("")): graph.graph_metadata(b.decode(), p)[
            "graph_identity"
        ]
        for p, b in tree.items()
        if p.parent in {graph.ROOT / "nodes", graph.ROOT / "optional-rq-overlay"}
    }
    result = []
    for p, b in tree.items():
        if p.parent not in {graph.ROOT / "nodes", graph.ROOT / "optional-rq-overlay"}:
            continue
        identity = graph.graph_metadata(b.decode(), p)["graph_identity"]
        for link in re.findall(r"\[\[([^]|]+)\|[^]]+\]\]", b.decode()):
            assert link in paths  # every link resolves to one generated identity
            result.append((identity, paths[link]))
    return result


def test_exact_identity_and_edge_parity(atlas):
    model, tree = projection(atlas, fictional_graph_records(atlas))
    default = {
        "CMP-MEM-RETRIEVAL",
        "CMP-CORTEX",
        "SYS-AGA",
        "WPAPER-FIXTURE",
        "READ-FIXTURE",
        "WFIND-FIXTURE",
        "SYN-FIXTURE",
        "TOPIC-FIXTURE",
    }
    assert {n.identity for n in model.nodes if not n.overlay} == default
    assert {n.identity for n in model.nodes if n.overlay} == {
        "WRQ-FIXTURE",
        "CMP-MEM-FACTS",
        "CMP-MEMORY",
    }
    ids = inventory(tree[graph.AUDIT].decode())
    assert ids == {n.identity for n in model.nodes}
    assert len(tree) == len(ids) + 2  # no hidden proxies
    expected = {
        ("WPAPER-FIXTURE", "CMP-MEM-RETRIEVAL"),
        ("WPAPER-FIXTURE", "CMP-CORTEX"),
        ("WPAPER-FIXTURE", "READ-FIXTURE"),
        ("READ-FIXTURE", "WPAPER-FIXTURE"),
        ("READ-FIXTURE", "WFIND-FIXTURE"),
        ("READ-FIXTURE", "CMP-MEM-RETRIEVAL"),
        ("WFIND-FIXTURE", "WPAPER-FIXTURE"),
        ("WFIND-FIXTURE", "READ-FIXTURE"),
        ("WFIND-FIXTURE", "CMP-MEM-RETRIEVAL"),
        ("SYN-FIXTURE", "WFIND-FIXTURE"),
        ("TOPIC-FIXTURE", "WPAPER-FIXTURE"),
        ("TOPIC-FIXTURE", "WFIND-FIXTURE"),
    }
    expected |= {(graph.MEMORY, "SYS-AGA"), ("CMP-CORTEX", "SYS-AGA")}
    overlay = {
        ("WRQ-FIXTURE", target) for target in ("CMP-MEM-RETRIEVAL", "CMP-CORTEX", "CMP-MEM-FACTS")
    }
    overlay |= {("CMP-MEM-FACTS", "CMP-MEMORY"), ("CMP-MEMORY", "SYS-AGA")}
    assert set(model.pairs(overlay=False)) == expected
    emitted = proxy_pairs(tree)
    audit = audit_pairs(tree[graph.AUDIT].decode())
    assert set(emitted) == set(audit) == set(model.pairs()) == expected | overlay
    assert len(emitted) == len(audit) == len(expected | overlay)
    assert not any("WRQ" in a or "WRQ" in b for a, b in model.pairs(overlay=False))
    assert set(model.pairs(overlay=False)) == expected  # disabling unchanged
    for declaration in model.declarations:
        assert declaration.property in tree[graph.AUDIT].decode()
        assert declaration.origin in tree[graph.AUDIT].decode()


def test_parallel_roles_share_one_link_and_complete_origins(atlas):
    records = list(fictional_graph_records(atlas))
    records[0] = records[0].model_copy(update={"research_method_or_baseline_refs": [graph.MEMORY]})
    model, tree = projection(atlas, tuple(records))
    pair = ("WPAPER-FIXTURE", graph.MEMORY)
    assert len(model.pairs()[pair]) == 2
    assert proxy_pairs(tree).count(pair) == audit_pairs(tree[graph.AUDIT].decode()).count(pair) == 1
    assert (
        "research_direct_subject_refs; research_method_or_baseline_refs"
        in tree[graph.AUDIT].decode()
    )


@pytest.mark.parametrize(
    "property",
    [
        "atlas_refs",
        "wiki_refs",
        "tags",
        "aliases",
        "supports_refs",
        "contradicts_refs",
        "qualifies_refs",
        "review_refs",
        "supersedes_refs",
        "rq_refs",
    ],
)
def test_unaccepted_fields_never_create_topology(atlas, property):
    records = list(fictional_graph_records(atlas))
    original, _ = projection(atlas, tuple(records))
    records[2] = records[2].model_copy(
        update={property: ["CMP-MEMORY", "DOM-EVIDENCE-MEMORY", "FUNC-OBSERVE"]}
    )
    changed, _ = projection(atlas, tuple(records))
    assert changed.nodes == original.nodes and changed.declarations == original.declarations
    assert all(
        d.target not in {"CMP-MEMORY", "DOM-EVIDENCE-MEMORY", "FUNC-OBSERVE"}
        for d in changed.declarations
        if d.edge_class != "technical skeleton"
    )


def test_no_recursive_closure_inheritance_or_inferred_synthesis(atlas):
    records = list(fictional_graph_records(atlas))
    records[3] = records[3].model_copy(
        update={"finding_refs": ["WFIND-FIXTURE", "WFIND-UNRELATED"]}
    )
    records[4] = records[4].model_copy(update={"paper_refs": ["WPAPER-FIXTURE", "WPAPER-OTHER"]})
    model, _ = projection(atlas, tuple(records))
    ids = {n.identity for n in model.nodes}
    assert not ids & {
        "WFIND-UNRELATED",
        "SYN-UNRELATED",
        "WPAPER-OTHER",
        "TOPIC-UNSUPPORTED",
        "IF-MEM-CORTEX",
    }
    assert not any(
        d.source in {"SYN-FIXTURE", "TOPIC-FIXTURE"} and d.target.startswith("CMP-")
        for d in model.declarations
    )
    assert any("another" in d or "outside bounded" in d for d in model.diagnostics)


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "wrong-type",
        "unmatched-reading",
        "historical",
        "draft",
        "legacy-rq",
        "wrong-rq-target",
        "unbound-rq",
    ],
)
def test_invalid_sparse_and_overlay_fail_closed(atlas, fault):
    records = list(fictional_graph_records(atlas))
    if fault == "missing":
        records[0] = records[0].model_copy(update={"reading_note_refs": ["READ-MISSING"]})
    elif fault == "wrong-type":
        records[1] = records[1].model_copy(update={"finding_refs": ["WDEC-FIXTURE"]})
    elif fault == "unmatched-reading":
        records[1] = records[1].model_copy(update={"paper_refs": ["WPAPER-OTHER"]})
    elif fault in {"historical", "draft"}:
        records[0] = records[0].model_copy(
            update={"document_maturity": "archived" if fault == "historical" else "draft"}
        )
    elif fault == "legacy-rq":
        records[5] = records[5].model_copy(update={"epistemic_schema_version": "0.2"})
    else:
        records[5] = records[5].model_copy(
            update={
                "research_direct_subject_refs": ["FUNC-OBSERVE", "MISSING"]
                if fault == "wrong-rq-target"
                else []
            }
        )
    model, tree = projection(atlas, tuple(records))
    assert (
        set(proxy_pairs(tree)) == set(audit_pairs(tree[graph.AUDIT].decode())) == set(model.pairs())
    )
    assert all("MISSING" not in n.identity and n.kind != "DecisionDraft" for n in model.nodes)
    if fault in {"legacy-rq", "wrong-rq-target", "unbound-rq"}:
        assert not any(n.kind == "ResearchQuestion" for n in model.nodes)
    if fault == "unmatched-reading":
        assert ("WPAPER-FIXTURE", "READ-FIXTURE") not in model.pairs()
    if fault in {"historical", "draft"}:
        assert not any(n.identity == "WPAPER-FIXTURE" for n in model.nodes)


def test_empty_truthful_fallback_no_global_settings(atlas):
    model, tree = projection(atlas, ())
    assert {n.identity for n in model.nodes} == {graph.MEMORY, "SYS-AGA"}
    assert set(model.pairs()) == {(graph.MEMORY, "SYS-AGA")}
    assert "No matching documented knowledge" in tree[graph.AUDIT].decode()
    assert "no eligible" in tree[graph.AUDIT].decode()
    text = tree[graph.PROFILE].decode()
    assert graph.DEFAULT_FILTER in text and graph.OVERLAY_FILTER in text
    assert "Orphans ON" in text and "Tags OFF" in text and "Arrows" in text
    assert all(str(path).startswith(str(graph.ROOT)) for path in tree)
    assert not any(".obsidian" in str(path) for path in tree)
    assert all(
        section in tree[graph.AUDIT].decode()
        for section in (
            "## Graph profile",
            "## Nodes",
            "## Edge Audit",
            "## Navigation / inspection",
            "## Sparse state",
        )
    )


def test_deterministic_bytes_paths_and_navigation_isolation(atlas):
    records = fictional_graph_records(atlas)
    model, tree = projection(atlas, records)
    reordered = tuple(
        r.model_copy(
            update={
                field: list(reversed(getattr(r, field)))
                for field in type(r).model_fields
                if field.endswith("_refs") and field in r.model_fields_set
            }
        )
        for r in reversed(records)
    )
    assert projection_key(atlas, reordered) != projection_key(atlas, records)
    assert projection(atlas, reordered) == (model, tree)
    # Caller dictionary mutations must never affect another result or cached bytes.
    _, independent = projection(atlas, records)
    assert independent == tree and independent is not tree
    independent.pop(graph.AUDIT)
    assert projection(atlas, records) == (model, tree)
    for path, data in tree.items():
        assert graph.is_graph_path(path) and graph.graph_metadata(data.decode(), path)
        if path not in {graph.AUDIT, graph.PROFILE}:
            body = data.decode()
            assert not re.search(r"\[[^]\n]+\]\([^\n]+\)", body)  # no Markdown navigation
            assert not any(
                token in body
                for token in ("[[Home", "[[Agent Anatomy", "[[indexes/", ".canvas", ".excalidraw")
            )
    audit = tree[graph.AUDIT].decode()
    assert "../../../.." in audit and "authored/" in audit
    assert "Agent Anatomy" in audit and "preferred/detail" in audit
    assert (
        "authored detail unavailable"
        in graph.render_graph(model, "a" * 40, atlas, records, {}, {})[graph.AUDIT].decode()
    )


def test_public_export_has_no_private_projection(atlas):
    model, private = projection(atlas, fictional_graph_records(atlas))
    public = workspace_tree(atlas)
    assert not set(private) & set(public)
    data = "".join(public.values()).encode()
    assert all(
        n.identity.encode() not in data
        for n in model.nodes
        if n.kind not in {"Component", "System"}
    )


@pytest.mark.parametrize(
    "family,legacy", [(graph.ROOT, "2.15"), (graph.scope_root(graph.MEMORY), "2.16")]
)
def test_generated_ownership_migration_zero_write_and_edited_rejection(
    family,
    legacy,
    cached_lifecycle_setup,  # noqa: F811
    setup,  # noqa: F811
):
    repo, vault, sha = setup
    for record in fictional_graph_records(load_registry(repo / "docs/research-atlas")):
        write_note(
            vault / "authored" / (record.wiki_id + ".md"),
            record.model_dump(mode="json", exclude_unset=True),
        )
    authored = outside_owned(vault)
    (vault / ".obsidian").mkdir()
    settings = vault / ".obsidian/graph.json"
    settings.write_text('{"operator": "untouched"}')
    initial = views.project(repo, vault, sha)
    preferred = views.identity_page_paths(load_registry(repo / "docs/research-atlas"))[graph.MEMORY]
    for context in (preferred, views.MEMORY_HUB_RESEARCH):
        assert str(views.OWNED_ROOT / graph.PROFILE.with_suffix("")).encode() in initial[context]
        assert str(views.OWNED_ROOT / graph.AUDIT.with_suffix("")).encode() in initial[context]
    current_atlas = load_registry(repo / "docs/research-atlas")
    for subject, entity in current_atlas.entities.items():
        if entity.type != "Component":
            continue
        preferred_path = views.identity_page_paths(current_atlas)[subject]
        route = str(views.OWNED_ROOT / graph.scope_root(subject) / "Graph Profile")
        assert route.encode() in initial[preferred_path]
        assert route.encode() in initial[views.RESEARCH_LANDSCAPE]
        assert b"Agent Anatomy" in initial[preferred_path]
    assert b"Knowledge Graph / exact affected Components" in initial[views.SOURCE_DETAIL]
    assert b"WPAPER-FIXTURE" in initial[views.SOURCE_DETAIL]
    # Historical 2.15 predates Graph; 2.16 retains pilot but predates scoped profiles.
    manifest = yaml.safe_load(initial[views.MANIFEST])
    manifest["view_schema_version"] = legacy
    for item in list(manifest["owned_files"]):
        path = PurePosixPath(item["path"])
        if path.is_relative_to(graph.SCOPES) or (
            legacy == "2.15" and path.is_relative_to(graph.ROOT)
        ):
            (vault / views.OWNED_ROOT / path).unlink()
            manifest["owned_files"].remove(item)
    (vault / views.OWNED_ROOT / views.MANIFEST).write_text(yaml_text(manifest))
    before = filesystem_state(vault)
    with pytest.raises(ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    migrated = views.project(repo, vault, sha)
    assert migrated == initial
    assert yaml.safe_load(migrated[views.MANIFEST])["view_schema_version"] == "2.17"
    assert settings.read_text() == '{"operator": "untouched"}'
    for path, data in authored.items():
        assert views.digest((vault / path).read_bytes()) == data
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    before = filesystem_state(vault)
    checked = workspace.check(repo, vault)
    assert checked.source_commit == sha
    # Real harness returns these stages only after both actual projector checks pass.
    assert checked.stages == ("technical projection check", "direct views check")
    # Preserve exact migrated output parity without repeating the full direct check.
    assert {path: (vault / views.OWNED_ROOT / path).read_bytes() for path in migrated} == migrated
    assert filesystem_state(vault) == before
    owned = views.validate_prior(vault / views.OWNED_ROOT)
    assert {p for p in owned if p.is_relative_to(graph.ROOT)} == {
        p for p in migrated if p.is_relative_to(graph.ROOT)
    }
    proxy = next(p for p in migrated if p.parent == family / "nodes")
    (vault / views.OWNED_ROOT / proxy).write_bytes(migrated[proxy] + b"\n[[Home]]\n")
    before = filesystem_state(vault)
    with pytest.raises(ProjectionError, match="graph.*edited"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before
    (vault / views.OWNED_ROOT / proxy).write_bytes(migrated[proxy])
    unowned = vault / views.OWNED_ROOT / family / "nodes/Unowned.md"
    unowned.write_text("authored work")
    before = filesystem_state(vault)
    with pytest.raises(ProjectionError, match="Unknown/unowned"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before
    assert settings.read_text() == '{"operator": "untouched"}'


@pytest.mark.parametrize(
    "path",
    [
        "knowledge-graph/other/nodes/CMP-OTHER.md",
        "knowledge-graph/memory-retrieval/nodes/Unknown.md",
        "knowledge-graph/memory-retrieval/nodes/X — EVID-X.md",
        "knowledge-graph/memory-retrieval/nodes/X — WRQ-X.md",
        "knowledge-graph/memory-retrieval/deeper/X — CMP-X.md",
    ],
)
def test_finite_paths_and_metadata_reject_spoofed_nodes(path):
    path = PurePosixPath(path)
    assert not graph.graph_metadata("---\ngenerated_by: research-wiki-derived\n---\n", path)


def test_presentation_routes_and_titles_never_add_graph_edges(atlas):
    records = list(fictional_graph_records(atlas))
    original, _ = projection(atlas, tuple(records))
    records[0] = records[0].model_copy(update={"title": "[[Home]] [return](Index.md) # Fixture"})
    changed, tree = projection(atlas, tuple(records))
    assert {n.identity for n in changed.nodes} == {n.identity for n in original.nodes}
    assert changed.declarations == original.declarations
    assert set(proxy_pairs(tree)) == set(original.pairs())
    # Multiple presentation routes are locators only, never selected node inputs.
    locators = {r.wiki_id: PurePosixPath("workbenches/alternate.md") for r in records}
    alternate = graph.render_graph(changed, "a" * 40, atlas, tuple(records), locators, {})
    proxies = {p: b for p, b in tree.items() if p not in {graph.AUDIT, graph.PROFILE}}
    assert proxies == {p: alternate[p] for p in proxies}
    assert inventory(tree[graph.AUDIT].decode()) == inventory(alternate[graph.AUDIT].decode())


def test_closed_graph_header_and_historical_owner_rejection(atlas):
    _, tree = projection(atlas, ())
    path = next(p for p in tree if p.parent == graph.ROOT / "nodes")
    data = tree[path].decode()
    assert not graph.graph_metadata(data.replace("source_commit:", "unexpected_field:"), path)
    assert not graph.graph_metadata(data.replace("a" * 40, "not-a-commit"), path)
    assert not graph.graph_metadata(
        data.replace("graph_class: Component", "graph_class: Evidence"), path
    )


def test_exact_registry_skeleton_default_and_overlay(atlas):
    model, tree = projection(atlas, fictional_graph_records(atlas))
    default_nodes = {
        n.identity for n in model.nodes if not n.overlay and n.kind in {"Component", "System"}
    }
    overlay_nodes = {n.identity for n in model.nodes if n.overlay and n.kind == "Component"}
    assert default_nodes == {graph.MEMORY, "CMP-CORTEX", "SYS-AGA"}
    assert overlay_nodes == {"CMP-MEM-FACTS", "CMP-MEMORY"}
    expected = {
        (graph.MEMORY, "SYS-AGA"),
        ("CMP-CORTEX", "SYS-AGA"),
        ("CMP-MEM-FACTS", "CMP-MEMORY"),
        ("CMP-MEMORY", "SYS-AGA"),
    }
    skeleton = [d for d in model.declarations if d.edge_class == "technical skeleton"]
    registry = {(e.source, e.target) for e in atlas.relationships if e.relation == "part_of"}
    assert {(d.source, d.target) for d in skeleton} == expected <= registry
    assert len(skeleton) == 4
    assert all(
        d.property == "part_of"
        and d.origin == f"public Registry relationship: {d.source} part_of {d.target}"
        for d in skeleton
    )
    assert all(atlas.ancestors(ref) <= default_nodes for ref in default_nodes)
    assert not {"CMP-MEMORY", "CMP-MEM-FACTS"} & default_nodes
    assert len({n.identity for n in model.nodes}) == len(model.nodes)
    assert sum(n.kind == "ResearchQuestion" for n in model.nodes) == 1
    assert not any(n.kind == "ResearchQuestion" and not n.overlay for n in model.nodes)
    audit = tree[graph.AUDIT].decode()
    rows = audit.split("## Edge Audit\n", 1)[1].split("## Navigation", 1)[0]
    assert rows.count("| technical skeleton |") == len(skeleton)
    assert "| Edge class |" in rows
    assert set(proxy_pairs(tree)) == set(audit_pairs(audit)) == set(model.pairs())
    # Every ancestor is orientation only, with no inherited scientific targeting.
    assert not any(
        d.target in {"SYS-AGA", "CMP-MEMORY"}
        for d in model.declarations
        if d.edge_class == "research / knowledge"
    )
    assert ("WRQ-FIXTURE", "CMP-MEM-FACTS") in model.pairs()
    assert ("WRQ-FIXTURE", "CMP-MEMORY") not in model.pairs()


def test_default_child_attachment_gets_ancestry_without_research_inheritance(atlas):
    records = list(fictional_graph_records(atlas))
    records[0] = records[0].model_copy(
        update={"research_direct_subject_refs": [graph.MEMORY, "CMP-MEM-FACTS"]}
    )
    records[2] = records[2].model_copy(
        update={"research_adjacent_context_refs": [graph.MEMORY, "CMP-MEM-FACTS"]}
    )
    model, tree = projection(atlas, tuple(records))
    default = {n.identity for n in model.nodes if not n.overlay}
    assert {graph.MEMORY, "CMP-MEM-FACTS", "CMP-MEMORY", "SYS-AGA"} <= default
    # Cortex remains an explicitly targeted overlay node, not a sibling expansion.
    assert "CMP-CORTEX" not in default
    assert "CMP-MEM-EPISODIC" not in {n.identity for n in model.nodes}
    for source in ("WPAPER-FIXTURE", "WFIND-FIXTURE", "WRQ-FIXTURE"):
        assert (source, "CMP-MEM-FACTS") in model.pairs()
        assert (source, "CMP-MEMORY") not in model.pairs()
        assert (source, "SYS-AGA") not in model.pairs()
    assert ("CMP-MEM-FACTS", "CMP-MEMORY") in model.pairs(overlay=False)
    assert ("CMP-MEMORY", "SYS-AGA") in model.pairs(overlay=False)
    assert (
        set(proxy_pairs(tree)) == set(audit_pairs(tree[graph.AUDIT].decode())) == set(model.pairs())
    )


@pytest.mark.parametrize(
    "relation", ["presented_in_domain", "contributes_to_function", "supplies", "decomposed_into"]
)
def test_non_containment_registry_context_never_enters_skeleton(atlas, relation):
    # Current Registry context edges cannot supply ancestry, even when all other
    # context families are removed. Domain/Function/legacy Assembly are not actors.
    reduced = Atlas(
        atlas.entities,
        tuple(e for e in atlas.relationships if e.relation in {"part_of", relation}),
        atlas.source_atlas_schema,
    )
    baseline, _ = projection(atlas, fictional_graph_records(atlas))
    changed, _ = projection(reduced, fictional_graph_records(reduced))
    assert changed.nodes == baseline.nodes
    assert changed.declarations == baseline.declarations
    assert all(n.kind not in {"Domain", "Function", "Assembly"} for n in changed.nodes)
    assert all(
        d.property == "part_of"
        for d in changed.declarations
        if d.edge_class == "technical skeleton"
    )


def test_reordered_registry_preserves_skeleton_bytes_and_independent_build(atlas):
    reordered = Atlas(
        dict(reversed(tuple(atlas.entities.items()))),
        tuple(reversed(atlas.relationships)),
        atlas.source_atlas_schema,
    )
    records = fictional_graph_records(atlas)
    assert projection_key(atlas, records) != projection_key(reordered, records)
    assert projection(atlas, records) == projection(reordered, records)


def scoped_projection(atlas, records, scope, mode="architecture"):
    snapshot = make_snapshot(
        [r.model_dump(mode="json", exclude_unset=True) for r in records], atlas
    )
    reference = build_index(atlas, snapshot, "a" * 40)
    reader = RQReader(atlas, records, SourceReader(SourceResolver(None)))
    model = graph.project_graph(atlas, reference, reader, scope=scope, mode=mode)
    tree = graph.render_graph(
        model,
        "a" * 40,
        atlas,
        records,
        {r.wiki_id: PurePosixPath("authored") / (r.wiki_id + ".md") for r in records},
        views.identity_page_paths(atlas),
    )
    return model, tree


def nested_atlas(atlas):
    entities = dict(atlas.entities)
    parent = "CMP-MEM-FACTS"
    for identity in ("CMP-FIXTURE-CHILD", "CMP-FIXTURE-DEEP"):
        entities[identity] = entities[parent].model_copy(update={"id": identity, "name": identity})
    template = next(e for e in atlas.relationships if e.relation == "part_of")
    return Atlas(
        entities,
        atlas.relationships
        + (
            template.model_copy(update={"source": "CMP-FIXTURE-CHILD", "target": parent}),
            template.model_copy(
                update={"source": "CMP-FIXTURE-DEEP", "target": "CMP-FIXTURE-CHILD"}
            ),
        ),
        atlas.source_atlas_schema,
    )


def scoped_parity(model, tree):
    paths = {
        str(graph.DERIVED / path.with_suffix("")): node.identity
        for node in model.nodes
        for path in (node.path,)
    }
    emitted = []
    for node in model.nodes:
        metadata = graph.graph_metadata(tree[node.path].decode(), node.path)
        assert metadata["graph_identity"] == node.identity
        for target in re.findall(r"\[\[([^]|]+)\|[^]]+\]\]", tree[node.path].decode()):
            assert target in paths  # navigation, authored/presentation paths cannot enter
            emitted.append((node.identity, paths[target]))
    audit = tree[model.root / "Edge Audit.md"].decode()
    assert set(emitted) == set(audit_pairs(audit)) == set(model.pairs())
    assert len(emitted) == len(set(emitted)) == len(audit_pairs(audit))
    for declaration in model.declarations:
        assert declaration.property in audit and declaration.origin in audit
    assert len(tree) == len(model.nodes) + 2
    assert len({n.identity for n in model.nodes}) == len(model.nodes)
    for path, data in tree.items():
        assert graph.is_graph_path(path) and graph.graph_metadata(data.decode(), path)
    return audit


@pytest.mark.parametrize("mode", graph.MODES)
def test_scoped_nested_subtree_cross_branch_exact_attachment_and_profiles(atlas, mode):
    technical = nested_atlas(atlas)
    records = list(fictional_graph_records(technical))
    records[0] = records[0].model_copy(
        update={
            "research_direct_subject_refs": ["CMP-FIXTURE-DEEP", "CMP-CORTEX", "CMP-CORTEX"],
            "title": "[[Home]] [return](Index.md) adversarial navigation",
        }
    )
    records[1] = records[1].model_copy(
        update={"research_method_or_baseline_refs": ["CMP-MEM-FACTS"]}
    )
    records[2] = records[2].model_copy(
        update={"research_adjacent_context_refs": ["CMP-FIXTURE-CHILD"]}
    )
    model, tree = scoped_projection(technical, tuple(records), "CMP-MEM-FACTS", mode)
    ids = {n.identity for n in model.nodes}
    assert {
        "SYS-AGA",
        "CMP-MEMORY",
        "CMP-MEM-FACTS",
        "CMP-FIXTURE-CHILD",
        "CMP-FIXTURE-DEEP",
        "CMP-CORTEX",
    } <= ids
    # Other technical branch is an exact participant, not a sibling-density expansion.
    assert "CMP-BODY" not in ids
    assert (graph.MEMORY in ids) == (mode == "rq-overlay")
    assert sum(n.identity == "WPAPER-FIXTURE" for n in model.nodes) == 1
    paper_targets = {
        d.target
        for d in model.declarations
        if d.source == "WPAPER-FIXTURE" and d.target.startswith("CMP-")
    }
    assert paper_targets == {"CMP-FIXTURE-DEEP", "CMP-CORTEX"}
    assert ("CMP-FIXTURE-DEEP", "CMP-FIXTURE-CHILD") in model.pairs()
    assert ("CMP-FIXTURE-CHILD", "CMP-MEM-FACTS") in model.pairs()
    assert ("CMP-MEM-FACTS", "CMP-MEMORY") in model.pairs()
    assert all(
        n.kind in {*graph.TYPES.values(), "Component", "System", "ResearchQuestion"}
        for n in model.nodes
    )
    assert not ids & {"WDEC-FIXTURE", "WPAPER-OTHER", "TOPIC-UNSUPPORTED", "SYN-UNRELATED"}
    assert any(n.kind == "ResearchQuestion" for n in model.nodes) == (mode == "rq-overlay")
    if mode == "rq-overlay":
        assert {d.target for d in model.declarations if d.source == "WRQ-FIXTURE"} == {
            graph.MEMORY,
            "CMP-CORTEX",
            "CMP-MEM-FACTS",
        }
    scoped_parity(model, tree)
    profile = tree[model.root / "Graph Profile.md"].decode()
    assert f'path:"{graph.DERIVED / model.root / "nodes"}/"' in profile
    assert all(str(path).startswith(str(model.root)) for path in tree)
    assert all(name in profile for name in graph.MODES)


def test_scoped_ancestry_does_not_select_parent_or_cross_participant_research(atlas):
    technical = nested_atlas(atlas)
    records = list(fictional_graph_records(technical))
    # Ancestor and unrelated cross-participant knowledge must not be selected.
    records[0] = records[0].model_copy(update={"research_direct_subject_refs": ["CMP-MEMORY"]})
    model, tree = scoped_projection(technical, tuple(records), "CMP-FIXTURE-DEEP")
    assert {n.identity for n in model.nodes} == {
        "CMP-FIXTURE-DEEP",
        "CMP-FIXTURE-CHILD",
        "CMP-MEM-FACTS",
        "CMP-MEMORY",
        "SYS-AGA",
    }
    assert all(d.edge_class == "technical skeleton" for d in model.declarations)
    audit = scoped_parity(model, tree)
    assert (
        "No matching documented knowledge" in audit and "None implies literature absence" in audit
    )


def test_architecture_minimal_relations_and_optional_detail(atlas):
    records = fictional_graph_records(atlas)
    architecture, _ = scoped_projection(atlas, records, graph.MEMORY)
    detail, tree = scoped_projection(atlas, records, graph.MEMORY, "knowledge-detail")
    assert {n.identity for n in architecture.nodes} == {n.identity for n in detail.nodes}
    assert set(architecture.pairs()) < set(detail.pairs())
    assert ("WPAPER-FIXTURE", "READ-FIXTURE") not in architecture.pairs()
    assert ("WPAPER-FIXTURE", "READ-FIXTURE") in detail.pairs()
    assert ("SYN-FIXTURE", "WFIND-FIXTURE") in architecture.pairs()
    assert {d for d in architecture.declarations if d.edge_class == "technical skeleton"} == {
        d for d in detail.declarations if d.edge_class == "technical skeleton"
    }
    scoped_parity(detail, tree)


@pytest.mark.parametrize("mode", graph.MODES)
def test_scoped_reordered_valid_inputs_deterministic(atlas, mode):
    records = fictional_graph_records(atlas)
    reordered = tuple(
        r.model_copy(
            update={
                field: list(reversed(getattr(r, field)))
                for field in type(r).model_fields
                if field.endswith("_refs") and field in r.model_fields_set
            }
        )
        for r in reversed(records)
    )
    reverse_atlas = Atlas(
        dict(reversed(list(atlas.entities.items()))),
        tuple(reversed(atlas.relationships)),
        atlas.source_atlas_schema,
    )
    assert scoped_projection(atlas, records, "CMP-MEMORY", mode) == scoped_projection(
        reverse_atlas, reordered, "CMP-MEMORY", mode
    )


def test_scoped_deep_targets_detail_only_and_broken_refs_diagnostic(atlas):
    records = list(fictional_graph_records(atlas))
    records[0] = records[0].model_copy(
        update={
            "research_direct_subject_refs": [graph.MEMORY, "IF-MEM-CORTEX"],
            "reading_note_refs": ["READ-MISSING"],
        }
    )
    model, tree = scoped_projection(atlas, tuple(records), graph.MEMORY)
    audit = scoped_parity(model, tree)
    assert "IF-MEM-CORTEX" not in {n.identity for n in model.nodes}
    assert "READ-MISSING" not in {n.identity for n in model.nodes}
    assert "Detail only; no accepted topology profile" in audit
    assert "IF-MEM-CORTEX" in audit and "READ-MISSING" in audit
    assert str(views.identity_page_paths(atlas)["IF-MEM-CORTEX"]) in audit


def test_scoped_large_inventory_is_bounded_disconnected_and_private(atlas):
    from test_research_wiki_schema import props

    from fh_agent.research_atlas.wiki_schema import validate_wiki_records

    records = validate_wiki_records(
        [
            props(
                "paper",
                wiki_id=f"WPAPER-LARGE-{i}",
                title=f"Fictional item {i}",
                document_maturity="in_review",
                research_direct_subject_refs=[graph.MEMORY],
            )
            for i in range(120)
        ]
        + [
            props(
                "topic",
                wiki_id="TOPIC-DISCONNECTED",
                title="Disconnected mapped inventory",
                document_maturity="in_review",
                tags=[graph.MEMORY],
            )
        ],
        atlas.entities.keys(),
    )
    model, tree = scoped_projection(atlas, records, graph.MEMORY)
    assert sum(n.kind == "Paper" for n in model.nodes) == 120
    assert len(model.nodes) == 122
    assert "TOPIC-DISCONNECTED" not in {n.identity for n in model.nodes}
    scoped_parity(model, tree)
    assert scoped_projection(atlas, tuple(reversed(records)), graph.MEMORY) == (model, tree)
    assert not set(tree) & set(workspace_tree(atlas))
    assert b"WPAPER-LARGE" not in "".join(workspace_tree(atlas).values()).encode()
    assert all(b"export_policy: deny" in data for data in tree.values())


@pytest.mark.parametrize(
    "scope,mode",
    [("SYS-AGA", "architecture"), ("CMP-MISSING", "architecture"), (graph.MEMORY, "mega-graph")],
)
def test_scoped_invalid_selection_fails_closed(atlas, scope, mode):
    with pytest.raises(ProjectionError):
        scoped_projection(atlas, (), scope, mode)


@pytest.mark.parametrize(
    "kind", ["System", "Interface", "Contract", "DataArtifact", "MeasurementPoint"]
)
def test_scoped_all_deep_g2_classes_retain_exact_detail_without_topology(atlas, kind):
    target = next(ref for ref, entity in atlas.entities.items() if entity.type == kind)
    records = list(fictional_graph_records(atlas))
    records[0] = records[0].model_copy(
        update={"research_direct_subject_refs": [graph.MEMORY, target]}
    )
    model, tree = scoped_projection(atlas, tuple(records), graph.MEMORY)
    assert ("WPAPER-FIXTURE", target) not in model.pairs()
    assert all(n.kind in {"System", "Component", *graph.TYPES.values()} for n in model.nodes)
    audit = scoped_parity(model, tree)
    assert target in audit and str(views.identity_page_paths(atlas)[target]) in audit
    assert "Detail only; no accepted topology profile" in audit


@pytest.mark.parametrize(
    "artifact", ["Issue-127", "PR-101", "Decision", "Index", "manifest", "Canvas"]
)
def test_scoped_navigation_operational_and_duplicate_presentation_exclusions(atlas, artifact):
    records = list(fictional_graph_records(atlas))
    original, _ = scoped_projection(atlas, tuple(records), graph.MEMORY)
    records[0] = records[0].model_copy(
        update={
            "wiki_refs": [artifact],
            "atlas_refs": [artifact],
            "tags": [artifact],
            "aliases": [artifact],
            "title": "[[" + artifact + "]] [return](" + artifact + ".md)",
        }
    )
    with pytest.raises(ProjectionError, match="Invalid private identity"):
        scoped_projection(atlas, tuple(records), graph.MEMORY)
    records[0] = records[0].model_copy(update={"atlas_refs": []})
    changed, tree = scoped_projection(atlas, tuple(records), graph.MEMORY)
    assert {n.identity for n in changed.nodes} == {n.identity for n in original.nodes}
    assert changed.declarations == original.declarations
    scoped_parity(changed, tree)
    # Several presentation files for a record never become graph identities.
    alternate = graph.render_graph(
        changed,
        "a" * 40,
        atlas,
        tuple(records),
        {r.wiki_id: PurePosixPath("presentations") / (artifact + ".md") for r in records},
        views.identity_page_paths(atlas),
    )
    assert all(alternate[n.path] == tree[n.path] for n in changed.nodes)
