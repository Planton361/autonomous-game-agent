"""Synthetic-only tests for the operator-facing private Workspace harness."""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest
from test_research_wiki_projection import (
    ROOT,
    commit,
    filesystem_state,
    git,
    snapshot,
    write_note,
)
from typer.testing import CliRunner

from fh_agent.cli import app
from fh_agent.research_atlas import private_projection as technical
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import product_migration as migration
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.final_projection import MANIFESTS
from fh_agent.research_atlas.preferred_paths import HOME, INTERNAL, PRODUCT, preferred_paths


def _copy_source(repo: Path, relative: Path) -> None:
    destination = repo / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / relative
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


@pytest.fixture
def setup(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = tmp_path / "public-checkout"
    vault = tmp_path / "private vault with spaces"
    repo.mkdir()
    vault.mkdir()
    for relative in (
        Path("docs/research-atlas/registry"),
        Path(views.CATALOG_PATH),
        Path("docs/research-atlas/Generated/Atlas Views.base"),
        Path("docs/research-atlas/Wiki Views"),
        Path("docs/research-atlas/Process Seeds"),
    ):
        _copy_source(repo, relative)
    source = repo / "src/fh_agent/research_atlas/source.py"
    source.parent.mkdir(parents=True)
    source.write_text("# synthetic committed source\n", encoding="utf-8")
    # AP1 production builds read the public presentation source and its frozen dependencies.
    from fh_agent.research_atlas.architecture_explanations import SOURCE, parse_explanations
    from fh_agent.research_atlas.validator import load_registry

    _copy_source(repo, Path(SOURCE))
    catalog = parse_explanations(
        (ROOT / SOURCE).read_bytes(), load_registry(ROOT / "docs/research-atlas")
    )
    for relative in sorted(
        {s.path for s in catalog.sources.values()} | catalog.dependencies.keys()
    ):
        _copy_source(repo, Path(relative))
    asset = repo / technical.HERO_SOURCE
    asset.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / technical.HERO_SOURCE, asset)
    git(repo, "init", "--quiet")
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    source_commit = commit(repo)
    (vault / ".research-wiki-private").write_text(
        'research_wiki_private_version: "1.0"\nproject: Planton361/autonomous-game-agent\n',
        encoding="utf-8",
    )
    write_note(vault / "authored/process.md")
    (vault / "authored/keep.bin").write_bytes(bytes(range(32)))
    return repo, vault, source_commit


def _generated_snapshot(vault: Path) -> dict[str, str]:
    result = {}
    for relative in workspace.RESTORED_ROOTS:
        root = vault / relative
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if path.is_file():
                result[str(path.relative_to(vault))] = technical.digest(path.read_bytes())
    return result


def _authored_snapshot(vault: Path) -> dict[str, str]:
    return {
        path: digest
        for path, digest in snapshot(vault).items()
        if path != str(HOME)
        and not any(PurePosixPath(path).is_relative_to(root) for root in migration.ROOTS)
    }


def test_apply_orders_restore_writes_and_checks_at_exact_head(setup, monkeypatch):
    repo, vault, source_commit = setup
    technical.project(repo, vault, source_commit)
    views.project(repo, vault, source_commit)
    before_generated = _generated_snapshot(vault)
    before_authored = _authored_snapshot(vault)
    calls = []
    write = migration.atomic_write

    def record(root, path, data):
        calls.append(path)
        return write(root, path, data)

    monkeypatch.setattr(migration, "atomic_write", record)
    result = workspace.apply(repo, vault)
    assert result.source_commit == source_commit
    assert set(calls[-2:]) == set(MANIFESTS.values())
    assert result.restore_point is not None
    assert _generated_snapshot(result.restore_point) == before_generated
    metadata = json.loads((result.restore_point / "restore-point.json").read_text())
    assert metadata["generated_roots_present"] == [str(technical.OWNED_ROOT), str(views.OWNED_ROOT)]
    assert _authored_snapshot(vault) == before_authored
    assert not list((vault / technical.OWNED_ROOT).rglob("*.*"))
    assert not list((vault / views.OWNED_ROOT).rglob("*.*"))


def test_apply_uses_private_vault_environment_fallback(setup, monkeypatch):
    repo, vault, source_commit = setup
    monkeypatch.setenv("PRIVATE_VAULT", str(vault))
    result = workspace.apply(repo)
    assert result.source_commit == source_commit
    assert result.restore_point is not None


def test_missing_marker_and_parent_directory_fail_before_backup_or_writes(setup):
    repo, vault, _ = setup
    before = filesystem_state(vault.parent)
    with pytest.raises(workspace.WorkspaceError, match="Private vault validation failed"):
        workspace.apply(repo, vault.parent)
    assert filesystem_state(vault.parent) == before


def test_restore_point_collision_never_overwrites_an_existing_point(setup):
    repo, vault, _ = setup
    context = workspace.resolve_context(repo, vault)
    now = datetime(2026, 9, 22, 1, 2, 3, tzinfo=UTC)
    first = workspace.create_restore_point(context, now=now)
    (first / "preserve").write_text("keep", encoding="utf-8")
    second = workspace.create_restore_point(context, now=now)
    assert second.name == first.name + "-01"
    assert (first / "preserve").read_text(encoding="utf-8") == "keep"


def test_restore_failure_stops_before_projector_writes(setup, monkeypatch):
    repo, vault, source_commit = setup
    technical.project(repo, vault, source_commit)
    before = filesystem_state(vault)

    def fail_copy(*args, **kwargs):
        raise OSError("synthetic backup failure")

    monkeypatch.setattr(workspace.shutil, "copytree", fail_copy)
    with pytest.raises(workspace.WorkspaceError, match="Restore-point copy failed"):
        workspace.apply(repo, vault)
    assert filesystem_state(vault) == before


def test_first_projector_failure_stops_pipeline_and_reports_restore_point(setup, monkeypatch):
    repo, vault, _ = setup
    before = filesystem_state(vault)

    def fail(*args):
        raise OSError("synthetic replacement failure")

    monkeypatch.setattr(migration, "atomic_write", fail)
    with pytest.raises(workspace.WorkspaceError, match="migration failed.*restore point"):
        workspace.apply(repo, vault)
    assert filesystem_state(vault) == before


def test_second_projector_and_final_check_fail_closed_with_restore_point(setup, monkeypatch):
    repo, vault, source_commit = setup
    technical.project(repo, vault, source_commit)
    views.project(repo, vault, source_commit)
    original = _generated_snapshot(vault)

    def fail_verify(*args):
        raise technical.ProjectionError("synthetic final-check failure")

    monkeypatch.setattr(migration, "verify", fail_verify)
    with pytest.raises(workspace.WorkspaceError, match="migration failed.*restore point"):
        workspace.apply(repo, vault)
    points = list((vault.parent / workspace.DEFAULT_RESTORE_DIRECTORY).iterdir())
    workspace.recover(repo, vault, points[0])
    assert _generated_snapshot(vault) == original


def test_unknown_owned_root_content_propagates_without_touching_authored_bytes(setup):
    repo, vault, _ = setup
    unknown = vault / technical.OWNED_ROOT / "unknown.md"
    unknown.parent.mkdir(parents=True)
    unknown.write_text("preserve", encoding="utf-8")
    before_authored = snapshot(vault, authored=True)
    with pytest.raises(workspace.WorkspaceError, match="Unknown/unowned"):
        workspace.apply(repo, vault)
    assert snapshot(vault, authored=True) == before_authored
    assert unknown.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("fault", ["unknown", "corrupt-manifest", "lost-owner"])
def test_apply_preflights_both_roots_before_any_workspace_mutation(setup, fault):
    repo, vault, _ = setup
    first = workspace.apply(repo, vault)
    assert first.restore_point is not None
    root = vault / INTERNAL
    if fault == "unknown":
        unknown = root / "unowned.md"
        unknown.write_text("synthetic unowned data", encoding="utf-8")
        expected_error = "Unknown/unowned"
    elif fault == "corrupt-manifest":
        (vault / MANIFESTS[views.OWNER]).write_text("not: [valid yaml", encoding="utf-8")
        expected_error = "manifest"
    else:
        page = vault / PRODUCT / "Views/Literature Inspection.md"
        page.write_text(
            page.read_text(encoding="utf-8").replace(views.OWNER, "synthetic-unowned"),
            encoding="utf-8",
        )
        expected_error = "owner marker"

    before_vault = filesystem_state(vault)
    before_restore_points = filesystem_state(first.restore_point.parent)
    before_authored = _authored_snapshot(vault)
    with pytest.raises(workspace.WorkspaceError, match=expected_error):
        workspace.apply(repo, vault)
    assert filesystem_state(vault) == before_vault
    assert filesystem_state(first.restore_point.parent) == before_restore_points
    assert _authored_snapshot(vault) == before_authored


@pytest.mark.parametrize(
    ("root", "relative"),
    [
        (PRODUCT, PurePosixPath("Diagrams/Agent Anatomy.excalidraw.md")),
        (PRODUCT, PurePosixPath("Views/Literature Inspection.md")),
    ],
)
def test_missing_owned_output_is_checkable_and_deterministically_restored(setup, root, relative):
    repo, vault, _ = setup
    first = workspace.apply(repo, vault)
    before_generated = _generated_snapshot(vault)
    before_authored = _authored_snapshot(vault)
    restore_root = first.restore_point.parent
    before_restore_points = filesystem_state(restore_root)
    (vault / root / relative).unlink()

    before_check = filesystem_state(vault)
    with pytest.raises(workspace.WorkspaceError, match="drift"):
        workspace.check(repo, vault)
    assert filesystem_state(vault) == before_check
    assert filesystem_state(restore_root) == before_restore_points

    workspace.apply(repo, vault)
    assert _generated_snapshot(vault) == before_generated
    assert _authored_snapshot(vault) == before_authored
    workspace.check(repo, vault)
    workspace.apply(repo, vault)
    assert _generated_snapshot(vault) == before_generated
    assert _authored_snapshot(vault) == before_authored


@pytest.mark.parametrize("stage", ["replacement", "retirement", "first-manifest"])
def test_interrupted_direct_generation_is_rejected_by_check_then_recovers(
    setup, monkeypatch, stage
):
    repo, vault, source_commit = setup
    technical.project(repo, vault, source_commit)
    views.project(repo, vault, source_commit)
    original = _generated_snapshot(vault)
    authored = _authored_snapshot(vault)
    write = migration.atomic_write
    with monkeypatch.context() as patch:

        def interrupt(root, path, data):
            write(root, path, data)
            if stage == "replacement" and path == INTERNAL / "Audit/Declared References.md":
                raise OSError("synthetic interrupted replacement")
            if stage == "first-manifest" and path == sorted(MANIFESTS.values())[0]:
                raise OSError("synthetic interrupted manifest")

        patch.setattr(migration, "atomic_write", interrupt)
        if stage == "retirement":
            unlink = Path.unlink

            def interrupt_unlink(path, *args, **kwargs):
                unlink(path, *args, **kwargs)
                if path.is_relative_to(vault / technical.OWNED_ROOT):
                    raise OSError("synthetic interrupted retirement")

            patch.setattr(Path, "unlink", interrupt_unlink)
        with pytest.raises(workspace.WorkspaceError, match="migration failed"):
            workspace.apply(repo, vault)
    state = filesystem_state(vault)
    with pytest.raises(workspace.WorkspaceError):
        workspace.check(repo, vault)
    assert filesystem_state(vault) == state
    point = next((vault.parent / workspace.DEFAULT_RESTORE_DIRECTORY).iterdir())
    workspace.recover(repo, vault, point)
    assert _generated_snapshot(vault) == original
    assert _authored_snapshot(vault) == authored
    workspace.apply(repo, vault)
    workspace.check(repo, vault)


def test_complete_workspace_paths_links_and_markdown_fallback_are_portable(setup):
    repo, vault, _ = setup
    # Reuse the accepted synthetic final-feature intake, including RQ and source inputs.
    from rq_reader_fixtures import fictional_catalog, fictional_records

    from fh_agent.research_atlas.validator import load_registry

    atlas = load_registry(repo / "docs/research-atlas")
    records = fictional_records(atlas)
    for record in records:
        write_note(
            vault / "authored" / (record.wiki_id + ".md"),
            record.model_dump(mode="json", exclude_unset=True),
        )
    (vault / ".research-source-catalog.json").write_text(fictional_catalog().model_dump_json())
    workspace.apply(repo, vault)
    before_generated = _generated_snapshot(vault)
    before_authored = _authored_snapshot(vault)
    generated_paths = tuple(PurePosixPath(path) for path in _generated_snapshot(vault))
    technical.validate_portable_paths(generated_paths)
    inventory = set(generated_paths)
    tree = migration.build(repo, vault, workspace.resolve_context(repo, vault).source_commit)
    assert set(tree.files) == inventory
    assert set(preferred_paths(atlas).values()) <= inventory
    assert HOME in inventory
    assert (vault / HOME).read_text().startswith("---\n")
    assert "Markdown fallback" in (vault / HOME).read_text()
    assert all(not p.is_relative_to(technical.OWNED_ROOT) for p in inventory)
    assert all(not p.is_relative_to(views.OWNED_ROOT) for p in inventory)

    windows_absolute = re.compile(rb"(?<![A-Za-z])[A-Za-z]:[\\/]")
    for relative in generated_paths:
        payload = (vault / relative).read_bytes()
        assert str(vault).encode() not in payload
        assert b"file://" not in payload.lower()
        assert windows_absolute.search(payload) is None
        if relative.suffix.lower() in {".md", ".canvas"}:
            text = payload.decode("utf-8")
            for target in re.findall(r"\[\[([^\]]+)\]\]", text):
                link = target.split(r"\|", 1)[0].split("|", 1)[0].split("#", 1)[0]
                # Same-note anchors are valid durable links on the current reader pages.
                if not link:
                    assert target.startswith("#")
                    continue
                assert not PurePosixPath(link).is_absolute()
                assert not PureWindowsPath(link).drive and "\\" not in link
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target:
                    continue
                link = target.split("#", 1)[0]
                assert not link.startswith(("/", "\\"))
                assert not PureWindowsPath(link).drive and "\\" not in link

    # Delete every payload, keeping valid finite ownership manifests. This includes
    # source-history indexes, RQ readers, Graph proxies/audits, Bases and rich assets.
    for relative in generated_paths:
        if relative not in {
            *MANIFESTS.values(),
            INTERNAL / "Indexes/source-resolution-index.yaml",
        }:
            (vault / relative).unlink()
    missing_state = filesystem_state(vault)
    with pytest.raises(workspace.WorkspaceError, match="drift"):
        workspace.check(repo, vault)
    assert filesystem_state(vault) == missing_state
    workspace.apply(repo, vault)
    assert _generated_snapshot(vault) == before_generated
    assert _authored_snapshot(vault) == before_authored
    workspace.check(repo, vault)
    workspace.apply(repo, vault)
    assert _generated_snapshot(vault) == before_generated
    assert _authored_snapshot(vault) == before_authored


def test_check_is_zero_write_and_never_creates_a_restore_point(setup):
    repo, vault, _ = setup
    applied = workspace.apply(repo, vault)
    assert applied.restore_point is not None
    restore_root = applied.restore_point.parent
    before_vault = filesystem_state(vault)
    before_restore_root = filesystem_state(restore_root)
    result = workspace.check(repo, vault)
    assert result.restore_point is None
    assert filesystem_state(vault) == before_vault
    assert filesystem_state(restore_root) == before_restore_root


def test_w05_manifest_migration_is_bounded_and_check_is_zero_write(setup):
    repo, vault, source_commit = setup
    technical.project(repo, vault, source_commit)
    views.project(repo, vault, source_commit)
    derived_root = vault / views.OWNED_ROOT
    manifest_path = derived_root / views.MANIFEST
    prior = views.read_yaml(manifest_path.read_text(encoding="utf-8"))
    detail_paths = set(views.TECHNICAL_DETAIL_PAYLOADS)
    # Reconstruct a genuine v2.3 fixture, excluding every subsequently owned surface.
    atlas = views.load_registry(repo / "docs/research-atlas")
    hub_overviews = {paths.overview for paths in views.COMPONENT_HUB_PATHS.values()}
    later_identity_paths = set(views.identity_page_paths(atlas).values()) - hub_overviews
    old_paths = (
        detail_paths
        | views.W07_PAYLOADS
        | views.W10_PAYLOADS
        | views.OBSERVE_SCOPE_PAYLOADS
        | later_identity_paths
        | views.SOURCE_PAYLOADS
        | {views.STEERING_BASE}
        | {
            Path(item["path"])
            for item in prior["owned_files"]
            if Path(item["path"]).parent == views.RQ_ROOT
            or Path(item["path"]).is_relative_to(views.GRAPH_ROOT)
            or Path(item["path"]).is_relative_to(views.GRAPH_SCOPES)
        }
    )
    for relative in old_paths:
        (derived_root / relative).unlink()
    prior["view_schema_version"] = "2.3"
    prior["reference_index_schema_version"] = "1.0"
    for field in (
        "presentation_fingerprint_version",
        "presentation_input_fingerprint",
        "source_resolution_fingerprint_version",
        "source_resolution_input_fingerprint",
    ):
        prior.pop(field)
    prior["owned_files"] = [
        item for item in prior["owned_files"] if Path(item["path"]) not in old_paths
    ]
    views.ManifestV23.model_validate(prior)
    manifest_path.write_bytes(views.yaml_text(prior).encode())

    authored_before = {
        path: digest
        for path, digest in snapshot(vault, authored=True).items()
        if not path.startswith(f"{views.OWNED_ROOT}/")
    }
    before_check = filesystem_state(vault)
    with pytest.raises(views.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, source_commit, check=True)
    assert filesystem_state(vault) == before_check

    views.project(repo, vault, source_commit)
    current = views.read_yaml(manifest_path.read_text(encoding="utf-8"))
    assert current["view_schema_version"] == "2.17"
    current_details = {
        Path(item["path"]) for item in current["owned_files"] if ".canvas" in item["path"]
    }
    current_details |= {
        Path(item["path"])
        for item in current["owned_files"]
        if item["path"].startswith(str(views.TECHNICAL_DETAIL_ROOT))
    }
    assert current_details == {Path(path) for path in detail_paths}
    authored_after = {
        path: digest
        for path, digest in snapshot(vault, authored=True).items()
        if not path.startswith(f"{views.OWNED_ROOT}/")
    }
    assert authored_after == authored_before

    unknown = derived_root / views.TECHNICAL_DETAIL_ROOT / "UNOWNED.md"
    unknown.parent.mkdir(parents=True, exist_ok=True)
    unknown.write_text("preserve this unowned file", encoding="utf-8")
    before_unknown_check = filesystem_state(vault)
    with pytest.raises(views.ProjectionError, match="Unknown/unowned derived files"):
        views.project(repo, vault, source_commit)
    assert filesystem_state(vault) == before_unknown_check
    authored_after_unknown = {
        path: digest
        for path, digest in snapshot(vault, authored=True).items()
        if not path.startswith(f"{views.OWNED_ROOT}/")
    }
    assert authored_after_unknown == authored_before


def test_cli_exposes_stable_workspace_commands_without_user_paths(setup):
    repo, vault, source_commit = setup
    result = CliRunner().invoke(app, ["workspace", "--help"])
    assert result.exit_code == 0
    assert "apply" in result.output and "check" in result.output
    result = CliRunner().invoke(
        app,
        ["workspace", "apply", "--repo-root", str(repo), "--vault-root", str(vault)],
    )
    assert result.exit_code == 0, result.output
    assert f"source SHA: {source_commit}" in result.output
    assert "restore point:" in result.output
    result = CliRunner().invoke(
        app,
        ["workspace", "check", "--repo-root", str(repo), "--vault-root", str(vault)],
    )
    assert result.exit_code == 0, result.output
    assert "restore point:" not in result.output
    harness_source = Path(workspace.__file__).read_text(encoding="utf-8")
    assert "PRIVATE_VAULT" in harness_source
    assert "/Users/" not in harness_source
