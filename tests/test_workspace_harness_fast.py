"""Fast fail-closed orchestration contracts for the private Workspace harness."""

import json
import re
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

from fh_agent.research_atlas import private_projection as technical_projection
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.private_projection import ProjectionError
from fh_agent.research_atlas.private_reference_index import build_index, make_snapshot
from fh_agent.research_atlas.validator import load_registry

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
    assert manifest["view_schema_version"] == "2.4"
    assert {
        PurePosixPath(item["path"])
        for item in manifest["owned_files"]
        if PurePosixPath(item["path"]).parent == views.TECHNICAL_DETAIL_ROOT
    } == views.TECHNICAL_DETAIL_PAYLOADS

    for hub_id in views.COMPONENT_HUB_PATHS:
        hub = views._component_hub_model(atlas, hub_id)
        technical = views.render_component_hub_view(
            SOURCE_COMMIT, atlas, hub, "technical", snapshot, False
        ).decode()
        overview = views.render_component_hub_view(
            SOURCE_COMMIT, atlas, hub, "overview", snapshot, False
        ).decode()
        research = views.render_component_hub_view(
            SOURCE_COMMIT, atlas, hub, "research", snapshot, False
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


@pytest.mark.parametrize(
    ("version", "paths"),
    [
        ("1.0", (views.INDEX,)),
        ("2.0", (views.REFERENCE_INDEX,)),
        ("2.1", (views.K3_HOME,)),
        ("2.2", (views.HIERARCHY, views.HIERARCHY_DIR / "SYS-AGA.md")),
        ("2.3", (views.MEMORY_HUB_TECHNICAL,)),
        ("2.4", (views.technical_detail_paths("IF-MEM-CORTEX")[1],)),
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
                    if version in {"2.1", "2.2", "2.3", "2.4"}
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
