"""Synthetic-only final IA and global ownership migration acceptance evidence."""

import base64
import gzip
import json
import re
import shutil
from copy import deepcopy
from dataclasses import replace
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import pytest
import test_workspace_harness as harness_fixtures
from projection_test_cache import cached_full_projections  # noqa: F401
from rq_reader_fixtures import fictional_records
from test_research_wiki_projection import filesystem_state, snapshot, write_note

from fh_agent.research_atlas import final_projection
from fh_agent.research_atlas import historical_reference as historical
from fh_agent.research_atlas import knowledge_graph as graph
from fh_agent.research_atlas import obsidian_semantics as semantics
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


@pytest.mark.parametrize("family", ["canvas", "excalidraw", "base-and-strict"])
def test_semantic_mutations_fail_before_restore_or_write(workspace_setup, family):
    repo, vault, _ = workspace_setup
    workspace.apply(repo, vault)
    current = {p: (vault / p).read_bytes() for p in migration._actual(vault)}
    canvases = [p for p in current if p.suffix == ".canvas"] if family == "canvas" else []
    canvas_faults = (
        "destination",
        "endpoint",
        "direction",
        "side",
        "add-node",
        "remove-node",
        "add-edge",
        "remove-edge",
        "geometry",
        "node-id",
        "edge-id",
        "node-type",
        "relation-label",
        "metadata",
        "schema",
    )
    # Exercise the exact shared preflight ownership predicate for every Canvas
    # and every mutation; then exercise full filesystem preflight for each fault,
    # rotating through all seven finite surfaces rather than duplicating I/O.
    for path in canvases:
        row = dict(owner=views.OWNER, **semantics.record(current[path], path, views.OWNER))
        for fault in canvas_faults:
            try:
                accepted = migration.intact(canvas_mutation(current[path], fault), path, row)
            except (ValueError, KeyError):
                accepted = False
            assert not accepted, (path, fault)
    for index, fault in enumerate(canvas_faults if family == "canvas" else ()):
        path = canvases[index % len(canvases)]
        assert_rejected_without_mutation(
            repo, vault, vault / path, canvas_mutation(current[path], fault)
        )
    excalidraws = [p for p in current if p.name.endswith(".excalidraw.md")]
    core_scene_faults = {
        "navigation",
        "relation",
        "customData",
        "label",
        "remove-element",
        "add-element",
        "envelope",
        "authored",
    }
    for path, data in current.items():
        kind = semantics.classification(path)
        if kind == semantics.Ownership.EXCALIDRAW and family == "excalidraw":
            row = dict(owner=public.OWNER, **semantics.record(data, path, public.OWNER))
            for index, fault in enumerate(
                (
                    "navigation",
                    "relation",
                    "customData",
                    "label",
                    "remove-element",
                    "add-element",
                    "geometry",
                    "index-order",
                    "index-partial",
                    "index-invalid",
                    "default-meaning",
                    "binding",
                    "background",
                    "unknown-appState",
                    "source-revision",
                    "cache",
                    "envelope",
                    "authored",
                )
            ):
                changed = excalidraw_mutation(data, fault)
                try:
                    accepted = migration.intact(changed, path, row)
                except ValueError:
                    accepted = False
                assert not accepted, (path, fault)
                # Every fault exercises both scene predicates. Core semantic
                # edits exercise both full APIs/scenes; additional serialization
                # guards rotate scenes for full zero-write preflight coverage.
                if fault in core_scene_faults or path == excalidraws[index % len(excalidraws)]:
                    assert_rejected_without_mutation(repo, vault, vault / path, changed)
            if "Agent Anatomy" in path.name:
                assert_rejected_without_mutation(
                    repo, vault, vault / path, excalidraw_mutation(data, "image")
                )
        elif kind == semantics.Ownership.BASE and family == "base-and-strict":
            value = read_yaml(data.decode())
            value["filters"] = {"and": ['file.inFolder("unrelated")']}
            assert_rejected_without_mutation(
                repo, vault, vault / path, views.yaml_text(value).encode()
            )
            changed = read_yaml(data.decode())
            changed["views"].append(deepcopy(changed["views"][0]))
            assert_rejected_without_mutation(
                repo, vault, vault / path, views.yaml_text(changed).encode()
            )
    if family != "base-and-strict":
        return
    # Strict generated Markdown remains byte-owned even for whitespace-only edits.
    assert_rejected_without_mutation(repo, vault, vault / HOME, (vault / HOME).read_bytes() + b"\n")
    asset = vault / INTERNAL / "Assets/Agent Anatomy Hero.svg"
    assert_rejected_without_mutation(repo, vault, asset, asset.read_bytes() + b"edited")


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
                assert (
                    line.replace("Originating Component Hub(s)", "Originating Components") in text
                )
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


def test_anatomy_is_selective_and_qualifies_explanatory_placements(baseline):
    tree, _, _ = baseline
    text = tree.files[PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md"].decode()
    scene = json.loads(re.search(r"```json\n([\s\S]*?)```", text)[1])
    labels = [item["text"] for item in scene["elements"] if item["type"] == "text"]
    assert "EXECUTIVE CONTROL" in labels
    assert "CONTRACT" not in labels
    assert "Observe Assembly Scope" not in text
    assert "Selective explanatory overview" in text
    assert "not complete architecture, exact Function membership or strict runtime order" in text
    assert any("Bridge: Acquire · Replay: Between Mission Runs" in label for label in labels)
    assert "MemoryUpdateRequest is a Cortex proposal" in text
    assert "frozen Body version through Life Episode restarts" in text
    assert "authorized future protocol between Mission Runs" in text


def test_final_navigation_labels_match_destinations(baseline):
    tree, _, _ = baseline
    stale = (
        "Component Hub",
        "Technical Hierarchy",
        "Research Knowledge Home",
        "Observe Assembly",
        "Hub Overview",
        "technical detail workbench",
        "Historical Memory pilot",
    )
    for path, data in tree.files.items():
        if path != HOME and not path.is_relative_to(PRODUCT):
            continue
        if path.suffix != ".md":
            continue
        for target, label in re.findall(r"\[\[([^|\]]+)\|([^\]]+)\]\]", data.decode()):
            assert not any(term in label for term in stale), (path, target, label)
            if target == str(HOME.with_suffix("")):
                assert label in {"Home", "Return Home", "Research Map Home"}, (path, label)
    domain = tree.files[PRODUCT / "Diagrams/Evidence, Memory & Retrieval.excalidraw.md"].decode()
    assert not any(term in domain for term in stale)


def test_consolidated_graph_links_have_distinct_resolving_mode_anchors(atlas, baseline):
    tree, _, _ = baseline
    for identity, node in atlas.entities.items():
        if node.type != "Component":
            continue
        guide = PRODUCT / "Graphs" / (identity + ".md")
        audit = INTERNAL / "Graphs" / identity / "Edge Audit.md"
        for path in (guide, audit):
            text = tree.files[path].decode()
            assert "Graph Profile.md" not in text
            assert "Edge Audit.md in this folder" not in text
            for title in MODES.values():
                assert f"[[#{title}|{title}]]" in text
                assert f"\n## {title}\n" in text
            for target in re.findall(r"\[\[([^|\]]+)\|", text):
                route, _, anchor = target.partition("#")
                if route in {str(guide.with_suffix("")), str(audit.with_suffix(""))}:
                    assert anchor in MODES.values(), (path, target)
                    destination = PurePosixPath(route + ".md")
                    assert f"\n## {anchor}\n" in tree.files[destination].decode()
        text = tree.files[guide].decode()
        assert text.count("Manual activation: open native global Graph") == 1
        assert text.count("Graph geometry, density and colors are not scientific authority") == 1


def test_canvas_primary_links_are_preferred_without_relation_changes(atlas, baseline):
    tree, _, derived = baseline
    preferred = preferred_paths(atlas)
    for identity in views.TECHNICAL_DETAIL_IDS:
        _, old_path = views.technical_detail_paths(identity)
        path = tree.routes[views.OWNED_ROOT / old_path]
        original = json.loads(derived[old_path])
        canvas = json.loads(tree.files[path])
        assert canvas["edges"] == original["edges"]
        for card in canvas["nodes"]:
            subject = next(
                ref for ref in atlas.entities if views._canvas_node_id(ref) == card["id"]
            )
            links = re.findall(r"\[\[([^|\]]+)\|([^\]]+)\]\]", card["text"])
            if subject in preferred:
                assert links[0] == (
                    str(preferred[subject].with_suffix("")),
                    atlas.entities[subject].name,
                )
                assert "> [!info]- Registry audit" in card["text"]
                assert links[1][1] == "Raw Registry record"
                assert links[1][0].startswith(str(INTERNAL / "Registry/Records"))
            else:
                assert atlas.entities[subject].type == "Evidence"
                assert links[0][1] == "Evidence audit / provenance"


def test_home_structure_function_types_and_scientific_navigation(atlas, baseline):
    tree, _, _ = baseline
    preferred = preferred_paths(atlas)
    home = tree.files[HOME].decode()
    assert home.index("## Start here") < home.index("## Complete identity inventory")
    assert "> [!info]- Components" in home
    assert "Flat inventories below are not a hierarchy or a runtime sequence" in home
    assert all(f"[[{path.with_suffix('')}|" in home for path in preferred.values())
    for identity in ("SYS-AGA", "CMP-MEMORY"):
        text = tree.files[preferred[identity]].decode()
        structural = text.split("### Structural navigation", 1)[1].split("### What this is", 1)[0]
        children = [
            edge.source
            for edge in atlas.relationships
            if edge.relation == "part_of" and edge.target == identity
        ]
        assert all(f"[[{preferred[child].with_suffix('')}|" in structural for child in children)
        assert text.count("> [!aga-child]-") == len(children)
        assert text.index("### Structural navigation") < text.index("### Subcomponents / go deeper")
    for identity, node in atlas.entities.items():
        if node.type != "Function":
            continue
        text = tree.files[preferred[identity]].decode().split("## Research", 1)[0]
        assert "| Participant | Technical type |" in text
        for edge in atlas.relationships:
            if edge.relation == "contributes_to_function" and edge.target == identity:
                participant = atlas.entities[edge.source]
                link = views._markdown_table_cell(
                    f"[[{preferred[edge.source].with_suffix('')}|{participant.name}]]"
                )
                assert f"| {link} | {participant.type} |" in text
    steering = tree.files[PRODUCT / "Views/Research Steering.md"].decode().split("<details>", 1)[0]
    assert steering.index("## Research Questions") < steering.index("## Graph navigation")
    assert steering.count("[[Research Map/Views/Graphs|") == 1
    assert "[[Research Map/Graphs/" not in steering
    assert "Current private scientific inventories" in steering


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
def test_failures_before_any_write_or_restore_point(workspace_setup, fault, monkeypatch):
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
    build = migration.build
    builds = []

    def expected_build(*args):
        assert fault == "case", "Invalid ownership must fail before current product construction"
        builds.append(args[2])
        return build(*args)

    monkeypatch.setattr(migration, "build", expected_build)
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError):
        workspace.apply(repo, vault)
    assert filesystem_state(vault.parent) == before
    assert builds == ([source_commit] if fault == "case" else [])


@pytest.mark.parametrize(
    "guard", ["validate_portable_paths", "validate_source_history", "validate_read_provenance"]
)
def test_valid_ownership_still_reaches_later_preflight_guards(workspace_setup, monkeypatch, guard):
    repo, vault, _ = workspace_setup
    workspace.apply(repo, vault)
    build = migration.build
    validate = getattr(migration, guard)
    built = False

    def expected_build(*args):
        nonlocal built
        result = build(*args)
        built = True
        return result

    def reject_later(*args):
        if not built:
            return validate(*args)
        raise ProjectionError("Synthetic later preflight guard")

    monkeypatch.setattr(migration, "build", expected_build)
    monkeypatch.setattr(migration, guard, reject_later)
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match="Synthetic later preflight guard"):
        workspace.apply(repo, vault)
    assert built
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


def managed_paths(tree):
    return [p for p in tree.files if semantics.classification(p) != semantics.Ownership.STRICT]


def drawing_scene(data):
    match = re.search(r"```json\n(.*?)\n```", data.decode(), re.S)
    return match, json.loads(match[1])


def plugin_scene(scene):
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    for rank, item in enumerate(scene["elements"]):
        item.update(version=item["version"] + 1, versionNonce=739174, updated=1791370800000)
        item["index"] = (
            "a" + digits[rank]
            if rank < 62
            else "b" + digits[(rank - 62) // 62] + digits[(rank - 62) % 62]
        )
        item.setdefault("created", None)
        item.setdefault("hasTextLink", False)
        if item.get("boundElements") is None:
            item["boundElements"] = []
        if item["type"] == "text":
            item.setdefault("labelPosition", None)
            item.setdefault("baseFontSize", None)
        if item["type"] == "image":
            item.setdefault("crop", None)
    scene["source"] = "https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.15.3"
    scene["prevTextMode"] = "parsed"
    scene["appState"].update(
        theme="dark",
        scrollX=-220.5,
        scrollY=39,
        zoom={"value": 1.25},
        activeTool={"type": "selection", "customType": None, "lastActiveTool": None},
        gridSize=20,
        gridModeEnabled=False,
        currentItemStrokeColor="#000000",
        currentItemBackgroundColor="transparent",
        currentItemFillStyle="solid",
        currentItemFontSize=20,
        currentItemFontFamily=2,
    )
    scene["files"] = {}  # Plugin syncFiles externalizes the strict generated SVG.
    return scene


def rewrite_managed(data, path, *, compressed=False):
    """Actual-style syntax churn only; fixture compression uses the upstream JS codec."""
    kind = semantics.classification(path)
    if kind == semantics.Ownership.BASE:
        value = read_yaml(data.decode())
        properties = value.get("properties", {})
        if "properties" in value:
            value["properties"] = {
                (key.removeprefix("note.") if key.startswith("note.") else key): item
                for key, item in properties.items()
            }
        for view in value.get("views", []):
            if "order" in view:
                view["order"] = [key.removeprefix("note.") for key in view["order"]]
            if "groupBy" in view:
                view["groupBy"]["property"] = view["groupBy"]["property"].removeprefix("note.")
            for sort in view.get("sort", []):
                sort["property"] = sort["property"].removeprefix("note.")
        return views.yaml_text(dict(reversed(tuple(value.items())))).encode()
    if kind == semantics.Ownership.CANVAS:
        value = json.loads(data)
        value["nodes"][0]["x"] = float(value["nodes"][0]["x"])
        for edge in value["edges"]:
            # JSON Canvas specifies these defaults; no side/direction inference.
            if edge.get("fromEnd") == "none":
                edge.pop("fromEnd")
            if edge.get("toEnd") == "arrow":
                edge.pop("toEnd")
        return json.dumps(dict(reversed(tuple(value.items()))), indent="\t").encode()
    match, scene = drawing_scene(data)
    scene = plugin_scene(scene)
    if compressed:
        name = "agent" if "Agent Anatomy" in path.name else "domain"
        payload = (
            (ROOT / "tests/fixtures/obsidian-reserialization" / (name + ".lz-base64"))
            .read_text()
            .rstrip()
        )
        language = "compressed-json"
    else:
        payload = json.dumps(dict(reversed(tuple(scene.items()))), indent="\t", ensure_ascii=False)
        language = "json"
    text = data.decode()
    # Plugin Markdown caches can gain empty separating lines; preserve all entries.
    text = text[: match.start()] + f"```{language}\n{payload}\n```" + text[match.end() :]
    text = text.replace("## Text Elements\n\n", "## Text Elements\n\n\n")
    return text.encode()


def test_closed_manifest_classes_and_every_managed_format(baseline):
    tree, _, _ = baseline
    counts = {kind: 0 for kind in semantics.Ownership}
    for owner, manifest in MANIFESTS.items():
        metadata = read_yaml(tree.files[manifest].decode())
        assert metadata["product_schema_version"] == "1.1"
        for row in metadata["owned_files"]:
            path = PurePosixPath(row["path"])
            counts[semantics.Ownership(row["ownership"])] += 1
            assert row == {"path": str(path), **semantics.record(tree.files[path], path, owner)}
    assert counts == {
        semantics.Ownership.STRICT: 506,
        semantics.Ownership.BASE: 3,
        semantics.Ownership.CANVAS: 7,
        semantics.Ownership.EXCALIDRAW: 2,
    }
    for path in managed_paths(tree):
        expected = semantics.semantic_digest(tree.files[path], path, tree.owners[path])
        for compressed in {False, True} if path.name.endswith(".excalidraw.md") else {False}:
            rewritten = rewrite_managed(tree.files[path], path, compressed=compressed)
            assert rewritten != tree.files[path]
            assert semantics.semantic_digest(rewritten, path, tree.owners[path]) == expected


def canvas_mutation(data, fault):
    value = json.loads(data)
    node, edge = value["nodes"][0], value["edges"][0]
    if fault == "destination":
        node = next(n for n in value["nodes"] if "[[Research Map/" in n.get("text", ""))
        node["text"] = node["text"].replace("Research Map/", "Wrong Destination/", 1)
    elif fault == "endpoint":
        edge["fromNode"] = edge["toNode"]
    elif fault == "direction":
        edge["fromEnd"], edge["toEnd"] = "arrow", "none"
    elif fault == "side":
        edge["fromSide"] = "left"
    elif fault == "add-node":
        value["nodes"].append(dict(node, id="added-project-node"))
    elif fault == "remove-node":
        value["nodes"].pop()
    elif fault == "add-edge":
        value["edges"].append(dict(edge, id="added-project-edge"))
    elif fault == "remove-edge":
        value["edges"].pop()
    elif fault == "geometry":
        node["x"] += 1
    elif fault == "node-id":
        node["id"] = "changed-project-identity"
    elif fault == "edge-id":
        edge["id"] = "changed-project-edge"
    elif fault == "node-type":
        node["type"] = "file"
    elif fault == "relation-label":
        edge["label"] = "inferred_relation"
    elif fault == "metadata":
        value["generated_by"] = "unrelated-author"
    else:
        value["canvas_view_schema_version"] = "999"
    return json.dumps(value).encode()


def excalidraw_mutation(data, fault):
    match, scene = drawing_scene(data)
    elements = scene["elements"]
    if fault == "navigation":
        next(e for e in elements if e.get("link"))["link"] = "[[Wrong Destination]]"
    elif fault == "relation":
        relation = next(e for e in elements if "atlas_relation" in e.get("customData", {}))[
            "customData"
        ]["atlas_relation"]
        relation["target"] = "CMP-CORTEX" if relation["target"] != "CMP-CORTEX" else "CMP-BODY"
    elif fault == "customData":
        next(e for e in elements if e.get("customData"))["customData"]["operator_added"] = True
    elif fault == "label":
        next(e for e in elements if e["type"] == "text")["text"] = "Incorrect architecture"
    elif fault == "remove-element":
        elements.pop()
    elif fault == "add-element":
        elements.append(dict(elements[0], id="added-project-element"))
    elif fault == "geometry":
        elements[0]["x"] += 1
    elif fault in {"index-order", "index-partial", "index-invalid"}:
        plugin_scene(scene)
        if fault == "index-order":
            elements[0]["index"], elements[1]["index"] = elements[1]["index"], elements[0]["index"]
        elif fault == "index-partial":
            elements[0].pop("index")
        else:
            elements[0]["index"] = "invalid-key"
    elif fault == "default-meaning":
        elements[0]["hasTextLink"] = True
    elif fault == "binding":
        elements[0]["boundElements"] = [{"id": elements[1]["id"], "type": "text"}]
    elif fault == "background":
        scene["appState"]["viewBackgroundColor"] = "#ff0000"
    elif fault == "unknown-appState":
        scene["appState"]["project_semantics"] = "changed"
    elif fault == "image":
        key = next(iter(scene["files"]))
        scene["files"][key]["dataURL"] += "changed"
    elif fault == "source-revision":
        return data.replace(b"source_commit: ", b"source_commit: changed", 1)
    elif fault == "cache":
        return data.replace(
            b"## Text Elements\n", b"## Text Elements\nOperator authored content\n", 1
        )
    elif fault == "envelope":
        return data.replace(public.OWNER.encode(), b"unrelated-author", 1)
    else:
        return data + b"\nOperator authored content\n"
    text = data.decode()
    return (text[: match.start(1)] + json.dumps(scene) + text[match.end(1) :]).encode()


def assert_rejected_without_mutation(repo, vault, path, data):
    canonical = path.read_bytes()
    path.write_bytes(data)
    before = filesystem_state(vault.parent)

    def unexpected_build(*args):
        raise AssertionError("Invalid ownership must fail before current product construction")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(migration, "build", unexpected_build)
        with pytest.raises(workspace.WorkspaceError):
            workspace.check(repo, vault)
        assert filesystem_state(vault.parent) == before
        with pytest.raises(workspace.WorkspaceError):
            workspace.apply(repo, vault)
        assert filesystem_state(vault.parent) == before
    path.write_bytes(canonical)


def test_observed_drift_family_check_apply_and_exact_restore_bytes(workspace_setup):
    repo, vault, _ = workspace_setup
    workspace.apply(repo, vault)
    canonical = snapshot(vault)
    rewritten = {}
    for path in migration._actual(vault):
        if semantics.classification(path) != semantics.Ownership.STRICT:
            rewritten[path] = rewrite_managed(
                (vault / path).read_bytes(), path, compressed=path.name.endswith(".excalidraw.md")
            )
            (vault / path).write_bytes(rewritten[path])
    assert len(rewritten) == 12  # 2 Excalidraw + ALL 7 retained Canvas + 3 Bases.
    before = filesystem_state(vault.parent)
    workspace.check(repo, vault)

    assert filesystem_state(vault.parent) == before
    result = workspace.apply(repo, vault)
    assert snapshot(vault) == canonical
    assert len(migration._actual(vault)) == 520
    receipt = json.loads((result.restore_point / "migration-plan.json").read_text())
    assert receipt["receipt_schema_version"] == "2.0"
    for path, data in rewritten.items():
        assert (result.restore_point / path).read_bytes() == data
        assert receipt["before"][str(path)] == public.digest(data)
        assert receipt["before_ownership"][str(path)][
            "semantic_sha256"
        ] == semantics.semantic_digest(data, path, receipt["before_ownership"][str(path)]["owner"])
    workspace.check(repo, vault)


def test_manifest_classification_is_closed_before_any_write(workspace_setup):
    repo, vault, _ = workspace_setup
    workspace.apply(repo, vault)
    manifest = vault / MANIFESTS[views.OWNER]
    original = manifest.read_bytes()
    for fault in (
        "unknown",
        "wrong-format",
        "missing-semantic",
        "extra-semantic",
        "extra-field",
        "unknown-version",
    ):
        value = read_yaml(original.decode())
        strict = next(r for r in value["owned_files"] if r["ownership"] == "strict-bytes")
        managed = next(r for r in value["owned_files"] if r["ownership"] != "strict-bytes")
        if fault == "unknown":
            managed["ownership"] = "arbitrary-ownership"
        elif fault == "wrong-format":
            strict["ownership"] = "obsidian-canvas-semantics"
        elif fault == "missing-semantic":
            managed.pop("semantic_sha256")
        elif fault == "extra-semantic":
            strict["semantic_sha256"] = "a" * 64
        elif fault == "extra-field":
            managed["adopt_unowned"] = True
        else:
            value["product_schema_version"] = "999"
        assert_rejected_without_mutation(repo, vault, manifest, views.yaml_text(value).encode())


def test_historical_exact_receipt_remains_bounded(workspace_setup):
    repo, vault, _ = workspace_setup
    before = snapshot(vault)
    result = workspace.apply(repo, vault)
    receipt = result.restore_point / "migration-plan.json"
    plan = json.loads(receipt.read_text())
    for key in ("receipt_schema_version", "before_ownership", "after_ownership"):
        plan.pop(key)
    receipt.write_text(json.dumps(plan))
    path = next(p for p in migration._actual(vault) if p.suffix == ".canvas")
    canonical = (vault / path).read_bytes()
    (vault / path).write_bytes(rewrite_managed(canonical, path))
    rewritten = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match="edited"):
        workspace.recover(repo, vault, result.restore_point)
    assert filesystem_state(vault.parent) == rewritten
    (vault / path).write_bytes(canonical)
    workspace.recover(repo, vault, result.restore_point)
    assert snapshot(vault) == before


def test_bounded_10_manifest_upgrade_proves_rewritten_diagrams(workspace_setup, monkeypatch):
    repo, vault, source_commit = workspace_setup
    # A real same-renderer Git tree, not a synthetic commit label over missing code.
    shutil.copytree(
        ROOT / "src/fh_agent/research_atlas",
        repo / "src/fh_agent/research_atlas",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copyfile(ROOT / "src/fh_agent/__init__.py", repo / "src/fh_agent/__init__.py")
    source_commit = harness_fixtures.commit(repo)
    workspace.apply(repo, vault)
    build = migration.build
    prove = migration.prove_ownership
    in_proof = False
    builds = []

    def expected_build(*args):
        builds.append((args[2], in_proof))
        return build(*args)

    def ownership_proof(*args):
        nonlocal in_proof
        in_proof = True
        try:
            return prove(*args)
        finally:
            in_proof = False

    monkeypatch.setattr(migration, "build", expected_build)
    monkeypatch.setattr(migration, "prove_ownership", ownership_proof)
    for manifest in MANIFESTS.values():
        value = read_yaml((vault / manifest).read_text())
        value["product_schema_version"] = "1.0"
        for row in value["owned_files"]:
            row.pop("ownership")
            if not row["path"].endswith(".base"):
                row.pop("semantic_sha256", None)
        (vault / manifest).write_text(views.yaml_text(value))
    for path in migration._actual(vault):
        if semantics.classification(path) != semantics.Ownership.STRICT:
            (vault / path).write_bytes(rewrite_managed((vault / path).read_bytes(), path))
    metadata = read_yaml((vault / MANIFESTS[public.OWNER]).read_text())
    intact_manifest = (vault / MANIFESTS[public.OWNER]).read_bytes()
    next(r for r in metadata["owned_files"] if r["path"].endswith(".excalidraw.md"))["sha256"] = (
        "b" * 64
    )
    (vault / MANIFESTS[public.OWNER]).write_text(views.yaml_text(metadata))
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match="historical"):
        workspace.apply(repo, vault)
    assert filesystem_state(vault.parent) == before
    assert builds == [(source_commit, True)]
    builds.clear()
    (vault / MANIFESTS[public.OWNER]).write_bytes(intact_manifest)
    workspace.apply(repo, vault)
    workspace.check(repo, vault)
    assert builds[0] == (source_commit, True)
    assert (source_commit, False) in builds
    assert all(
        read_yaml((vault / p).read_text())["product_schema_version"] == "1.1"
        for p in MANIFESTS.values()
    )


def original_10_oracle():
    """Public bytes emitted by actual commit A, not current renderer/schema downgrade."""
    data = (ROOT / "src/fh_agent/research_atlas/historical_references/8e544d2.json.gz").read_bytes()
    assert public.digest(data) == "c8cf4a6bbe318c895f2c4e68859b0599069ec4774147e990f32f0171cc3ec1af"
    value = json.loads(gzip.decompress(data))
    files = {PurePosixPath(p): base64.b64decode(v) for p, v in value["files"].items()}
    assert public.digest(files[PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md"]) == (
        "2947d718331e317698a9da0c268411a37d3d1f1658364bf7543b742bad0ca39c"
    )
    return ProductTree(files, {PurePosixPath(p): v for p, v in value["owners"].items()}, {})


@pytest.fixture
def original_10_workspace(workspace_setup):
    repo, vault, _ = workspace_setup
    # Only synthetic inputs. Original Git objects are read locally, never fetched.
    (vault / "authored/process.md").unlink()
    shutil.copytree(
        ROOT / "src/fh_agent/research_atlas",
        repo / "src/fh_agent/research_atlas",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copyfile(ROOT / "src/fh_agent/__init__.py", repo / "src/fh_agent/__init__.py")
    commit = harness_fixtures.commit(repo)
    common = Path(harness_fixtures.git(ROOT, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = ROOT / common
    (repo / ".git/objects/info/alternates").write_text(str(common.resolve() / "objects") + "\n")
    oracle = original_10_oracle()
    for path, data in oracle.files.items():
        (vault / path).parent.mkdir(parents=True, exist_ok=True)
        (vault / path).write_bytes(data)
    return repo, vault, commit, oracle


def test_cross_revision_10_original_bytes_then_supported_upgrade(original_10_workspace):
    repo, vault, commit, oracle = original_10_workspace
    reference = historical.resolve(repo, vault, historical.HISTORICAL_COMMIT, migration.build)
    assert reference.files == oracle.files
    assert reference.owners == oracle.owners
    current = migration.build(repo, vault, historical.HISTORICAL_COMMIT)
    diagrams = [p for p in managed_paths(oracle) if not p.suffix == ".base"]
    assert len(diagrams) == 9
    assert all(current.files[p] != oracle.files[p] for p in diagrams)
    for p in managed_paths(oracle):
        (vault / p).write_bytes(rewrite_managed(oracle.files[p], p))
    before = snapshot(vault)
    result = workspace.apply(repo, vault)
    assert result.source_commit == commit
    assert result.restore_point is not None
    assert all(
        public.digest((result.restore_point / p).read_bytes()) == before[str(p)]
        for p in oracle.files
    )
    assert (vault / "authored/keep.bin").read_bytes() == bytes(range(32))
    state = filesystem_state(vault.parent)
    workspace.check(repo, vault)
    assert filesystem_state(vault.parent) == state
    assert all(
        read_yaml((vault / p).read_text())["product_schema_version"] == "1.1"
        for p in MANIFESTS.values()
    )


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("reference-corrupt", "Corrupt historical original reference"),
        ("reference-missing", "No such file"),
        ("reference-symlink", "Symlink boundary"),
        ("git-object-missing", "Git source check"),
        ("unsupported-renderer", "Unsupported historical renderer"),
        ("wrong-commit", "Git source check"),
        ("wrong-provenance", "Historical manifest provenance"),
        ("wrong-sha", "historical semantic ownership"),
        ("wrong-owner", "Invalid final owner manifest"),
        ("wrong-path", "Unknown/unowned"),
        ("unavailable-input", "Historical admissible inputs"),
        ("canvas-side", "Owned content was edited"),
        ("excalidraw-height", "Owned content was edited"),
        ("excalidraw-whitespace", "Owned content was edited"),
        ("excalidraw-image-route", "Generated illustration route"),
    ],
)
def test_cross_revision_10_rejections_are_zero_write(
    original_10_workspace, monkeypatch, fault, reason
):
    repo, vault, _, oracle = original_10_workspace
    canvas = next(p for p in oracle.files if p.suffix == ".canvas")
    anatomy = PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md"
    domain = PRODUCT / "Diagrams/Evidence, Memory & Retrieval.excalidraw.md"
    # Exercise actual historical promotion, including harmless permitted serialization.
    for p in managed_paths(oracle):
        (vault / p).write_bytes(rewrite_managed(oracle.files[p], p))
    if fault.startswith("reference-"):
        path = repo.parent / "original-reference.json.gz"
        if fault == "reference-corrupt":
            path.write_bytes(historical.REFERENCE_PATH.read_bytes() + b"corrupt")
        elif fault == "reference-symlink":
            path.symlink_to(historical.REFERENCE_PATH)
        monkeypatch.setattr(historical, "REFERENCE_PATH", path)
    elif fault == "git-object-missing":
        (repo / ".git/objects/info/alternates").unlink()
    elif fault == "unsupported-renderer":
        revision = harness_fixtures.git(repo, "rev-list", "--max-parents=0", "HEAD")
        for path in MANIFESTS.values():
            metadata = read_yaml((vault / path).read_text())
            metadata["provenance"]["source_commit"] = revision
            (vault / path).write_text(views.yaml_text(metadata))

        def unexpected_build(*args):
            raise AssertionError("Untrusted historical renderer must reject before build")

        monkeypatch.setattr(migration, "build", unexpected_build)
    elif fault in {"wrong-commit", "wrong-provenance", "wrong-sha", "wrong-owner", "wrong-path"}:
        path = vault / MANIFESTS[public.OWNER]
        metadata = read_yaml(path.read_text())
        if fault == "wrong-commit":
            metadata["provenance"]["source_commit"] = "f" * 40
        elif fault == "wrong-provenance":
            metadata["provenance"]["record_count"] += 1
        elif fault == "wrong-owner":
            metadata["generated_by"] = views.OWNER
        else:
            row = next(r for r in metadata["owned_files"] if r["path"] == str(anatomy))
            if fault == "wrong-sha":
                row["sha256"] = "b" * 64
            else:
                row["path"] = str(PRODUCT / "Diagrams/Untrusted.excalidraw.md")
        path.write_text(views.yaml_text(metadata))
    elif fault == "unavailable-input":
        write_note(vault / "authored/process.md")
    elif fault == "canvas-side":
        (vault / canvas).write_bytes(canvas_mutation(oracle.files[canvas], "side"))
    elif fault in {"excalidraw-height", "excalidraw-whitespace"}:
        data = oracle.files[domain]
        match, scene = drawing_scene(data)
        element = next(e for e in scene["elements"] if e["type"] == "text")
        if fault == "excalidraw-height":
            element["height"] += 0.5
        else:
            element["text"] += " "
        text = data.decode()
        (vault / domain).write_text(
            text[: match.start(1)] + json.dumps(scene) + text[match.end(1) :]
        )
    else:
        (vault / anatomy).write_bytes(
            oracle.files[anatomy].replace(
                b"[[_Research Map Internals/Assets/Agent Anatomy Hero.svg]]",
                b"[[Agent Anatomy Hero.svg]]",
            )
        )
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match=reason):
        workspace.apply(repo, vault)
    assert filesystem_state(vault.parent) == before
    assert not (vault.parent / workspace.DEFAULT_RESTORE_DIRECTORY).exists()


def test_10_matching_bytes_do_not_hide_wrong_provenance(original_10_workspace):
    repo, vault, _, _ = original_10_workspace
    manifest = vault / MANIFESTS[public.OWNER]
    metadata = read_yaml(manifest.read_text())
    metadata["provenance"]["record_count"] += 1
    manifest.write_text(views.yaml_text(metadata))
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match="provenance"):
        workspace.apply(repo, vault)
    assert filesystem_state(vault.parent) == before


def test_semantic_receipt_recovery_preserves_plugin_bytes_and_blocks_edits(
    workspace_setup, monkeypatch
):
    repo, vault, _ = workspace_setup
    workspace.apply(repo, vault)
    for path in migration._actual(vault):
        if semantics.classification(path) != semantics.Ownership.STRICT:
            (vault / path).write_bytes(rewrite_managed((vault / path).read_bytes(), path))
    plugin_before = snapshot(vault)
    write = migration.atomic_write

    def interrupt(root, path, data):
        write(root, path, data)
        if path.suffix == ".canvas":
            raise OSError("synthetic interruption")

    with monkeypatch.context() as patch:
        patch.setattr(migration, "atomic_write", interrupt)
        with pytest.raises(workspace.WorkspaceError, match="migration failed"):
            workspace.apply(repo, vault)
    point = max((vault.parent / workspace.DEFAULT_RESTORE_DIRECTORY).iterdir())
    canvas = next(p for p in migration._actual(vault) if p.suffix == ".canvas")
    canonical = (vault / canvas).read_bytes()
    (vault / canvas).write_bytes(canvas_mutation(canonical, "direction"))
    before = filesystem_state(vault)
    with pytest.raises(workspace.WorkspaceError, match="edited"):
        workspace.recover(repo, vault, point)
    assert filesystem_state(vault) == before
    (vault / canvas).write_bytes(rewrite_managed(canonical, canvas))
    workspace.recover(repo, vault, point)
    assert snapshot(vault) == plugin_before
    workspace.check(repo, vault)


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
