import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from fh_agent.evals.controlled_live_smoke_validator import ControlledLiveSmokeValidationReport
from fh_agent.evals.live_audit_pipeline import LiveAuditPipelineResult
from fh_agent.evals.live_run_manifest import ManifestMode
from fh_agent.evals.live_run_preflight import LiveRunPreflightResult

REVIEW_SUMMARY_VERSION = "1"
PASSED_NEXT_STEP = (
    "Review architecture before enabling any input; next technical step may be "
    "wait-only/no-op action logging or longer observation-only smoke."
)

ReviewConclusion = Literal["passed", "failed"]


class ControlledLiveSmokeReviewArtifactPaths(BaseModel):
    """Artifact paths used to build the controlled smoke review summary."""

    model_config = ConfigDict(extra="forbid")

    preflight_report: Path
    live_audit_pipeline: Path
    live_smoke_report: Path
    live_smoke_report_validation: Path
    review_summary: Path


class ControlledLiveSmokeReviewSummary(BaseModel):
    """Compact handoff summary for an observation-only controlled smoke run."""

    model_config = ConfigDict(extra="forbid")

    review_summary_version: str = REVIEW_SUMMARY_VERSION
    created_at: datetime
    run_id: str
    mode: ManifestMode
    runtime_mode: str
    preflight_ok: bool
    validator_passed: bool
    validation_error_count: int
    captured_frame_count: int
    screenshot_count: int
    evidence_count: int
    actions_requested: int
    no_input_sent: bool
    stop_reason: str
    forbidden_runtime_markers_absent: bool
    hidden_state_fields_absent: bool
    planner_active: bool
    manager_active: bool
    body_active: bool
    learning_active: bool
    artifact_paths: ControlledLiveSmokeReviewArtifactPaths
    conclusion: ReviewConclusion
    recommended_next_step: str
    failure_reasons: tuple[str, ...] = ()

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def create_controlled_live_smoke_review_summary(
    *,
    run_dir: Path,
    created_at: datetime | None = None,
) -> ControlledLiveSmokeReviewSummary:
    paths = _default_artifact_paths(run_dir)
    preflight = _read_model(paths.preflight_report, LiveRunPreflightResult)
    pipeline = _read_model(paths.live_audit_pipeline, LiveAuditPipelineResult)
    smoke_report = _read_json_object(paths.live_smoke_report)
    validation = _read_model(
        paths.live_smoke_report_validation,
        ControlledLiveSmokeValidationReport,
    )

    forbidden_markers_absent = _validation_check_passed(
        validation,
        "forbidden_runtime_markers_absent",
    )
    hidden_fields_absent = _validation_check_passed(validation, "hidden_state_fields_absent")
    status = _object_value(smoke_report, "status")
    screenshot_count = len(_list_value(smoke_report, "screenshot_paths"))
    evidence_count = len(_list_value(smoke_report, "evidence_ids"))
    runtime_mode = str(smoke_report.get("runtime_mode", ""))
    captured_frame_count = _int_value(smoke_report, "captured_frame_count")
    actions_requested = _int_value(status, "actions_requested")
    no_input_sent = smoke_report.get("no_input_sent") is True
    failure_reasons = _failure_reasons(
        preflight_ok=preflight.ok,
        validator_passed=validation.status.passed,
        no_input_sent=no_input_sent,
        runtime_mode=runtime_mode,
        captured_frame_count=captured_frame_count,
        screenshot_count=screenshot_count,
        actions_requested=actions_requested,
        forbidden_markers_absent=forbidden_markers_absent,
        hidden_fields_absent=hidden_fields_absent,
    )
    conclusion: ReviewConclusion = "passed" if not failure_reasons else "failed"

    return ControlledLiveSmokeReviewSummary(
        created_at=created_at or datetime.now(UTC),
        run_id=str(smoke_report.get("run_id") or pipeline.run_id),
        mode=_mode_value(smoke_report, pipeline.mode),
        runtime_mode=runtime_mode,
        preflight_ok=preflight.ok,
        validator_passed=validation.status.passed,
        validation_error_count=validation.status.error_count,
        captured_frame_count=captured_frame_count,
        screenshot_count=screenshot_count,
        evidence_count=evidence_count,
        actions_requested=actions_requested,
        no_input_sent=no_input_sent,
        stop_reason=str(status.get("stop_reason", "")),
        forbidden_runtime_markers_absent=forbidden_markers_absent,
        hidden_state_fields_absent=hidden_fields_absent,
        planner_active=smoke_report.get("autonomous_planner_active") is True,
        manager_active=smoke_report.get("manager_orchestration_active") is True,
        body_active=smoke_report.get("body_control_active") is True,
        learning_active=smoke_report.get("learning_active") is True,
        artifact_paths=paths,
        conclusion=conclusion,
        recommended_next_step=(
            PASSED_NEXT_STEP
            if conclusion == "passed"
            else f"Fix failed review checks: {'; '.join(failure_reasons)}"
        ),
        failure_reasons=tuple(failure_reasons),
    )


def write_controlled_live_smoke_review_summary(
    summary: ControlledLiveSmokeReviewSummary,
    *,
    overwrite: bool = False,
) -> Path:
    path = summary.artifact_paths.review_summary
    if path.exists() and not overwrite:
        msg = f"controlled live-smoke review summary already exists: {path}"
        raise FileExistsError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary.to_deterministic_json() + "\n", encoding="utf-8")
    return path


def _default_artifact_paths(run_dir: Path) -> ControlledLiveSmokeReviewArtifactPaths:
    reports_dir = run_dir / "reports"
    return ControlledLiveSmokeReviewArtifactPaths(
        preflight_report=reports_dir / "preflight_report.json",
        live_audit_pipeline=reports_dir / "live_audit_pipeline.json",
        live_smoke_report=reports_dir / "live_smoke_report.json",
        live_smoke_report_validation=reports_dir / "live_smoke_report_validation.json",
        review_summary=reports_dir / "controlled_live_smoke_review.json",
    )


def _read_model(path: Path, model_type):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return model_type.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid controlled smoke review artifact: {path}: {exc}"
        raise ValueError(msg) from exc


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"invalid controlled smoke review artifact: {path}: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"invalid controlled smoke review artifact: {path}: expected object"
        raise ValueError(msg)
    return payload


def _object_value(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_value(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) else 0


def _mode_value(payload: dict[str, object], fallback: ManifestMode) -> ManifestMode:
    value = payload.get("mode")
    if value in ("official_screen_only", "debug_visible_bridge", "dry_run"):
        return value
    return fallback


def _validation_check_passed(
    validation: ControlledLiveSmokeValidationReport,
    name: str,
) -> bool:
    return any(check.name == name and check.passed for check in validation.checks)


def _failure_reasons(
    *,
    preflight_ok: bool,
    validator_passed: bool,
    no_input_sent: bool,
    runtime_mode: str,
    captured_frame_count: int,
    screenshot_count: int,
    actions_requested: int,
    forbidden_markers_absent: bool,
    hidden_fields_absent: bool,
) -> list[str]:
    reasons: list[str] = []
    if not preflight_ok:
        reasons.append("preflight did not pass")
    if not validator_passed:
        reasons.append("validator did not pass")
    if not no_input_sent:
        reasons.append("report does not confirm no_input_sent=true")
    if runtime_mode != "observation_only":
        reasons.append("runtime_mode is not observation_only")
    if captured_frame_count < 1:
        reasons.append("captured_frame_count is below 1")
    if screenshot_count != captured_frame_count:
        reasons.append("screenshot_count does not match captured_frame_count")
    if actions_requested != 0:
        reasons.append("actions_requested is not zero")
    if not forbidden_markers_absent:
        reasons.append("forbidden runtime marker check failed")
    if not hidden_fields_absent:
        reasons.append("hidden-state field check failed")
    return reasons
