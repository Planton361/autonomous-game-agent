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
from test_research_wiki_schema import props
from typer.testing import CliRunner

from fh_agent.cli import app
from fh_agent.research_atlas import private_projection as technical
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import workspace_harness as workspace


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
        Path("docs/research-atlas/Generated/Atlas Views.base"),
        Path("docs/research-atlas/Wiki Views"),
        Path("docs/research-atlas/Process Seeds"),
    ):
        _copy_source(repo, relative)
    source = repo / "src/fh_agent/research_atlas/source.py"
    source.parent.mkdir(parents=True)
    source.write_text("# synthetic committed source\n", encoding="utf-8")
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
    return {
        str(path.relative_to(vault)): technical.digest(path.read_bytes())
        for root in workspace.RESTORED_ROOTS
        for path in (vault / root).rglob("*")
        if path.is_file()
    }


def _authored_snapshot(vault: Path) -> dict[str, str]:
    derived_prefix = f"{views.OWNED_ROOT}/"
    return {
        path: digest
        for path, digest in snapshot(vault, authored=True).items()
        if not path.startswith(derived_prefix)
    }


def test_apply_orders_restore_writes_and_checks_at_exact_head(setup, monkeypatch):
    repo, vault, source_commit = setup
    technical.project(repo, vault, source_commit)
    views.project(repo, vault, source_commit)
    before_generated = _generated_snapshot(vault)
    before_authored = snapshot(vault, authored=True)
    calls: list[tuple[str, str, bool, bool]] = []
    technical_project = technical.project
    views_project = views.project

    def record_technical(repo_root, vault_root, source_ref, *, check=False, preflight=False):
        calls.append(("technical", source_ref, check, preflight))
        return technical_project(
            repo_root, vault_root, source_ref, check=check, preflight=preflight
        )

    def record_views(repo_root, vault_root, source_ref, *, check=False, preflight=False):
        calls.append(("views", source_ref, check, preflight))
        return views_project(repo_root, vault_root, source_ref, check=check, preflight=preflight)

    monkeypatch.setattr(workspace, "technical_project", record_technical)
    monkeypatch.setattr(workspace, "views_project", record_views)
    result = workspace.apply(repo, vault)

    assert result.source_commit == source_commit
    assert calls == [
        ("technical", source_commit, False, True),
        ("views", source_commit, False, True),
        ("technical", source_commit, False, False),
        ("views", source_commit, False, False),
        ("technical", source_commit, True, False),
        ("views", source_commit, True, False),
    ]
    assert result.restore_point is not None
    assert _generated_snapshot(result.restore_point) == before_generated
    assert json.loads((result.restore_point / "restore-point.json").read_text()) == {
        "generated_roots_present": [str(root) for root in workspace.RESTORED_ROOTS],
        "restore_point_schema_version": "1.0",
        "source_commit": source_commit,
    }
    assert snapshot(vault, authored=True) == before_authored


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
    calls: list[str] = []

    def fail_copy(*args, **kwargs):
        raise OSError("synthetic backup failure")

    monkeypatch.setattr(workspace.shutil, "copytree", fail_copy)

    def preflight_technical(*args, preflight=False, **kwargs):
        calls.append("technical-preflight" if preflight else "technical-apply")

    def preflight_views(*args, preflight=False, **kwargs):
        calls.append("views-preflight" if preflight else "views-apply")

    monkeypatch.setattr(workspace, "technical_project", preflight_technical)
    monkeypatch.setattr(workspace, "views_project", preflight_views)
    with pytest.raises(workspace.WorkspaceError, match="Restore-point copy failed"):
        workspace.apply(repo, vault)
    assert calls == ["technical-preflight", "views-preflight"]


def test_first_projector_failure_stops_pipeline_and_reports_restore_point(setup, monkeypatch):
    repo, vault, _ = setup
    calls: list[str] = []

    def fail_technical(*args, preflight=False, **kwargs):
        calls.append("technical-preflight" if preflight else "technical-apply")
        if not preflight:
            raise technical.ProjectionError("synthetic technical failure")

    monkeypatch.setattr(workspace, "technical_project", fail_technical)
    monkeypatch.setattr(
        workspace,
        "views_project",
        lambda *args, preflight=False, **kwargs: calls.append(
            "views-preflight" if preflight else "views-apply"
        ),
    )
    with pytest.raises(
        workspace.WorkspaceError, match="technical projection failed.*restore point"
    ):
        workspace.apply(repo, vault)
    assert calls == ["technical-preflight", "views-preflight", "technical-apply"]


def test_second_projector_and_final_check_fail_closed_with_restore_point(setup, monkeypatch):
    repo, vault, source_commit = setup
    calls: list[tuple[str, bool, bool]] = []
    technical_project = technical.project
    views_project = views.project

    def record_technical(repo_root, vault_root, source_ref, *, check=False, preflight=False):
        calls.append(("technical", check, preflight))
        return technical_project(
            repo_root, vault_root, source_ref, check=check, preflight=preflight
        )

    def fail_views(repo_root, vault_root, source_ref, *, check=False, preflight=False):
        calls.append(("views", check, preflight))
        if not check and not preflight:
            raise views.ProjectionError("synthetic view failure")
        return views_project(repo_root, vault_root, source_ref, check=check, preflight=preflight)

    monkeypatch.setattr(workspace, "technical_project", record_technical)
    monkeypatch.setattr(workspace, "views_project", fail_views)
    with pytest.raises(workspace.WorkspaceError, match="direct views failed.*restore point"):
        workspace.apply(repo, vault)
    assert calls == [
        ("technical", False, True),
        ("views", False, True),
        ("technical", False, False),
        ("views", False, False),
    ]

    monkeypatch.setattr(workspace, "views_project", views_project)

    def fail_final_check(repo_root, vault_root, source_ref, *, check=False, preflight=False):
        calls.append(("technical", check, preflight))
        if check:
            raise technical.ProjectionError("synthetic final-check failure")
        return technical_project(
            repo_root, vault_root, source_ref, check=check, preflight=preflight
        )

    monkeypatch.setattr(workspace, "technical_project", fail_final_check)
    with pytest.raises(
        workspace.WorkspaceError, match="technical projection check failed.*restore point"
    ):
        workspace.apply(repo, vault)
    assert calls[-1] == ("technical", True, False)
    assert source_commit


def test_unknown_owned_root_content_propagates_without_touching_authored_bytes(setup):
    repo, vault, _ = setup
    unknown = vault / technical.OWNED_ROOT / "unknown.md"
    unknown.parent.mkdir(parents=True)
    unknown.write_text("preserve", encoding="utf-8")
    before_authored = snapshot(vault, authored=True)
    with pytest.raises(workspace.WorkspaceError, match="Unknown/unowned files"):
        workspace.apply(repo, vault)
    assert snapshot(vault, authored=True) == before_authored
    assert unknown.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("fault", ["unknown", "corrupt-manifest", "lost-owner"])
def test_apply_preflights_both_roots_before_any_workspace_mutation(setup, fault):
    repo, vault, _ = setup
    first = workspace.apply(repo, vault)
    assert first.restore_point is not None
    root = vault / views.OWNED_ROOT
    if fault == "unknown":
        unknown = root / "unowned.md"
        unknown.write_text("synthetic unowned data", encoding="utf-8")
        expected_error = "Unknown/unowned derived files"
    elif fault == "corrupt-manifest":
        (root / views.MANIFEST).write_text("not: [valid yaml", encoding="utf-8")
        expected_error = "manifest"
    else:
        page = root / views.LITERATURE_INSPECTION
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
        (technical.OWNED_ROOT, technical.MAP),
        (views.OWNED_ROOT, views.LITERATURE_INSPECTION),
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


def test_interrupted_direct_generation_is_rejected_by_check_then_recovers(setup, monkeypatch):
    repo, vault, _ = setup
    authored = vault / "authored/references/Synthetic Paper.md"
    write_note(authored, props("paper", wiki_id="WPAPER-HARNESS", title="Synthetic paper"))
    workspace.apply(repo, vault)
    paper_bytes = authored.read_bytes()

    moved = vault / "authored/moved/Synthetic Paper.md"
    moved.parent.mkdir(parents=True)
    authored.rename(moved)
    authored_before = _authored_snapshot(vault)
    atomic_write = views.atomic_write

    def interrupt_after_navigation(root, relative, data):
        result = atomic_write(root, relative, data)
        if relative == views.NAVIGATION:
            raise OSError("synthetic interrupted direct-view generation")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(views, "atomic_write", interrupt_after_navigation)
        with pytest.raises(workspace.WorkspaceError, match="direct views failed"):
            workspace.apply(repo, vault)

    interrupted_state = filesystem_state(vault)
    with pytest.raises(workspace.WorkspaceError, match="drift"):
        workspace.check(repo, vault)
    assert filesystem_state(vault) == interrupted_state
    assert _authored_snapshot(vault) == authored_before
    assert moved.read_bytes() == paper_bytes

    workspace.apply(repo, vault)
    workspace.check(repo, vault)
    recovered = _generated_snapshot(vault)
    workspace.apply(repo, vault)
    assert _generated_snapshot(vault) == recovered
    assert _authored_snapshot(vault) == authored_before
    assert moved.read_bytes() == paper_bytes


def test_complete_workspace_paths_links_and_markdown_fallback_are_portable(setup):
    repo, vault, _ = setup
    workspace.apply(repo, vault)
    generated_paths = tuple(PurePosixPath(path) for path in _generated_snapshot(vault))
    technical.validate_portable_paths(generated_paths)
    inventory = set(generated_paths)
    required = {
        technical.OWNED_ROOT / technical.HOME,
        technical.OWNED_ROOT / technical.ANATOMY,
        technical.OWNED_ROOT / technical.DOMAIN_SLICE,
        views.OWNED_ROOT / views.K3_HOME,
        views.OWNED_ROOT / views.HIERARCHY,
        views.OWNED_ROOT / views.RESEARCH_LANDSCAPE,
        views.OWNED_ROOT / views.LITERATURE_INSPECTION,
        views.OWNED_ROOT / views.NAVIGATION,
    }
    assert required <= inventory

    home = (vault / views.OWNED_ROOT / views.K3_HOME).read_text(encoding="utf-8")
    landscape = (vault / views.OWNED_ROOT / views.RESEARCH_LANDSCAPE).read_text(encoding="utf-8")
    direct_index = (vault / views.OWNED_ROOT / views.INDEX).read_text(encoding="utf-8")
    assert "Markdown fallback" in home
    assert "If Excalidraw is unavailable" in home
    assert "Technical Hierarchy" in home
    assert "Literature Inspection" in landscape and "Literature Inspection" in direct_index
    for paths in views.COMPONENT_HUB_PATHS.values():
        for path in (paths.overview, paths.research):
            assert views.OWNED_ROOT / path in inventory
        assert str(paths.research.with_suffix("")) in landscape
        overview = (vault / views.OWNED_ROOT / paths.overview).read_text(encoding="utf-8")
        assert str(paths.research.with_suffix("")) in overview

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
                assert link and not PurePosixPath(link).is_absolute()
                assert not PureWindowsPath(link).drive and "\\" not in link
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target:
                    continue
                link = target.split("#", 1)[0]
                assert not link.startswith(("/", "\\"))
                assert not PureWindowsPath(link).drive and "\\" not in link


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
    old_paths = detail_paths | {views.RESEARCH_LANDSCAPE, views.LITERATURE_INSPECTION}
    for relative in old_paths:
        (derived_root / relative).unlink()
    prior["view_schema_version"] = "2.3"
    prior["owned_files"] = [
        item for item in prior["owned_files"] if Path(item["path"]) not in old_paths
    ]
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
    assert current["view_schema_version"] == "2.6"
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
