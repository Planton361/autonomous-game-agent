"""Synthetic-only final IA and global ownership migration acceptance evidence."""

import json
import re
from dataclasses import replace
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import pytest
import test_workspace_harness as harness_fixtures
from projection_test_cache import cached_full_projections  # noqa: F401
from rq_reader_fixtures import fictional_records
from test_research_wiki_projection import filesystem_state, snapshot, write_note

from fh_agent.research_atlas import final_projection
from fh_agent.research_atlas import knowledge_graph as graph
from fh_agent.research_atlas import private_projection as public
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import product_migration as migration
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.final_projection import MANIFESTS, MODES, ProductTree, package
from fh_agent.research_atlas.preferred_paths import HOME, INTERNAL, PRODUCT, preferred_paths
from fh_agent.research_atlas.private_projection import ProjectionError, markdown_parts, read_yaml
from fh_agent.research_atlas.private_reference_index import build_index, make_snapshot
from fh_agent.research_atlas.reader_export import export_reader
from fh_agent.research_atlas.rq_presentation import RQReader
from fh_agent.research_atlas.schema import Relationship
from fh_agent.research_atlas.validator import load_registry

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


@pytest.fixture
def workspace_setup(tmp_path, monkeypatch):
    # Identical synthetic source bytes have one reproducible Git identity. This
    # enables content-keyed pure reuse without caching any filesystem validation.
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2026-09-01T00:00:00+00:00")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2026-09-01T00:00:00+00:00")
    return harness_fixtures.setup.__wrapped__(tmp_path)


@pytest.fixture(scope="module", autouse=True)
def cached_pure_packaging():
    """Reuse immutable renders by complete content/order keys; all I/O stays live."""
    technical_render = public.projection_tree
    final_render = package
    technical_cache = {}
    final_cache = {}

    def atlas_key(atlas):
        return (
            atlas.source_atlas_schema,
            tuple((identity, node.model_dump_json()) for identity, node in atlas.entities.items()),
            tuple(edge.model_dump_json() for edge in atlas.relationships),
        )

    def technical(atlas, commit, digests):
        key = (atlas_key(atlas), commit, tuple(digests.items()))
        if key not in technical_cache:
            technical_cache[key] = technical_render(atlas, commit, digests)
        return dict(technical_cache[key])

    def final(atlas, technical, derived):
        # Include byte content and original ordering. Reordered/changed inputs
        # exercise the real renderer independently; no pickle is loaded/executed.
        key = (atlas_key(atlas), tuple(technical.items()), tuple(derived.items()))
        if key not in final_cache:
            final_cache[key] = final_render(atlas, technical, derived)
        result = final_cache[key]
        return ProductTree(dict(result.files), dict(result.owners), dict(result.routes))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(public, "projection_tree", technical)
        patch.setattr(final_projection, "package", final)
        patch.setattr(migration, "package", final)
        patch.setitem(globals(), "package", final)
        yield


@pytest.fixture(scope="module")
def atlas():
    return load_registry(ROOT / "docs/research-atlas")


def intermediate(atlas, records=()):
    props = [r.model_dump(mode="json", exclude_unset=True) for r in records]
    snapshot = make_snapshot(props, atlas)
    locators = {
        r.wiki_id: PurePosixPath("authored/Deep Folder") / (r.wiki_id + ".md") for r in records
    }
    reference = build_index(atlas, snapshot, COMMIT)
    technical = public.projection_tree(atlas, COMMIT, {x: "a" * 64 for x in public.REGISTRY_FILES})
    derived = views.reference_views_tree(
        COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        locators,
        snapshot,
        False,
        records,
    )
    return technical, derived, reference, locators


@pytest.fixture(scope="module")
def baseline(atlas):
    technical, derived, reference, locators = intermediate(atlas)
    return package(atlas, technical, derived), technical, derived


def test_exact_synthetic_inventory_and_owner_counts(atlas, baseline):
    tree, technical, derived = baseline
    assert len(technical) + len(derived) == 696
    assert len(tree.files) == 520
    assert 696 - 520 == 176
    assert set(tree.routes) - {
        views.OWNED_ROOT / views.LEGACY_MEMORY_WORKBENCH,
        views.OWNED_ROOT / views.LEGACY_VERIFIER_WORKBENCH,
    } == {public.OWNED_ROOT / p for p in technical} | {views.OWNED_ROOT / p for p in derived}
    assert {HOME} == {p for p in tree.files if len(p.parts) == 1}
    assert all(
        p == HOME or p.is_relative_to(PRODUCT) or p.is_relative_to(INTERNAL) for p in tree.files
    )
    assert set(tree.owners.values()) == {public.OWNER, views.OWNER}
    assert set(tree.owners) == set(tree.files)
    assert sum(p.suffix == ".base" for p in tree.files) == 3
    assert sum(p.suffix == ".canvas" for p in tree.files) == 7
    assert set(preferred_paths(atlas).values()) <= tree.files.keys()
    assert len(preferred_paths(atlas)) == 61
    assert len(set(preferred_paths(atlas).values())) == 61
    assert not any(
        p.name
        in {
            "Technical Atlas Index.md",
            "Direct Views Index.md",
            "Technical Hierarchy.md",
            "System Anatomy.excalidraw.md",
        }
        for p in tree.files
    )
    assert (INTERNAL / "Home.md") not in tree.files
    for owner, manifest in MANIFESTS.items():
        rows = read_yaml(tree.files[manifest].decode())["owned_files"]
        assert {PurePosixPath(r["path"]) for r in rows} == {
            p for p in tree.files if tree.owners[p] == owner and p != manifest
        }
        assert all(r["sha256"] == public.digest(tree.files[PurePosixPath(r["path"])]) for r in rows)


def test_exact_component_paths_and_function_non_ancestry(atlas, baseline):
    tree, _, _ = baseline
    paths = preferred_paths(atlas)
    for edge in atlas.relationships:
        if edge.relation != "part_of" or atlas.entities[edge.source].type != "Component":
            continue
        parent = atlas.entities[edge.target]
        assert paths[edge.source].parent == (
            PRODUCT / "Components"
            if parent.type == "System"
            else paths[edge.target].with_suffix("")
        )
    assert paths["CMP-BOUNDED-REFLEX"] == PRODUCT / "Components/Body/Bounded Reflex.md"
    assert paths["CMP-MANAGER-GROUNDING"] == PRODUCT / "Components/Manager/Grounding.md"
    for identity, path in paths.items():
        kind = atlas.entities[identity].type
        if kind == "Function":
            assert path.parent == PRODUCT / "Functions"
            text = tree.files[path].decode()
            assert "Functional context (non-containment)" in text
            assert "no technical parent is asserted" in text
        if kind in views.SUPPORTED_IDENTITY_PAGE_TYPES:
            text = tree.files[path].decode()
            assert "[[Research Map Home|Home]]" in text
            assert "## Technical" in text and "## Research" in text
            assert "Sources" in text and "[!info]-" in text
            assert "Return Home" in text


def test_multi_parent_flat_route_all_actual_paths_and_order_invariance(atlas):
    child = "CMP-BOUNDED-REFLEX"
    extra = Relationship(source=child, relation="part_of", target="CMP-MEMORY")
    ambiguous = replace(atlas, relationships=atlas.relationships + (extra,))
    paths = preferred_paths(ambiguous)
    assert paths[child] == PRODUCT / f"Components/Identities/Bounded Reflex — {child}.md"
    old_paths = views.identity_page_paths(ambiguous)
    model = views.identity_page_model(
        ambiguous,
        build_index(ambiguous, make_snapshot([], ambiguous), COMMIT),
        child,
        page_paths=old_paths,
    )
    locations = views._identity_page_location(ambiguous, model, old_paths)
    assert any("Body" in line for line in locations)
    assert any("Memory" in line for line in locations)
    reversed_atlas = replace(ambiguous, relationships=tuple(reversed(ambiguous.relationships)))
    assert preferred_paths(reversed_atlas) == paths


def test_route_separation_and_zero_non_rq_readers(atlas):
    records = fictional_records(atlas)
    technical, derived, _, locators = intermediate(atlas, records)
    tree = package(atlas, technical, derived)
    paths = preferred_paths(atlas)
    assert paths["RQ-PROGRAM-AB-001"].parent == PRODUCT / "Program/Research Questions"
    assert paths["THREAD-EXPERIENCE-TO-ACTION-001"].parent == PRODUCT / "Program/Research Threads"
    assert paths["DEC-ATLAS-PILOT-001"].parent == PRODUCT / "Project/Decisions"
    readers = [p for p in tree.files if p.is_relative_to(PRODUCT / "Research")]
    assert len(readers) == sum(r.doc_type == "research_question" for r in records)
    assert all(p.parent == PRODUCT / "Research/Question Readers" for p in readers)
    for record in records:
        if record.doc_type != "research_question":
            assert not any(record.wiki_id in p.name for p in readers)
    for path in readers:
        assert "authored/Deep%20Folder" in tree.files[path].decode()
    assert all(p not in tree.files for p in locators.values())


def test_complete_detail_companion_audits_preserved(atlas, baseline):
    tree, _, derived = baseline
    for identity in views.TECHNICAL_DETAIL_IDS:
        path = preferred_paths(atlas)[identity]
        text = tree.files[path].decode()
        old_detail, _ = views.technical_detail_paths(identity)
        body = markdown_parts(derived[old_detail].decode())[1]
        for line in body.splitlines():
            if line.strip() and "[[" not in line and "](" not in line:
                assert line in text
        assert "Complete consolidated detail audit" in text
        assert tree.routes[views.OWNED_ROOT / old_detail] == path


@pytest.mark.parametrize("populated", [False, True])
def test_exact_graph_inventory_pairs_and_every_origin_per_mode(atlas, baseline, populated):
    records = fictional_records(atlas) if populated else ()
    technical, derived, reference, locators = intermediate(atlas, records)
    tree = package(atlas, technical, derived)
    component_ids = {i for i, n in atlas.entities.items() if n.type == "Component"}
    assert {p.stem for p in tree.files if p.parent == PRODUCT / "Graphs"} == component_ids
    audits = {p.parent.name for p in tree.files if p.name == "Edge Audit.md"}
    assert audits == component_ids
    for identity in sorted(component_ids):
        audit = tree.files[INTERNAL / "Graphs" / identity / "Edge Audit.md"].decode()
        guide = tree.files[PRODUCT / "Graphs" / (identity + ".md")].decode()
        for mode, title in MODES.items():
            section = audit.split("\n## " + title + "\n", 1)[1].split("\n## ", 1)[0]
            projected = graph.project_graph(
                atlas,
                reference,
                RQReader(atlas, records, views.SourceReader(views.SourceResolver(None))),
                scope=identity,
                mode=mode,
            )
            proxy_paths = {
                tree.routes[views.OWNED_ROOT / n.path]: n.identity for n in projected.nodes
            }
            actual_nodes = {
                p for p in tree.files if p.is_relative_to(INTERNAL / "Graphs" / identity / title)
            }
            assert actual_nodes == set(proxy_paths)
            proxy_pairs = set()
            for path, source in proxy_paths.items():
                text = tree.files[path].decode()
                for link in re.findall(r"\[\[([^|]+)\|", text):
                    destination = PurePosixPath(link + ".md")
                    assert destination in proxy_paths
                    proxy_pairs.add((source, proxy_paths[destination]))
            assert proxy_pairs == set(projected.pairs())
            audited_pairs = set(re.findall(r"\| (\S+) → (\S+) \|", section))
            assert audited_pairs == proxy_pairs
            for declaration in projected.declarations:
                assert declaration.origin + " / " + declaration.property in section
            assert all(n.identity in section for n in projected.nodes)
            assert all(graph.literal(d) in section for d in projected.diagnostics)
            assert "detail-only endpoints" in section
            assert "## " + title in guide
            assert str(INTERNAL / "Graphs" / identity / title / "Nodes") in guide


def test_deterministic_output(atlas, baseline):
    tree, technical, derived = baseline
    assert (
        package(
            atlas, dict(reversed(list(technical.items()))), dict(reversed(list(derived.items())))
        ).files
        == tree.files
    )


def test_all_generated_links_filters_and_canvas_routes_resolve(workspace_setup):
    repo, vault, _ = workspace_setup
    for record in fictional_records(load_registry(repo / "docs/research-atlas")):
        write_note(
            vault / "authored/Deep Folder" / (record.wiki_id + ".md"),
            record.model_dump(mode="json", exclude_unset=True),
        )
    workspace.apply(repo, vault)
    tree = migration.build(repo, vault, workspace.resolve_context(repo, vault).source_commit)
    for path, payload in tree.files.items():
        if path.suffix not in {".md", ".canvas", ".base"}:
            continue
        text = payload.decode()
        assert "_generated/derived" not in text
        assert "_generated/technical-atlas" not in text
        for link in re.findall(r"\[\[([^\]]+)\]\]", text):
            route = link.split("|", 1)[0].split("#", 1)[0].rstrip("\\")
            if not route:
                continue
            target = vault / route
            assert target.is_file() or (vault / (route + ".md")).is_file(), (path, route)
        for link in re.findall(r"\]\(([^)\s]+)\)", text):
            if "://" in link or link.startswith("#"):
                continue
            relative = unquote(link.split("#", 1)[0])
            assert (vault / path.parent / relative).is_file(), (path, relative)
        if path.suffix == ".canvas":
            canvas = json.loads(text)
            for node in canvas["nodes"]:
                if node["type"] == "file":
                    assert (vault / node["file"]).is_file()
    base = tree.files[PRODUCT / "Tables/Research Wiki Direct Views.base"].decode()
    assert '!file.inFolder("Research Map")' in base
    assert '!file.inFolder("_Research Map Internals")' in base
    assert (
        'file.inFolder("_Research Map Internals/Registry")'
        in tree.files[PRODUCT / "Tables/Technical Atlas Views.base"].decode()
    )


@pytest.mark.parametrize(
    "fault", ["edit", "owner", "manifest", "unowned", "collision", "case", "symlink", "owner-lost"]
)
def test_failures_before_any_write_or_restore_point(workspace_setup, fault):
    repo, vault, source_commit = workspace_setup
    public.project(repo, vault, source_commit)
    views.project(repo, vault, source_commit)
    if fault in {"edit", "owner"}:
        path = (
            vault
            / public.OWNED_ROOT
            / public.private_path(load_registry(repo / "docs/research-atlas").entities["CMP-BODY"])
        )
        data = path.read_text()
        path.write_text(
            data + "edited" if fault == "edit" else data.replace(public.OWNER, "wrong-owner")
        )
    elif fault == "manifest":
        (vault / public.OWNED_ROOT / public.MANIFEST).write_text("corrupt")
    elif fault == "owner-lost":
        (vault / views.OWNED_ROOT / views.MANIFEST).unlink()
    elif fault == "unowned":
        path = vault / INTERNAL / "Audit/unowned.md"
        path.parent.mkdir(parents=True)
        path.write_text("authored bytes")
    elif fault == "collision":
        (vault / HOME).mkdir()
    elif fault == "case":
        (vault / "research map").mkdir()
    else:
        (vault / HOME).symlink_to(vault / "authored/process.md")
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError):
        workspace.apply(repo, vault)
    assert filesystem_state(vault.parent) == before


def test_apply_idempotence_authored_preservation_restore_and_private_export(workspace_setup):
    repo, vault, source_commit = workspace_setup
    public.project(repo, vault, source_commit)
    views.project(repo, vault, source_commit)
    authored = {p: d for p, d in snapshot(vault).items() if not p.startswith("_generated/")}
    result = workspace.apply(repo, vault)
    state = snapshot(vault)
    workspace.check(repo, vault)
    workspace.apply(repo, vault)
    assert snapshot(vault) == state
    assert all(snapshot(vault)[p] == data for p, data in authored.items())
    receipt = json.loads((result.restore_point / "migration-plan.json").read_text())
    assert len(receipt["before"]) == 696
    assert len(receipt["after"]) == 520
    page = preferred_paths(load_registry(repo / "docs/research-atlas"))["CMP-BODY"]
    export_reader(repo, vault, page, PurePosixPath("reader-exports/Body.md"))
    derivative = (vault / "reader-exports/Body.md").read_text()
    assert "Technical" in derivative and "Research" in derivative
    with pytest.raises(ProjectionError):
        export_reader(repo, vault, page, PurePosixPath("authored/Overwrite.md"))
    with pytest.raises(ProjectionError):
        export_reader(repo, vault, HOME, PurePosixPath("reader-exports/Home.md"))


def test_recovery_refuses_edited_output_before_mutation(workspace_setup, monkeypatch):
    repo, vault, _ = workspace_setup
    write = migration.atomic_write

    def interrupt(root, path, data):
        write(root, path, data)
        raise OSError("interrupted")

    monkeypatch.setattr(migration, "atomic_write", interrupt)
    with pytest.raises(workspace.WorkspaceError):
        workspace.apply(repo, vault)
    point = next((vault.parent / workspace.DEFAULT_RESTORE_DIRECTORY).iterdir())
    generated = next(
        p for p in vault.rglob("*") if p.is_file() and p.is_relative_to(vault / PRODUCT)
    )
    generated.write_text("operator edit")
    before = filesystem_state(vault)
    with pytest.raises(workspace.WorkspaceError, match="edited"):
        workspace.recover(repo, vault, point)
    assert filesystem_state(vault) == before


def test_obsidian_base_serialization_preserves_semantic_ownership(workspace_setup):
    repo, vault, _ = workspace_setup
    workspace.apply(repo, vault)
    path = vault / PRODUCT / "Tables/Technical Atlas Views.base"
    # Core Bases can reserialize YAML and drop comments; semantic ownership survives.
    path.write_text(views.yaml_text(read_yaml(path.read_text())))
    before = filesystem_state(vault)
    workspace.check(repo, vault)
    assert filesystem_state(vault) == before
    workspace.apply(repo, vault)


def test_final_missing_owner_manifest_and_source_history_fail_closed(workspace_setup):
    repo, vault, _ = workspace_setup
    workspace.apply(repo, vault)
    manifest = vault / MANIFESTS[views.OWNER]
    intact = manifest.read_bytes()
    manifest.unlink()
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match="unowned"):
        workspace.apply(repo, vault)
    assert filesystem_state(vault.parent) == before
    manifest.write_bytes(intact)
    source = vault / INTERNAL / "Indexes/source-resolution-index.yaml"
    source.unlink()
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match="Missing source history"):
        workspace.apply(repo, vault)
    assert filesystem_state(vault.parent) == before


def test_future_component_without_system_chain_uses_nonsemantic_identity_route(atlas):
    future = atlas.entities["CMP-BODY"].model_copy(
        update={"id": "CMP-FUTURE", "name": "Future Component"}
    )
    extended = replace(atlas, entities={**atlas.entities, future.id: future})
    assert preferred_paths(extended)[future.id] == (
        PRODUCT / "Components/Identities/Future Component — CMP-FUTURE.md"
    )


def test_direct_legacy_w05_to_final_migration_is_bounded(workspace_setup):
    repo, vault, source_commit = workspace_setup
    public.project(repo, vault, source_commit)
    old = views.project(repo, vault, source_commit)
    manifest = read_yaml(old[views.MANIFEST].decode())
    # Retain only actual v2.3 owned families; no new ownership is manufactured.
    retained = {
        views.TECHNICAL_BASE,
        views.DIRECT_BASE,
        views.INDEX,
        views.REFERENCE_INDEX,
        views.HIERARCHY,
        views.K3_HOME,
    }
    retained.update(h.overview for h in views.COMPONENT_HUB_PATHS.values())
    retained.update(p for p in old if p.parent == views.HIERARCHY_DIR)
    for row in list(manifest["owned_files"]):
        path = PurePosixPath(row["path"])
        if path not in retained:
            (vault / views.OWNED_ROOT / path).unlink()
            manifest["owned_files"].remove(row)
    for field in (
        "presentation_fingerprint_version",
        "presentation_input_fingerprint",
        "source_resolution_fingerprint_version",
        "source_resolution_input_fingerprint",
    ):
        manifest.pop(field)
    manifest["view_schema_version"] = "2.3"
    manifest["reference_index_schema_version"] = "1.0"
    views.ManifestV23.model_validate(manifest)
    (vault / views.OWNED_ROOT / views.MANIFEST).write_text(views.yaml_text(manifest))
    before = filesystem_state(vault)
    with pytest.raises(workspace.WorkspaceError, match="drift"):
        workspace.check(repo, vault)
    assert filesystem_state(vault) == before
    workspace.apply(repo, vault)
    workspace.check(repo, vault)


def test_generated_exclusion_is_rooted_and_authored_nested_names_stay_inputs(workspace_setup):
    repo, vault, _ = workspace_setup
    atlas = load_registry(repo / "docs/research-atlas")
    for record in fictional_records(atlas):
        write_note(
            vault / "authored/Research Map" / (record.wiki_id + ".md"),
            record.model_dump(mode="json", exclude_unset=True),
        )
    _, locators, records = views.authored_snapshot(vault, atlas)
    assert len(records) == len(fictional_records(atlas))
    record_ids = {record.wiki_id for record in records}
    assert all(
        str(path).startswith("authored/Research Map/")
        for identity, path in locators.items()
        if identity in record_ids
    )
    workspace.apply(repo, vault)
    _, refreshed, reread = views.authored_snapshot(vault, atlas)
    assert refreshed == locators and reread == records
