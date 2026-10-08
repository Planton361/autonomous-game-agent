"""Synthetic-only final IA and global ownership migration acceptance evidence."""

import ast
import base64
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import pytest
import test_workspace_harness as harness_fixtures
import yaml
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
from fh_agent.research_atlas.architecture_explanations import (
    AREAS,
    GUIDES,
    SOURCE,
    parse_explanations,
    validate_dependencies,
)
from fh_agent.research_atlas.final_projection import (
    ARCHITECTURE_CANVAS,
    ARCHITECTURE_TREE,
    EXECUTION_CANVAS,
    EXECUTION_FLOW,
    EXECUTION_FLOW_ORIENTATION_IDS,
    INTERACTION_CANVAS,
    INTERACTION_MAP,
    INTERACTION_ORIENTATION_IDS,
    INTERACTION_RELATIONS,
    MANIFESTS,
    MODES,
    ProductTree,
    architecture_tree,
    execution_flow,
    interaction_map,
    package,
)
from fh_agent.research_atlas.preferred_paths import HOME, INTERNAL, PRODUCT, preferred_paths
from fh_agent.research_atlas.private_projection import ProjectionError, markdown_parts, read_yaml
from fh_agent.research_atlas.private_reference_index import build_index, make_snapshot
from fh_agent.research_atlas.reader_export import export_reader
from fh_agent.research_atlas.rq_presentation import RQReader
from fh_agent.research_atlas.schema import Relationship
from fh_agent.research_atlas.validator import Atlas, load_registry

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

    def final(atlas, technical, derived, *, explanations=None):
        # Include byte content and original ordering. Reordered/changed inputs
        # exercise the real renderer independently; no pickle is loaded/executed.
        key = (
            atlas_key(atlas),
            tuple(technical.items()),
            tuple(derived.items()),
            explanations.model_dump_json() if explanations is not None else None,
        )
        if key not in final_cache:
            final_cache[key] = final_render(atlas, technical, derived, explanations=explanations)
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
    assert len(tree.files) == 526
    assert 696 - 526 == 170
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
    assert sum(p.suffix == ".canvas" for p in tree.files) == 10
    assert {ARCHITECTURE_TREE, ARCHITECTURE_CANVAS} <= tree.files.keys()
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


def assert_architecture_parity(atlas, body, payload):
    paths = preferred_paths(atlas)
    canvas = json.loads(payload)
    actors = {i for i, n in atlas.entities.items() if n.type in {"System", "Component"}}
    nodes = {}
    markdown_trails = set()
    stack = []
    for line in body.splitlines():
        match = re.match(r"^( *)- \[\[.*\]\] — (System|Component) · `([^`]+)`", line)
        if match:
            depth = len(match[1]) // 2
            stack[depth:] = [match[3]]
            markdown_trails.add(tuple(stack))
    for node in canvas["nodes"]:
        if node["id"] == "legend" or node["type"] != "text":
            continue
        identity = re.search(r"`((?:SYS|CMP)-[^`]+)`", node["text"])[1]
        assert f"[[{paths[identity].with_suffix('')}|" in node["text"]
        assert atlas.entities[identity].technical.implementation_status in node["text"]
        nodes[node["id"]] = identity
    assert set(nodes.values()) == actors
    assert {trail[-1] for trail in markdown_trails} == actors
    visual_pairs = {(nodes[e["toNode"]], nodes[e["fromNode"]]) for e in canvas["edges"]}
    markdown_pairs = {(trail[-1], trail[-2]) for trail in markdown_trails if len(trail) > 1}
    declared = {(e.source, e.target) for e in atlas.relationships if e.relation == "part_of"}
    assert visual_pairs == markdown_pairs == declared
    assert len(canvas["edges"]) == len(markdown_trails) - sum(len(t) == 1 for t in markdown_trails)
    assert all(e["label"] == "contains" and e["toEnd"] == "none" for e in canvas["edges"])
    cards = [n for n in canvas["nodes"] if n["id"] != "legend" and n["type"] == "text"]
    for index, left in enumerate(cards):
        for right in cards[index + 1 :]:
            assert (
                left["x"] + left["width"] <= right["x"]
                or right["x"] + right["width"] <= left["x"]
                or left["y"] + left["height"] <= right["y"]
                or right["y"] + right["height"] <= left["y"]
            ), (left, right)
    return markdown_trails, nodes


def test_architecture_tree_complete_ancestry_navigation_and_fallback(atlas, baseline):
    tree = baseline[0]
    body = tree.files[ARCHITECTURE_TREE].decode()
    assert_architecture_parity(atlas, body, tree.files[ARCHITECTURE_CANVAS])
    route = f"[[{ARCHITECTURE_TREE.with_suffix('')}|Architecture Tree]]"
    for page in [HOME, PRODUCT / "Guides/Using the Research Map.md"] + [
        p
        for i, p in preferred_paths(atlas).items()
        if atlas.entities[i].type in {"System", "Component"}
    ]:
        assert route in tree.files[page].decode()
    assert f"![[{ARCHITECTURE_CANVAS}]]" in body
    assert "embed previews shapes only" in body
    assert f"[[{ARCHITECTURE_CANVAS}|Open Architecture Tree Canvas]]" in body
    assert "## Linked Markdown tree" in body
    assert "## Context outside ancestry" in body
    assert "target-only" in body and "does not certify capability" in body
    assert "child `part_of` parent" in body


def test_architecture_tree_multiple_paths_detached_roots_and_order_invariance(atlas):
    # A multi-parent ancestor repeats its descendant paths without selecting a parent.
    relationships = tuple(
        e
        for e in atlas.relationships
        if not (e.relation == "part_of" and e.source == "CMP-SCREEN-CAPTURE")
    ) + (Relationship(source="CMP-MEMORY", relation="part_of", target="CMP-MANAGER"),)
    altered = replace(atlas, relationships=relationships)
    body, canvas = architecture_tree(altered, preferred_paths(altered))
    trails, nodes = assert_architecture_parity(altered, body, canvas)
    assert "### No System containment chain" in body
    assert ("CMP-SCREEN-CAPTURE",) in trails
    assert sum(i == "CMP-MEM-EPISODIC" for i in nodes.values()) == 2
    assert ("SYS-AGA", "CMP-MANAGER", "CMP-MEMORY", "CMP-MEM-EPISODIC") in trails
    assert ("SYS-AGA", "CMP-MEMORY", "CMP-MEM-EPISODIC") in trails
    reordered = replace(
        altered,
        entities=dict(reversed(list(altered.entities.items()))),
        relationships=tuple(reversed(relationships)),
    )
    assert architecture_tree(reordered, preferred_paths(reordered)) == (body, canvas)


def test_architecture_tree_context_never_adds_ancestry_and_cycle_rejects(atlas):
    expected = architecture_tree(atlas, preferred_paths(atlas))
    context = Relationship(source="CMP-MEMORY", relation="controls", target="CMP-MANAGER")
    altered = replace(atlas, relationships=atlas.relationships + (context,))
    assert architecture_tree(altered, preferred_paths(altered)) == expected
    cyclic = replace(
        atlas,
        relationships=atlas.relationships
        + (Relationship(source="CMP-MEMORY", relation="part_of", target="CMP-MEM-EPISODIC"),),
    )
    with pytest.raises(ProjectionError, match="containment cycle"):
        architecture_tree(cyclic, preferred_paths(atlas))


def test_execution_flow_gates_and_complete_plain_markdown_fallback(atlas, baseline):
    text = baseline[0].files[EXECUTION_FLOW].decode()
    assert text.count("```mermaid\n") == 1
    diagram = text.split("```mermaid\n")[1].split("```", 1)[0]
    assert diagram.startswith("flowchart TD\n")
    # Source-grounded authority branches, independent of containment or runtime tests.
    edges = set(re.findall(r"^    (\w+) (?:-->|-\.->)(?:\|[^\n]+?\|)? (\w+)$", diagram, re.M))
    assert ("cortex", "manager") in edges
    assert not any(
        target in {"body", "safety", "execute"} for origin, target in edges if origin == "cortex"
    )
    assert {
        ("manager", "contract"),
        ("contract", "body"),
        ("body", "safety"),
        ("safety", "execute"),
        ("execute", "outcome"),
        ("outcome", "verifier"),
        ("verifier", "evaluate"),
        ("evaluate", "close"),
        ("close", "context"),
    } <= edges
    assert {origin for origin, target in edges if target == "execute"} == {"safety"}
    assert {
        ("firewall", "reject"),
        ("manager", "reject"),
        ("safety", "reject"),
        ("reject", "close"),
        ("capture", "firewall"),
        ("bridge", "firewall"),
    } <= edges
    assert "no focus / unsafe / unloggable" in diagram
    assert "optional allowlisted visible feed" in diagram
    assert "Body / eligible Reflex" in diagram
    assert "no active prior contract" in diagram
    assert "same Mission Run / frozen Body" in diagram
    assert "between Mission Runs; separately authorized" in diagram
    assert {origin for origin, target in edges if target == "learn"} == {"terminal"}
    assert ("learn", "next") in edges

    fallback = re.sub(r"```mermaid\n.*?```", "", text, flags=re.S)
    assert list(map(int, re.findall(r"^(\d+)\. ", fallback, re.M))) == list(range(1, 10))
    for required in (
        "Hidden game state is never authority",
        "Cortex cannot directly call InputExecutor",
        "not invoked per frame",
        "Only Manager opens a valid bounded Skill Contract",
        "Reflex cannot invent goals",
        "functional emergency stop",
        "durable proposal/execution/rejection logging with before/after evidence linkage",
        "without labelling it an executed action",
        "Cortex never grades itself",
        "screenshot/hash change alone is not success",
        "Success, failure, timeout, no-progress, target loss, safety event, "
        "contamination, death or contradiction",
        "Manager stop path directly",
        "closes/suspends the prior contract",
        "no between-Life-Episode model/controller replacement or Body-weight update",
        "Only between Mission Runs",
        "separately authorized future protocol",
        "held-out validation and safety/false-success checks",
        "certify or reject",
        "activate only a certified version",
        "not a trace of a demonstrated live loop",
        "neither Phase-D nor Phase-H exit",
        "missing Registry mapping implies no omitted capability or scientific weakness",
        "not a per-frame schedule or a strictly sequential order",
        "Process arrows never declare Registry relations or `part_of` ancestry",
        "Native visual rendering remains unverified",
    ):
        assert required in fallback
    for locator in (
        "02_ARCHITECTURE_CANONICAL.md#1-normative-architecture",
        "#2-multi-timescale-control",
        "#6-cortex-contract",
        "#7-manager--executive-contract",
        "#9-body-design",
        "#10-reflex",
        "#11-independent-verification-and-reward",
        "#12-learning-lifecycle",
        "#14-safetyinput",
        "ALIGN-2026-09-19-v1.0/README.md#nested-experimental-units",
        "#mission-run-identity-and-mutable-state",
        "#restart-and-terminal-semantics",
        "03_RESEARCH_ROADMAP_CANONICAL.md#status-rule",
    ):
        assert locator in fallback


def test_execution_flow_independent_run_without_training_and_optional_candidate_paths(baseline):
    text = baseline[0].files[EXECUTION_FLOW].decode()
    diagram = text.split("```mermaid\n")[1].split("```", 1)[0]
    # A real direct transition must coexist with separately authorized learning;
    # merely describing learning as optional does not supply a no-training route.
    assert re.search(
        r'^    terminal -->\|"already eligible Body; no retraining"\| next$', diagram, re.M
    )
    assert re.search(
        r'^    terminal -\.->\|"between Mission Runs; separately authorized"\| learn$',
        diagram,
        re.M,
    )
    assert re.search(
        r'^    learn -\.->\|"activate certified candidate only"\| next$', diagram, re.M
    )
    assert re.search(
        r'^    learn -\.->\|"candidate rejected; retain eligible prior Body"\| next$',
        diagram,
        re.M,
    )
    assert "Next independently eligible Mission Run" in diagram
    assert "eligible Body; fresh state" in diagram and "independently frozen identity" in diagram
    fallback = re.sub(r"```mermaid\n.*?```", "", text, flags=re.S)
    for required in (
        "may begin without retraining using the already eligible Body version",
        "protocol-defined fresh experimental state, a new mission identity/manifest",
        "independently frozen identities, including Body version and weights",
        "Neither path authorizes automatic run start or within-Mission-Run "
        "parameter/controller replacement",
        "Only between Mission Runs",
        "separately authorized future protocol",
        "held-out validation and safety/false-success checks",
        "activate only a certified version",
        "A rejected candidate must never activate",
        "rejection does not prevent a new independently eligible Mission Run "
        "with the already eligible Body version",
        "no between-Life-Episode model/controller replacement or Body-weight update",
    ):
        assert required in fallback


def test_execution_flow_preferred_navigation_statuses_and_order_invariance(atlas, baseline):
    tree = baseline[0]
    paths = preferred_paths(atlas)
    text = tree.files[EXECUTION_FLOW].decode()
    linked_types = set()
    for identity in re.findall(r"`((?:SYS|CMP|FUNC|CON|DAT)-[^`]+)`", text):
        node = atlas.entities[identity]
        assert f"[[{paths[identity].with_suffix('')}\\|{node.name}]]" in text
        assert paths[identity] in tree.files
        technical = getattr(node, "technical", None)
        row = next(line for line in text.splitlines() if f"`{identity}`" in line)
        assert (technical.implementation_status if technical else "not applicable (context)") in row
        linked_types.add(node.type)
    assert linked_types == {"System", "Component", "Function", "Contract", "DataArtifact"}
    assert "CMP-BOUNDED-REFLEX` | target-only" in text
    assert "CMP-TEMPORAL-STATE` | target-only" in text
    route = f"[[{EXECUTION_FLOW.with_suffix('')}|Ablaufdiagramm]]"
    navigation = {HOME, PRODUCT / "Guides/Using the Research Map.md"} | {
        paths[i] for i in EXECUTION_FLOW_ORIENTATION_IDS
    }
    assert {p for p, data in tree.files.items() if route.encode() in data} == navigation
    reordered = replace(
        atlas,
        entities=dict(reversed(list(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    assert execution_flow(reordered, preferred_paths(reordered)) == execution_flow(atlas, paths)
    # Changing a contextual relation never interprets a process arrow as ancestry.
    altered = replace(
        atlas,
        relationships=atlas.relationships
        + (Relationship(source="CMP-CORTEX", relation="controls", target="CMP-BODY"),),
    )
    assert execution_flow(altered, paths) == execution_flow(atlas, paths)
    unmapped = replace(
        atlas, entities={i: n for i, n in atlas.entities.items() if i != "CMP-TEMPORAL-STATE"}
    )
    unmapped_paths = {i: p for i, p in paths.items() if i != "CMP-TEMPORAL-STATE"}
    without_mapping = execution_flow(unmapped, unmapped_paths)
    assert "Temporal State + evidence / retrieval" in without_mapping
    assert "missing Registry mapping implies no omitted capability" in without_mapping
    metadata = markdown_parts(text)[0]
    assert metadata["generated_by"] == views.OWNER
    manifest = read_yaml(tree.files[MANIFESTS[views.OWNER]].decode())
    record = next(r for r in manifest["owned_files"] if r["path"] == str(EXECUTION_FLOW))
    assert record["ownership"] == "strict-bytes"
    assert "semantic_sha256" not in record


def test_execution_flow_independent_frozen_baseline_product_delta(
    atlas, baseline, tmp_path, monkeypatch
):
    # Execute only the reviewed immutable generator at the Issue's exact base,
    # with the SAME frozen synthetic inputs. Current code is never the baseline oracle.
    revision = "7628d264316c04a59f6b7d89f43609352fbc6d8c"
    source = harness_fixtures.git(
        ROOT, "show", f"{revision}:src/fh_agent/research_atlas/final_projection.py"
    )
    file = tmp_path / "baseline_final_projection.py"
    file.write_text(source)
    name = "fh_agent.research_atlas._issue164_baseline"
    spec = spec_from_file_location(name, file)
    module = module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    _, technical, derived = baseline
    after = immutable_interaction_base(atlas, technical, derived, tmp_path, monkeypatch)
    before = module.package(atlas, technical, derived)
    assert len(before.files) == 522 and len(after.files) == 523
    assert set(after.files) - set(before.files) == {EXECUTION_FLOW}
    assert not set(before.files) - set(after.files)
    paths = preferred_paths(atlas)
    changed = {p for p in before.files if before.files[p] != after.files[p]}
    assert changed == {
        HOME,
        PRODUCT / "Guides/Using the Research Map.md",
        MANIFESTS[views.OWNER],
    } | {paths[i] for i in EXECUTION_FLOW_ORIENTATION_IDS}
    assert before.routes == after.routes
    assert {p: after.owners[p] for p in before.owners} == before.owners
    # Everything else, including Tree/Canvas, all seven relation Canvases,
    # Bases, Excalidraw, Graphs, Registry, ledger and technical manifest is byte-identical.
    assert all(before.files[p] == after.files[p] for p in before.files.keys() - changed)
    assert after.owners[EXECUTION_FLOW] == views.OWNER
    assert (
        immutable_interaction_base(atlas, technical, derived, tmp_path, monkeypatch).files
        == after.files
    )

    # The bounded CONTROL repair changes only the diagram and its manifest hash
    # relative to the reviewed PR head, retaining every other generated byte.
    reviewed_revision = "3772366f7beb7e826ec9ecce317becadce281472"
    file.write_text(
        harness_fixtures.git(
            ROOT, "show", f"{reviewed_revision}:src/fh_agent/research_atlas/final_projection.py"
        )
    )
    name = "fh_agent.research_atlas._issue164_reviewed"
    spec = spec_from_file_location(name, file)
    module = module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    reviewed = module.package(atlas, technical, derived)
    assert after.files.keys() == reviewed.files.keys()
    assert {p for p in reviewed.files if reviewed.files[p] != after.files[p]} == {
        EXECUTION_FLOW,
        MANIFESTS[views.OWNER],
    }
    assert after.routes == reviewed.routes and after.owners == reviewed.owners


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
    assert len(receipt["after"]) == 534
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
        semantics.Ownership.STRICT: 509,
        semantics.Ownership.BASE: 3,
        semantics.Ownership.CANVAS: 10,
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
    assert len(rewritten) == 15  # 2 Excalidraw + all 10 Canvas + 3 Bases.
    before = filesystem_state(vault.parent)
    workspace.check(repo, vault)

    assert filesystem_state(vault.parent) == before
    result = workspace.apply(repo, vault)
    assert snapshot(vault) == canonical
    assert len(migration._actual(vault)) == 534
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


ISSUE166_BASE = "3c028f74068d027e98c68a267d72036e1a8fb647"


def immutable_interaction_base(
    atlas, technical, derived, tmp_path, monkeypatch, revision=ISSUE166_BASE
):
    source = harness_fixtures.git(
        ROOT, "show", f"{revision}:src/fh_agent/research_atlas/final_projection.py"
    )
    file = tmp_path / "issue166_baseline.py"
    file.write_text(source)
    name = "fh_agent.research_atlas._issue166_baseline"
    spec = spec_from_file_location(name, file)
    module = module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module.package(atlas, technical, derived)


def interaction_rows(text):
    return re.findall(r"^\| `([^`]+)` \| .*?`([^`]+)`.*? \| .*?`([^`]+)`.*? \|$", text, re.M)


def interaction_visual_rows(text):
    return [
        (relation, source.replace("_", "-"), target.replace("_", "-"))
        for source, relation, target in re.findall(
            r'^    ([A-Z0-9_]+) -->\|"([a-z_]+)"\| ([A-Z0-9_]+)$', text, re.M
        )
    ]


def test_interaction_exact_typed_directed_coverage_and_preferred_links(atlas, baseline):
    tree = baseline[0]
    text = tree.files[INTERACTION_MAP].decode()
    expected = sorted(
        (e.relation, e.source, e.target)
        for e in atlas.relationships
        if e.relation in INTERACTION_RELATIONS
    )
    assert len(expected) == 47 and len({r for r, _, _ in expected}) == 9
    assert interaction_rows(text) == expected
    assert sorted(interaction_visual_rows(text)) == expected
    assert len(interaction_visual_rows(text)) == len(set(interaction_visual_rows(text)))
    paths = preferred_paths(atlas)
    for relation, source, target in expected:
        row = next(
            line
            for line in text.splitlines()
            if line.startswith(f"| `{relation}` |")
            and f"`{source}`" in line
            and f"`{target}`" in line
        )
        for identity in (source, target):
            node = atlas.entities[identity]
            assert f"[[{paths[identity].with_suffix('')}\\|{node.name}]]" in row
            assert node.type in row and node.technical.implementation_status in row
            assert paths[identity] in tree.files
    assert "Component · target-only" in text and "Component · partial" in text
    panels = re.findall(r"```mermaid\n(.*?)```", text, re.S)
    assert len(panels) >= 8
    assert all(len(interaction_visual_rows(panel)) <= 8 for panel in panels)
    route = f"[[{INTERACTION_MAP.with_suffix('')}|Interaction Map]]".encode()
    assert {p for p, data in tree.files.items() if route in data} == {
        HOME,
        PRODUCT / "Guides/Using the Research Map.md",
        *(paths[i] for i in INTERACTION_ORIENTATION_IDS),
    }
    manifest = read_yaml(tree.files[MANIFESTS[views.OWNER]].decode())
    record = next(r for r in manifest["owned_files"] if r["path"] == str(INTERACTION_MAP))
    assert record["ownership"] == "strict-bytes" and "semantic_sha256" not in record
    fallback = re.sub(r"```mermaid\n.*?```", "", text, flags=re.S)
    assert interaction_rows(fallback) == expected
    for phrase in (
        "no presentation inversion",
        "Shared payloads never imply",
        "not temporal ordering",
        "Manager alone",
        "Independent Verifier",
        "hidden-state access is an integrity incident",
        "Body weights remain frozen",
        "between Mission Runs",
        "no capability, completeness or novelty conclusion",
        "laptop legibility remain unverified",
        "working full loop, scientific finding",
    ):
        assert phrase in fallback


def test_interaction_order_content_sparse_optional_and_status_changes(atlas):
    paths = preferred_paths(atlas)
    text = interaction_map(atlas, paths)
    reordered = replace(
        atlas,
        entities=dict(reversed(list(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    assert interaction_map(reordered, preferred_paths(reordered)) == text
    additions = (
        Relationship(relation="updates", source="CMP-MEMORY", target="DAT-OBSERVATION"),
        Relationship(relation="retrieves_from", source="CMP-CORTEX", target="DAT-SCREEN-FRAME"),
        Relationship(relation="consumes", source="CMP-BODY", target="CON-CORTEX-CONTEXT"),
    )
    changed = replace(atlas, relationships=atlas.relationships + additions)
    expected = {(e.relation, e.source, e.target) for e in additions}
    assert (
        set(interaction_rows(interaction_map(changed, paths)))
        == set(interaction_rows(text)) | expected
    )
    assert (
        set(interaction_visual_rows(interaction_map(changed, paths)))
        == set(interaction_rows(text)) | expected
    )
    # Payload sharing adds precisely the declaration, never Cortex -> Body coupling.
    assert ("controls", "CMP-CORTEX", "CMP-BODY") not in interaction_rows(
        interaction_map(changed, paths)
    )
    empty = replace(
        atlas,
        relationships=tuple(
            e for e in atlas.relationships if e.relation not in INTERACTION_RELATIONS
        ),
    )
    rendered = interaction_map(empty, paths)
    assert interaction_rows(rendered) == interaction_visual_rows(rendered) == []
    assert "No selected technical relations; no interaction inferred" in rendered
    assert "No selected Registry relations in this panel" in rendered
    node = atlas.entities["CMP-CORTEX"]
    updated = node.model_copy(
        update={"technical": node.technical.model_copy(update={"implementation_status": "unknown"})}
    )
    changed_status = replace(atlas, entities={**atlas.entities, node.id: updated})
    assert "Component · unknown" in interaction_map(changed_status, paths)
    assert interaction_rows(interaction_map(changed_status, paths)) == interaction_rows(text)
    # An otherwise valid technical target outside known panels is still rendered.
    extra = Relationship(
        relation="observes", source="CMP-CORTEX", target="MEAS-CORTEX-PROPOSAL-001"
    )
    extended = interaction_map(replace(atlas, relationships=atlas.relationships + (extra,)), paths)
    assert "Additional declared technical interactions" in extended
    assert "MeasurementPoint" in extended
    assert (extra.relation, extra.source, extra.target) in interaction_visual_rows(extended)


def test_interaction_independent_frozen_product_delta(atlas, baseline, tmp_path, monkeypatch):
    _, technical, derived = baseline
    after = immutable_interaction_base(
        atlas,
        technical,
        derived,
        tmp_path,
        monkeypatch,
        revision="1bc0a8acf6625fa71bf2b7d6287ed73c35181647",
    )
    before = immutable_interaction_base(atlas, technical, derived, tmp_path, monkeypatch)
    assert len(before.files) == 523 and len(after.files) == len(before.files) + 1
    assert set(after.files) - set(before.files) == {INTERACTION_MAP}
    assert not set(before.files) - set(after.files)
    paths = preferred_paths(atlas)
    changed = {p for p in before.files if before.files[p] != after.files[p]}
    assert changed == {
        HOME,
        PRODUCT / "Guides/Using the Research Map.md",
        MANIFESTS[views.OWNER],
        *(paths[i] for i in INTERACTION_ORIENTATION_IDS),
    }
    assert before.routes == after.routes
    assert before.owners == {p: after.owners[p] for p in before.owners}
    assert all(before.files[p] == after.files[p] for p in before.files.keys() - changed)
    assert before.files[ARCHITECTURE_TREE] == after.files[ARCHITECTURE_TREE]
    assert before.files[EXECUTION_FLOW] == after.files[EXECUTION_FLOW]
    assert after.owners[INTERACTION_MAP] == views.OWNER
    assert (
        immutable_interaction_base(
            atlas,
            technical,
            derived,
            tmp_path,
            monkeypatch,
            revision="1bc0a8acf6625fa71bf2b7d6287ed73c35181647",
        ).files
        == after.files
    )
    # Enumerated paths are retained in pytest output and PR evidence.
    print(
        "Interaction Map generated delta:", *sorted(map(str, changed | {INTERACTION_MAP})), sep="\n"
    )


ISSUE168_BASE = "1bc0a8acf6625fa71bf2b7d6287ed73c35181647"


def canvas_relation_rows(data):
    canvas = json.loads(data)
    nodes = {n["id"]: n for n in canvas["nodes"]}

    def identity(node):
        return re.search(r"`([A-Z]+-[^`]+)`", node["text"])[1]

    return [
        (e["label"], identity(nodes[e["fromNode"]]), identity(nodes[e["toNode"]]))
        for e in canvas["edges"]
    ]


def assert_canvas_geometry(data):
    canvas = json.loads(data)
    nodes = {n["id"]: n for n in canvas["nodes"]}
    assert len(nodes) == len(canvas["nodes"])
    assert len({e["id"] for e in canvas["edges"]}) == len(canvas["edges"])
    for edge in canvas["edges"]:
        assert edge["fromNode"] in nodes and edge["toNode"] in nodes
    cards = [n for n in nodes.values() if n["type"] == "text"]
    for index, left in enumerate(cards):
        for right in cards[index + 1 :]:
            assert (
                left["x"] + left["width"] <= right["x"]
                or right["x"] + right["width"] <= left["x"]
                or left["y"] + left["height"] <= right["y"]
                or right["y"] + right["height"] <= left["y"]
            ), (left, right)
    for card in cards:
        if card["id"] == "legend":
            continue
        groups = [n for n in nodes.values() if n["type"] == "group"]
        if groups:
            assert any(
                g["x"] <= card["x"]
                and g["y"] <= card["y"]
                and g["x"] + g["width"] >= card["x"] + card["width"]
                and g["y"] + g["height"] >= card["y"] + card["height"]
                for g in groups
            )
    return canvas, nodes


def test_three_primary_canvases_navigation_and_vertical_detail(atlas, baseline):
    tree = baseline[0]
    for page, path in (
        (ARCHITECTURE_TREE, ARCHITECTURE_CANVAS),
        (EXECUTION_FLOW, EXECUTION_CANVAS),
        (INTERACTION_MAP, INTERACTION_CANVAS),
    ):
        assert path in tree.files and tree.owners[path] == views.OWNER
        for navigation in (HOME, PRODUCT / "Guides/Using the Research Map.md"):
            assert f"[[{path}|Open Canvas]]" in tree.files[navigation].decode()
        assert f"![[{path}]]" in tree.files[page].decode()
        assert f"[[{path}|Open " in tree.files[page].decode()
        canvas, _ = assert_canvas_geometry(tree.files[path])
        legend = next(n for n in canvas["nodes"] if n["id"] == "legend")["text"]
        for destination in (ARCHITECTURE_CANVAS, EXECUTION_CANVAS, INTERACTION_CANVAS):
            assert f"[[{destination}|" in legend
    canvas, nodes = assert_canvas_geometry(tree.files[ARCHITECTURE_CANVAS])
    for edge in canvas["edges"]:
        assert edge["fromSide"] == "bottom" and edge["toSide"] == "top"
        assert nodes[edge["fromNode"]]["y"] < nodes[edge["toNode"]]["y"]
    for node in nodes.values():
        if node["id"] != "legend" and node["type"] == "text":
            identity = re.search(r"`((?:SYS|CMP)-[^`]+)`", node["text"])[1]
            actual = atlas.entities[identity]
            assert actual.description in node["text"]
            assert actual.technical.verification_status in node["text"]
            assert actual.technical.architecture_authority in node["text"]
    assert max(n["y"] for n in nodes.values()) > max(n["x"] for n in nodes.values())


def test_interaction_canvas_exact_rows_context_and_order_invariance(atlas, baseline):
    from fh_agent.research_atlas.diagram_canvas import interaction_canvas

    paths = preferred_paths(atlas)
    data = baseline[0].files[INTERACTION_CANVAS]
    canvas, nodes = assert_canvas_geometry(data)
    assert sorted(canvas_relation_rows(data)) == interaction_rows(
        baseline[0].files[INTERACTION_MAP].decode()
    )
    assert len(canvas["edges"]) == 47
    assert all(e["toEnd"] == "arrow" for e in canvas["edges"])
    identities = {
        re.search(r"`([A-Z]+-[^`]+)`", n["text"])[1]
        for n in nodes.values()
        if n["type"] == "text" and n["id"] != "legend"
    }
    assert identities == {
        i
        for i, n in atlas.entities.items()
        if n.type in {"Component", "Interface", "Contract", "DataArtifact", "Environment"}
    }
    for n in nodes.values():
        if n["type"] != "text" or n["id"] == "legend":
            continue
        identity = re.search(r"`([A-Z]+-[^`]+)`", n["text"])[1]
        assert atlas.entities[identity].description in n["text"]
        assert f"[[{paths[identity].with_suffix('')}|" in n["text"]
    reordered = replace(
        atlas,
        entities=dict(reversed(list(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    assert (
        interaction_canvas(
            reordered,
            preferred_paths(reordered),
            INTERACTION_RELATIONS,
            final_projection.INTERACTION_GROUPS,
        )
        == data
    )
    additions = (
        Relationship(relation="consumes", source="CMP-BODY", target="CON-CORTEX-CONTEXT"),
        Relationship(relation="updates", source="CMP-MEMORY", target="DAT-OBSERVATION"),
    )
    changed = replace(atlas, relationships=atlas.relationships + additions)
    actual = canvas_relation_rows(
        interaction_canvas(
            changed, paths, INTERACTION_RELATIONS, final_projection.INTERACTION_GROUPS
        )
    )
    assert sorted(actual) == sorted(
        canvas_relation_rows(data) + [(e.relation, e.source, e.target) for e in additions]
    )
    assert ("controls", "CMP-CORTEX", "CMP-BODY") not in actual
    empty = replace(
        atlas,
        relationships=tuple(
            e for e in atlas.relationships if e.relation not in INTERACTION_RELATIONS
        ),
    )
    rendered = interaction_canvas(
        empty, paths, INTERACTION_RELATIONS, final_projection.INTERACTION_GROUPS
    )
    assert_canvas_geometry(rendered)
    assert canvas_relation_rows(rendered) == []


def test_execution_canvas_source_gates_boundaries_and_independence(atlas, baseline):
    from fh_agent.research_atlas.diagram_canvas import execution_canvas

    data = baseline[0].files[EXECUTION_CANVAS]
    canvas, nodes = assert_canvas_geometry(data)
    assert len([n for n in nodes.values() if n["type"] == "group"]) == 6
    assert len([n for n in nodes.values() if n["type"] == "text" and n["id"] != "legend"]) == 40
    pairs = {(e["fromNode"], e["toNode"]) for e in canvas["edges"]}
    assert ("cortex", "execute") not in pairs and ("cortex", "proposal") not in pairs
    for gate in ("validate", "capability", "ground", "safety", "focus", "capacity", "logging"):
        assert (gate, "reject") in pairs
    for required in (
        ("close", "observation"),
        ("evaluate", "body"),
        ("reflex", "proposal"),
        ("episode", "restart"),
        ("restart", "capture"),
        ("episode", "terminal"),
        ("continuity", "reject"),
        ("terminal", "next"),
        ("certify", "next"),
    ):
        assert required in pairs
    candidate_paths = [
        e for e in canvas["edges"] if e["fromNode"] == "certify" and e["toNode"] == "next"
    ]
    assert len({(e["fromSide"], e["toSide"]) for e in candidate_paths}) == 2
    assert {s for s, t in pairs if t == "train"} == {"replay"}
    assert "after termination + separate authorization" in next(
        e["label"] for e in canvas["edges"] if e["toNode"] == "train"
    )
    assert "same frozen identities/Body weights" in nodes["restart"]["text"]
    assert "No primitive keys/timings" in nodes["cortex"]["text"]
    for node in nodes.values():
        if node["type"] == "text" and node["id"] != "legend":
            assert (
                "[Source](https://github.com/Planton361/autonomous-game-agent/blob/main/docs/"
                in node["text"]
            )
    reordered = replace(
        atlas,
        entities=dict(reversed(list(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    assert execution_canvas(reordered, preferred_paths(reordered)) == data
    context = Relationship(relation="controls", source="CMP-CORTEX", target="CMP-BODY")
    altered = replace(atlas, relationships=atlas.relationships + (context,))
    assert execution_canvas(altered, preferred_paths(altered)) == data


def test_canvas_upgrade_independent_exact_main_delta(atlas, baseline, tmp_path, monkeypatch):
    after, technical, derived = baseline
    before = immutable_interaction_base(
        atlas, technical, derived, tmp_path, monkeypatch, revision=ISSUE168_BASE
    )
    assert len(before.files) == 524 and len(after.files) == 526
    added = {EXECUTION_CANVAS, INTERACTION_CANVAS}
    assert set(after.files) - set(before.files) == added
    assert not set(before.files) - set(after.files)
    changed = {p for p in before.files if before.files[p] != after.files[p]}
    assert changed == {
        HOME,
        PRODUCT / "Guides/Using the Research Map.md",
        MANIFESTS[views.OWNER],
        ARCHITECTURE_TREE,
        ARCHITECTURE_CANVAS,
        EXECUTION_FLOW,
        INTERACTION_MAP,
    }
    assert before.routes == after.routes
    assert before.owners == {p: after.owners[p] for p in before.owners}
    assert package(atlas, technical, derived).files == after.files
    # Added detail is measured against the immutable prior visual content, not current code.
    prior = json.loads(before.files[ARCHITECTURE_CANVAS])
    current = json.loads(after.files[ARCHITECTURE_CANVAS])
    assert sum(len(n["text"]) for n in current["nodes"] if n["type"] == "text") > 2 * sum(
        len(n["text"]) for n in prior["nodes"]
    )
    old_stages = re.findall(r"^    \w+[\[{]", before.files[EXECUTION_FLOW].decode(), re.M)
    new_stages = [
        n
        for n in json.loads(after.files[EXECUTION_CANVAS])["nodes"]
        if n["type"] == "text" and n["id"] != "legend"
    ]
    assert len(new_stages) >= 2 * len(old_stages)
    print("Canvas-first exact-main delta:", *sorted(map(str, changed | added)), sep="\n")


def test_execution_canvas_optional_restart_entry_and_repair_delta(
    atlas, baseline, tmp_path, monkeypatch
):
    tree, technical, derived = baseline
    canvas, nodes = assert_canvas_geometry(tree.files[EXECUTION_CANVAS])
    incoming = [edge for edge in canvas["edges"] if edge["toNode"] == "continuity"]
    assert len(incoming) == 1
    entry = incoming[0]
    assert entry["fromNode"] == "process_restart"
    assert entry["label"] == "optional restart"
    trigger = nodes[entry["fromNode"]]
    assert "Optional application/process restart event" in trigger["text"]
    assert "Out-of-band during an active Mission Run" in trigger["text"]
    assert "independent of contract completion or Life Episode death" in trigger["text"]
    assert "no new Mission Run" in trigger["text"]
    assert "ALIGN-2026-09-19-v1.0/README.md#restart-and-terminal-semantics" in trigger["text"]
    assert not any(edge["toNode"] == trigger["id"] for edge in canvas["edges"])
    assert trigger["y"] == nodes["continuity"]["y"]
    assert entry["fromSide"] == "right" and entry["toSide"] == "left"
    assert {
        (edge["toNode"], edge["label"])
        for edge in canvas["edges"]
        if edge["fromNode"] == "continuity"
    } == {
        ("capture", "identities / provenance preserved"),
        ("reject", "continuity lost: stop / quarantine"),
    }
    assert "Preserve manifest, frozen identities and provenance" in nodes["continuity"]["text"]
    assert "stop/quarantine; never relabel as clean new run" in nodes["continuity"]["text"]

    # The reviewed generator imports its Canvas module: pin BOTH modules so the
    # current repair cannot become its own same-input before-state oracle.
    revision = "347e1b85ee64f9abcf8652ac72eff49ed47351fb"
    with monkeypatch.context() as patch:
        file = tmp_path / "reviewed_diagram_canvas.py"
        file.write_text(
            harness_fixtures.git(
                ROOT, "show", f"{revision}:src/fh_agent/research_atlas/diagram_canvas.py"
            )
        )
        name = "fh_agent.research_atlas.diagram_canvas"
        spec = spec_from_file_location(name, file)
        module = module_from_spec(spec)
        patch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        before = immutable_interaction_base(
            atlas, technical, derived, tmp_path, patch, revision=revision
        )
    assert before.files.keys() == tree.files.keys()
    assert len(tree.files) == 526
    assert before.routes == tree.routes and before.owners == tree.owners
    assert {path for path in tree.files if tree.files[path] != before.files[path]} == {
        EXECUTION_CANVAS,
        MANIFESTS[views.OWNER],
    }
    assert not any(
        edge["toNode"] == "continuity"
        for edge in json.loads(before.files[EXECUTION_CANVAS])["edges"]
    )
    assert len(canvas["edges"]) == len(json.loads(before.files[EXECUTION_CANVAS])["edges"]) + 1
    assert package(atlas, technical, derived).files == tree.files


# AP1 presentation content runs in the existing required migration acceptance module.
@pytest.fixture(scope="module")
def ap1_source():
    atlas = load_registry(ROOT / "docs/research-atlas")
    catalog = parse_explanations((ROOT / SOURCE).read_bytes(), atlas)
    return atlas, catalog


@pytest.fixture(scope="module")
def ap1_products(ap1_source):
    atlas, catalog = ap1_source
    technical, derived, _, _ = intermediate(atlas)
    before = final_projection.package(atlas, technical, derived)
    after = final_projection.package(atlas, technical, derived, explanations=catalog)
    return before, after, technical, derived


def test_28_substantive_explanations_preferred_paths_and_exact_delta(ap1_source, ap1_products):
    atlas, catalog = ap1_source
    before, after, _, _ = ap1_products
    paths = preferred_paths(atlas)
    components = {i for i, node in atlas.entities.items() if node.type == "Component"}
    assert len(components) == len(catalog.components) == 28
    assert len(set(paths[i] for i in components)) == 28
    for identity in components:
        item = catalog.components[identity]
        body = after.files[paths[identity]].decode()
        technical = body.split("## Technical\n", 1)[1].split("## Research\n", 1)[0]
        assert item.mechanism in technical and len(item.mechanism.split()) >= 30
        assert item.normative in technical and item.limitations in technical
        assert item.responsibility in technical and item.why in technical
        assert item.inputs in technical and item.outputs in technical
        assert item.example in technical and item.research_relevance in body
        assert "No separate mechanism" not in technical
        assert "No separate limitation" not in technical
        assert "**Normative target:**" in technical
        assert "**Current mechanism and boundary:**" in technical
        assert "Registry implementation:" in technical
        assert "pending CONTROL content review" in body
        for key in item.sources:
            locator = catalog.sources[key]
            assert f"/{catalog.source_revision}/{locator.path}#L{locator.line}" in body
        if atlas.entities[identity].technical.implementation_status == "target-only":
            assert "Target-only:" in item.implementation and "missing" in item.implementation
    guides = {PRODUCT / "Guides" / (name + ".md") for name in GUIDES}
    assert after.files.keys() - before.files.keys() == guides | {
        PRODUCT / "Diagrams" / (name + ".svg")
        for name in (
            "System Overview",
            "Architecture Tree",
            "Interaction Map",
            "Experience to Knowledge",
            "Scientific Experiment",
        )
    }
    assert not before.files.keys() - after.files.keys()
    changed = {p for p in before.files if before.files[p] != after.files[p]}
    assert changed == {paths[i] for i in components} | {
        HOME,
        PRODUCT / "Guides/Using the Research Map.md",
        ARCHITECTURE_TREE,
        ARCHITECTURE_CANVAS,
        EXECUTION_FLOW,
        EXECUTION_CANVAS,
        INTERACTION_MAP,
        INTERACTION_CANVAS,
        final_projection.MANIFESTS["research-wiki-derived"],
        MANIFESTS[public.OWNER],
    }
    assert len(before.files) == 526 and len(after.files) == 534
    assert len(before.files.keys() - changed) == 488
    assert before.routes == after.routes  # No alternate identity or migration route.
    assert all(before.owners[p] == after.owners[p] for p in before.files)


def test_part_of_and_immediate_interactions_are_exact(ap1_source, ap1_products):
    atlas, _ = ap1_source
    _, tree, _, _ = ap1_products
    paths = preferred_paths(atlas)
    edges = [e for e in atlas.relationships if e.relation == "part_of"]
    assert len(edges) == 28
    assert {e.source for e in edges} == {
        i for i, node in atlas.entities.items() if node.type == "Component"
    }
    for edge in edges:
        assert (
            paths[edge.target].with_suffix("").as_posix() in tree.files[paths[edge.source]].decode()
        )
        expected_parent = (
            PRODUCT / "Components"
            if atlas.entities[edge.target].type == "System"
            else paths[edge.target].with_suffix("")
        )
        assert paths[edge.source].parent == expected_parent
    for identity, node in atlas.entities.items():
        if node.type != "Component":
            continue
        body = tree.files[paths[identity]].decode()
        table = body.split("### Immediate typed interactions", 1)[1].split(
            "### Current implementation state", 1
        )[0]
        rows = [line for line in table.splitlines() if line.startswith("| `")]
        declared = sorted(
            (
                e
                for e in atlas.relationships
                if e.relation in final_projection.INTERACTION_RELATIONS
                and identity in {e.source, e.target}
            ),
            key=lambda e: (e.relation, e.source, e.target),
        )
        assert len(rows) == len(declared)
        for row, edge in zip(rows, declared, strict=True):
            assert row.startswith(f"| `{edge.relation}` |")
            left = str(paths[edge.source].with_suffix(""))
            right = str(paths[edge.target].with_suffix(""))
            assert row.index(left) <= row.rindex(right)
        for child in (e.source for e in edges if e.target == identity):
            assert (
                str(paths[child].with_suffix(""))
                in body.split("### True subcomponents", 1)[1].split(
                    "### Immediate typed interactions", 1
                )[0]
            )


def test_guides_complete_cycle_continuity_and_research_boundaries(ap1_source, ap1_products):
    atlas, catalog = ap1_source
    _, tree, _, _ = ap1_products
    bodies = {name: tree.files[PRODUCT / "Guides" / (name + ".md")].decode() for name in GUIDES}
    overview = bodies[GUIDES[0]]
    # Independent approved-design oracle: changing AREAS alone must not bless a new taxonomy.
    groups = {
        "Observation & Perception": {
            "CMP-SCREEN-CAPTURE",
            "CMP-VISIBLE-STATE-BRIDGE",
            "CMP-NO-SPOILER-FIREWALL",
            "CMP-PERCEPTION",
            "CMP-OBSERVATION-BUILDER",
            "CMP-PERCEPTION-UI-STATE",
            "CMP-TEMPORAL-STATE",
        },
        "Evidence, Memory & Retrieval": {
            "CMP-EVIDENCE-LEDGER",
            "CMP-MEMORY",
            "CMP-MEM-EPISODIC",
            "CMP-MEM-FACTS",
            "CMP-MEM-HYPOTHESES",
            "CMP-MEM-TOPOLOGY",
            "CMP-MEM-STRATEGY",
            "CMP-SKILL-COMPETENCE",
            "CMP-MEM-RETRIEVAL",
        },
        "Strategic Reasoning": {"CMP-CORTEX"},
        "Executive Control": {
            "CMP-MANAGER",
            "CMP-MANAGER-GROUNDING",
            "CMP-MANAGER-SCHED-COMP",
        },
        "Action & Safety": {
            "CMP-BODY",
            "CMP-BOUNDED-REFLEX",
            "CMP-SAFETY-FILTER",
            "CMP-INPUT-EXECUTOR",
        },
        "Independent Verification": {"CMP-INDEPENDENT-VERIFIER"},
        "Between-Mission-Run Learning": {
            "CMP-REPLAY-BUFFER",
            "CMP-SKILL-TRAINER",
            "CMP-BODY-CERTIFICATION",
        },
    }
    assert AREAS == tuple(groups)
    assert tuple(re.findall(r"^## (.+)$", overview, re.M)) == ("Diagram", *groups, "Sources")
    identities = [identity for group in groups.values() for identity in group]
    assert len(identities) == len(set(identities)) == 28
    assert set(identities) == set(catalog.components)
    paths = preferred_paths(atlas)
    for area, group in groups.items():
        assert {i for i, item in catalog.components.items() if item.area == area} == group
        section = overview.split(f"## {area}\n", 1)[1].split("\n## ", 1)[0]
        # Each Component occurs in its own didactic section, regardless of technical ancestry.
        assert {i for i in identities if f"[[{paths[i].with_suffix('')}|" in section} == group
        for identity in group:
            assert (
                f"[[Research Map/Guides/System Overview#{area}|{area}]]"
                in tree.files[paths[identity]].decode()
            )
    assert "not a mandatory Cortex call per primitive" in overview
    assert (
        "new Observation → Independent Verifier → VerifierResult → Manager transition" in overview
    )
    assert "abstaining when evidence is insufficient" in overview
    assert "Progress can continue a still-valid contract" in overview
    assert "Replanning calls Cortex" in overview
    assert "No parameter training or controller replacement occurs inside a Mission Run" in overview
    assert "is a System sibling of Memory" in overview
    assert "admission ownership is design-open" in overview
    assert "valid contract" in overview and "durable before/after logging" in overview
    experience = bodies[GUIDES[1]]
    assert "Consolidation/Admission ownership is explicitly design-open" in experience
    assert "Memory inheritance is not automatic" in experience
    assert "never between Life Episodes in one Mission Run" in experience
    experiment = bodies[GUIDES[2]]
    assert "Mission Run > Life Episode > Grounded Skill Contract > primitive action" in experiment
    assert "silent budget expansion is not" in experiment
    for mode in (
        "screen-only",
        "bridge-assisted",
        "debug",
        "networked-api-exploratory",
        "contaminated",
    ):
        assert mode in experiment
    assert "Research A" in experiment and "Research B" in experiment
    assert "no experiment was executed" in experiment
    assert "never pool" in experiment and "Missing mandatory provenance" in experiment


def test_guide_and_component_links_resolve_including_heading_targets(ap1_source, ap1_products):
    atlas, catalog = ap1_source
    _, tree, _, _ = ap1_products
    paths = preferred_paths(atlas)
    changed = (
        {HOME}
        | {paths[i] for i in catalog.components}
        | {PRODUCT / "Guides" / (name + ".md") for name in GUIDES}
    )
    for path in changed:
        body = tree.files[path].decode()
        assert "[[id:" not in body and "[[guide:" not in body
        for value in re.findall(r"\[\[([^\]]+)\]\]", body):
            target = value.split("|", 1)[0].rstrip("\\")
            route, _, heading = target.partition("#")
            resolved = (
                path
                if not route
                else next((p for p in tree.files if str(p) in {route, route + ".md"}), None)
            )
            assert resolved is not None, (path, target)
            if heading:
                headings = re.findall(
                    r"^\s*(?:>\s*)*#{1,6} (.+)$", tree.files[resolved].decode(), re.M
                )
                assert heading in headings, (path, target)
    for identity in catalog.components:
        assert (
            str(paths[identity].with_suffix(""))
            in tree.files[PRODUCT / "Guides/System Overview.md"].decode()
        )


def test_deterministic_content_and_order_permutations(ap1_source, ap1_products):
    atlas, catalog = ap1_source
    _, tree, technical, derived = ap1_products
    again = final_projection.package(atlas, technical, derived, explanations=catalog)
    assert again == tree
    reordered = Atlas(
        dict(reversed(list(atlas.entities.items()))),
        tuple(reversed(atlas.relationships)),
        source_atlas_schema=atlas.source_atlas_schema,
    )
    other = final_projection.package(reordered, technical, derived, explanations=catalog)
    assert other.files == tree.files and other.routes == tree.routes


def test_source_revision_fingerprints_and_exact_symbols(ap1_source):
    _, catalog = ap1_source
    validate_dependencies(catalog, ROOT)
    # Recorded exact base really contains the inspected bytes, independent of current HEAD.
    for path, expected in {
        **{s.path: s.sha256 for s in catalog.sources.values()},
        **catalog.dependencies,
    }.items():
        payload = subprocess.run(
            ["git", "show", f"{catalog.source_revision}:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert hashlib.sha256(payload).hexdigest() == expected
    for locator in catalog.sources.values():
        if locator.kind == "test":
            assert locator.locator in {
                n.name
                for n in ast.walk(ast.parse((ROOT / locator.path).read_text()))
                if isinstance(n, ast.FunctionDef)
            }


@pytest.mark.parametrize(
    "mutation", ["coverage", "guides", "locator", "source", "type", "approval", "link"]
)
def test_invalid_source_fails_closed(ap1_source, mutation):
    atlas, _ = ap1_source
    data = yaml.safe_load((ROOT / SOURCE).read_text())
    if mutation == "coverage":
        data["components"].pop("CMP-CORTEX")
    elif mutation == "guides":
        data["guides"]["Extra"] = data["guides"]["System Overview"]
    elif mutation == "locator":
        data["sources"]["cortex"]["path"] = "../private-secret.md"
    elif mutation == "source":
        data["components"]["CMP-CORTEX"]["sources"].append("invented")
    elif mutation == "type":
        data["sources"]["cortex"]["kind"] = "scientific-result"
    elif mutation == "approval":
        data["review_status"] = "approved"
    else:
        data["guides"]["System Overview"]["intro"] += " [[id:CMP-INVENTED]]"
    with pytest.raises(ProjectionError):
        parse_explanations(yaml.safe_dump(data).encode(), atlas)


@pytest.mark.parametrize(
    "path",
    [
        "src/fh_agent/planner/cortex.py",
        "docs/canonical/02_ARCHITECTURE_CANONICAL.md",
        "docs/research-atlas/registry/relationships.yaml",
    ],
)
def test_supporting_change_requires_review_but_unrelated_change_does_not(
    ap1_source, tmp_path, path
):
    _, catalog = ap1_source
    for relative in {s.path for s in catalog.sources.values()} | catalog.dependencies.keys():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    (tmp_path / "unrelated.md").write_text("An unrelated future commit\n")
    validate_dependencies(catalog, tmp_path)
    changed = tmp_path / path
    changed.write_text(changed.read_text() + "\n# supporting source changed\n")
    with pytest.raises(ProjectionError, match="review required"):
        validate_dependencies(catalog, tmp_path)


def test_invalid_heading_or_symbol_locator_is_rejected(ap1_source):
    atlas, catalog = ap1_source
    data = catalog.model_dump(mode="json")
    data["sources"]["cortex"]["locator"] = "Cortex.invented"
    with pytest.raises(ProjectionError, match="Invalid explanation source locator"):
        validate_dependencies(parse_explanations(yaml.safe_dump(data).encode(), atlas), ROOT)
    data = catalog.model_dump(mode="json")
    data["sources"]["arch6"]["line"] = 999999
    with pytest.raises(ProjectionError, match="Invalid explanation source locator"):
        validate_dependencies(parse_explanations(yaml.safe_dump(data).encode(), atlas), ROOT)


# AP2 runs in the same required migration job; no new CI selection or timing gate.
@pytest.fixture(scope="module")
def ap2_reviewed_tree(ap1_source, ap1_products, tmp_path_factory):
    """Compare at identical inputs to the exact CONTROL-accepted AP1 code."""
    atlas, catalog = ap1_source
    _, _, technical, derived = ap1_products
    revision = "e133d5377f9e21d4bc26264cc3f452760dcf5747"
    source = subprocess.run(
        ["git", "show", f"{revision}:src/fh_agent/research_atlas/final_projection.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    file = tmp_path_factory.mktemp("ap1-accepted") / "projection.py"
    file.write_bytes(source)
    name = "fh_agent.research_atlas.ap1_accepted_projection"
    spec = spec_from_file_location(name, file)
    module = module_from_spec(spec)
    # dataclass introspection requires the module while loading trusted repository code.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        return module.package(atlas, technical, derived, explanations=catalog)
    finally:
        del sys.modules[name]


def test_ap2_exact_ap1_delta_ownership_and_preservation(
    ap1_source, ap1_products, ap2_reviewed_tree
):
    from fh_agent.research_atlas.diagram_svg import SVG_NAMES

    _, after, _, _ = ap1_products
    before = ap2_reviewed_tree
    svg = {PRODUCT / "Diagrams" / (title + ".svg") for title in SVG_NAMES}
    assert len(before.files) == 529 and len(after.files) == 534
    assert after.files.keys() - before.files.keys() == svg
    assert not before.files.keys() - after.files.keys()
    changed = {p for p in before.files if before.files[p] != after.files[p]}
    assert changed == {
        HOME,
        PRODUCT / "Guides/Using the Research Map.md",
        *(PRODUCT / "Guides" / (name + ".md") for name in GUIDES),
        ARCHITECTURE_TREE,
        EXECUTION_FLOW,
        INTERACTION_MAP,
        ARCHITECTURE_CANVAS,
        EXECUTION_CANVAS,
        INTERACTION_CANVAS,
        MANIFESTS[views.OWNER],
        MANIFESTS[public.OWNER],
    }
    assert len(changed) == 13
    assert len(before.files.keys() - changed) == 516
    assert before.routes == after.routes
    assert all(before.owners[p] == after.owners[p] for p in before.files)
    manifest = read_yaml(after.files[MANIFESTS[public.OWNER]].decode())
    for path in svg:
        assert after.owners[path] == public.OWNER
        row = next(r for r in manifest["owned_files"] if r["path"] == str(path))
        assert row["sha256"] == hashlib.sha256(after.files[path]).hexdigest()
        assert row["ownership"] == "strict-bytes"
    # All prose, preferred Component bytes, references and research audits stay intact.
    for path in (PRODUCT / "Guides" / (name + ".md") for name in GUIDES):
        body = after.files[path].decode()
        first, panel, rest = body.partition("\n## Diagram\n")
        assert panel
        resume = rest.index("\n## ")
        assert (first + rest[resume:]).encode() == before.files[path]
    ledger = "## Complete linked relation ledger"
    assert (
        after.files[INTERACTION_MAP].decode().split(ledger, 1)[1]
        == (before.files[INTERACTION_MAP].decode().split(ledger, 1)[1])
    )
    for path in (ARCHITECTURE_CANVAS, EXECUTION_CANVAS, INTERACTION_CANVAS):
        old = json.loads(before.files[path])
        new = json.loads(after.files[path])
        assert old["edges"] == new["edges"]
        assert "Secondary historical Canvas" in new["nodes"][0]["text"]
        assert "Open primary" in new["nodes"][0]["text"]
        new["nodes"][0]["text"] = new["nodes"][0]["text"].split("\n\n", 1)[1]
        new["nodes"][0]["height"] -= 64
        assert new == old


def test_ap2_drawn_tree_and_interaction_exact_sets(ap1_source, ap1_products):
    import xml.etree.ElementTree as ET

    from fh_agent.research_atlas.diagram_svg import architecture_dot, svg_assets
    from fh_agent.research_atlas.graphviz_tree import DOT_SHA256

    atlas, _ = ap1_source
    _, tree, _, _ = ap1_products
    ns = {"s": "http://www.w3.org/2000/svg"}
    drawing = ET.fromstring(tree.files[PRODUCT / "Diagrams/Architecture Tree.svg"])
    nodes = drawing.findall('.//s:g[@class="node"]', ns)
    assert {n.attrib["id"] for n in nodes} == {
        i for i, n in atlas.entities.items() if n.type in {"System", "Component"}
    }
    assert len(nodes) == 29
    edges = drawing.findall('.//s:g[@class="edge"]', ns)
    actual = {tuple(e.attrib["id"].split(":")[1:]) for e in edges}
    expected = {(e.source, e.target) for e in atlas.relationships if e.relation == "part_of"}
    assert actual == expected and len(edges) == 28
    assert hashlib.sha256(architecture_dot(atlas).encode()).hexdigest() == DOT_SHA256
    for node in nodes:
        texts = [t.text for t in node.findall("s:text", ns)]
        assert atlas.entities[node.attrib["id"]].technical.implementation_status in texts
    # Literal approved 14-triple oracle; a renderer constant alone cannot bless new edges.
    approved = {
        ("CMP-MEM-RETRIEVAL", "supplies", "IF-MEM-CORTEX"),
        ("CMP-CORTEX", "consumes", "IF-MEM-CORTEX"),
        ("CMP-CORTEX", "supplies", "CON-PLANNER-OUTPUT"),
        ("CMP-MANAGER", "consumes", "CON-PLANNER-OUTPUT"),
        ("CMP-CORTEX", "proposes_to", "CMP-MANAGER"),
        ("CMP-MANAGER", "supplies", "CON-SKILL-CONTRACT"),
        ("CMP-BODY", "executes", "CON-SKILL-CONTRACT"),
        ("CON-SKILL-CONTRACT", "constrains", "CMP-BODY"),
        ("CMP-BODY", "supplies", "CON-PRIMITIVE-ACTION"),
        ("CMP-INPUT-EXECUTOR", "consumes", "CON-PRIMITIVE-ACTION"),
        ("CMP-INDEPENDENT-VERIFIER", "supplies", "CON-VERIFIER-RESULT"),
        ("CMP-MANAGER", "consumes", "CON-VERIFIER-RESULT"),
        ("CMP-MEMORY", "consumes", "CON-VERIFIER-RESULT"),
        ("CMP-REPLAY-BUFFER", "consumes", "CON-VERIFIER-RESULT"),
    }
    drawing = ET.fromstring(tree.files[PRODUCT / "Diagrams/Interaction Map.svg"])
    arrows = drawing.findall('.//s:g[@data-semantics="registry"]', ns)
    actual = {
        (g.attrib["data-source"], g.attrib["data-relation"], g.attrib["data-target"])
        for g in arrows
    }
    assert actual == approved and len(arrows) == 14
    assert approved <= {(e.source, e.relation, e.target) for e in atlas.relationships}
    ledger = tree.files[INTERACTION_MAP].decode().split("## Complete linked relation ledger")[1]
    assert len(re.findall(r"^\| `", ledger, re.M)) == 47
    assert not any("part_of" == g.attrib["data-relation"] for g in arrows)
    changed = replace(
        atlas,
        relationships=tuple(
            e
            for e in atlas.relationships
            if (e.source, e.relation, e.target) != ("CMP-CORTEX", "proposes_to", "CMP-MANAGER")
        ),
    )
    with pytest.raises(ProjectionError, match="subset changed"):
        svg_assets(changed)
    changed = replace(
        atlas,
        relationships=tuple(
            e
            for e in atlas.relationships
            if e.source != "CMP-MEM-RETRIEVAL" or e.relation != "part_of"
        ),
    )
    with pytest.raises(ProjectionError, match="single-root"):
        svg_assets(changed)


def test_ap2_process_boundaries_and_primary_navigation(ap1_products):
    import xml.etree.ElementTree as ET

    _, tree, _, _ = ap1_products
    ns = {"s": "http://www.w3.org/2000/svg"}
    overview = ET.fromstring(tree.files[PRODUCT / "Diagrams/System Overview.svg"])
    edges = {
        (g.attrib["data-source"], g.attrib["data-target"])
        for g in overview.findall('.//s:g[@data-semantics="normative"]', ns)
    }
    assert {
        ("observation", "cortex"),
        ("cortex", "manager"),
        ("manager", "contract"),
        ("contract", "body"),
        ("body", "input"),
        ("input", "game"),
        ("game", "newobs"),
        ("newobs", "verifier"),
        ("verifier", "result"),
        ("result", "transition"),
        ("transition", "manager"),
        ("manager", "body"),
        ("transition", "cortex"),
        ("retrieval", "cortex"),
    } == edges
    assert not overview.findall('.//s:g[@data-semantics="registry"]', ns)
    text = tree.files[EXECUTION_FLOW].decode()
    panels = re.findall(r"```mermaid\n(.*?)```", text, re.S)
    assert len(panels) == 5
    assert "result --> evaluate" in panels[0]
    assert "same permissions and budget" in panels[1]
    assert "reject --> close" in panels[2] and "Body / Reflex stop signal" in panels[2]
    assert panels[3].index("closes / suspends prior contract") < panels[3].index(
        "New Cortex intention"
    )
    assert "same Mission Run / frozen Body" in panels[4]
    assert "already eligible Body; no retraining" in panels[4]
    assert "between Mission Runs; separately authorized" in panels[4]
    assert "candidate rejected; retain eligible prior Body" in panels[4]
    home = tree.files[HOME].decode()
    assert "## Understand the Agent" in home and "## Understand and review Research" in home
    assert "## Inspect sources and evidence" in home and "Direct Component entry" in home
    assert ".canvas" not in home
    for title in ("System Overview", "Experience to Knowledge", "Scientific Experiment"):
        body = tree.files[PRODUCT / "Guides" / (title + ".md")].decode()
        assert "Open full-size SVG" in body and "**Normative**" in body
        assert "**Implementation**" in body and "**Design-open**" in body
    assert "Open full-size SVG and zoom" in tree.files[ARCHITECTURE_TREE].decode()
    assert "Architecture Tree.svg" not in home
    for path in (ARCHITECTURE_TREE, EXECUTION_FLOW, INTERACTION_MAP):
        body = tree.files[path].decode()
        assert "Secondary historical Canvas" in body
        if path != EXECUTION_FLOW:
            assert "![[Research Map/Diagrams/" in body
        assert "![[Research Map/Diagrams/" + path.stem + ".canvas]]" not in body
        # Every ordinary Obsidian route and local heading resolves, including SVGs.
        for value in re.findall(r"\[\[([^\]]+)\]\]", body):
            route, _, heading = value.split("|", 1)[0].rstrip("\\").partition("#")
            target = (
                path
                if not route
                else next((p for p in tree.files if str(p) in {route, route + ".md"}), None)
            )
            assert target is not None, (path, value)
            if heading:
                assert heading in re.findall(
                    r"^\s*(?:>\s*)*#{1,6} (.+)$", tree.files[target].decode(), re.M
                )


def test_ap2_svg_geometry_labels_and_scientific_nesting(ap1_products):
    import xml.etree.ElementTree as ET

    _, tree, _, _ = ap1_products
    ns = {"s": "http://www.w3.org/2000/svg"}

    def box(rect):
        a = rect.attrib
        return tuple(float(a[k]) for k in ("x", "y", "width", "height"))

    def overlaps(a, b):
        x, y, w, h = a
        u, v, m, n = b
        return x < u + m and u < x + w and y < v + n and v < y + h

    for name in (
        "System Overview",
        "Interaction Map",
        "Experience to Knowledge",
        "Scientific Experiment",
    ):
        root = ET.fromstring(tree.files[PRODUCT / "Diagrams" / (name + ".svg")])
        assert root.attrib["width"] == "960"
        cards = root.findall(".//s:g[@data-node]", ns)
        rects = [box(c.find("s:rect", ns)) for c in cards]
        for i, card in enumerate(cards):
            x, y, w, h = rects[i]
            assert 0 <= x < x + w <= 960 and 0 <= y < y + h <= float(root.attrib["height"])
            for text in card.findall("s:text", ns):
                assert float(text.attrib["font-size"]) >= 17
                assert x < float(text.attrib["x"]) < x + w
                assert y < float(text.attrib["y"]) <= y + h - 8
            for other in rects[i + 1 :]:
                # Explicit nesting is intentional in the scientific units figure.
                nested = (
                    x <= other[0]
                    and y <= other[1]
                    and x + w >= other[0] + other[2]
                    and y + h >= other[1] + other[3]
                )
                assert not overlaps(rects[i], other) or (name == "Scientific Experiment" and nested)
        labels = [box(r) for r in root.findall('.//s:rect[@data-label="true"]', ns)]
        for i, label in enumerate(labels):
            assert not any(overlaps(label, r) for r in rects), (name, label)
            assert not any(overlaps(label, r) for r in labels[i + 1 :]), (name, label)
    root = ET.fromstring(tree.files[PRODUCT / "Diagrams/Scientific Experiment.svg"])
    cards = {
        g.attrib["data-node"]: box(g.find("s:rect", ns))
        for g in root.findall(".//s:g[@data-node]", ns)
    }
    for n in (1, 2):
        x, y, w, h = cards[f"contract{n}"]
        u, v, m, k = cards[f"action{n}"]
        assert x < u and y < v and u + m < x + w and v + k <= y + h


@pytest.mark.parametrize(
    "name",
    [
        "System Overview",
        "Architecture Tree",
        "Interaction Map",
        "Experience to Knowledge",
        "Scientific Experiment",
    ],
)
def test_ap2_svg_edits_are_rejected_without_writes(ap1_products, tmp_path, name):
    _, tree, _, _ = ap1_products
    path = PRODUCT / "Diagrams" / (name + ".svg")
    target = tmp_path / str(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(tree.files[path])
    prior = {
        path: {
            "owner": public.OWNER,
            "ownership": "strict-bytes",
            "sha256": hashlib.sha256(tree.files[path]).hexdigest(),
        }
    }
    assert migration.prove_ownership(ROOT, tmp_path, tmp_path, prior) == prior
    target.write_bytes(target.read_bytes() + b"<!-- user change -->")
    before = filesystem_state(tmp_path)
    with pytest.raises(ProjectionError, match="Owned content was edited"):
        migration.prove_ownership(ROOT, tmp_path, tmp_path, prior)
    assert filesystem_state(tmp_path) == before
