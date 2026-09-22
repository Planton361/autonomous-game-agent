"""Fast fail-closed orchestration contracts for the private Workspace harness."""

from pathlib import Path

import pytest

from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.private_projection import ProjectionError


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
