import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from fh_agent.evals.controlled_live_smoke_review import ControlledLiveSmokeReviewSummary
from fh_agent.evals.controlled_live_smoke_validator import ControlledLiveSmokeValidationReport

STABILITY_REVIEW_VERSION = "2"
REQUIRED_RUN_COUNT = 3
SINGLE_DIRECTIONAL_TAP_ACTION = "move_right_short"
REQUIRED_REAL_INPUT_MODE = "single_directional_tap"
REQUIRED_ALLOWED_REAL_PRIMITIVES = (SINGLE_DIRECTIONAL_TAP_ACTION,)

StabilityConclusion = Literal["passed", "failed"]


class ControlledLiveSmokeStabilityRunSummary(BaseModel):
    """One reviewed 13.4-style single directional tap run in a stability batch."""

    model_config = ConfigDict(extra="forbid")

    report_path: Path
    validation_path: Path
    review_path: Path
    run_id: str
    official_screen_only: bool
    real_input_mode: str
    allowed_real_primitives: tuple[str, ...]
    max_input_count: int
    inputs_sent: int
    executed_action_count: int
    executed_wait_count: int
    forbidden_input_count: int
    forbidden_executed_action_count: int
    hidden_state_violation_count: int
    validator_passed: bool
    mechanical_review_passed: bool
    manual_visual_review_passed: bool
    pre_screenshot_evidence_present: bool
    post_screenshot_evidence_present: bool
    pre_post_dimensions_match: bool
    focus_guard_immediate_before_input: bool
    emergency_stop_immediate_before_input: bool
    planner_active: bool
    manager_active: bool
    body_active: bool
    bridge_active: bool
    llm_active: bool
    ocr_active: bool
    rl_active: bool
    learning_active: bool
    passed: bool
    failure_reasons: tuple[str, ...] = ()


class ControlledLiveSmokeStabilityReview(BaseModel):
    """Aggregate review for three independent manual 13.4 single tap runs."""

    model_config = ConfigDict(extra="forbid")

    stability_review_version: str = STABILITY_REVIEW_VERSION
    created_at: datetime
    conclusion: StabilityConclusion
    run_count: int
    run_ids: tuple[str, ...]
    real_input_mode: str = REQUIRED_REAL_INPUT_MODE
    allowed_real_primitives: tuple[str, ...] = REQUIRED_ALLOWED_REAL_PRIMITIVES
    total_inputs_sent: int
    total_executed_action_count: int
    max_inputs_sent_per_run: int
    max_executed_action_count_per_run: int
    forbidden_input_count_total: int
    forbidden_executed_action_count_total: int
    hidden_state_violation_count_total: int
    all_validations_passed: bool
    all_reviews_passed: bool
    all_manual_visual_reviews_passed: bool
    all_pre_post_dimensions_match: bool
    all_focus_guard_immediate_before_input: bool
    all_emergency_stop_immediate_before_input: bool
    runs: tuple[ControlledLiveSmokeStabilityRunSummary, ...]
    failure_reasons: tuple[str, ...] = ()

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def create_controlled_live_smoke_stability_review(
    *,
    review_paths: tuple[Path, ...],
    report_paths: tuple[Path, ...] = (),
    validation_paths: tuple[Path, ...] = (),
    created_at: datetime | None = None,
) -> ControlledLiveSmokeStabilityReview:
    reviews = tuple(read_controlled_live_smoke_review_summary(path) for path in review_paths)
    resolved_report_paths = (
        report_paths
        if report_paths
        else tuple(review.artifact_paths.live_smoke_report for review in reviews)
    )
    resolved_validation_paths = (
        validation_paths
        if validation_paths
        else tuple(review.artifact_paths.live_smoke_report_validation for review in reviews)
    )
    if len(resolved_report_paths) != len(review_paths) or len(resolved_validation_paths) != len(
        review_paths,
    ):
        msg = "--report, --validation, and --review counts must match"
        raise ValueError(msg)

    runs = tuple(
        _run_summary_from_artifacts(
            report_path=report_path,
            validation_path=validation_path,
            review_path=review_path,
            review=review,
        )
        for report_path, validation_path, review_path, review in zip(
            resolved_report_paths,
            resolved_validation_paths,
            review_paths,
            reviews,
            strict=True,
        )
    )
    aggregate_failures = _aggregate_failure_reasons(runs)
    run_failures = tuple(f"{run.run_id}:{reason}" for run in runs for reason in run.failure_reasons)
    failure_reasons = (*aggregate_failures, *run_failures)
    conclusion: StabilityConclusion = "passed" if not failure_reasons else "failed"
    return ControlledLiveSmokeStabilityReview(
        created_at=created_at or datetime.now(UTC),
        conclusion=conclusion,
        run_count=len(runs),
        run_ids=tuple(run.run_id for run in runs),
        total_inputs_sent=sum(run.inputs_sent for run in runs),
        total_executed_action_count=sum(run.executed_action_count for run in runs),
        max_inputs_sent_per_run=max((run.inputs_sent for run in runs), default=0),
        max_executed_action_count_per_run=max(
            (run.executed_action_count for run in runs),
            default=0,
        ),
        forbidden_input_count_total=sum(run.forbidden_input_count for run in runs),
        forbidden_executed_action_count_total=sum(
            run.forbidden_executed_action_count for run in runs
        ),
        hidden_state_violation_count_total=sum(run.hidden_state_violation_count for run in runs),
        all_validations_passed=all(run.validator_passed for run in runs),
        all_reviews_passed=all(run.mechanical_review_passed for run in runs),
        all_manual_visual_reviews_passed=all(run.manual_visual_review_passed for run in runs),
        all_pre_post_dimensions_match=all(run.pre_post_dimensions_match for run in runs),
        all_focus_guard_immediate_before_input=all(
            run.focus_guard_immediate_before_input for run in runs
        ),
        all_emergency_stop_immediate_before_input=all(
            run.emergency_stop_immediate_before_input for run in runs
        ),
        runs=runs,
        failure_reasons=failure_reasons,
    )


def write_controlled_live_smoke_stability_review(
    review: ControlledLiveSmokeStabilityReview,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    if path.exists() and not overwrite:
        msg = f"controlled live-smoke stability review already exists: {path}"
        raise FileExistsError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(review.to_deterministic_json() + "\n", encoding="utf-8")
    return path


def read_controlled_live_smoke_review_summary(path: Path) -> ControlledLiveSmokeReviewSummary:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ControlledLiveSmokeReviewSummary.model_validate(payload)
    except FileNotFoundError as exc:
        msg = f"controlled live-smoke review file does not exist: {path}"
        raise ValueError(msg) from exc
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid controlled live-smoke review file: {path}: {exc}"
        raise ValueError(msg) from exc


def read_controlled_live_smoke_validation_report(
    path: Path,
) -> ControlledLiveSmokeValidationReport:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ControlledLiveSmokeValidationReport.model_validate(payload)
    except FileNotFoundError as exc:
        msg = f"controlled live-smoke validation file does not exist: {path}"
        raise ValueError(msg) from exc
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid controlled live-smoke validation file: {path}: {exc}"
        raise ValueError(msg) from exc


def read_controlled_live_smoke_report(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"controlled live-smoke report file does not exist: {path}"
        raise ValueError(msg) from exc
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"invalid controlled live-smoke report file: {path}: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"invalid controlled live-smoke report file: {path}: expected object"
        raise ValueError(msg)
    return payload


def _run_summary_from_artifacts(
    *,
    report_path: Path,
    validation_path: Path,
    review_path: Path,
    review: ControlledLiveSmokeReviewSummary,
) -> ControlledLiveSmokeStabilityRunSummary:
    report = read_controlled_live_smoke_report(report_path)
    validation = read_controlled_live_smoke_validation_report(validation_path)
    run_id = _str_value(report, "run_id", default=review.run_id)
    pre_present, post_present, dimensions_match = _pre_post_screenshot_evidence_status(report)
    actions_requested = _int_value(_object_value(report, "status"), "actions_requested")
    requested_action_names = _action_names(_list_value(report, "requested_actions"))
    executed_action_names = _action_names(_list_value(report, "executed_actions"))
    allowed_real_primitives = _str_tuple_value(report, "allowed_real_primitives")
    inputs_sent = _int_value(report, "inputs_sent")
    executed_action_count = _int_value(report, "executed_action_count")
    forbidden_input_count = _int_value(report, "forbidden_input_count")
    forbidden_executed_action_count = _int_value(report, "forbidden_executed_action_count")
    hidden_state_violation_count = _int_value(report, "hidden_state_violation_count")
    validator_passed = (
        validation.status.passed
        and validation.status.error_count == 0
        and review.validator_passed
        and review.validation_error_count == 0
    )
    mechanical_review_passed = review.conclusion == "passed" and not review.failure_reasons
    manual_visual_review_passed = (
        review.visual_review_required is True
        and review.requires_manual_visual_review is True
        and review.visual_review_status == "passed"
    )
    focus_guard_immediate = (
        inputs_sent == 1
        and _int_value(report, "focus_guard_check_count") == 1
        and _int_value(report, "focus_guard_pre_input_pass_count") == 1
        and review.focus_guard_check_count == 1
        and review.focus_guard_pre_input_pass_count == 1
    )
    emergency_stop_immediate = (
        inputs_sent == 1
        and _int_value(report, "emergency_stop_check_count") == 1
        and _int_value(report, "emergency_stop_pre_input_clear_count") == 1
        and review.emergency_stop_check_count == 1
        and review.emergency_stop_pre_input_clear_count == 1
    )
    flags = _active_runtime_flags(report=report, review=review)
    checks = {
        "run_id_matches_review": run_id == review.run_id,
        "official_screen_only": (
            report.get("mode") == "official_screen_only"
            and report.get("official_screen_only") is True
            and review.mode == "official_screen_only"
            and review.official_screen_only is True
        ),
        "real_input_mode_single_directional_tap": (
            _str_value(report, "real_input_mode", default="") == REQUIRED_REAL_INPUT_MODE
            and review.real_input_mode == REQUIRED_REAL_INPUT_MODE
        ),
        "allowed_real_primitives_move_right_short": (
            allowed_real_primitives == REQUIRED_ALLOWED_REAL_PRIMITIVES
            and review.allowed_real_primitives == REQUIRED_ALLOWED_REAL_PRIMITIVES
        ),
        "max_input_count_one": (
            _int_value(report, "max_input_count") == 1
            and review.max_input_count == 1
            and report.get("max_input_count_exceeded") is False
            and review.max_input_count_exceeded is False
        ),
        "input_attempt_count_one": _int_value(report, "input_attempt_count") == 1
        and review.input_attempt_count == 1,
        "inputs_sent_one": inputs_sent == 1 and review.inputs_sent == 1,
        "executed_action_count_one": executed_action_count == 1
        and review.executed_action_count == 1,
        "executed_wait_count_zero": _int_value(report, "executed_wait_count") == 0
        and review.executed_wait_count == 0,
        "forbidden_input_count_zero": forbidden_input_count == 0
        and review.forbidden_input_count == 0,
        "forbidden_executed_action_count_zero": forbidden_executed_action_count == 0
        and review.forbidden_executed_action_count == 0,
        "hidden_state_violation_count_zero": hidden_state_violation_count == 0
        and review.hidden_state_violation_count == 0,
        "validator_passed": validator_passed,
        "mechanical_review_passed": mechanical_review_passed,
        "manual_visual_review_passed": manual_visual_review_passed,
        "pre_screenshot_evidence_present": pre_present and review.pre_input_evidence_count > 0,
        "post_screenshot_evidence_present": post_present and review.post_input_evidence_count > 0,
        "pre_post_dimensions_match": dimensions_match
        and _validation_check_passed(
            validation,
            "single_directional_tap_pre_post_screenshot_evidence",
        ),
        "focus_guard_immediate_before_input": focus_guard_immediate,
        "emergency_stop_immediate_before_input": emergency_stop_immediate,
        "actions_requested_one": actions_requested == 1 and review.actions_requested == 1,
        "requested_actions_single_move_right_short": requested_action_names
        == (SINGLE_DIRECTIONAL_TAP_ACTION,)
        and review.requested_action_names == (SINGLE_DIRECTIONAL_TAP_ACTION,),
        "executed_actions_single_move_right_short": executed_action_names
        == (SINGLE_DIRECTIONAL_TAP_ACTION,)
        and review.executed_action_names == (SINGLE_DIRECTIONAL_TAP_ACTION,),
        "no_confirm_cancel_open_menu": not (
            {"confirm", "cancel", "open_menu"} & set(requested_action_names + executed_action_names)
        ),
        "no_bridge_planner_llm_ocr_rl_active_flags": not any(flags.values()),
        "hidden_state_fields_absent": review.hidden_state_fields_absent
        and _validation_check_passed(validation, "hidden_state_fields_absent"),
        "forbidden_runtime_markers_absent": review.forbidden_runtime_markers_absent
        and _validation_check_passed(validation, "forbidden_runtime_markers_absent"),
    }
    failure_reasons = tuple(name for name, passed in checks.items() if not passed)
    return ControlledLiveSmokeStabilityRunSummary(
        report_path=report_path,
        validation_path=validation_path,
        review_path=review_path,
        run_id=run_id,
        official_screen_only=checks["official_screen_only"],
        real_input_mode=_str_value(report, "real_input_mode", default=""),
        allowed_real_primitives=allowed_real_primitives,
        max_input_count=_int_value(report, "max_input_count"),
        inputs_sent=inputs_sent,
        executed_action_count=executed_action_count,
        executed_wait_count=_int_value(report, "executed_wait_count"),
        forbidden_input_count=forbidden_input_count,
        forbidden_executed_action_count=forbidden_executed_action_count,
        hidden_state_violation_count=hidden_state_violation_count,
        validator_passed=validator_passed,
        mechanical_review_passed=mechanical_review_passed,
        manual_visual_review_passed=manual_visual_review_passed,
        pre_screenshot_evidence_present=pre_present,
        post_screenshot_evidence_present=post_present,
        pre_post_dimensions_match=dimensions_match,
        focus_guard_immediate_before_input=focus_guard_immediate,
        emergency_stop_immediate_before_input=emergency_stop_immediate,
        planner_active=flags["planner"],
        manager_active=flags["manager"],
        body_active=flags["body"],
        bridge_active=flags["bridge"],
        llm_active=flags["llm"],
        ocr_active=flags["ocr"],
        rl_active=flags["rl"],
        learning_active=flags["learning"],
        passed=not failure_reasons,
        failure_reasons=failure_reasons,
    )


def _aggregate_failure_reasons(
    runs: tuple[ControlledLiveSmokeStabilityRunSummary, ...],
) -> tuple[str, ...]:
    checks = {
        "run_count_3": len(runs) == REQUIRED_RUN_COUNT,
        "unique_run_ids": len({run.run_id for run in runs}) == len(runs),
        "all_runs_passed": all(run.passed for run in runs),
        "total_inputs_sent_3": sum(run.inputs_sent for run in runs) == REQUIRED_RUN_COUNT,
        "total_executed_action_count_3": (
            sum(run.executed_action_count for run in runs) == REQUIRED_RUN_COUNT
        ),
        "forbidden_input_count_total_zero": sum(run.forbidden_input_count for run in runs) == 0,
        "forbidden_executed_action_count_total_zero": (
            sum(run.forbidden_executed_action_count for run in runs) == 0
        ),
        "hidden_state_violation_count_total_zero": (
            sum(run.hidden_state_violation_count for run in runs) == 0
        ),
    }
    return tuple(name for name, passed in checks.items() if not passed)


def _pre_post_screenshot_evidence_status(
    report: dict[str, object],
) -> tuple[bool, bool, bool]:
    pre_ids = _string_list_value(report, "pre_input_evidence_ids")
    post_ids = _string_list_value(report, "post_input_evidence_ids")
    evidence_by_id = _screenshot_evidence_by_id(report)
    pre_dimensions = _dimensions_for_ids(pre_ids, evidence_by_id)
    post_dimensions = _dimensions_for_ids(post_ids, evidence_by_id)
    pre_present = bool(pre_ids) and len(pre_dimensions) == len(pre_ids)
    post_present = bool(post_ids) and len(post_dimensions) == len(post_ids)
    dimensions_match = pre_present and post_present and set(pre_dimensions) == set(post_dimensions)
    return pre_present, post_present, dimensions_match


def _dimensions_for_ids(
    evidence_ids: list[str],
    evidence_by_id: dict[str, dict[str, object]],
) -> list[tuple[int, int]]:
    dimensions: list[tuple[int, int]] = []
    for evidence_id in evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            continue
        dimension = _screenshot_dimensions(evidence)
        if dimension is not None:
            dimensions.append(dimension)
    return dimensions


def _screenshot_evidence_by_id(report: dict[str, object]) -> dict[str, dict[str, object]]:
    evidence_by_id: dict[str, dict[str, object]] = {}
    for item in _list_value(report, "screenshot_evidence"):
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


def _active_runtime_flags(
    *,
    report: dict[str, object],
    review: ControlledLiveSmokeReviewSummary,
) -> dict[str, bool]:
    return {
        "planner": report.get("autonomous_planner_active") is True or review.planner_active,
        "manager": report.get("manager_orchestration_active") is True or review.manager_active,
        "body": report.get("body_control_active") is True or review.body_active,
        "bridge": report.get("bridge_active") is True or review.bridge_active,
        "llm": report.get("llm_active") is True,
        "ocr": report.get("ocr_active") is True or review.ocr_active,
        "rl": report.get("rl_active") is True,
        "learning": report.get("learning_active") is True or review.learning_active,
    }


def _validation_check_passed(
    validation: ControlledLiveSmokeValidationReport,
    name: str,
) -> bool:
    return any(check.name == name and check.passed for check in validation.checks)


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


def _str_tuple_value(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _action_names(actions: list[object]) -> tuple[str, ...]:
    names: list[str] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        name = action.get("action")
        if isinstance(name, str):
            names.append(name)
    return tuple(names)
