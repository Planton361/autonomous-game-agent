import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from fh_agent.evals.live_run_manifest import (
    LiveRunManifest,
    LiveRunSafetyLimits,
    ManifestMode,
    NoSpoilerPolicySnapshot,
)

PLAN_VERSION = "1"

StopConditionName = Literal[
    "max_duration",
    "max_actions",
    "max_frames",
    "focus_lost",
    "emergency_stop",
    "hidden_state_violation",
    "preflight_not_allowed",
    "manifest_not_allowed",
    "runtime_error",
]


class LiveSmokeStopCondition(BaseModel):
    """A planned stop condition for a future smoke run; this module does not enforce it."""

    model_config = ConfigDict(extra="forbid")

    name: StopConditionName
    threshold: int | bool | None = None
    message: str


class LiveSmokeExpectedOutputs(BaseModel):
    """Output paths expected from a future controlled smoke run."""

    model_config = ConfigDict(extra="forbid")

    events_jsonl: Path
    screenshots_dir: Path
    reports_dir: Path
    final_report_path: Path
    smoke_plan_path: Path


class LiveSmokeRunPlan(BaseModel):
    """Dry audit plan for a future live smoke run, never an executable runner."""

    model_config = ConfigDict(extra="forbid")

    plan_version: str = PLAN_VERSION
    run_id: str
    created_at: datetime
    source_manifest_path: Path
    source_preflight_path: Path | None = None
    execution_enabled: bool = False
    official_run_allowed: bool
    mode: ManifestMode
    safety_limits: LiveRunSafetyLimits
    stop_conditions: tuple[LiveSmokeStopCondition, ...]
    expected_outputs: LiveSmokeExpectedOutputs
    no_spoiler_policy_snapshot: NoSpoilerPolicySnapshot
    validation_errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def execution_must_stay_disabled(self) -> "LiveSmokeRunPlan":
        if self.execution_enabled:
            msg = "live smoke plans must never enable execution"
            raise ValueError(msg)
        return self

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def create_live_smoke_plan(
    *,
    manifest: LiveRunManifest,
    source_manifest_path: Path,
    source_preflight_path: Path | None = None,
    smoke_plan_path: Path | None = None,
    final_report_path: Path | None = None,
    created_at: datetime | None = None,
) -> LiveSmokeRunPlan:
    """Create a dry smoke-run plan from an already-written live-run manifest."""

    plan_path = smoke_plan_path or manifest.paths.reports_dir / "live_smoke_plan.json"
    report_path = final_report_path or manifest.paths.reports_dir / "live_smoke_report.json"
    validation_errors = _validation_errors_for_manifest(manifest)
    official_run_allowed = manifest.official_run_allowed and not validation_errors

    return LiveSmokeRunPlan(
        run_id=manifest.run_id,
        created_at=created_at or datetime.now(UTC),
        source_manifest_path=source_manifest_path,
        source_preflight_path=source_preflight_path,
        official_run_allowed=official_run_allowed,
        mode=manifest.mode,
        safety_limits=manifest.safety_limits,
        stop_conditions=_stop_conditions_from_limits(manifest.safety_limits),
        expected_outputs=LiveSmokeExpectedOutputs(
            events_jsonl=manifest.paths.events_jsonl,
            screenshots_dir=manifest.paths.screenshots_dir,
            reports_dir=manifest.paths.reports_dir,
            final_report_path=report_path,
            smoke_plan_path=plan_path,
        ),
        no_spoiler_policy_snapshot=manifest.no_spoiler_policy,
        validation_errors=tuple(validation_errors),
    )


def write_live_smoke_plan(plan: LiveSmokeRunPlan, *, overwrite: bool = False) -> Path:
    """Persist the dry smoke plan JSON, refusing to clobber by default."""

    plan_path = plan.expected_outputs.smoke_plan_path
    if plan_path.exists() and not overwrite:
        msg = f"smoke plan already exists: {plan_path}"
        raise FileExistsError(msg)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(plan.to_deterministic_json() + "\n", encoding="utf-8")
    return plan_path


def read_live_run_manifest(path: Path) -> LiveRunManifest:
    """Load and validate a LiveRunManifest JSON file."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return LiveRunManifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid live-run manifest: {path}: {exc}"
        raise ValueError(msg) from exc


def _stop_conditions_from_limits(
    safety_limits: LiveRunSafetyLimits,
) -> tuple[LiveSmokeStopCondition, ...]:
    return (
        LiveSmokeStopCondition(
            name="max_duration",
            threshold=safety_limits.max_duration_seconds,
            message="stop when max duration is reached",
        ),
        LiveSmokeStopCondition(
            name="max_actions",
            threshold=safety_limits.max_actions,
            message="stop when max action count is reached",
        ),
        LiveSmokeStopCondition(
            name="max_frames",
            threshold=safety_limits.max_frames,
            message="stop when max frame count is reached",
        ),
        LiveSmokeStopCondition(
            name="focus_lost",
            threshold=safety_limits.require_focused_window,
            message="stop if the target window focus is lost",
        ),
        LiveSmokeStopCondition(
            name="emergency_stop",
            threshold=safety_limits.require_emergency_stop,
            message="stop if emergency stop is requested",
        ),
        LiveSmokeStopCondition(
            name="hidden_state_violation",
            threshold=True,
            message="stop if any hidden-state field is observed",
        ),
        LiveSmokeStopCondition(
            name="preflight_not_allowed",
            threshold=True,
            message="stop if preflight status does not allow a controlled run",
        ),
        LiveSmokeStopCondition(
            name="manifest_not_allowed",
            threshold=True,
            message="stop if manifest status does not allow an official run",
        ),
        LiveSmokeStopCondition(
            name="runtime_error",
            threshold=True,
            message="stop on any future runtime error",
        ),
    )


def _validation_errors_for_manifest(manifest: LiveRunManifest) -> list[str]:
    errors: list[str] = []
    if manifest.preflight_summary.ok is False:
        errors.append("preflight_not_allowed")
    if manifest.official_run_allowed is False:
        errors.append("manifest_not_allowed")
    if manifest.safety_limits.allow_real_input:
        errors.append("allow_real_input_must_be_false_for_dry_plan")
    return errors
