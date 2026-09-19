import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fh_agent.projectctl import (
    CommandResult,
    RuntimeInfo,
    app,
    collect_doctor_report,
    evaluate_handoff_state,
    render_json_report,
)


def test_handoff_is_safe_only_for_clean_synchronized_issue_branch() -> None:
    result = evaluate_handoff_state(
        branch="codex/64-project-doctor",
        clean=True,
        origin_matches=True,
        tracked_remote="origin/codex/64-project-doctor",
        relation="synchronized",
        remote_ref_available=True,
    )

    assert result.status == "PASS"
    assert result.safe is True
    assert result.reasons == ()


@pytest.mark.parametrize(
    ("relation", "status"),
    [
        ("ahead", "FAIL"),
        ("behind", "FAIL"),
        ("diverged", "FAIL"),
    ],
)
def test_handoff_rejects_non_synchronized_relation(relation, status) -> None:
    result = evaluate_handoff_state(
        branch="codex/64-project-doctor",
        clean=True,
        origin_matches=True,
        tracked_remote="origin/codex/64-project-doctor",
        relation=relation,
        remote_ref_available=True,
    )

    assert result.status == status
    assert result.safe is False
    assert relation in result.reasons[0]


def test_handoff_rejects_dirty_tree_and_wrong_origin() -> None:
    result = evaluate_handoff_state(
        branch="codex/64-project-doctor",
        clean=False,
        origin_matches=False,
        tracked_remote="origin/codex/64-project-doctor",
        relation="synchronized",
        remote_ref_available=True,
    )

    assert result.status == "FAIL"
    assert result.safe is False
    assert any("uncommitted" in reason for reason in result.reasons)
    assert any("origin" in reason for reason in result.reasons)


def test_handoff_warns_when_remote_state_is_unknown() -> None:
    result = evaluate_handoff_state(
        branch="codex/64-project-doctor",
        clean=True,
        origin_matches=True,
        tracked_remote="origin/codex/64-project-doctor",
        relation="unknown",
        remote_ref_available=False,
    )

    assert result.status == "WARN"
    assert result.safe is False
    assert any("no fetch" in reason for reason in result.reasons)


def test_handoff_rejects_direct_main_work() -> None:
    result = evaluate_handoff_state(
        branch="main",
        clean=True,
        origin_matches=True,
        tracked_remote="origin/main",
        relation="synchronized",
        remote_ref_available=True,
    )

    assert result.status == "FAIL"
    assert result.safe is False
    assert any("main" in reason for reason in result.reasons)


def test_doctor_uses_only_read_only_probes_and_reports_missing_optional_tools(
    tmp_path: Path,
) -> None:
    calls: list[tuple[tuple[str, ...], Path | None]] = []
    root = tmp_path / "repo"
    root.mkdir()

    def fake_runner(command, cwd):
        calls.append((tuple(command), cwd))
        responses = {
            ("uv", "--version"): CommandResult(0, "uv 0.11.14\n"),
            ("git", "--version"): CommandResult(0, "git version 2.51.0\n"),
            ("git", "rev-parse", "--show-toplevel"): CommandResult(0, f"{root}\n"),
            ("git", "branch", "--show-current"): CommandResult(0, "codex/64-project-doctor\n"),
            ("git", "status", "--porcelain=v1", "--untracked-files=all"): CommandResult(0, ""),
            ("git", "rev-parse", "--verify", "HEAD"): CommandResult(0, "abc123\n"),
            ("git", "remote", "get-url", "origin"): CommandResult(
                0,
                "https://workflow-token:secret-value@github.com/Planton361/autonomous-game-agent.git\n",
            ),
            (
                "git",
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{upstream}",
            ): CommandResult(0, "origin/codex/64-project-doctor\n"),
            (
                "git",
                "show-ref",
                "--verify",
                "--quiet",
                "refs/remotes/origin/codex/64-project-doctor",
            ): CommandResult(0, ""),
            (
                "git",
                "rev-list",
                "--left-right",
                "--count",
                "HEAD...origin/codex/64-project-doctor",
            ): CommandResult(0, "0\t0\n"),
        }
        return responses.get(tuple(command), CommandResult(1, stderr="not configured"))

    runtime = RuntimeInfo(
        python_version="3.12.13",
        python_supported=True,
        interpreter="/fake/python3.12",
        system="Linux",
        architecture="x86_64",
        system_supported=True,
    )
    report = collect_doctor_report(
        root,
        runner=fake_runner,
        which=lambda name: f"/fake/{name}" if name in {"uv", "git"} else None,
        runtime=runtime,
    )

    assert report["overall"] == "WARN"
    assert report["handoff"]["safe"] is True
    assert report["repository"]["remote_relation"] == "synchronized"
    assert report["tools"]["gh"]["available"] is False
    assert report["tools"]["codex"]["available"] is False
    rendered = render_json_report(report)
    assert "workflow-token" not in rendered
    assert "secret-value" not in rendered
    assert all("fetch" not in command and "pull" not in command for command, _ in calls)
    assert not any(command[0] in {"commit", "push", "login"} for command, _ in calls)


def test_doctor_reports_wrong_origin_and_unknown_remote_without_fetch(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def fake_runner(command, cwd):
        responses = {
            ("uv", "--version"): CommandResult(0, "uv 0.11.14\n"),
            ("git", "--version"): CommandResult(0, "git version 2.51.0\n"),
            ("git", "rev-parse", "--show-toplevel"): CommandResult(0, f"{root}\n"),
            ("git", "branch", "--show-current"): CommandResult(0, "codex/64-project-doctor\n"),
            ("git", "status", "--porcelain=v1", "--untracked-files=all"): CommandResult(0, ""),
            ("git", "rev-parse", "--verify", "HEAD"): CommandResult(0, "abc123\n"),
            ("git", "remote", "get-url", "origin"): CommandResult(
                0, "git@github.com:someone/other-repository.git\n"
            ),
            (
                "git",
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{upstream}",
            ): CommandResult(0, "origin/codex/64-project-doctor\n"),
            (
                "git",
                "show-ref",
                "--verify",
                "--quiet",
                "refs/remotes/origin/codex/64-project-doctor",
            ): CommandResult(1),
        }
        return responses.get(tuple(command), CommandResult(1))

    report = collect_doctor_report(
        root,
        runner=fake_runner,
        which=lambda name: f"/fake/{name}" if name in {"uv", "git"} else None,
        runtime=RuntimeInfo("3.12.13", True, "/fake/python", "Darwin", "arm64", True),
    )

    assert report["overall"] == "FAIL"
    assert report["repository"]["origin"]["matches"] is False
    assert report["handoff"]["status"] == "FAIL"
    assert report["handoff"]["safe"] is False
    assert report["repository"]["remote_relation"] == "unknown"


def test_doctor_json_is_deterministic_and_contains_no_remote_url_or_auth_output() -> None:
    report = {
        "tool": "projectctl",
        "command": "doctor",
        "overall": "WARN",
        "environment": {},
        "tools": {"gh": {"auth": {"status": "authenticated"}}},
        "repository": {"origin": {"identity": "Planton361/autonomous-game-agent"}},
        "handoff": {"safe": False},
        "checks": [],
    }

    rendered = render_json_report(report)

    assert json.loads(rendered) == report
    assert "token" not in rendered.casefold()
    assert "password" not in rendered.casefold()


def test_projectctl_cli_help_smoke() -> None:
    result = CliRunner().invoke(app, ["doctor", "--help"])

    assert result.exit_code == 0
    assert "read-only" in result.stdout.casefold()
