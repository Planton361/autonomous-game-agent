import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from fh_agent.evals.live_run_preflight import LiveRunPreflightResult

ManifestMode = Literal[
    "screen-only",
    "bridge-assisted",
    "debug",
    "networked-api-exploratory",
    "contaminated",
]
ExecutionMode = Literal["live", "dry-run"]
LegacyManifestMode = Literal["official_screen_only", "debug_visible_bridge", "dry_run"]

MANIFEST_VERSION = "2"
LEGACY_MANIFEST_VERSION = "1"
LEGACY_MANIFEST_STATUS = "legacy-v1-unmigrated"
OFFICIAL_RESEARCH_MODES: tuple[ManifestMode, ...] = ("screen-only", "bridge-assisted")

ALLOWED_BRIDGE_FIELDS: tuple[str, ...] = (
    "message_window_visible",
    "visible_message_text",
    "menu_open",
    "visible_menu_items",
    "combat_ui_visible",
    "death_screen_visible",
    "player_screen_position",
    "visible_sprite_screen_positions",
    "visible_sprite_visual_hashes",
    "screenshot_id",
)

FORBIDDEN_BRIDGE_FIELDS: tuple[str, ...] = (
    "map_id",
    "event_id",
    "event_name",
    "event_comments",
    "event_trigger_conditions",
    "game_switches",
    "game_variables",
    "enemy_database",
    "enemy_hp",
    "enemy_resistances",
    "item_database_effects",
    "ending_flags",
    "savegame_variables",
)


class LiveRunSafetyLimits(BaseModel):
    """Hard limits for a future controlled run; this module does not execute them."""

    model_config = ConfigDict(extra="forbid")

    max_duration_seconds: int = Field(default=30, gt=0, le=300)
    max_actions: int = Field(default=25, ge=0, le=500)
    max_frames: int = Field(default=120, ge=0, le=3000)
    require_focused_window: bool = True
    require_emergency_stop: bool = True
    allow_real_input: bool = False


class LiveRunPaths(BaseModel):
    """Durable locations planned for a future controlled run."""

    model_config = ConfigDict(extra="forbid")

    run_dir: Path
    events_jsonl: Path
    screenshots_dir: Path
    reports_dir: Path
    manifest_path: Path


class FixedResolutionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int
    height: int


class PreflightSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    run_id: str | None
    failed_checks: tuple[str, ...] = ()
    error_checks: tuple[str, ...] = ()


class RepoMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch: str | None = None
    commit: str | None = None
    dirty: bool | None = None


class NoSpoilerPolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    official_runs_must_not_use_hidden_state: bool = True
    game_specific_claims_require_evidence_ids: bool = True
    allowed_evidence_sources: tuple[str, ...] = (
        "screenshots",
        "visible_text",
        "sanitized_bridge_observations",
        "observed_outcomes",
    )
    forbidden_hidden_state_fields: tuple[str, ...] = FORBIDDEN_BRIDGE_FIELDS


class LiveRunManifest(BaseModel):
    """Current v2 audit manifest with research and execution modes kept separate."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["2"] = MANIFEST_VERSION
    run_id: str
    created_at: datetime
    mode: ManifestMode
    execution_mode: ExecutionMode = "live"
    preflight_summary: PreflightSummary
    official_run_allowed: bool
    safety_limits: LiveRunSafetyLimits
    expected_window_title: str | None = None
    expected_resolution: FixedResolutionSnapshot | None = None
    allowed_bridge_fields: tuple[str, ...] = ALLOWED_BRIDGE_FIELDS
    forbidden_bridge_fields: tuple[str, ...] = FORBIDDEN_BRIDGE_FIELDS
    paths: LiveRunPaths
    repo_metadata: RepoMetadata | None = None
    no_spoiler_policy: NoSpoilerPolicySnapshot = Field(default_factory=NoSpoilerPolicySnapshot)

    @model_validator(mode="after")
    def enforce_mode_policy(self) -> "LiveRunManifest":
        if self.official_run_allowed and (
            self.execution_mode != "live" or self.mode not in OFFICIAL_RESEARCH_MODES
        ):
            msg = (
                "official_run_allowed requires live execution mode and an existing canonical "
                "official research cohort"
            )
            raise ValueError(msg)
        return self

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class LegacyLiveRunManifest(BaseModel):
    """Readable v1 manifest retained without silently converting its legacy run mode."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["1"] = LEGACY_MANIFEST_VERSION
    legacy_status: Literal["legacy-v1-unmigrated"] = LEGACY_MANIFEST_STATUS
    run_id: str
    created_at: datetime
    mode: LegacyManifestMode
    preflight_summary: PreflightSummary
    official_run_allowed: bool
    safety_limits: LiveRunSafetyLimits
    expected_window_title: str | None = None
    expected_resolution: FixedResolutionSnapshot | None = None
    allowed_bridge_fields: tuple[str, ...] = ALLOWED_BRIDGE_FIELDS
    forbidden_bridge_fields: tuple[str, ...] = FORBIDDEN_BRIDGE_FIELDS
    paths: LiveRunPaths
    repo_metadata: RepoMetadata | None = None
    no_spoiler_policy: NoSpoilerPolicySnapshot = Field(default_factory=NoSpoilerPolicySnapshot)


LiveRunManifestArtifact = LiveRunManifest | LegacyLiveRunManifest


def create_live_run_manifest(
    *,
    run_id: str,
    mode: ManifestMode,
    preflight_result: LiveRunPreflightResult,
    execution_mode: ExecutionMode = "live",
    runs_dir: Path = Path("runs"),
    screenshots_dir: Path = Path("screenshots"),
    reports_dir: Path | None = None,
    manifest_path: Path | None = None,
    safety_limits: LiveRunSafetyLimits | None = None,
    expected_window_title: str | None = None,
    expected_resolution: FixedResolutionSnapshot | None = None,
    created_at: datetime | None = None,
    repo_metadata: RepoMetadata | None = None,
) -> LiveRunManifest:
    """Create a current manifest without starting any live runtime."""

    if not run_id:
        msg = "run_id must not be empty"
        raise ValueError(msg)

    run_dir = runs_dir / run_id
    resolved_reports_dir = reports_dir or run_dir / "reports"
    resolved_manifest_path = manifest_path or resolved_reports_dir / "live_run_manifest.json"
    paths = LiveRunPaths(
        run_dir=run_dir,
        events_jsonl=run_dir / "events.jsonl",
        screenshots_dir=screenshots_dir / run_id,
        reports_dir=resolved_reports_dir,
        manifest_path=resolved_manifest_path,
    )
    summary = _preflight_summary(preflight_result)
    official_run_allowed = _official_run_allowed(
        mode=mode,
        execution_mode=execution_mode,
        preflight_summary=summary,
    )

    return LiveRunManifest(
        run_id=run_id,
        created_at=created_at or datetime.now(UTC),
        mode=mode,
        execution_mode=execution_mode,
        preflight_summary=summary,
        official_run_allowed=official_run_allowed,
        safety_limits=safety_limits or LiveRunSafetyLimits(),
        expected_window_title=expected_window_title,
        expected_resolution=expected_resolution,
        paths=paths,
        repo_metadata=repo_metadata if repo_metadata is not None else collect_repo_metadata(),
    )


def write_live_run_manifest(manifest: LiveRunManifest, *, overwrite: bool = False) -> Path:
    """Persist a current manifest JSON, refusing to clobber existing files by default."""

    manifest_path = manifest.paths.manifest_path
    if manifest_path.exists() and not overwrite:
        msg = f"manifest already exists: {manifest_path}"
        raise FileExistsError(msg)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.to_deterministic_json() + "\n", encoding="utf-8")
    return manifest_path


def read_preflight_report(path: Path) -> LiveRunPreflightResult:
    """Load a preflight JSON report produced by the live-preflight command."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return LiveRunPreflightResult.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid preflight report: {path}: {exc}"
        raise ValueError(msg) from exc


def collect_repo_metadata(repo_dir: Path | None = None) -> RepoMetadata | None:
    """Best-effort Git metadata for auditability."""

    repo_path = repo_dir or Path.cwd()
    branch = _git_value(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _git_value(repo_path, "rev-parse", "HEAD")
    dirty_status = _git_value(repo_path, "status", "--short")
    if branch is None and commit is None and dirty_status is None:
        return None
    return RepoMetadata(
        branch=branch,
        commit=commit,
        dirty=bool(dirty_status) if dirty_status is not None else None,
    )


def _preflight_summary(preflight_result: LiveRunPreflightResult) -> PreflightSummary:
    failed_checks = tuple(check.name for check in preflight_result.checks if not check.passed)
    error_checks = tuple(
        check.name
        for check in preflight_result.checks
        if not check.passed and check.severity == "error"
    )
    return PreflightSummary(
        ok=preflight_result.ok,
        run_id=preflight_result.run_id,
        failed_checks=failed_checks,
        error_checks=error_checks,
    )


def _official_run_allowed(
    *,
    mode: ManifestMode,
    execution_mode: ExecutionMode,
    preflight_summary: PreflightSummary,
) -> bool:
    return (
        execution_mode == "live"
        and mode in OFFICIAL_RESEARCH_MODES
        and preflight_summary.ok
    )


def _git_value(repo_dir: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ("git", *args),
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()
