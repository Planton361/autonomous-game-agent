"""Fast fail-closed orchestration contracts for the private Workspace harness."""

import html
import json
import posixpath
import re
from dataclasses import replace
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import pytest
from test_research_wiki_schema import props as wiki_props

from fh_agent.research_atlas import private_projection as technical_projection
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.private_projection import ProjectionError
from fh_agent.research_atlas.private_reference_index import (
    build_index,
    component_navigation_rows,
    make_snapshot,
)
from fh_agent.research_atlas.schema import Relationship
from fh_agent.research_atlas.validator import Atlas, load_registry
from fh_agent.research_atlas.wiki_schema import WIKI_PREFIXES

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "a" * 40
DETAIL_ENDPOINTS = (
    "IF-MEM-CORTEX",
    "CON-CORTEX-CONTEXT",
    "DAT-RETRIEVAL-SNAPSHOT",
    "MEAS-RETRIEVAL-DELIVERY-001",
    "CON-VERIFIER-RESULT",
    "DAT-OBSERVATION",
    "DAT-VISIBLE-OUTCOME",
)


@pytest.fixture
def atlas():
    return load_registry(ROOT / "docs/research-atlas")


def component_research_fixture_records():
    """Synthetic RA-2 rows for every accepted N-C prefix and audit boundary."""
    memory = "CMP-MEM-RETRIEVAL"
    return [
        wiki_props("paper", wiki_id="WPAPER-K0", research_direct_subject_refs=[memory]),
        wiki_props("paper", wiki_id="WPAPER-K1-INVERSE"),
        wiki_props(
            "reading_note",
            wiki_id="READ-K1-INVERSE",
            paper_refs=["WPAPER-K1-INVERSE"],
            research_measurement_relevance_refs=[memory],
        ),
        wiki_props("paper", wiki_id="WPAPER-K1-FORWARD", reading_note_refs=["READ-K1-FORWARD"]),
        wiki_props(
            "reading_note",
            wiki_id="READ-K1-FORWARD",
            paper_refs=["WPAPER-K1-FORWARD"],
            research_project_transfer_refs=[memory],
        ),
        wiki_props("paper", wiki_id="WPAPER-K2"),
        wiki_props(
            "finding",
            wiki_id="WFIND-K2",
            source_refs=["WPAPER-K2"],
            research_adjacent_context_refs=[memory],
        ),
        wiki_props("paper", wiki_id="WPAPER-K3"),
        wiki_props(
            "reading_note",
            wiki_id="READ-K3",
            paper_refs=["WPAPER-K3"],
            finding_refs=["WFIND-K3"],
        ),
        wiki_props(
            "finding",
            wiki_id="WFIND-K3",
            research_method_or_baseline_refs=[memory],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-VERIFIER",
            research_direct_subject_refs=["CMP-INDEPENDENT-VERIFIER"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-OTHER-COMPONENT",
            research_direct_subject_refs=["CMP-CORTEX"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-DOMAIN-SIBLING",
            research_direct_subject_refs=["CMP-MEMORY"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-INTERFACE",
            research_direct_subject_refs=["IF-MEM-CORTEX"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-CONTRACT",
            research_direct_subject_refs=["CON-VERIFIER-RESULT"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-DATA",
            research_direct_subject_refs=["DAT-OBSERVATION"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-MEASUREMENT",
            research_direct_subject_refs=["MEAS-RETRIEVAL-DELIVERY-001"],
        ),
        wiki_props("reading_note", wiki_id="READ-WRONG-TYPE", paper_refs=[memory]),
        wiki_props("reading_note", wiki_id="READ-UNRESOLVED", paper_refs=["WPAPER-MISSING"]),
    ]


def component_research_tree(atlas, records=None, *, locators=None):
    records = component_research_fixture_records() if records is None else records
    snapshot = make_snapshot(records, atlas)
    private_records = views.landscape_private_records(records, atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    if locators is None:
        locators = {
            record["wiki_id"]: PurePosixPath("authored") / f"{record['wiki_id']}.md"
            for record in records
        }
    if "WFIND-K3" in locators:
        locators["WFIND-K3"] = PurePosixPath("authored/finding [fixture] #3.md")
    return (
        views.reference_views_tree(
            SOURCE_COMMIT,
            (ROOT / views.PUBLIC_SOURCE).read_bytes(),
            (ROOT / views.DIRECT_SOURCE).read_bytes(),
            reference,
            atlas,
            locators,
            snapshot,
            False,
            private_records,
        ),
        snapshot,
        reference,
        locators,
    )


@pytest.fixture
def context(tmp_path: Path) -> workspace.WorkspaceContext:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    vault.mkdir()
    return workspace.WorkspaceContext(repo, vault, "a" * 40)


def test_apply_orders_one_exact_head_and_both_final_checks(context, monkeypatch, tmp_path):
    restore_point = tmp_path / "restore"
    calls: list[tuple[str, str, bool]] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(
        workspace,
        "create_restore_point",
        lambda *_: restore_point,
    )

    def technical(repo_root, vault_root, source_ref, *, check=False):
        calls.append(("technical", source_ref, check))

    def views(repo_root, vault_root, source_ref, *, check=False):
        calls.append(("views", source_ref, check))

    monkeypatch.setattr(workspace, "technical_project", technical)
    monkeypatch.setattr(workspace, "views_project", views)
    result = workspace.apply(context.repo_root, context.vault_root)

    assert result.restore_point == restore_point
    assert calls == [
        ("technical", context.source_commit, False),
        ("views", context.source_commit, False),
        ("technical", context.source_commit, True),
        ("views", context.source_commit, True),
    ]


def test_apply_stops_at_first_failed_projector_and_names_restore_point(
    context, monkeypatch, tmp_path
):
    restore_point = tmp_path / "restore"
    calls: list[str] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(workspace, "create_restore_point", lambda *_: restore_point)

    def technical(*args, **kwargs):
        calls.append("technical")
        raise ProjectionError("synthetic failure")

    monkeypatch.setattr(workspace, "technical_project", technical)
    monkeypatch.setattr(workspace, "views_project", lambda *args, **kwargs: calls.append("views"))
    with pytest.raises(workspace.WorkspaceError, match="technical projection failed.*restore"):
        workspace.apply(context.repo_root, context.vault_root)
    assert calls == ["technical"]


def test_final_check_failure_is_nonzero_apply_failure(context, monkeypatch, tmp_path):
    restore_point = tmp_path / "restore"
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(workspace, "create_restore_point", lambda *_: restore_point)

    def technical(*args, check=False, **kwargs):
        calls.append(("technical", check))
        if check:
            raise ProjectionError("synthetic check failure")

    monkeypatch.setattr(workspace, "technical_project", technical)
    monkeypatch.setattr(
        workspace,
        "views_project",
        lambda *args, check=False, **kwargs: calls.append(("views", check)),
    )
    with pytest.raises(
        workspace.WorkspaceError, match="technical projection check failed.*restore"
    ):
        workspace.apply(context.repo_root, context.vault_root)
    assert calls == [("technical", False), ("views", False), ("technical", True)]


def test_check_is_restore_free_and_runs_only_both_checks(context, monkeypatch):
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(
        workspace,
        "create_restore_point",
        lambda *_: pytest.fail("check must not create a restore point"),
    )
    monkeypatch.setattr(
        workspace,
        "technical_project",
        lambda *args, check=False, **kwargs: calls.append(("technical", check)),
    )
    monkeypatch.setattr(
        workspace,
        "views_project",
        lambda *args, check=False, **kwargs: calls.append(("views", check)),
    )
    result = workspace.check(context.repo_root, context.vault_root)
    assert result.restore_point is None
    assert calls == [("technical", True), ("views", True)]


def test_w05_detail_endpoint_set_and_empty_verifier_lanes(atlas):
    models = views.technical_detail_models(atlas)
    assert tuple(model.endpoint_id for model in models) == DETAIL_ENDPOINTS
    assert views.TECHNICAL_DETAIL_ENDPOINT_TYPES == {
        "IF-MEM-CORTEX": "Interface",
        "CON-CORTEX-CONTEXT": "Contract",
        "DAT-RETRIEVAL-SNAPSHOT": "DataArtifact",
        "MEAS-RETRIEVAL-DELIVERY-001": "MeasurementPoint",
        "CON-VERIFIER-RESULT": "Contract",
        "DAT-OBSERVATION": "DataArtifact",
        "DAT-VISIBLE-OUTCOME": "DataArtifact",
    }
    assert all(
        atlas.entities[model.endpoint_id].type
        == views.TECHNICAL_DETAIL_ENDPOINT_TYPES[model.endpoint_id]
        for model in models
    )
    verifier = views._component_hub_model(atlas, "CMP-INDEPENDENT-VERIFIER")
    assert verifier.interface_ids == ()
    assert verifier.measurement_point_ids == ()
    verifier_interface_lane = "\n".join(views._render_component_hub_interface_lane(atlas, verifier))
    assert "No corresponding `IF-*` Registry record exists" in verifier_interface_lane
    assert not any("MeasurementPoint" in identity for identity in DETAIL_ENDPOINTS)


def test_w05_canvas_markdown_links_and_relation_sets_match(atlas):
    models = views.technical_detail_models(atlas)
    technical_tree = technical_projection.projection_tree(
        atlas,
        SOURCE_COMMIT,
        {name: "b" * 64 for name in technical_projection.REGISTRY_FILES},
    )
    for model in models:
        markdown = views.render_technical_detail_workbench(SOURCE_COMMIT, atlas, model).decode()
        canvas = json.loads(views.render_technical_detail_canvas(atlas, model))
        assert set(canvas) == {
            "generated_by",
            "canvas_view_schema_version",
            "nodes",
            "edges",
        }
        assert canvas["generated_by"] == views.OWNER
        assert canvas["canvas_view_schema_version"] == "1.0"
        assert all(
            isinstance(node[key], int)
            for node in canvas["nodes"]
            for key in ("x", "y", "width", "height")
        )
        assert all(
            edge["toEnd"] == "arrow" and edge["fromEnd"] == "none" for edge in canvas["edges"]
        )

        identity_by_node_id = {
            views._canvas_node_id(identity): identity
            for edge in model.direct_relationships
            for identity in (edge.source, edge.target)
        } | {views._canvas_node_id(model.endpoint_id): model.endpoint_id}
        canvas_relations = {
            (
                identity_by_node_id[edge["fromNode"]],
                edge["label"],
                identity_by_node_id[edge["toNode"]],
            )
            for edge in canvas["edges"]
        }
        expected_relations = {
            (edge.source, edge.relation, edge.target) for edge in model.direct_relationships
        }
        assert canvas_relations == expected_relations

        relation_section = markdown.split("## Exact direct Registry relations\n\n", 1)[1].split(
            "\n## Scoped Canvas map\n", 1
        )[0]
        markdown_relations = {
            line for line in relation_section.splitlines() if line.startswith("- [[")
        }
        expected_markdown = {
            f"- {views._technical_link(atlas, edge.source)} — `{edge.relation}` → "
            f"{views._technical_link(atlas, edge.target)}"
            for edge in model.direct_relationships
        }
        assert markdown_relations == expected_markdown

        canvas_links = [
            target
            for node in canvas["nodes"]
            for target in re.findall(r"\[\[([^\]|]+)\|[^\]]+\]\]", node["text"])
        ]
        assert len(canvas_links) == len(canvas["nodes"])
        for target in canvas_links:
            assert not target.startswith("/") and "Users/" not in target
            relative = PurePosixPath(target).relative_to(technical_projection.OWNED_ROOT)
            assert relative.with_suffix(".md") in technical_tree

        assert "| Architecture authority |" in markdown
        assert "| Implementation status |" in markdown
        assert "| Technical verification |" in markdown
        if model.endpoint_id == "MEAS-RETRIEVAL-DELIVERY-001":
            assert "measurement target relation only" in markdown
            assert "Measurement validity: **not established here**" in markdown
            assert "Scientific evidence or effect: **not established here**" in markdown
            assert "Accepted scientific claim: **none created or implied**" in markdown
        if model.endpoint_id == "DAT-RETRIEVAL-SNAPSHOT":
            assert len(canvas["nodes"]) == 4
        if model.endpoint_id == "DAT-OBSERVATION":
            assert len(canvas["nodes"]) >= 8


def test_w05_rendering_manifest_and_hub_links_are_order_invariant(atlas):
    snapshot = make_snapshot([], atlas)
    shuffled = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )

    def render_registry(source):
        private_snapshot = make_snapshot([], source)
        reference = build_index(source, private_snapshot, SOURCE_COMMIT)
        return views.reference_views_tree(
            SOURCE_COMMIT,
            (ROOT / views.PUBLIC_SOURCE).read_bytes(),
            (ROOT / views.DIRECT_SOURCE).read_bytes(),
            reference,
            source,
            {},
            private_snapshot,
            False,
        )

    current_tree = render_registry(atlas)
    shuffled_tree = render_registry(shuffled)
    assert current_tree == shuffled_tree
    technical_tree = technical_projection.projection_tree(
        atlas,
        SOURCE_COMMIT,
        {name: "b" * 64 for name in technical_projection.REGISTRY_FILES},
    )
    assert technical_projection.ANATOMY in technical_tree
    assert technical_projection.DOMAIN_SLICE in technical_tree
    manifest = views.read_yaml(current_tree[views.MANIFEST].decode())
    assert manifest["view_schema_version"] == "2.5"
    assert {
        PurePosixPath(item["path"])
        for item in manifest["owned_files"]
        if PurePosixPath(item["path"]).parent == views.TECHNICAL_DETAIL_ROOT
    } == views.TECHNICAL_DETAIL_PAYLOADS

    for hub_id in views.COMPONENT_HUB_PATHS:
        hub = views._component_hub_model(atlas, hub_id)
        research_model = views._component_research_model(
            atlas, build_index(atlas, snapshot, SOURCE_COMMIT), hub_id
        )
        technical = views.render_component_hub_view(
            SOURCE_COMMIT, atlas, hub, "technical", snapshot, False
        ).decode()
        overview = views.render_component_hub_view(
            SOURCE_COMMIT, atlas, hub, "overview", snapshot, False
        ).decode()
        research = views.render_component_hub_view(
            SOURCE_COMMIT,
            atlas,
            hub,
            "research",
            snapshot,
            False,
            research_model,
            {},
        ).decode()
        expected_ids = (
            *hub.interface_ids,
            *hub.contract_ids,
            *hub.data_artifact_ids,
            *hub.measurement_point_ids,
        )
        for identity in expected_ids:
            workbench, canvas = views.technical_detail_paths(identity)
            assert str(views.OWNED_ROOT / workbench.with_suffix("")) in technical
            assert str(views.OWNED_ROOT / canvas) in technical
            assert workbench in current_tree and canvas in current_tree
            detail_markdown = current_tree[workbench].decode()
            links = re.findall(r"\[\[([^\]|]+)\|[^\]]+\]\]", detail_markdown)
            assert links
            for target in links:
                path = PurePosixPath(target)
                if path.is_relative_to(views.OWNED_ROOT):
                    relative = path.relative_to(views.OWNED_ROOT)
                    if relative.suffix != ".canvas":
                        relative = relative.with_suffix(".md")
                    assert relative in current_tree
                else:
                    assert path.is_relative_to(technical_projection.OWNED_ROOT)
                    relative = path.relative_to(technical_projection.OWNED_ROOT)
                    if relative.suffix == ".excalidraw":
                        relative = PurePosixPath(f"{relative}.md")
                    else:
                        relative = relative.with_suffix(".md")
                    assert relative in technical_tree
        detail_prefix = str(views.OWNED_ROOT / views.TECHNICAL_DETAIL_ROOT)
        assert detail_prefix not in overview
        assert detail_prefix not in research


def test_w06_component_research_renders_exact_registry_and_all_nc_rows(atlas):
    tree, snapshot, reference, locators = component_research_tree(atlas)
    memory_model = views._component_research_model(atlas, reference, "CMP-MEM-RETRIEVAL")
    verifier_model = views._component_research_model(atlas, reference, "CMP-INDEPENDENT-VERIFIER")
    memory_rows = component_navigation_rows(reference, "CMP-MEM-RETRIEVAL")
    assert memory_model.research_question_relationships == (
        next(
            edge
            for edge in atlas.relationships
            if edge.source == "CMP-MEM-RETRIEVAL"
            and edge.relation == "related_to_research_question"
        ),
    )
    assert verifier_model.research_question_relationships == ()
    assert {row.target_identifier for row in memory_rows} == {"CMP-MEM-RETRIEVAL"}
    assert len(memory_rows) == 6
    assert {row.recipe for row in memory_rows} == {
        "N-C/K0/E9:forward",
        "N-C/K1/E1:inverse/E9:forward",
        "N-C/K1/E2:forward/E9:forward",
        "N-C/K2/E3:inverse/E9:forward",
        "N-C/K3/E1:inverse/E4:forward/E9:forward",
    }
    assert sum(row.recipe.startswith("N-C/K1/E1:") for row in memory_rows) == 2
    assert all(row.recipe.startswith("N-C/") and row.path_eligible for row in memory_rows)
    assert {row.recipe.split("/")[1] for row in memory_rows} == {"K0", "K1", "K2", "K3"}
    assert {row.path_kind for row in memory_rows} == {"direct", "derived"}
    assert any(row.prerequisite_refs for row in memory_rows)
    assert {row.originating_role for row in memory_rows} == {
        "research_direct_subject_refs",
        "research_method_or_baseline_refs",
        "research_measurement_relevance_refs",
        "research_project_transfer_refs",
        "research_adjacent_context_refs",
    }

    memory = tree[views.MEMORY_HUB_RESEARCH].decode()
    verifier = tree[views.VERIFIER_HUB_RESEARCH].decode()
    question = atlas.entities["RQ-PROGRAM-AB-001"]
    assert f"{question.name} · `RQ-PROGRAM-AB-001`" in memory
    assert "`related_to_research_question` →" in memory
    assert (
        "No current Registry Research Question relation is declared for this Component." in verifier
    )
    assert "RQ-PROGRAM-AB-001" not in verifier

    for row in memory_rows:
        assert memory.count(row.row_id) == 1
        assert f"`{row.path_kind}`" in memory
        assert f"`{row.recipe}`" in memory
    k3 = next(row for row in memory_rows if "/K3/" in row.recipe)
    assert k3.source_wiki_id == "WFIND-K3"
    assert k3.source_doc_type == "finding"
    assert k3.navigation_start is not None
    assert k3.navigation_start.identifier == "WPAPER-K3"
    k3_number = memory_rows.index(k3) + 1
    k3_block = memory.split(f"### Path {k3_number} · `{k3.path_kind}`\n", 1)[1].split(
        "\n### Path ", 1
    )[0]
    assert "Declaring record: [WFIND-K3](" in k3_block
    assert "Paper/source identity: [WPAPER-K3](" in k3_block
    assert "Declaring record: [WPAPER-K3]" not in k3_block
    assert "Originating property: `research_method_or_baseline_refs`" in memory
    assert "Originating role: `research_method_or_baseline_refs`" in memory
    assert "Target Component: [CMP-MEM-RETRIEVAL](" in k3_block
    assert "resolved-public`; type `Component`; record version `none`; profile `none`" in k3_block
    assert "Index row: `navigation-path` · view `component` · eligible `true`" in k3_block
    assert "Final reference type check: `not-constrained`" in k3_block
    assert "Index diagnostics: none" in k3_block
    assert "Declared target:" in memory and "Prerequisite references:" in memory
    assert "`E9`" in memory and "direction `forward`" in memory
    assert "revision `v1`" in k3_block
    assert "finding%20%5Bfixture%5D%20%233.md" in k3_block
    locator_link = re.search(r"\[WFIND-K3\]\(([^)]+)\)", k3_block)
    assert locator_link is not None
    research_parent = (views.OWNED_ROOT / views.MEMORY_HUB_RESEARCH).parent.as_posix()
    resolved_locator = PurePosixPath(
        posixpath.normpath(posixpath.join(research_parent, unquote(locator_link[1])))
    )
    assert resolved_locator == locators["WFIND-K3"]
    k1_forward = next(row for row in memory_rows if "E2:forward" in row.recipe)
    k1_forward_block = memory.split(
        f"### Path {memory_rows.index(k1_forward) + 1} · `{k1_forward.path_kind}`\n", 1
    )[1].split("\n### Path ", 1)[0]
    assert "Prerequisite references:\n  1. Edge `E1`" in k1_forward_block
    assert "property `paper_refs`" in k1_forward_block
    assert "method used" not in memory
    assert "best baseline" not in memory
    assert "implementation studied" not in memory

    for unrelated_identity in (
        "WPAPER-VERIFIER",
        "WPAPER-OTHER-COMPONENT",
        "WPAPER-DOMAIN-SIBLING",
        "WPAPER-INTERFACE",
        "WPAPER-CONTRACT",
        "WPAPER-DATA",
        "WPAPER-MEASUREMENT",
        "READ-WRONG-TYPE",
        "READ-UNRESOLVED",
        "CMP-CORTEX",
        "CMP-MEMORY",
        "IF-MEM-CORTEX",
    ):
        assert unrelated_identity not in memory
    assert "Open Declared Literature Navigation" in memory
    assert "Direct Reference Audit" in memory
    navigation = html.unescape(tree[views.NAVIGATION].decode())
    assert "READ-WRONG-TYPE" in navigation and "wrong-target-type" in navigation
    assert "READ-UNRESOLVED" in navigation and "unresolved-reference" in navigation
    assert all("/Users/" not in data.decode() for data in tree.values())
    assert all(not path.is_absolute() for path in locators.values())


def test_w06_component_research_does_not_roll_up_parent_or_domain_sibling(atlas):
    parent_edge = Relationship(
        relation="part_of",
        source="CMP-MEM-RETRIEVAL",
        target="CMP-CORTEX",
    )
    with_parent = Atlas(atlas.entities, (*atlas.relationships, parent_edge))
    hub = views._component_hub_model(with_parent, "CMP-MEM-RETRIEVAL")
    memory_domains = views._relationship_targets(atlas, "CMP-MEM-RETRIEVAL", "presented_in_domain")
    sibling_domains = views._relationship_targets(atlas, "CMP-MEMORY", "presented_in_domain")
    assert "CMP-CORTEX" in hub.technical_parent_ids
    assert memory_domains and set(memory_domains) & set(sibling_domains)

    tree, snapshot, reference, locators = component_research_tree(with_parent)
    model = views._component_research_model(with_parent, reference, "CMP-MEM-RETRIEVAL")
    memory = views.render_component_hub_view(
        SOURCE_COMMIT,
        with_parent,
        hub,
        "research",
        snapshot,
        False,
        model,
        locators,
    ).decode()
    assert {row.target_identifier for row in model.literature_paths} == {"CMP-MEM-RETRIEVAL"}
    assert "WPAPER-OTHER-COMPONENT" not in memory
    assert "WPAPER-DOMAIN-SIBLING" not in memory
    assert "CMP-CORTEX" not in memory and "CMP-MEMORY" not in memory
    assert tree[views.MEMORY_HUB_RESEARCH].decode() == memory


def test_w06_component_research_empty_state_is_neutral_and_keeps_exact_rq(atlas):
    snapshot = make_snapshot([], atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    hub = views._component_hub_model(atlas, "CMP-MEM-RETRIEVAL")
    research_model = views._component_research_model(atlas, reference, hub.subject_id)
    memory = views.render_component_hub_view(
        SOURCE_COMMIT,
        atlas,
        hub,
        "research",
        snapshot,
        False,
        research_model,
        {},
    ).decode()
    assert "No matching declared Component literature paths are present in this snapshot." in memory
    assert "No current Registry Research Question relation is declared" not in memory
    assert "No literature is present" not in memory
    assert "research gap" not in memory
    assert "No authored private research records are present in this snapshot." in memory
    assert "Direct Reference Audit" in memory


def w07_private_fixtures():
    records = []
    for kind in views.LANDSCAPE_PRIVATE_TYPES:
        identity = f"{WIKI_PREFIXES[kind]}-W07-001"
        changes = {
            "wiki_id": identity,
            "title": f"Synthetic W07 {kind.replace('_', ' ')}",
            "record_version": 7,
            "document_maturity": "in_review",
            "research_direct_subject_refs": ["CMP-CORTEX"],
        }
        if kind == "research_question":
            changes.update(question_stage="literature_mapped", decision_state="none")
        elif kind == "finding":
            changes.update(review_state="checked")
        elif kind == "search_record":
            changes["document_maturity"] = "draft"
        records.append(wiki_props(kind, **changes))
    records.extend(
        wiki_props(
            "search_record",
            wiki_id=f"SEARCH-W07-MANY-{index:02d}",
            title=f"Synthetic W07 search record {index:02d}",
            target_refs=["WRQ-FIXTURE"],
            research_direct_subject_refs=["CMP-CORTEX"],
        )
        for index in range(24)
    )
    return records


def test_w07_global_landscape_is_complete_markdown_and_order_invariant(atlas):
    records = w07_private_fixtures()
    snapshot = make_snapshot(records, atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    locators = {
        record["wiki_id"]: PurePosixPath("authored") / f"synthetic note [{record['wiki_id']}] #1.md"
        for record in records
    }
    private_records = views.landscape_private_records(records, atlas)
    page = views.render_research_landscape(
        SOURCE_COMMIT, atlas, snapshot, locators, private_records
    )
    text = page.decode()

    assert text.startswith("---\ngenerated_by: research-wiki-derived\n")
    assert text.startswith("---") and "# Research Landscape" in text
    assert "derived navigation projection" in text
    assert "Research Knowledge Home" in text and "Agent Anatomy" in text
    assert "Technical Hierarchy" in text
    assert "Declared Literature Navigation" in text
    assert "Direct Reference Audit" in text and "Direct Views Index" in text
    assert "No new" not in text
    for node in atlas.entities.values():
        if node.type in views.LANDSCAPE_PUBLIC_TYPES:
            assert node.name in text and node.id in text and node.type in text
    exact_relation_count = sum(
        edge.relation == "related_to_research_question" for edge in atlas.relationships
    )
    assert text.count("`related_to_research_question`") == exact_relation_count + 1
    assert "`part_of`" not in text
    assert "domain-member" not in text.lower()

    for kind in views.LANDSCAPE_PRIVATE_TYPES:
        assert f"### {views.LANDSCAPE_PRIVATE_LABELS[kind]}" in text
        assert f"Synthetic W07 {kind.replace('_', ' ')}" in text
    public_section = text.split("## Private authored RA-2 inventory", 1)[0]
    assert "Synthetic W07 research question" not in public_section
    for index in range(24):
        assert f"SEARCH-W07-MANY-{index:02d}" in text
        assert f"Synthetic W07 search record {index:02d}" in text
    assert "Record class: `research_question`" in text
    assert "Record version: `7`" in text
    assert "Document maturity: `in_review`" in text
    assert "`question_stage`: `literature_mapped`" in text
    assert "`decision_state`: `none`" in text
    assert "`review_state`: `checked`" in text
    assert "`research_direct_subject_refs`: `CMP-CORTEX`" in text
    assert "synthetic%20note%20%5BSEARCH-W07-MANY-00%5D%20%231.md" in text
    assert "No current records are present for this record class in this snapshot." in text
    assert "No current declared relationships are present" not in text
    assert "evidence score" not in text.lower()
    assert "confidence score" not in text.lower()
    assert "priority score" not in text.lower()
    assert "top-k" not in text.lower()
    assert ".base" not in text.lower()

    shuffled = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    shuffled_snapshot = make_snapshot(reversed(records), shuffled)
    shuffled_reference = build_index(shuffled, shuffled_snapshot, SOURCE_COMMIT)
    shuffled_locators = dict(reversed(tuple(locators.items())))
    shuffled_records = views.landscape_private_records(list(reversed(records)), shuffled)
    shuffled_tree = views.reference_views_tree(
        SOURCE_COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        shuffled_reference,
        shuffled,
        shuffled_locators,
        shuffled_snapshot,
        False,
        shuffled_records,
    )
    current_tree = views.reference_views_tree(
        SOURCE_COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        locators,
        snapshot,
        False,
        private_records,
    )
    assert current_tree == shuffled_tree
    assert views.RESEARCH_LANDSCAPE in current_tree
    assert views.RESEARCH_LANDSCAPE in views.K3_PAYLOADS
    assert b"Research Landscape" in current_tree[views.K3_HOME]
    assert b"Research Landscape" in current_tree[views.INDEX]
    home_text = current_tree[views.K3_HOME].decode()
    assert home_text.index("Open the Global Research Landscape") < home_text.index("Component Hubs")
    for subject_id, paths in views.COMPONENT_HUB_PATHS.items():
        assert subject_id in text
        assert str(views.OWNED_ROOT / paths.research.with_suffix("")) in text
    manifest = views.read_yaml(current_tree[views.MANIFEST].decode())
    owned = {item["path"] for item in manifest["owned_files"]}
    assert str(views.RESEARCH_LANDSCAPE) in owned
    assert str(SOURCE_COMMIT).encode() in page
    assert b"/Users/" not in page and b"C:\\" not in page


def test_w07_landscape_keeps_public_and_navigation_sections_useful_when_private_empty(atlas):
    snapshot = make_snapshot([], atlas)
    page = views.render_research_landscape(SOURCE_COMMIT, atlas, snapshot, {}, ()).decode()
    assert "Program A–B working question" in page
    assert "Experience to Action" in page
    assert "No current records are present for this record class in this snapshot." in page
    for record_type in ("Paper", "Finding", "ExperimentLead"):
        section = page.split(f"### {record_type}\n", 1)[1].split("\n### ", 1)[0]
        assert "No current records are present for this record class in this snapshot." in section
    assert "Declared Literature Navigation" in page
    assert "Direct Reference Audit" in page and "Direct Views Index" in page
    assert "Technical Hierarchy" in page and "Memory Retrieval" in page
    assert "research absence" in page and "does not state" in page
    no_question_relations = replace(
        atlas,
        relationships=tuple(
            edge for edge in atlas.relationships if edge.relation != "related_to_research_question"
        ),
    )
    no_relations_page = views.render_research_landscape(
        SOURCE_COMMIT, no_question_relations, snapshot, {}, ()
    ).decode()
    assert "No current declared relationships are present in this snapshot." in no_relations_page
    legacy_record = {
        "wiki_schema_version": "0.1",
        "wiki_id": "PROC-W07-LEGACY",
        "doc_type": "process",
        "privacy": "private",
        "export_policy": "deny",
        "atlas_refs": [],
    }
    legacy_snapshot = make_snapshot([legacy_record], atlas)
    legacy_page = views.render_research_landscape(
        SOURCE_COMMIT, atlas, legacy_snapshot, {}, ()
    ).decode()
    process_section = legacy_page.split("### Process\n", 1)[1].split("\n### ", 1)[0]
    assert "No current RA-2 records are present" in process_section


def test_w06_component_research_is_order_invariant_and_adds_no_owned_paths(atlas):
    records = component_research_fixture_records()
    current_tree, _, _, _ = component_research_tree(atlas, records)
    shuffled_atlas = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    reversed_records = tuple(reversed(records))
    shuffled_locators = {
        record["wiki_id"]: PurePosixPath("authored") / f"{record['wiki_id']}.md"
        for record in reversed_records
    }
    shuffled_tree, _, _, _ = component_research_tree(
        shuffled_atlas, reversed_records, locators=shuffled_locators
    )
    assert current_tree == shuffled_tree
    manifest = views.read_yaml(current_tree[views.MANIFEST].decode())
    assert manifest["view_schema_version"] == "2.5"
    owned = {PurePosixPath(item["path"]) for item in manifest["owned_files"]}
    assert views.K3_PAYLOADS <= owned
    assert not any("Component Research" in str(path) for path in owned)
    assert not any(path.suffix == ".base" and "Component" in path.name for path in owned)


def test_w05_manifest_ownership_is_exact_and_version_bounded(tmp_path: Path):
    root = tmp_path / "derived"
    manifest_path = root / views.MANIFEST
    manifest_path.parent.mkdir(parents=True)

    def write_manifest(version, paths):
        manifest = {
            "view_schema_version": version,
            "generated_by": views.OWNER,
            "source_repository": "Planton361/autonomous-game-agent",
            "source_commit": SOURCE_COMMIT,
            "source_atlas_schema": "0.2",
            "source_sha256": {
                "public_atlas_base": "c" * 64,
                "research_wiki_direct_base": "d" * 64,
            },
            "reference_index_schema_version": "1.0",
            "private_input_fingerprint": "e" * 64,
            "owned_files": [
                {
                    "path": str(path),
                    "sha256": "f" * 64,
                    "ownership": views.STRICT_OWNERSHIP,
                }
                for path in paths
            ],
        }
        manifest_path.write_bytes(views.yaml_text(manifest).encode())

    write_manifest("2.4", sorted(views.TECHNICAL_DETAIL_PAYLOADS))
    prior = views.validate_prior(root)
    assert set(prior) == views.TECHNICAL_DETAIL_PAYLOADS

    write_manifest("2.3", [views.technical_detail_paths("IF-MEM-CORTEX")[0]])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    unknown = views.TECHNICAL_DETAIL_ROOT / "UNOWNED.md"
    write_manifest("2.4", [unknown])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    write_manifest("2.4", [views.RESEARCH_LANDSCAPE])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    write_manifest("2.5", [views.RESEARCH_LANDSCAPE])
    assert set(views.validate_prior(root)) == {views.RESEARCH_LANDSCAPE}
    unknown_index = PurePosixPath("indexes/Unowned Landscape.md")
    write_manifest("2.5", [unknown_index])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)


@pytest.mark.parametrize(
    ("version", "paths"),
    [
        ("1.0", (views.INDEX,)),
        ("2.0", (views.REFERENCE_INDEX,)),
        ("2.1", (views.K3_HOME,)),
        ("2.2", (views.HIERARCHY, views.HIERARCHY_DIR / "SYS-AGA.md")),
        ("2.3", (views.MEMORY_HUB_TECHNICAL,)),
        ("2.4", (views.technical_detail_paths("IF-MEM-CORTEX")[1],)),
        ("2.5", (views.RESEARCH_LANDSCAPE,)),
    ],
)
def test_w05_manifest_prior_versions_keep_bounded_paths(tmp_path: Path, version, paths):
    root = tmp_path / "derived"
    manifest_path = root / views.MANIFEST
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "view_schema_version": version,
        "generated_by": views.OWNER,
        "source_repository": "Planton361/autonomous-game-agent",
        "source_commit": SOURCE_COMMIT,
        "source_atlas_schema": "0.2",
        "source_sha256": {
            "public_atlas_base": "a" * 64,
            "research_wiki_direct_base": "b" * 64,
        },
        "owned_files": [
            {
                "path": str(path),
                "sha256": "c" * 64,
                **(
                    {"ownership": views.STRICT_OWNERSHIP}
                    if version in {"2.1", "2.2", "2.3", "2.4", "2.5"}
                    else {}
                ),
            }
            for path in paths
        ],
    }
    if version != "1.0":
        manifest.update(
            reference_index_schema_version="1.0",
            private_input_fingerprint="d" * 64,
        )
    manifest_path.write_bytes(views.yaml_text(manifest).encode())
    assert set(views.validate_prior(root)) == set(paths)
