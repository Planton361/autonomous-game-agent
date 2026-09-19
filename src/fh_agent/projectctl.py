"""Read-only project-control checks for the cross-device development workflow."""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

import typer

from fh_agent import __version__

EXPECTED_REPOSITORY = "Planton361/autonomous-game-agent"
EXPECTED_PYTHON = (3, 12)
SUPPORTED_SYSTEMS = frozenset({"Darwin", "Linux"})
CommandRunner = Callable[[Sequence[str], Path | None], "CommandResult"]
Which = Callable[[str], str | None]
Status = Literal["PASS", "WARN", "FAIL"]
RemoteRelation = Literal["synchronized", "ahead", "behind", "diverged", "unknown"]


@dataclass(frozen=True)
class CommandResult:
    """Safe subset of a subprocess result used by the doctor."""

    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None


@dataclass(frozen=True)
class RuntimeInfo:
    """Runtime facts, injectable so tests do not depend on the operator host."""

    python_version: str
    python_supported: bool
    interpreter: str
    system: str
    architecture: str
    system_supported: bool


@dataclass(frozen=True)
class HandoffAssessment:
    """Pure evaluation of the cross-device handoff contract."""

    status: Status
    safe: bool
    branch: str | None
    expected_remote: str | None
    tracked_remote: str | None
    relation: RemoteRelation
    remote_ref_available: bool | None
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "safe": self.safe,
            "branch": self.branch,
            "expected_remote": self.expected_remote,
            "tracked_remote": self.tracked_remote,
            "relation": self.relation,
            "remote_ref_available": self.remote_ref_available,
            "reasons": list(self.reasons),
        }


app = typer.Typer(
    add_completion=False,
    help="Read-only project-control checks for the GitHub-centered workflow.",
)


def _run_command(command: Sequence[str], cwd: Path | None) -> CommandResult:
    """Run one fixed, non-shell command with a bounded timeout."""

    try:
        result = subprocess.run(
            tuple(command),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except FileNotFoundError as exc:
        return CommandResult(returncode=None, error=str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(returncode=None, error=f"timed out after {exc.timeout}s")
    except OSError as exc:
        return CommandResult(returncode=None, error=str(exc))
    return CommandResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _runtime_info() -> RuntimeInfo:
    version_info = sys.version_info
    python_version = ".".join(
        str(value) for value in (version_info.major, version_info.minor, version_info.micro)
    )
    system = platform.system() or "unknown"
    architecture = platform.machine() or "unknown"
    return RuntimeInfo(
        python_version=python_version,
        python_supported=(version_info.major, version_info.minor) >= EXPECTED_PYTHON,
        interpreter=sys.executable or "unknown",
        system=system,
        architecture=architecture,
        system_supported=system in SUPPORTED_SYSTEMS,
    )


def _successful(result: CommandResult | None) -> bool:
    return result is not None and result.returncode == 0


def _first_nonempty_line(value: str) -> str:
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _version_from(result: CommandResult) -> str | None:
    """Extract only a version token; never expose arbitrary tool output."""

    match = re.search(
        r"(?<!\d)\d+\.\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?(?!\d)",
        f"{result.stdout}\n{result.stderr}",
    )
    return match.group(0) if match else None


def _check(
    name: str,
    status: Status,
    message: str,
    **details: object,
) -> dict[str, object]:
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details,
    }


def _tool_report(
    name: str,
    *,
    required: bool,
    runner: CommandRunner,
    which: Which,
) -> tuple[dict[str, object], dict[str, object]]:
    executable = which(name)
    if executable is None:
        status: Status = "FAIL" if required else "WARN"
        message = f"{name} is unavailable"
        return (
            {
                "available": False,
                "version": None,
                "status": status,
            },
            _check(name, status, message, available=False),
        )

    result = runner([name, "--version"], None)
    version = _version_from(result) if _successful(result) else None
    if not _successful(result):
        status = "FAIL" if required else "WARN"
        message = f"{name} is present but its version check failed"
    else:
        status = "PASS"
        message = f"{name} available"
    return (
        {
            "available": True,
            "version": version or "available",
            "status": status,
        },
        _check(name, status, message, available=True, version=version or "available"),
    )


def _repository_identity(remote_url: str) -> str | None:
    """Return a credential-free host/path identity for common Git URL forms."""

    value = remote_url.strip().splitlines()[0] if remote_url.strip() else ""
    if not value:
        return None

    host: str | None
    path: str
    scp_match = re.match(r"^[^/@\s]+@(?P<host>[^:\s]+):(?P<path>.+)$", value)
    if scp_match:
        host = scp_match.group("host")
        path = scp_match.group("path")
    else:
        parsed = urlparse(value)
        host = parsed.hostname
        path = parsed.path

    if host is None or not path:
        return None
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not path or any(part in {".", ".."} for part in path.split("/")):
        return None
    normalized_host = host.casefold()
    return f"{path}" if normalized_host == "github.com" else f"{normalized_host}/{path}"


def _parse_relation(result: CommandResult) -> RemoteRelation:
    if not _successful(result):
        return "unknown"
    parts = result.stdout.split()
    if len(parts) != 2:
        return "unknown"
    try:
        ahead_count, behind_count = (int(value) for value in parts)
    except ValueError:
        return "unknown"
    if ahead_count == 0 and behind_count == 0:
        return "synchronized"
    if ahead_count > 0 and behind_count == 0:
        return "ahead"
    if ahead_count == 0 and behind_count > 0:
        return "behind"
    if ahead_count > 0 and behind_count > 0:
        return "diverged"
    return "unknown"


def _valid_remote_name(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._~/-]+", value))


def evaluate_handoff_state(
    *,
    branch: str | None,
    clean: bool | None,
    origin_matches: bool | None,
    tracked_remote: str | None,
    relation: RemoteRelation,
    remote_ref_available: bool | None,
) -> HandoffAssessment:
    """Evaluate handoff safety without probing the network or changing state."""

    expected_remote = f"origin/{branch}" if branch else None
    reasons: list[str] = []
    blocking = False
    uncertain = False

    if branch is None:
        blocking = True
        reasons.append("the checkout is detached or has no current branch")
    elif branch == "main":
        blocking = True
        reasons.append("direct work on main is forbidden")

    if clean is False:
        blocking = True
        reasons.append("working tree contains uncommitted or untracked changes")
    elif clean is None:
        uncertain = True
        reasons.append("working-tree cleanliness is unknown")

    if origin_matches is False:
        blocking = True
        reasons.append(f"origin is not {EXPECTED_REPOSITORY}")
    elif origin_matches is None:
        uncertain = True
        reasons.append("origin repository identity is unknown")

    if expected_remote is None or tracked_remote is None:
        uncertain = True
        reasons.append("the active branch has no verifiable expected upstream")
    elif tracked_remote != expected_remote:
        blocking = True
        reasons.append(f"branch tracks {tracked_remote}, expected {expected_remote}")

    if remote_ref_available is False:
        uncertain = True
        reasons.append("the local remote-tracking ref is missing; no fetch was attempted")
    elif remote_ref_available is None:
        uncertain = True
        reasons.append("the local remote-tracking ref could not be inspected")

    if relation == "unknown":
        uncertain = True
        reasons.append("local-vs-remote relation is unknown; no fetch was attempted")
    elif relation != "synchronized":
        blocking = True
        reasons.append(f"local branch is {relation} relative to its tracked remote")

    if blocking:
        status: Status = "FAIL"
    elif uncertain:
        status = "WARN"
    else:
        status = "PASS"

    return HandoffAssessment(
        status=status,
        safe=status == "PASS",
        branch=branch,
        expected_remote=expected_remote,
        tracked_remote=tracked_remote,
        relation=relation,
        remote_ref_available=remote_ref_available,
        reasons=tuple(reasons),
    )


def _auth_report(
    *,
    runner: CommandRunner,
    gh_available: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    if not gh_available:
        return (
            {"status": "unavailable"},
            _check("gh-auth", "WARN", "gh authentication status unavailable"),
        )

    result = runner(["gh", "auth", "status", "--hostname", "github.com"], None)
    if _successful(result):
        auth_status = "authenticated"
        status: Status = "PASS"
        message = "gh authentication detected"
    else:
        output = f"{result.stdout}\n{result.stderr}".casefold()
        if any(
            phrase in output
            for phrase in ("not logged in", "not authenticated", "no authentication")
        ):
            auth_status = "not_authenticated"
            message = "gh is available but not authenticated"
        else:
            auth_status = "unknown"
            message = "gh authentication status could not be determined"
        status = "WARN"

    # Deliberately omit gh's output: it can contain account or credential details.
    return (
        {"status": auth_status},
        _check("gh-auth", status, message, authentication=auth_status),
    )


def _command_output(result: CommandResult) -> str:
    return _first_nonempty_line(result.stdout)


def collect_doctor_report(
    repo_root: Path | None = None,
    *,
    runner: CommandRunner | None = None,
    which: Which | None = None,
    runtime: RuntimeInfo | None = None,
) -> dict[str, object]:
    """Collect a deterministic, read-only doctor report."""

    command_runner = runner or _run_command
    executable_lookup = which or shutil.which
    current_runtime = runtime or _runtime_info()
    candidate_root = (repo_root or Path.cwd()).resolve()
    checks: list[dict[str, object]] = []

    python_status: Status = "PASS" if current_runtime.python_supported else "FAIL"
    python_message = (
        f"Python {current_runtime.python_version} active"
        if current_runtime.python_supported
        else f"Python {current_runtime.python_version} is below 3.12"
    )
    checks.append(
        _check(
            "python",
            python_status,
            python_message,
            version=current_runtime.python_version,
            interpreter=current_runtime.interpreter,
            minimum="3.12",
        )
    )

    uv_tool, uv_check = _tool_report(
        "uv", required=True, runner=command_runner, which=executable_lookup
    )
    git_tool, git_check = _tool_report(
        "git", required=True, runner=command_runner, which=executable_lookup
    )
    gh_tool, gh_check = _tool_report(
        "gh", required=False, runner=command_runner, which=executable_lookup
    )
    codex_tool, codex_check = _tool_report(
        "codex", required=False, runner=command_runner, which=executable_lookup
    )
    checks.extend((uv_check, git_check))

    system_status: Status = "PASS" if current_runtime.system_supported else "FAIL"
    checks.append(
        _check(
            "host",
            system_status,
            f"{current_runtime.system}/{current_runtime.architecture}",
            os=current_runtime.system,
            architecture=current_runtime.architecture,
            supported_systems=sorted(SUPPORTED_SYSTEMS),
        )
    )

    root_result = command_runner(["git", "rev-parse", "--show-toplevel"], candidate_root)
    root: Path | None = None
    if _successful(root_result):
        root_text = _command_output(root_result)
        if root_text:
            root = Path(root_text).resolve()
    if root is None:
        checks.append(
            _check(
                "repository-root",
                "FAIL",
                "current directory is not a readable Git repository",
            )
        )
    else:
        checks.append(_check("repository-root", "PASS", str(root), root=str(root)))

    branch: str | None = None
    clean: bool | None = None
    head: str | None = None
    origin_identity: str | None = None
    origin_matches: bool | None = None
    tracked_remote: str | None = None
    remote_ref_available: bool | None = None
    relation: RemoteRelation = "unknown"

    if root is not None:
        branch_result = command_runner(["git", "branch", "--show-current"], root)
        branch_value = _command_output(branch_result) if _successful(branch_result) else ""
        branch = branch_value or None
        if branch is None:
            checks.append(_check("branch", "FAIL", "detached HEAD or branch unavailable"))
        elif branch == "main":
            checks.append(
                _check("branch", "FAIL", "direct work on main is forbidden", branch=branch)
            )
        else:
            checks.append(_check("branch", "PASS", branch, branch=branch))

        status_result = command_runner(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"], root
        )
        if _successful(status_result):
            clean = not bool(status_result.stdout)
            checks.append(
                _check(
                    "working-tree",
                    "PASS" if clean else "FAIL",
                    "clean" if clean else "dirty",
                    clean=clean,
                )
            )
        else:
            checks.append(_check("working-tree", "FAIL", "working-tree status unavailable"))

        head_result = command_runner(["git", "rev-parse", "--verify", "HEAD"], root)
        head_value = _command_output(head_result) if _successful(head_result) else ""
        head = head_value or None
        checks.append(
            _check(
                "head",
                "PASS" if head is not None else "FAIL",
                head or "HEAD unavailable",
                head=head,
            )
        )

        origin_result = command_runner(["git", "remote", "get-url", "origin"], root)
        origin_url = _command_output(origin_result) if _successful(origin_result) else ""
        origin_identity = _repository_identity(origin_url)
        origin_matches = (
            origin_identity.casefold() == EXPECTED_REPOSITORY.casefold()
            if origin_identity is not None
            else False
        )
        if origin_matches:
            origin_status: Status = "PASS"
            origin_message = f"origin identity {origin_identity}"
        elif origin_identity is None:
            origin_status = "FAIL"
            origin_message = "origin repository identity unavailable"
        else:
            origin_status = "FAIL"
            origin_message = f"origin identity {origin_identity} does not match expected repository"
        checks.append(
            _check(
                "origin",
                origin_status,
                origin_message,
                identity=origin_identity,
                expected=EXPECTED_REPOSITORY,
                matches=origin_matches,
            )
        )

        if branch is not None:
            tracking_result = command_runner(
                ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
                root,
            )
            tracking_value = (
                _command_output(tracking_result) if _successful(tracking_result) else ""
            )
            tracked_remote = tracking_value or None
        expected_remote = f"origin/{branch}" if branch else None
        tracking_matches = (
            tracked_remote == expected_remote
            if tracked_remote is not None and expected_remote is not None
            else None
        )
        if tracking_matches is True:
            tracking_status: Status = "PASS"
            tracking_message = f"tracks {tracked_remote}"
        elif tracking_matches is False:
            tracking_status = "FAIL"
            tracking_message = f"tracks {tracked_remote}; expected {expected_remote}"
        else:
            tracking_status = "WARN"
            tracking_message = "no verifiable upstream branch"
        checks.append(
            _check(
                "tracking",
                tracking_status,
                tracking_message,
                expected=expected_remote,
                actual=tracked_remote,
                matches=tracking_matches,
            )
        )

        comparison_remote = tracked_remote or expected_remote
        if _valid_remote_name(comparison_remote):
            remote_ref_result = command_runner(
                [
                    "git",
                    "show-ref",
                    "--verify",
                    "--quiet",
                    f"refs/remotes/{comparison_remote}",
                ],
                root,
            )
            if remote_ref_result.returncode == 0:
                remote_ref_available = True
            elif remote_ref_result.returncode is not None:
                remote_ref_available = False
            else:
                remote_ref_available = None
            if remote_ref_available:
                relation_result = command_runner(
                    ["git", "rev-list", "--left-right", "--count", f"HEAD...{comparison_remote}"],
                    root,
                )
                relation = _parse_relation(relation_result)
        relation_status: Status = "PASS" if relation == "synchronized" else "WARN"
        relation_message = relation
        if relation in {"ahead", "behind", "diverged"}:
            relation_status = "FAIL"
        checks.append(
            _check(
                "remote-relation",
                relation_status,
                relation_message,
                relation=relation,
                remote=comparison_remote,
                remote_ref_available=remote_ref_available,
            )
        )
    else:
        checks.extend(
            (
                _check("branch", "FAIL", "branch unavailable because repository root is unknown"),
                _check("working-tree", "FAIL", "working-tree status unavailable"),
                _check("head", "FAIL", "HEAD unavailable"),
                _check("origin", "FAIL", "origin unavailable because repository root is unknown"),
                _check("tracking", "WARN", "tracking state unavailable"),
                _check("remote-relation", "WARN", "local-vs-remote relation unknown"),
            )
        )

    handoff = evaluate_handoff_state(
        branch=branch,
        clean=clean,
        origin_matches=origin_matches,
        tracked_remote=tracked_remote,
        relation=relation,
        remote_ref_available=remote_ref_available,
    )
    checks.append(
        _check(
            "handoff",
            handoff.status,
            "safe" if handoff.safe else "; ".join(handoff.reasons),
            safe=handoff.safe,
            relation=handoff.relation,
        )
    )

    checks.append(gh_check)
    gh_auth, gh_auth_check = _auth_report(
        runner=command_runner,
        gh_available=bool(gh_tool["available"]),
    )
    checks.append(gh_auth_check)
    checks.append(codex_check)

    tools = {
        "uv": uv_tool,
        "git": git_tool,
        "gh": {**gh_tool, "auth": gh_auth},
        "codex": codex_tool,
    }
    repository = {
        "root": str(root) if root is not None else None,
        "branch": branch,
        "head": head,
        "clean": clean,
        "origin": {
            "identity": origin_identity,
            "expected": EXPECTED_REPOSITORY,
            "matches": origin_matches,
        },
        "tracking": {
            "expected": f"origin/{branch}" if branch else None,
            "actual": tracked_remote,
            "matches": (
                tracked_remote == f"origin/{branch}"
                if branch is not None and tracked_remote is not None
                else None
            ),
        },
        "remote_relation": relation,
        "remote_ref_available": remote_ref_available,
    }
    environment = {
        "python": {
            "version": current_runtime.python_version,
            "interpreter": current_runtime.interpreter,
            "supported": current_runtime.python_supported,
        },
        "os": current_runtime.system,
        "architecture": current_runtime.architecture,
        "supported_host": current_runtime.system_supported,
    }

    statuses = [check["status"] for check in checks]
    overall: Status = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    return {
        "tool": "projectctl",
        "command": "doctor",
        "overall": overall,
        "environment": environment,
        "tools": tools,
        "repository": repository,
        "handoff": handoff.as_dict(),
        "checks": checks,
    }


def render_human_report(report: dict[str, object]) -> str:
    """Render the stable, concise human-readable form of a doctor report."""

    lines = [f"projectctl doctor: {report['overall']}"]
    for check in report["checks"]:
        assert isinstance(check, dict)
        lines.append(f"{check['status']} {check['name']}: {check['message']}")
    return "\n".join(lines)


def render_json_report(report: dict[str, object]) -> str:
    return json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2)


@app.callback()
def root(
    version: bool = typer.Option(False, "--version", help="Show projectctl version and exit."),
) -> None:
    """Run read-only project-control commands."""

    if version:
        typer.echo(f"projectctl {__version__}")
        raise typer.Exit()


@app.command()
def doctor(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of human output."),
    ] = False,
    output_format: Annotated[
        Literal["human", "json"],
        typer.Option("--format", help="Output format: human or json."),
    ] = "human",
    repo_root: Annotated[
        Path | None,
        typer.Option("--repo-root", help="Repository directory to inspect (defaults to cwd)."),
    ] = None,
) -> None:
    """Check workstation, repository, and read-only cross-device handoff readiness."""

    report = collect_doctor_report(repo_root)
    if json_output or output_format == "json":
        typer.echo(render_json_report(report))
    else:
        typer.echo(render_human_report(report))
    if report["overall"] == "FAIL":
        raise typer.Exit(code=1)


def main() -> None:
    app()


__all__ = [
    "CommandResult",
    "HandoffAssessment",
    "RuntimeInfo",
    "app",
    "collect_doctor_report",
    "evaluate_handoff_state",
    "main",
    "render_human_report",
    "render_json_report",
]
