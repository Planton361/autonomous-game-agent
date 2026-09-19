import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import fh_agent.projectctl as projectctl
from fh_agent.projectctl import (
    CommandResult,
    RuntimeInfo,
    app,
    collect_doctor_report,
    evaluate_handoff_state,
    render_json_report,
)


def git_probe(*arguments: str) -> tuple[str, ...]:
    return ("git", "--no-optional-locks", *arguments)


def test_handoff_is_safe_only_for_clean_synchronized_issue_branch() -> None:
    result = evaluate_handoff_state(
        branch="codex/64-project-doctor",
        clean=True,
        origin_matches=True,
        tracked_remote="origin/codex/64-project-doctor",
        relation="synchronized",
        remote_ref_available=True,
        remote_ref_fresh=True,
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
        remote_ref_fresh=True,
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
        remote_ref_fresh=True,
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
        remote_ref_fresh=True,
    )

    assert result.status == "FAIL"
    assert result.safe is False
    assert any("main" in reason for reason in result.reasons)


@pytest.mark.parametrize(
    ("tracked_remote", "remote_ref_available", "relation", "status"),
    [
        ("origin/other-issue", True, "synchronized", "FAIL"),
        (None, False, "unknown", "WARN"),
    ],
)
def test_handoff_rejects_tracking_mismatch_or_missing_upstream(
    tracked_remote, remote_ref_available, relation, status
) -> None:
    result = evaluate_handoff_state(
        branch="codex/64-project-doctor",
        clean=True,
        origin_matches=True,
        tracked_remote=tracked_remote,
        relation=relation,
        remote_ref_available=remote_ref_available,
        remote_ref_fresh=True if remote_ref_available else None,
    )

    assert result.status == status
    assert result.safe is False
    assert any("upstream" in reason or "tracks" in reason for reason in result.reasons)


def test_doctor_uses_only_read_only_probes_and_reports_missing_optional_tools(
    tmp_path: Path,
) -> None:
    calls: list[tuple[tuple[str, ...], Path | None]] = []
    root = tmp_path / "repo"
    root.mkdir()
    fetch_head = root / "FETCH_HEAD"
    fetch_head.write_text(
        "abc123\tbranch 'codex/64-project-doctor' of "
        "https://github.com/Planton361/autonomous-game-agent.git\n",
        encoding="utf-8",
    )

    def fake_runner(command, cwd):
        calls.append((tuple(command), cwd))
        responses = {
            ("uv", "--version"): CommandResult(0, "uv 0.11.14\n"),
            ("git", "--version"): CommandResult(0, "git version 2.51.0\n"),
            git_probe("rev-parse", "--show-toplevel"): CommandResult(0, f"{root}\n"),
            git_probe("branch", "--show-current"): CommandResult(0, "codex/64-project-doctor\n"),
            git_probe("status", "--porcelain=v1", "--untracked-files=all"): CommandResult(0, ""),
            git_probe("rev-parse", "--verify", "HEAD"): CommandResult(0, "abc123\n"),
            git_probe("remote", "get-url", "--all", "origin"): CommandResult(
                0,
                "https://workflow-token:secret-value@github.com/Planton361/autonomous-game-agent.git\n"
                "https://second-user:second-secret@github.com/Planton361/autonomous-game-agent.git\n",
            ),
            git_probe("remote", "get-url", "--push", "--all", "origin"): CommandResult(
                0,
                "git@github.com:Planton361/autonomous-game-agent.git\n"
                "https://push-user:push-secret@github.com/Planton361/autonomous-game-agent.git\n",
            ),
            git_probe(
                "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
            ): CommandResult(0, "origin/codex/64-project-doctor\n"),
            git_probe(
                "rev-parse", "--verify", "refs/remotes/origin/codex/64-project-doctor"
            ): CommandResult(0, "abc123\n"),
            git_probe("rev-parse", "--git-path", "FETCH_HEAD"): CommandResult(0, f"{fetch_head}\n"),
            git_probe(
                "rev-list", "--left-right", "--count", "HEAD...origin/codex/64-project-doctor"
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
    assert report["repository"]["remote_ref_fresh"] is True
    assert report["repository"]["origin"]["matches"] is True
    assert len(report["repository"]["origin"]["fetch_identities"]) == 2
    assert len(report["repository"]["origin"]["push_identities"]) == 2
    assert report["tools"]["gh"]["available"] is False
    assert report["tools"]["codex"]["available"] is False
    rendered = render_json_report(report)
    assert "workflow-token" not in rendered
    assert "secret-value" not in rendered
    assert "second-secret" not in rendered
    assert "push-secret" not in rendered
    assert all("fetch" not in command and "pull" not in command for command, _ in calls)
    assert not any(command[0] in {"commit", "push", "login"} for command, _ in calls)
    git_probes = [
        command for command, _ in calls if command[0] == "git" and command[1:] != ("--version",)
    ]
    assert git_probes
    assert all(command[1] == "--no-optional-locks" for command in git_probes)


def test_doctor_reports_wrong_origin_and_unknown_remote_without_fetch(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    def fake_runner(command, cwd):
        responses = {
            ("uv", "--version"): CommandResult(0, "uv 0.11.14\n"),
            ("git", "--version"): CommandResult(0, "git version 2.51.0\n"),
            git_probe("rev-parse", "--show-toplevel"): CommandResult(0, f"{root}\n"),
            git_probe("branch", "--show-current"): CommandResult(0, "codex/64-project-doctor\n"),
            git_probe("status", "--porcelain=v1", "--untracked-files=all"): CommandResult(0, ""),
            git_probe("rev-parse", "--verify", "HEAD"): CommandResult(0, "abc123\n"),
            git_probe("remote", "get-url", "--all", "origin"): CommandResult(
                0, "git@github.com:someone/other-repository.git\n"
            ),
            git_probe("remote", "get-url", "--push", "--all", "origin"): CommandResult(
                0, "git@github.com:someone/other-repository.git\n"
            ),
            git_probe(
                "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
            ): CommandResult(0, "origin/codex/64-project-doctor\n"),
            git_probe(
                "rev-parse", "--verify", "refs/remotes/origin/codex/64-project-doctor"
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


def test_doctor_rejects_wrong_push_identity_with_expected_fetch(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    fetch_head = root / "FETCH_HEAD"
    fetch_head.write_text(
        "abc123\tbranch 'codex/64-project-doctor' of "
        "https://github.com/Planton361/autonomous-game-agent.git\n",
        encoding="utf-8",
    )

    def fake_runner(command, cwd):
        responses = {
            ("uv", "--version"): CommandResult(0, "uv 0.11.14\n"),
            ("git", "--version"): CommandResult(0, "git version 2.51.0\n"),
            git_probe("rev-parse", "--show-toplevel"): CommandResult(0, f"{root}\n"),
            git_probe("branch", "--show-current"): CommandResult(0, "codex/64-project-doctor\n"),
            git_probe("status", "--porcelain=v1", "--untracked-files=all"): CommandResult(0, ""),
            git_probe("rev-parse", "--verify", "HEAD"): CommandResult(0, "abc123\n"),
            git_probe("remote", "get-url", "--all", "origin"): CommandResult(
                0, "https://github.com/Planton361/autonomous-game-agent.git\n"
            ),
            git_probe("remote", "get-url", "--push", "--all", "origin"): CommandResult(
                0, "git@github.com:someone/other-repository.git\n"
            ),
            git_probe(
                "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
            ): CommandResult(0, "origin/codex/64-project-doctor\n"),
            git_probe(
                "rev-parse", "--verify", "refs/remotes/origin/codex/64-project-doctor"
            ): CommandResult(0, "abc123\n"),
            git_probe("rev-parse", "--git-path", "FETCH_HEAD"): CommandResult(0, f"{fetch_head}\n"),
            git_probe(
                "rev-list", "--left-right", "--count", "HEAD...origin/codex/64-project-doctor"
            ): CommandResult(0, "0\t0\n"),
        }
        return responses.get(tuple(command), CommandResult(1))

    report = collect_doctor_report(
        root,
        runner=fake_runner,
        which=lambda name: f"/fake/{name}" if name in {"uv", "git"} else None,
        runtime=RuntimeInfo("3.12.13", True, "/fake/python", "Linux", "x86_64", True),
    )

    assert report["repository"]["origin"]["matches"] is False
    assert report["handoff"]["status"] == "FAIL"
    assert report["handoff"]["safe"] is False


def test_doctor_marks_present_but_unproven_remote_ref_unknown(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    fetch_head = root / "FETCH_HEAD"
    fetch_head.write_text(
        "abc123\tbranch 'codex/64-project-doctor' of git@github.com:someone/other-repository.git\n",
        encoding="utf-8",
    )

    def fake_runner(command, cwd):
        responses = {
            ("uv", "--version"): CommandResult(0, "uv 0.11.14\n"),
            ("git", "--version"): CommandResult(0, "git version 2.51.0\n"),
            git_probe("rev-parse", "--show-toplevel"): CommandResult(0, f"{root}\n"),
            git_probe("branch", "--show-current"): CommandResult(0, "codex/64-project-doctor\n"),
            git_probe("status", "--porcelain=v1", "--untracked-files=all"): CommandResult(0, ""),
            git_probe("rev-parse", "--verify", "HEAD"): CommandResult(0, "abc123\n"),
            git_probe("remote", "get-url", "--all", "origin"): CommandResult(
                0, "https://github.com/Planton361/autonomous-game-agent.git\n"
            ),
            git_probe("remote", "get-url", "--push", "--all", "origin"): CommandResult(
                0, "https://github.com/Planton361/autonomous-game-agent.git\n"
            ),
            git_probe(
                "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
            ): CommandResult(0, "origin/codex/64-project-doctor\n"),
            git_probe(
                "rev-parse", "--verify", "refs/remotes/origin/codex/64-project-doctor"
            ): CommandResult(0, "abc123\n"),
            git_probe("rev-parse", "--git-path", "FETCH_HEAD"): CommandResult(0, f"{fetch_head}\n"),
        }
        return responses.get(tuple(command), CommandResult(1))

    report = collect_doctor_report(
        root,
        runner=fake_runner,
        which=lambda name: f"/fake/{name}" if name in {"uv", "git"} else None,
        runtime=RuntimeInfo("3.12.13", True, "/fake/python", "Linux", "x86_64", True),
    )

    assert report["repository"]["remote_ref_available"] is True
    assert report["repository"]["remote_ref_fresh"] is False
    assert report["repository"]["remote_relation"] == "unknown"
    assert report["handoff"]["status"] == "WARN"
    assert report["handoff"]["safe"] is False
    assert "origin-fetch provenance" in " ".join(report["handoff"]["reasons"])


def test_doctor_does_not_render_git_error_output(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    secret = "super-secret-token"

    def fake_runner(command, cwd):
        responses = {
            ("uv", "--version"): CommandResult(0, "uv 0.11.14\n"),
            ("git", "--version"): CommandResult(0, "git version 2.51.0\n"),
            git_probe("rev-parse", "--show-toplevel"): CommandResult(0, f"{root}\n"),
        }
        return responses.get(tuple(command), CommandResult(1, stderr=f"fatal: token={secret}"))

    report = collect_doctor_report(
        root,
        runner=fake_runner,
        which=lambda name: f"/fake/{name}" if name in {"uv", "git"} else None,
        runtime=RuntimeInfo("3.12.13", True, "/fake/python", "Linux", "x86_64", True),
    )

    assert secret not in render_json_report(report)
    assert secret not in projectctl.render_human_report(report)


@pytest.mark.parametrize(
    ("failure", "message_fragment"),
    [
        (FileNotFoundError("git missing"), "git missing"),
        (subprocess.TimeoutExpired(["git", "status"], 5), "timed out"),
        (OSError("permission denied"), "permission denied"),
    ],
)
def test_run_command_handles_subprocess_failures(monkeypatch, failure, message_fragment) -> None:
    def raise_failure(*args, **kwargs):
        raise failure

    monkeypatch.setattr(projectctl.subprocess, "run", raise_failure)

    result = projectctl._run_command(["git", "status"], None)

    assert result.returncode is None
    assert result.error is not None
    assert message_fragment in result.error


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
