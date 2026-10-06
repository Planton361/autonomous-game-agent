"""Safe local orchestration for the private Research Wiki projectors."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import product_migration
from .preferred_paths import HOME, INTERNAL, PRODUCT
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
from .private_views import (
    OWNED_ROOT as DERIVED_ROOT,
)
from .private_views import (
    SOURCE_PATHS as VIEW_SOURCE_PATHS,
)
from .private_views import (
    git as views_git,
)

PRIVATE_VAULT_ENV = "PRIVATE_VAULT"
DEFAULT_RESTORE_DIRECTORY = ".research-wiki-restore-points"
RESTORED_ROOTS = (
    TECHNICAL_ROOT,
    DERIVED_ROOT,
    PRODUCT,
    INTERNAL,
    HOME,
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
            no_symlink_boundary(source)
            if relative != HOME:
                inspect_owned(source)
            if source.exists():
                if relative == HOME:
                    shutil.copy2(source, point / relative)
                else:
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


def apply(
    repo_root: Path,
    vault_root: Path | None = None,
    restore_root: Path | None = None,
) -> WorkspaceResult:
    """Preflight the complete old/new inventory before restore point or mutation."""
    context = resolve_context(repo_root, vault_root)
    try:
        tree, actual = product_migration.preflight(
            context.repo_root, context.vault_root, context.source_commit
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkspaceError(f"Research Map preflight failed: {exc}") from exc
    restore_point = create_restore_point(context, restore_root)
    # External receipts support explicit recovery without adopting interrupted output.
    plan = {
        "source_commit": context.source_commit,
        "before": {
            str(p): product_migration.digest((context.vault_root / p).read_bytes()) for p in actual
        },
        "after": {str(p): product_migration.digest(data) for p, data in tree.files.items()},
    }
    (restore_point / "migration-plan.json").write_text(json.dumps(plan, sort_keys=True) + "\n")
    try:
        product_migration.apply(context.vault_root, tree, actual)
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkspaceError(
            f"Research Map migration failed: {exc}; restore point: {restore_point}"
        ) from exc
    return WorkspaceResult(
        context.source_commit,
        (
            "global preflight",
            "restore point",
            "replacement verification",
            "legacy retirement",
            "owner manifests",
            "Research Map check",
        ),
        restore_point,
    )


def check(repo_root: Path, vault_root: Path | None = None) -> WorkspaceResult:
    """Read-only exact inventory/content check; never creates restore points."""
    context = resolve_context(repo_root, vault_root)
    try:
        tree, _ = product_migration.preflight(
            context.repo_root, context.vault_root, context.source_commit
        )
        product_migration.verify(context.vault_root, tree)
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkspaceError(f"Research Map check failed: {exc}") from exc
    return WorkspaceResult(context.source_commit, ("Research Map check",))


def recover(repo_root: Path, vault_root: Path, restore_point: Path) -> WorkspaceResult:
    """Explicit bounded recovery from an external receipt; edited output fails closed."""
    context = resolve_context(repo_root, vault_root)
    point = restore_point.absolute()
    try:
        no_symlink_boundary(point)
        if point.resolve().is_relative_to(context.vault_root) or point.resolve().is_relative_to(
            context.repo_root
        ):
            raise WorkspaceError("Recovery point must be external")
        plan = json.loads((point / "migration-plan.json").read_text())
        if (
            set(plan) != {"source_commit", "before", "after"}
            or plan["source_commit"] != context.source_commit
        ):
            raise WorkspaceError("Recovery receipt does not match exact source head")
        expected = product_migration.build(
            context.repo_root, context.vault_root, context.source_commit
        )
        expected_digests = {
            str(p): product_migration.digest(data) for p, data in expected.files.items()
        }
        if plan["after"] != expected_digests:
            raise WorkspaceError("Recovery receipt does not match current frozen inputs/output")
        snapshot_files = product_migration._actual(point.resolve())
        snapshot_owners = product_migration._legacy(point.resolve()) | product_migration._current(
            point.resolve()
        )
        if {str(p) for p in snapshot_files} != set(
            plan["before"]
        ) or snapshot_files - snapshot_owners.keys():
            raise WorkspaceError("Recovery snapshot inventory is unowned or corrupt")
        for relative in snapshot_files:
            row = snapshot_owners[relative]
            data = (point / relative).read_bytes()
            semantic_base = relative.suffix == ".base" and row.get("semantic_sha256")
            if not semantic_base and not product_migration._owner(data, relative, row["owner"]):
                raise WorkspaceError("Recovery snapshot lost owner marker")
            if semantic_base:
                intact = (
                    product_migration.views._base_semantic_digest(data) == row["semantic_sha256"]
                )
            else:
                intact = product_migration.digest(data) == row["sha256"]
            if not intact:
                raise WorkspaceError("Recovery snapshot ownership digest is corrupt")
        paths = set(plan["before"]) | set(plan["after"])
        product_migration.validate_portable_paths(paths)
        before = {Path(p): value for p, value in plan["before"].items()}
        allowed = set(product_migration._actual(context.vault_root))
        if {str(p) for p in allowed} - paths:
            raise WorkspaceError("Recovery encountered unowned output")
        for path in paths:
            relative = product_migration.PurePosixPath(path)
            if not (
                relative == HOME
                or any(relative.is_relative_to(root) for root in product_migration.ROOTS)
            ):
                raise WorkspaceError("Recovery receipt escapes generated boundaries")
            target = product_migration.target_path(context.vault_root, relative)
            if target.exists() and (
                not target.is_file()
                or product_migration.digest(target.read_bytes())
                not in {plan["before"].get(path), plan["after"].get(path)}
            ):
                raise WorkspaceError("Recovery output was edited or collided")
            if Path(path) in before:
                backup = product_migration.target_path(point.resolve(), relative)
                if (
                    not backup.is_file()
                    or product_migration.digest(backup.read_bytes()) != before[Path(path)]
                ):
                    raise WorkspaceError("Recovery snapshot is corrupt")
        # Preserve original manifests last, just as on forward migration.
        manifests = {
            TECHNICAL_ROOT / "manifest/projection.yaml",
            DERIVED_ROOT / "manifest/direct-views.yaml",
            *product_migration.MANIFESTS.values(),
        }
        for path in sorted(plan["before"]):
            relative = product_migration.PurePosixPath(path)
            if relative not in manifests:
                product_migration.atomic_write(
                    context.vault_root, relative, (point / relative).read_bytes()
                )
        for path in allowed:
            if str(path) not in plan["before"]:
                product_migration.target_path(context.vault_root, path).unlink()
        for path in sorted(plan["before"]):
            relative = product_migration.PurePosixPath(path)
            if relative in manifests:
                product_migration.atomic_write(
                    context.vault_root, relative, (point / relative).read_bytes()
                )
        restored = {
            str(p): product_migration.digest((context.vault_root / p).read_bytes())
            for p in product_migration._actual(context.vault_root)
        }
        if restored != plan["before"]:
            raise WorkspaceError("Recovery verification failed")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise WorkspaceError(f"Recovery failed closed: {exc}") from exc
    return WorkspaceResult(
        context.source_commit, ("external receipt validation", "generated recovery"), point
    )
