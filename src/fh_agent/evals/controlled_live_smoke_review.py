import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from fh_agent.evals.controlled_live_smoke_validator import (
    PRE_POST_DIMENSION_MISMATCH_MESSAGE,
    ControlledLiveSmokeValidationReport,
)
from fh_agent.evals.live_audit_pipeline import LiveAuditPipelineResult
from fh_agent.evals.live_run_manifest import ManifestMode
from fh_agent.evals.live_run_preflight import LiveRunPreflightResult

REVIEW_SUMMARY_VERSION = "1"
SINGLE_DIRECTIONAL_TAP_ACTION = "move_right_short"
PASSED_NEXT_STEP = (
    "Review architecture before enabling any input; next technical step may be "
    "wait-only/no-op action logging or longer observation-only smoke."
)
SINGLE_TAP_MECHANICAL_NEXT_STEP = (
    "Mechanical review passed; manual visual screenshot review is still required before "
    "counting the run as a full 13.4 pass."
)

ReviewConclusion = Literal["passed", "failed"]
AutomatedReviewScope = Literal["mechanical"]
VisualReviewStatus = Literal["not_required", "not_performed"]


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
    frame_count: int
    captured_frame_count: int
    min_frame_count: int | None = None
    max_frame_count: int | None = None
    screenshot_count: int
    evidence_count: int
    duration_seconds: float | None = None
    average_capture_interval_seconds: float | None = None
    action_logging_mode: str = "disabled"
    dryrun_orchestration_mode: str = "disabled"
    real_input_mode: str = "disabled"
    real_wait_only_active: bool = False
    allowed_real_primitives: tuple[str, ...] = ()
    input_attempt_count: int = 0
    allowed_input_count: int = 0
    forbidden_input_count: int = 0
    executed_wait_count: int = 0
    forbidden_executed_action_count: int = 0
    focus_guard_check_count: int = 0
    focus_guard_pre_input_pass_count: int = 0
    emergency_stop_check_count: int = 0
    emergency_stop_pre_input_clear_count: int = 0
    rate_limit_enabled: bool = False
    max_input_count: int = 0
    max_input_count_exceeded: bool = False
    capture_script: str | None = None
    official_screen_only: bool = False
    pre_input_evidence_count: int = 0
    post_input_evidence_count: int = 0
    dryrun_task_count: int = 0
    dryrun_skill_count: int = 0
    allowed_dryrun_task_count: int = 0
    forbidden_dryrun_task_count: int = 0
    allowed_dryrun_action_intent_count: int = 0
    forbidden_dryrun_action_intent_count: int = 0
    manager_dryrun_active: bool = False
    body_dryrun_active: bool = False
    actions_requested: int
    inputs_sent: int = 0
    allowed_action_intent_count: int = 0
    forbidden_action_intent_count: int = 0
    executed_action_count: int = 0
    requested_action_names: tuple[str, ...] = ()
    executed_action_names: tuple[str, ...] = ()
    input_action_counters: dict[str, int]
    no_input_sent: bool
    stop_reason: str
    forbidden_runtime_markers_absent: bool
    hidden_state_fields_absent: bool
    planner_active: bool
    manager_active: bool
    body_active: bool
    learning_active: bool
    bridge_active: bool
    ocr_active: bool = False
    hidden_state_violation_count: int = 0
    automated_review_scope: AutomatedReviewScope = "mechanical"
    visual_review_required: bool = False
    visual_review_status: VisualReviewStatus = "not_required"
    requires_manual_visual_review: bool = False
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
    min_frame_count: int | None = None,
    max_frame_count: int | None = None,
    created_at: datetime | None = None,
) -> ControlledLiveSmokeReviewSummary:
    paths = _default_artifact_paths(run_dir)
    smoke_report = _read_json_object(paths.live_smoke_report)
    validation = _read_model(
        paths.live_smoke_report_validation,
        ControlledLiveSmokeValidationReport,
    )
    preflight_ok = _preflight_ok_from_artifact_or_current_report(paths, smoke_report)
    pipeline = _pipeline_from_artifact_or_current_report(paths, smoke_report)

    forbidden_markers_absent = _validation_check_passed(
        validation,
        "forbidden_runtime_markers_absent",
    )
    hidden_fields_absent = _validation_check_passed(validation, "hidden_state_fields_absent")
    status = _object_value(smoke_report, "status")
    screenshot_count = len(_list_value(smoke_report, "screenshot_paths"))
    evidence_count = len(_list_value(smoke_report, "evidence_ids"))
    runtime_mode = str(smoke_report.get("runtime_mode", ""))
    mode = _mode_value(
        smoke_report,
        pipeline.mode if pipeline is not None else "official_screen_only",
    )
    captured_frame_count = _int_value(smoke_report, "captured_frame_count")
    actions_requested = _int_value(status, "actions_requested")
    inputs_sent = _int_value(smoke_report, "inputs_sent")
    action_logging_mode = _str_value(smoke_report, "action_logging_mode", default="disabled")
    dryrun_orchestration_mode = _str_value(
        smoke_report,
        "dryrun_orchestration_mode",
        default="disabled",
    )
    real_input_mode = _str_value(smoke_report, "real_input_mode", default="disabled")
    dryrun_tasks = _list_value(smoke_report, "dryrun_tasks")
    dryrun_task_count = _int_value(smoke_report, "dryrun_task_count")
    dryrun_skill_count = _int_value(smoke_report, "dryrun_skill_count")
    requested_actions = _list_value(smoke_report, "requested_actions")
    executed_actions = _list_value(smoke_report, "executed_actions")
    action_counts = _action_intent_counts(
        requested_actions=requested_actions,
        executed_actions=executed_actions,
    )
    dryrun_counts = _dryrun_counts(dryrun_tasks=dryrun_tasks)
    no_input_sent = smoke_report.get("no_input_sent") is True
    stop_reason = str(status.get("stop_reason", ""))
    duration_seconds, average_capture_interval_seconds = _capture_timing(smoke_report)
    planner_active = smoke_report.get("autonomous_planner_active") is True
    manager_active = smoke_report.get("manager_orchestration_active") is True
    body_active = smoke_report.get("body_control_active") is True
    learning_active = smoke_report.get("learning_active") is True
    bridge_active = smoke_report.get("bridge_active") is True
    ocr_active = smoke_report.get("ocr_active") is True
    manager_dryrun_active = smoke_report.get("manager_dryrun_active") is True
    body_dryrun_active = smoke_report.get("body_dryrun_active") is True
    visual_review_required = real_input_mode == "single_directional_tap"
    failure_reasons = _failure_reasons(
        mode=mode,
        preflight_ok=preflight_ok,
        validator_passed=validation.status.passed,
        no_input_sent=no_input_sent,
        runtime_mode=runtime_mode,
        captured_frame_count=captured_frame_count,
        min_frame_count=min_frame_count,
        max_frame_count=max_frame_count,
        screenshot_count=screenshot_count,
        evidence_count=evidence_count,
        action_logging_mode=action_logging_mode,
        dryrun_orchestration_mode=dryrun_orchestration_mode,
        real_input_mode=real_input_mode,
        dryrun_task_count=dryrun_task_count,
        dryrun_skill_count=dryrun_skill_count,
        dryrun_tasks=dryrun_tasks,
        dryrun_counts=dryrun_counts,
        actions_requested=actions_requested,
        inputs_sent=inputs_sent,
        requested_actions=requested_actions,
        executed_actions=executed_actions,
        stop_reason=stop_reason,
        forbidden_markers_absent=forbidden_markers_absent,
        hidden_fields_absent=hidden_fields_absent,
        planner_active=planner_active,
        manager_active=manager_active,
        body_active=body_active,
        learning_active=learning_active,
        bridge_active=bridge_active,
        ocr_active=ocr_active,
        manager_dryrun_active=manager_dryrun_active,
        body_dryrun_active=body_dryrun_active,
        smoke_report=smoke_report,
    )
    conclusion: ReviewConclusion = "passed" if not failure_reasons else "failed"

    return ControlledLiveSmokeReviewSummary(
        created_at=created_at or datetime.now(UTC),
        run_id=str(
            smoke_report.get("run_id")
            or (pipeline.run_id if pipeline is not None else run_dir.name)
        ),
        mode=mode,
        runtime_mode=runtime_mode,
        preflight_ok=preflight_ok,
        validator_passed=validation.status.passed,
        validation_error_count=validation.status.error_count,
        frame_count=captured_frame_count,
        captured_frame_count=captured_frame_count,
        min_frame_count=min_frame_count,
        max_frame_count=max_frame_count,
        screenshot_count=screenshot_count,
        evidence_count=evidence_count,
        duration_seconds=duration_seconds,
        average_capture_interval_seconds=average_capture_interval_seconds,
        action_logging_mode=action_logging_mode,
        dryrun_orchestration_mode=dryrun_orchestration_mode,
        real_input_mode=real_input_mode,
        real_wait_only_active=smoke_report.get("real_wait_only_active") is True,
        allowed_real_primitives=_str_tuple_value(smoke_report, "allowed_real_primitives"),
        input_attempt_count=_int_value(smoke_report, "input_attempt_count"),
        allowed_input_count=_int_value(smoke_report, "allowed_input_count"),
        forbidden_input_count=_int_value(smoke_report, "forbidden_input_count"),
        executed_wait_count=_int_value(smoke_report, "executed_wait_count"),
        forbidden_executed_action_count=_int_value(
            smoke_report,
            "forbidden_executed_action_count",
        ),
        focus_guard_check_count=_int_value(smoke_report, "focus_guard_check_count"),
        focus_guard_pre_input_pass_count=_int_value(
            smoke_report,
            "focus_guard_pre_input_pass_count",
        ),
        emergency_stop_check_count=_int_value(smoke_report, "emergency_stop_check_count"),
        emergency_stop_pre_input_clear_count=_int_value(
            smoke_report,
            "emergency_stop_pre_input_clear_count",
        ),
        rate_limit_enabled=smoke_report.get("rate_limit_enabled") is True,
        max_input_count=_int_value(smoke_report, "max_input_count"),
        max_input_count_exceeded=smoke_report.get("max_input_count_exceeded") is True,
        capture_script=_optional_str_value(smoke_report, "capture_script"),
        official_screen_only=smoke_report.get("official_screen_only") is True,
        pre_input_evidence_count=len(_list_value(smoke_report, "pre_input_evidence_ids")),
        post_input_evidence_count=len(_list_value(smoke_report, "post_input_evidence_ids")),
        dryrun_task_count=dryrun_task_count,
        dryrun_skill_count=dryrun_skill_count,
        allowed_dryrun_task_count=dryrun_counts["allowed_tasks"],
        forbidden_dryrun_task_count=dryrun_counts["forbidden_tasks"],
        allowed_dryrun_action_intent_count=dryrun_counts["allowed_actions"],
        forbidden_dryrun_action_intent_count=dryrun_counts["forbidden_actions"],
        manager_dryrun_active=manager_dryrun_active,
        body_dryrun_active=body_dryrun_active,
        actions_requested=actions_requested,
        inputs_sent=inputs_sent,
        allowed_action_intent_count=action_counts["allowed"],
        forbidden_action_intent_count=action_counts["forbidden"],
        executed_action_count=action_counts["executed"],
        requested_action_names=_action_names(requested_actions),
        executed_action_names=_action_names(executed_actions),
        input_action_counters={
            "actions_requested": actions_requested,
            "inputs_sent": inputs_sent,
        },
        no_input_sent=no_input_sent,
        stop_reason=stop_reason,
        forbidden_runtime_markers_absent=forbidden_markers_absent,
        hidden_state_fields_absent=hidden_fields_absent,
        planner_active=planner_active,
        manager_active=manager_active,
        body_active=body_active,
        learning_active=learning_active,
        bridge_active=bridge_active,
        ocr_active=ocr_active,
        hidden_state_violation_count=_int_value(smoke_report, "hidden_state_violation_count"),
        visual_review_required=visual_review_required,
        visual_review_status=("not_performed" if visual_review_required else "not_required"),
        requires_manual_visual_review=visual_review_required,
        artifact_paths=paths,
        conclusion=conclusion,
        recommended_next_step=(
            SINGLE_TAP_MECHANICAL_NEXT_STEP
            if conclusion == "passed" and visual_review_required
            else PASSED_NEXT_STEP
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


def _preflight_ok_from_artifact_or_current_report(
    paths: ControlledLiveSmokeReviewArtifactPaths,
    smoke_report: dict[str, object],
) -> bool:
    if paths.preflight_report.exists():
        return _read_model(paths.preflight_report, LiveRunPreflightResult).ok
    if _str_value(smoke_report, "real_input_mode", default="disabled") != "single_directional_tap":
        return _read_model(paths.preflight_report, LiveRunPreflightResult).ok
    return _single_directional_tap_current_run_safety_metadata_ok(smoke_report)


def _pipeline_from_artifact_or_current_report(
    paths: ControlledLiveSmokeReviewArtifactPaths,
    smoke_report: dict[str, object],
) -> LiveAuditPipelineResult | None:
    if paths.live_audit_pipeline.exists():
        return _read_model(paths.live_audit_pipeline, LiveAuditPipelineResult)
    if _str_value(smoke_report, "real_input_mode", default="disabled") == "single_directional_tap":
        return None
    return _read_model(paths.live_audit_pipeline, LiveAuditPipelineResult)


def _single_directional_tap_current_run_safety_metadata_ok(
    smoke_report: dict[str, object],
) -> bool:
    status = _object_value(smoke_report, "status")
    return all(
        (
            smoke_report.get("execution_enabled") is False,
            smoke_report.get("official_run_allowed") is True,
            smoke_report.get("user_started") is True,
            smoke_report.get("mode") == "official_screen_only",
            smoke_report.get("runtime_mode") == "observation_only",
            smoke_report.get("allow_real_input") is True,
            smoke_report.get("official_screen_only") is True,
            smoke_report.get("real_input_mode") == "single_directional_tap",
            smoke_report.get("action_logging_mode") == "disabled",
            smoke_report.get("dryrun_orchestration_mode") == "disabled",
            smoke_report.get("allowed_real_primitives") == [SINGLE_DIRECTIONAL_TAP_ACTION],
            _int_value(status, "actions_requested") == 1,
            _int_value(smoke_report, "input_attempt_count") == 1,
            _int_value(smoke_report, "inputs_sent") == 1,
            _int_value(smoke_report, "allowed_input_count") == 1,
            _int_value(smoke_report, "forbidden_input_count") == 0,
            _int_value(smoke_report, "executed_action_count") == 1,
            _int_value(smoke_report, "executed_wait_count") == 0,
            _int_value(smoke_report, "forbidden_executed_action_count") == 0,
            _int_value(smoke_report, "focus_guard_check_count") == 1,
            _int_value(smoke_report, "focus_guard_pre_input_pass_count") == 1,
            _int_value(smoke_report, "emergency_stop_check_count") == 1,
            _int_value(smoke_report, "emergency_stop_pre_input_clear_count") == 1,
            _int_value(smoke_report, "max_input_count") == 1,
            smoke_report.get("max_input_count_exceeded") is False,
            bool(_list_value(smoke_report, "pre_input_evidence_ids")),
            bool(_list_value(smoke_report, "post_input_evidence_ids")),
            not _pre_post_screenshot_evidence_failures(smoke_report),
            smoke_report.get("capture_script") == "./scripts/capture_active_window_ppm.sh",
            _int_value(smoke_report, "hidden_state_violation_count") == 0,
            smoke_report.get("autonomous_planner_active") is False,
            smoke_report.get("manager_orchestration_active") is False,
            smoke_report.get("body_control_active") is False,
            smoke_report.get("bridge_active") is False,
            smoke_report.get("ocr_active") is False,
            smoke_report.get("learning_active") is False,
        )
    )


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


def _pre_post_screenshot_evidence_failures(payload: dict[str, object]) -> list[str]:
    pre_ids = _string_list_value(payload, "pre_input_evidence_ids")
    post_ids = _string_list_value(payload, "post_input_evidence_ids")
    failures: list[str] = []
    if not pre_ids:
        failures.append("pre-input screenshot evidence is missing")
    if not post_ids:
        failures.append("post-input screenshot evidence is missing")
    if failures:
        return failures

    evidence_by_id = _screenshot_evidence_by_id(payload)
    referenced_evidence = []
    for label, evidence_ids in (("pre-input", pre_ids), ("post-input", post_ids)):
        for evidence_id in evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                failures.append(f"{label} screenshot evidence entry is missing: {evidence_id}")
                continue
            path = evidence.get("screenshot_path")
            if not isinstance(path, str) or not path:
                failures.append(f"{label} screenshot path is missing: {evidence_id}")
            elif not Path(path).is_file():
                failures.append(f"{label} screenshot path does not exist: {path}")
            dimensions = _screenshot_dimensions(evidence)
            if dimensions is None:
                failures.append(f"{label} screenshot dimensions are missing: {evidence_id}")
                continue
            referenced_evidence.append((label, dimensions))

    pre_dimensions = {
        dimensions for label, dimensions in referenced_evidence if label == "pre-input"
    }
    post_dimensions = {
        dimensions for label, dimensions in referenced_evidence if label == "post-input"
    }
    if pre_dimensions and post_dimensions and pre_dimensions != post_dimensions:
        failures.append(PRE_POST_DIMENSION_MISMATCH_MESSAGE)
    return failures


def _screenshot_evidence_by_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    evidence_by_id: dict[str, dict[str, object]] = {}
    for item in _list_value(payload, "screenshot_evidence"):
        if not isinstance(item, dict):
            continue
        evidence_id = item.get("evidence_id")
        if isinstance(evidence_id, str) and evidence_id:
            evidence_by_id[evidence_id] = item
    return evidence_by_id


def _screenshot_dimensions(evidence: dict[str, object]) -> tuple[int, int] | None:
    width = evidence.get("width")
    height = evidence.get("height")
    if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
        return width, height
    return None


def _object_value(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_value(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _string_list_value(payload: dict[str, object], key: str) -> list[str]:
    return [value for value in _list_value(payload, key) if isinstance(value, str) and value]


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) else 0


def _str_value(payload: dict[str, object], key: str, *, default: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else default


def _optional_str_value(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _str_tuple_value(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _mode_value(payload: dict[str, object], fallback: ManifestMode) -> ManifestMode:
    value = payload.get("mode")
    if value in ("official_screen_only", "debug_visible_bridge", "dry_run"):
        return value
    return fallback


def _capture_timing(payload: dict[str, object]) -> tuple[float | None, float | None]:
    timestamps = []
    for item in _list_value(payload, "screenshot_evidence"):
        if not isinstance(item, dict):
            continue
        timestamp = item.get("timestamp")
        if not isinstance(timestamp, str):
            continue
        try:
            timestamps.append(datetime.fromisoformat(timestamp.replace("Z", "+00:00")))
        except ValueError:
            continue
    if len(timestamps) < 2:
        return None, None
    duration = (timestamps[-1] - timestamps[0]).total_seconds()
    average = duration / (len(timestamps) - 1)
    return duration, average


def _validation_check_passed(
    validation: ControlledLiveSmokeValidationReport,
    name: str,
) -> bool:
    return any(check.name == name and check.passed for check in validation.checks)


def _action_intent_counts(
    *,
    requested_actions: list[object],
    executed_actions: list[object],
) -> dict[str, int]:
    allowed = 0
    forbidden = 0
    requested_executed = 0
    for action in requested_actions:
        if not isinstance(action, dict):
            forbidden += 1
            continue
        safe_no_input = (
            action.get("action") == "wait"
            and action.get("requested") is True
            and action.get("executed") is False
            and action.get("input_sent") is False
            and action.get("reason") in {"noop_action_logging", "dryrun_orchestration_wait_only"}
        )
        safe_real_wait = (
            action.get("action") == "wait"
            and action.get("requested") is True
            and action.get("executed") is True
            and action.get("input_sent") is True
            and action.get("reason") == "real_wait_only_noop"
        )
        safe_single_directional_tap = (
            action.get("action") == SINGLE_DIRECTIONAL_TAP_ACTION
            and action.get("requested") is True
            and action.get("executed") is True
            and action.get("input_sent") is True
            and action.get("reason") == "single_directional_tap"
        )
        if safe_no_input or safe_real_wait or safe_single_directional_tap:
            allowed += 1
        else:
            forbidden += 1
        if action.get("executed") is True:
            requested_executed += 1
    return {
        "allowed": allowed,
        "forbidden": forbidden,
        "executed": max(len(executed_actions), requested_executed),
    }


def _action_names(actions: list[object]) -> tuple[str, ...]:
    names: list[str] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        name = action.get("action")
        if isinstance(name, str):
            names.append(name)
    return tuple(names)


def _dryrun_counts(*, dryrun_tasks: list[object]) -> dict[str, int]:
    allowed_tasks = 0
    forbidden_tasks = 0
    allowed_actions = 0
    forbidden_actions = 0
    for task in dryrun_tasks:
        if not isinstance(task, dict):
            forbidden_tasks += 1
            forbidden_actions += 1
            continue
        action = task.get("action_intent")
        safe_task = (
            task.get("static_goal") == "maintain_observation_without_input"
            and task.get("selected_skill") == "wait"
            and isinstance(action, dict)
        )
        safe_action = (
            isinstance(action, dict)
            and action.get("action") == "wait"
            and action.get("requested") is True
            and action.get("executed") is False
            and action.get("input_sent") is False
            and action.get("reason") == "dryrun_orchestration_wait_only"
        )
        if safe_task and safe_action:
            allowed_tasks += 1
            allowed_actions += 1
        else:
            forbidden_tasks += 1
            forbidden_actions += 1
    return {
        "allowed_tasks": allowed_tasks,
        "forbidden_tasks": forbidden_tasks,
        "allowed_actions": allowed_actions,
        "forbidden_actions": forbidden_actions,
    }


def _failure_reasons(
    *,
    mode: ManifestMode,
    preflight_ok: bool,
    validator_passed: bool,
    no_input_sent: bool,
    runtime_mode: str,
    captured_frame_count: int,
    min_frame_count: int | None,
    max_frame_count: int | None,
    screenshot_count: int,
    evidence_count: int,
    action_logging_mode: str,
    dryrun_orchestration_mode: str,
    real_input_mode: str,
    dryrun_task_count: int,
    dryrun_skill_count: int,
    dryrun_tasks: list[object],
    dryrun_counts: dict[str, int],
    actions_requested: int,
    inputs_sent: int,
    requested_actions: list[object],
    executed_actions: list[object],
    stop_reason: str,
    forbidden_markers_absent: bool,
    hidden_fields_absent: bool,
    planner_active: bool,
    manager_active: bool,
    body_active: bool,
    learning_active: bool,
    bridge_active: bool,
    ocr_active: bool,
    manager_dryrun_active: bool,
    body_dryrun_active: bool,
    smoke_report: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    if mode != "official_screen_only":
        reasons.append("mode is not official_screen_only")
    if not preflight_ok:
        reasons.append("preflight did not pass")
    if not validator_passed:
        reasons.append("validator did not pass")
    real_wait_only = real_input_mode == "wait_only_noop"
    single_directional_tap = real_input_mode == "single_directional_tap"
    real_input_active = real_wait_only or single_directional_tap
    if not no_input_sent and not real_input_active:
        reasons.append("report does not confirm no_input_sent=true")
    if runtime_mode != "observation_only":
        reasons.append("runtime_mode is not observation_only")
    if captured_frame_count < 1:
        reasons.append("captured_frame_count is below 1")
    if min_frame_count is not None and captured_frame_count < min_frame_count:
        reasons.append("captured_frame_count is below the configured minimum")
    if max_frame_count is not None and captured_frame_count > max_frame_count:
        reasons.append("captured_frame_count is above the configured maximum")
    if screenshot_count != captured_frame_count:
        reasons.append("screenshot_count does not match captured_frame_count")
    if evidence_count != captured_frame_count:
        reasons.append("evidence_count does not match captured_frame_count")
    if inputs_sent != 0 and not real_input_active:
        reasons.append("inputs_sent is not zero")
    if single_directional_tap:
        action_counts = _action_intent_counts(
            requested_actions=requested_actions,
            executed_actions=executed_actions,
        )
        if action_logging_mode != "disabled" or dryrun_orchestration_mode != "disabled":
            reasons.append("single directional tap mode is combined with another action mode")
        if smoke_report.get("allowed_real_primitives") != [SINGLE_DIRECTIONAL_TAP_ACTION]:
            reasons.append("allowed_real_primitives is not exactly move_right_short")
        if actions_requested != 1 or len(requested_actions) != 1:
            reasons.append("single directional tap action request count is not one")
        if _int_value(smoke_report, "input_attempt_count") != 1:
            reasons.append("input_attempt_count is not one")
        if inputs_sent != 1:
            reasons.append("inputs_sent is not one")
        if no_input_sent:
            reasons.append("single directional tap report still claims no_input_sent=true")
        if action_counts["forbidden"] > 0:
            reasons.append("forbidden action intents are present")
        if _int_value(smoke_report, "executed_action_count") != 1:
            reasons.append("executed_action_count is not one")
        if action_counts["executed"] != 1:
            reasons.append("executed action count is not one")
        if _action_names(executed_actions) != (SINGLE_DIRECTIONAL_TAP_ACTION,):
            reasons.append("executed action names are not exactly move_right_short")
        if _int_value(smoke_report, "allowed_input_count") != 1:
            reasons.append("allowed_input_count is not one")
        if _int_value(smoke_report, "forbidden_input_count") != 0:
            reasons.append("forbidden_input_count is not zero")
        if _int_value(smoke_report, "executed_wait_count") != 0:
            reasons.append("executed_wait_count is not zero")
        if _int_value(smoke_report, "forbidden_executed_action_count") != 0:
            reasons.append("forbidden_executed_action_count is not zero")
        if _int_value(smoke_report, "focus_guard_check_count") != 1:
            reasons.append("focus_guard_check_count is not one")
        if _int_value(smoke_report, "focus_guard_pre_input_pass_count") != 1:
            reasons.append("focus_guard_pre_input_pass_count is not one")
        if _int_value(smoke_report, "emergency_stop_check_count") != 1:
            reasons.append("emergency_stop_check_count is not one")
        if _int_value(smoke_report, "emergency_stop_pre_input_clear_count") != 1:
            reasons.append("emergency_stop_pre_input_clear_count is not one")
        if _int_value(smoke_report, "max_input_count") != 1:
            reasons.append("max_input_count is not one")
        if smoke_report.get("max_input_count_exceeded") is not False:
            reasons.append("max_input_count_exceeded is not false")
        if not _list_value(smoke_report, "pre_input_evidence_ids"):
            reasons.append("pre-input evidence is missing")
        if not _list_value(smoke_report, "post_input_evidence_ids"):
            reasons.append("post-input evidence is missing")
        if smoke_report.get("capture_script") != "./scripts/capture_active_window_ppm.sh":
            reasons.append("capture_script is not the active-window script")
        if smoke_report.get("official_screen_only") is not True:
            reasons.append("official_screen_only is false")
        if _int_value(smoke_report, "hidden_state_violation_count") != 0:
            reasons.append("hidden_state_violation_count is not zero")
        reasons.extend(_pre_post_screenshot_evidence_failures(smoke_report))
    elif real_wait_only:
        action_counts = _action_intent_counts(
            requested_actions=requested_actions,
            executed_actions=executed_actions,
        )
        if action_logging_mode != "disabled" or dryrun_orchestration_mode != "disabled":
            reasons.append("real wait-only mode is combined with another action mode")
        if actions_requested != len(requested_actions):
            reasons.append("actions_requested does not match requested_actions")
        if inputs_sent < 1 or actions_requested != inputs_sent:
            reasons.append("real wait-only inputs_sent/action count mismatch")
        if smoke_report.get("real_wait_only_active") is not True:
            reasons.append("real_wait_only_active is false")
        if no_input_sent:
            reasons.append("real wait-only report still claims no_input_sent=true")
        if action_counts["forbidden"] > 0:
            reasons.append("forbidden action intents are present")
        if action_counts["executed"] != inputs_sent:
            reasons.append("executed action count does not match inputs_sent")
        if _int_value(smoke_report, "allowed_input_count") != inputs_sent:
            reasons.append("allowed_input_count does not match inputs_sent")
        if _int_value(smoke_report, "forbidden_input_count") != 0:
            reasons.append("forbidden_input_count is not zero")
        if _int_value(smoke_report, "executed_wait_count") != inputs_sent:
            reasons.append("executed_wait_count does not match inputs_sent")
        if _int_value(smoke_report, "forbidden_executed_action_count") != 0:
            reasons.append("forbidden_executed_action_count is not zero")
        if _int_value(smoke_report, "focus_guard_check_count") < inputs_sent:
            reasons.append("focus_guard_check_count is below inputs_sent")
        if _int_value(smoke_report, "focus_guard_pre_input_pass_count") < inputs_sent:
            reasons.append("focus_guard_pre_input_pass_count is below inputs_sent")
        if _int_value(smoke_report, "emergency_stop_check_count") < inputs_sent:
            reasons.append("emergency_stop_check_count is below inputs_sent")
        if _int_value(smoke_report, "emergency_stop_pre_input_clear_count") < inputs_sent:
            reasons.append("emergency_stop_pre_input_clear_count is below inputs_sent")
        if smoke_report.get("rate_limit_enabled") is not True:
            reasons.append("rate_limit_enabled is false")
        if _int_value(smoke_report, "max_input_count") < 1:
            reasons.append("max_input_count is below 1")
        if smoke_report.get("max_input_count_exceeded") is True:
            reasons.append("max_input_count_exceeded is true")
        capture_script = smoke_report.get("capture_script")
        if (
            not isinstance(capture_script, str)
            or "capture_active_window_ppm.sh" not in capture_script
            or "capture_one_frame_ppm.sh" in capture_script
        ):
            reasons.append("capture_script is not the active-window script")
        if smoke_report.get("official_screen_only") is not True:
            reasons.append("official_screen_only is false")
        if _int_value(smoke_report, "hidden_state_violation_count") != 0:
            reasons.append("hidden_state_violation_count is not zero")
    elif dryrun_orchestration_mode == "wait_only":
        if actions_requested != len(requested_actions):
            reasons.append("actions_requested does not match requested_actions")
        if actions_requested < 1:
            reasons.append("dryrun wait_only did not request any action intents")
        if dryrun_task_count < 1:
            reasons.append("dryrun_task_count is below 1")
        if dryrun_skill_count < 1:
            reasons.append("dryrun_skill_count is below 1")
        if dryrun_task_count != len(dryrun_tasks):
            reasons.append("dryrun_task_count does not match dryrun_tasks")
        if dryrun_skill_count != len(dryrun_tasks):
            reasons.append("dryrun_skill_count does not match dryrun_tasks")
        if dryrun_counts["forbidden_tasks"] > 0:
            reasons.append("forbidden dryrun tasks are present")
        if dryrun_counts["forbidden_actions"] > 0:
            reasons.append("forbidden dryrun action intents are present")
        action_counts = _action_intent_counts(
            requested_actions=requested_actions,
            executed_actions=executed_actions,
        )
        if action_counts["forbidden"] > 0:
            reasons.append("forbidden action intents are present")
        if action_counts["executed"] > 0:
            reasons.append("executed action intents are present")
        if not manager_dryrun_active:
            reasons.append("manager_dryrun_active is false")
        if not body_dryrun_active:
            reasons.append("body_dryrun_active is false")
    elif dryrun_orchestration_mode != "disabled":
        reasons.append("dryrun_orchestration_mode is not allowed")
    elif dryrun_task_count != 0 or dryrun_skill_count != 0 or dryrun_tasks:
        reasons.append("dryrun tasks are present while dryrun is disabled")
    elif action_logging_mode == "disabled":
        if actions_requested != 0:
            reasons.append("actions_requested is not zero")
        if requested_actions:
            reasons.append("requested_actions is not empty")
    elif action_logging_mode == "wait_only_noop":
        if actions_requested != len(requested_actions):
            reasons.append("actions_requested does not match requested_actions")
        action_counts = _action_intent_counts(
            requested_actions=requested_actions,
            executed_actions=executed_actions,
        )
        if actions_requested < 1:
            reasons.append("wait_only_noop did not request any action intents")
        if action_counts["forbidden"] > 0:
            reasons.append("forbidden action intents are present")
        if action_counts["executed"] > 0:
            reasons.append("executed action intents are present")
    else:
        reasons.append("action_logging_mode is not allowed")
    if stop_reason != "max_frames_reached":
        reasons.append("stop_reason is not max_frames_reached")
    if not forbidden_markers_absent:
        reasons.append("forbidden runtime marker check failed")
    if not hidden_fields_absent:
        reasons.append("hidden-state field check failed")
    if planner_active:
        reasons.append("planner_active is true")
    if manager_active:
        reasons.append("manager_active is true")
    if body_active:
        reasons.append("body_active is true")
    if learning_active:
        reasons.append("learning_active is true")
    if bridge_active:
        reasons.append("bridge_active is true")
    if ocr_active:
        reasons.append("ocr_active is true")
    return reasons
