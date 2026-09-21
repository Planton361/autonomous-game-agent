"""Safe local orchestration for the private Research Wiki projectors."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .private_projection import (
    OWNED_ROOT as TECHNICAL_ROOT,
)
from .private_projection import (
    ProjectionError,
    inspect_owned,
    no_symlink_boundary,
    source_state,
    validate_private_vault,
)
from .private_projection import (
    project as technical_project,
)
from .private_views import (
    OWNED_ROOT as DERIVED_ROOT,
)
from .private_views import (
    SOURCE_PATHS as VIEW_SOURCE_PATHS,
)
from .private_views import (
    git as views_git,
)
from .private_views import (
    project as views_project,
)

PRIVATE_VAULT_ENV = "PRIVATE_VAULT"
DEFAULT_RESTORE_DIRECTORY = ".research-wiki-restore-points"
RESTORED_ROOTS = (
    TECHNICAL_ROOT,
    DERIVED_ROOT,
)
EXPECTED_ORIGIN_URLS = frozenset(
    {
        "https://github.com/Planton361/autonomous-game-agent",
        "git@github.com:Planton361/autonomous-game-agent",
        "ssh://git@github.com/Planton361/autonomous-game-agent",
    }
)


class WorkspaceError(ValueError):
    """Expected workspace orchestration failure."""


@dataclass(frozen=True)
class WorkspaceContext:
    repo_root: Path
    vault_root: Path
    source_commit: str


@dataclass(frozen=True)
class WorkspaceResult:
    source_commit: str
    stages: tuple[str, ...]
    restore_point: Path | None = None


def _origin_url(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "config", "--get", "remote.origin.url"],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        raise WorkspaceError("Expected repository origin is not configured")
    return result.stdout.strip().removesuffix(".git").rstrip("/")


def _validate_repository(repo_root: Path) -> tuple[Path, str]:
    repo = repo_root.expanduser().resolve()
    if not repo.is_dir():
        raise WorkspaceError("Repository root must be an existing directory")
    if _origin_url(repo) not in EXPECTED_ORIGIN_URLS:
        raise WorkspaceError("Repository origin must identify Planton361/autonomous-game-agent")
    try:
        source_commit = source_state(repo, "HEAD")
    except ProjectionError as exc:
        raise WorkspaceError(f"Repository checkout is not supported: {exc}") from exc
    try:
        dirty_views = views_git(
            repo,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            *VIEW_SOURCE_PATHS,
        )
    except ProjectionError as exc:
        raise WorkspaceError(f"Repository checkout is not supported: {exc}") from exc
    if dirty_views:
        raise WorkspaceError(
            "Repository checkout is not supported: direct-view sources are dirty; "
            "commit or resolve source changes first"
        )
    return repo, source_commit


def resolve_vault_root(vault_root: Path | None, *, environ: dict[str, str] | None = None) -> Path:
    """Resolve an explicit vault or the established local-only environment setting."""
    if vault_root is None:
        environment = os.environ if environ is None else environ
        value = environment.get(PRIVATE_VAULT_ENV)
        if not value:
            raise WorkspaceError("Provide --vault-root or set PRIVATE_VAULT")
        vault_root = Path(value)
    return vault_root.expanduser()


def resolve_context(repo_root: Path, vault_root: Path | None) -> WorkspaceContext:
    repo, source_commit = _validate_repository(repo_root)
    vault_input = resolve_vault_root(vault_root)
    try:
        vault = validate_private_vault(vault_input, repo)
    except ProjectionError as exc:
        raise WorkspaceError(f"Private vault validation failed: {exc}") from exc
    return WorkspaceContext(repo, vault, source_commit)


def _restore_root(context: WorkspaceContext, restore_root: Path | None) -> Path:
    candidate = (
        restore_root.expanduser()
        if restore_root is not None
        else context.vault_root.parent / DEFAULT_RESTORE_DIRECTORY
    )
    candidate = candidate.absolute()
    try:
        no_symlink_boundary(candidate)
    except ProjectionError as exc:
        raise WorkspaceError(f"Restore-point location is unsafe: {exc}") from exc
    resolved = candidate.resolve()
    if resolved.is_relative_to(context.vault_root):
        raise WorkspaceError("Restore-point location must be outside the active vault")
    if resolved.is_relative_to(context.repo_root):
        raise WorkspaceError("Restore-point location must be outside the repository")
    return resolved


def _restore_point_name(source_commit: str, timestamp: datetime) -> str:
    return "workspace-" + timestamp.strftime("%Y%m%dT%H%M%S.%fZ") + "-" + source_commit[:12]


def create_restore_point(
    context: WorkspaceContext,
    restore_root: Path | None = None,
    *,
    now: datetime | None = None,
) -> Path:
    """Copy only pre-apply generated roots into a never-overwritten local restore point."""
    destination_root = _restore_root(context, restore_root)
    try:
        destination_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError("Cannot create restore-point directory") from exc
    timestamp = now or datetime.now(UTC)
    base_name = _restore_point_name(context.source_commit, timestamp)
    for suffix in range(1000):
        name = base_name if suffix == 0 else f"{base_name}-{suffix:02d}"
        point = destination_root / name
        try:
            point.mkdir()
        except FileExistsError:
            continue
        except OSError as exc:
            raise WorkspaceError("Cannot create restore point") from exc
        break
    else:
        raise WorkspaceError("Cannot allocate a unique restore-point location")

    present_roots: list[str] = []
    try:
        for relative in RESTORED_ROOTS:
            source = context.vault_root / relative
            inspect_owned(source)
            if source.exists():
                shutil.copytree(source, point / relative, copy_function=shutil.copy2)
                present_roots.append(str(relative))
        (point / "restore-point.json").write_text(
            json.dumps(
                {
                    "restore_point_schema_version": "1.0",
                    "source_commit": context.source_commit,
                    "generated_roots_present": present_roots,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except (OSError, ProjectionError) as exc:
        raise WorkspaceError(f"Restore-point copy failed at {point}") from exc
    return point


def _run_projector(
    stage: str,
    projector: Callable[..., object],
    context: WorkspaceContext,
    *,
    check: bool,
    restore_point: Path | None,
) -> None:
    try:
        projector(context.repo_root, context.vault_root, context.source_commit, check=check)
    except (OSError, UnicodeError, ProjectionError) as exc:
        message = f"{stage} failed: {exc}"
        if restore_point is not None:
            message += f"; restore point: {restore_point}"
        raise WorkspaceError(message) from exc


def apply(
    repo_root: Path,
    vault_root: Path | None = None,
    restore_root: Path | None = None,
) -> WorkspaceResult:
    """Create a restore point, then apply both projections and both zero-write checks."""
    context = resolve_context(repo_root, vault_root)
    restore_point = create_restore_point(context, restore_root)
    _run_projector(
        "technical projection",
        technical_project,
        context,
        check=False,
        restore_point=restore_point,
    )
    _run_projector("direct views", views_project, context, check=False, restore_point=restore_point)
    _run_projector(
        "technical projection check",
        technical_project,
        context,
        check=True,
        restore_point=restore_point,
    )
    _run_projector(
        "direct views check", views_project, context, check=True, restore_point=restore_point
    )
    return WorkspaceResult(
        context.source_commit,
        (
            "restore point",
            "technical projection",
            "direct views",
            "technical projection check",
            "direct views check",
        ),
        restore_point,
    )


def check(repo_root: Path, vault_root: Path | None = None) -> WorkspaceResult:
    """Run both existing projector checks without creating any local workspace artifacts."""
    context = resolve_context(repo_root, vault_root)
    _run_projector(
        "technical projection check", technical_project, context, check=True, restore_point=None
    )
    _run_projector("direct views check", views_project, context, check=True, restore_point=None)
    return WorkspaceResult(
        context.source_commit,
        ("technical projection check", "direct views check"),
    )
