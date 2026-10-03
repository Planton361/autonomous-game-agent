"""Native Graph identity/link/audit parity and fail-closed private ownership."""

import re
from pathlib import Path, PurePosixPath

import pytest
import yaml
from knowledge_graph_fixtures import fictional_graph_records
from projection_test_cache import cached_full_projections  # noqa: F401
from test_research_wiki_projection import filesystem_state, git, write_note
from test_research_wiki_views import outside_owned, setup  # noqa: F401

from fh_agent.research_atlas import knowledge_graph as graph
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.private_projection import ProjectionError, yaml_text
from fh_agent.research_atlas.private_reference_index import build_index, make_snapshot
from fh_agent.research_atlas.rq_presentation import RQReader
from fh_agent.research_atlas.source_presentation import SourceReader
from fh_agent.research_atlas.source_resolution import SourceResolver
from fh_agent.research_atlas.validator import load_registry
from fh_agent.research_atlas.workspace import workspace_tree


@pytest.fixture(scope="module")
def atlas():
    return load_registry(Path(__file__).resolve().parents[1] / "docs/research-atlas")


def projection(atlas, records):
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
    return model, tree


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
        "WPAPER-FIXTURE",
        "READ-FIXTURE",
        "WFIND-FIXTURE",
        "SYN-FIXTURE",
        "TOPIC-FIXTURE",
    }
    assert {n.identity for n in model.nodes if not n.overlay} == default
    assert {n.identity for n in model.nodes if n.overlay} == {"WRQ-FIXTURE", "CMP-MEM-FACTS"}
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
    overlay = {
        ("WRQ-FIXTURE", target) for target in ("CMP-MEM-RETRIEVAL", "CMP-CORTEX", "CMP-MEM-FACTS")
    }
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
        "CMP-MEMORY",
        "SYS-AGA",
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
    assert [n.identity for n in model.nodes] == [graph.MEMORY]
    assert not model.pairs()
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
    assert projection(atlas, reordered) == (model, tree)
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
        n.identity.encode() not in data for n in model.nodes if not n.identity.startswith("CMP-")
    )


def test_generated_ownership_migration_zero_write_and_edited_rejection(setup):  # noqa: F811
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
    # One intact historical 2.15 manifest without any graph files.
    manifest = yaml.safe_load(initial[views.MANIFEST])
    manifest["view_schema_version"] = "2.15"
    for item in list(manifest["owned_files"]):
        path = PurePosixPath(item["path"])
        if path.is_relative_to(graph.ROOT):
            (vault / views.OWNED_ROOT / path).unlink()
            manifest["owned_files"].remove(item)
    (vault / views.OWNED_ROOT / views.MANIFEST).write_text(yaml_text(manifest))
    before = filesystem_state(vault)
    with pytest.raises(ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    migrated = views.project(repo, vault, sha)
    assert yaml.safe_load(migrated[views.MANIFEST])["view_schema_version"] == "2.16"
    assert settings.read_text() == '{"operator": "untouched"}'
    for path, data in authored.items():
        assert views.digest((vault / path).read_bytes()) == data
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    before = filesystem_state(vault)
    assert workspace.check(repo, vault).source_commit == sha
    assert views.project(repo, vault, sha, check=True) == migrated
    assert filesystem_state(vault) == before
    owned = views.validate_prior(vault / views.OWNED_ROOT)
    assert {p for p in owned if p.is_relative_to(graph.ROOT)} == {
        p for p in migrated if p.is_relative_to(graph.ROOT)
    }
    proxy = next(p for p in migrated if p.parent == graph.ROOT / "nodes")
    (vault / views.OWNED_ROOT / proxy).write_bytes(migrated[proxy] + b"\n[[Home]]\n")
    before = filesystem_state(vault)
    with pytest.raises(ProjectionError, match="graph.*edited"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before
    (vault / views.OWNED_ROOT / proxy).write_bytes(migrated[proxy])
    unowned = vault / views.OWNED_ROOT / graph.ROOT / "nodes/Unowned.md"
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
