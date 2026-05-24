import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from fh_agent.evals.controlled_live_smoke_runner import ControlledLiveSmokeReport

VALIDATION_REPORT_VERSION = "1"
SINGLE_DIRECTIONAL_TAP_ACTION = "move_right_short"
PRE_POST_DIMENSION_MISMATCH_MESSAGE = (
    "pre/post screenshots do not match target window dimensions; possible focus steal or OS dialog."
)
ValidationSeverity = Literal["info", "error"]
ValidationStatus = Literal["passed", "failed"]

ALLOWED_RUNTIME_EVENT_KINDS: tuple[str, ...] = (
    "runtime_start",
    "frame_captured",
    "noop_action_intent",
    "wait_intent",
    "action_request",
    "input_executed",
    "dryrun_task_intent",
    "stop_condition_triggered",
    "runtime_end",
)
FORBIDDEN_MARKER_PARTS: tuple[tuple[str, ...], ...] = (
    ("movement",),
    ("move", "_", "up", "_", "short"),
    ("move", "_", "down", "_", "short"),
    ("move", "_", "left", "_", "short"),
    ("move", "_", "right", "_", "short"),
    ("confirm",),
    ("cancel",),
    ("open", "_", "menu"),
    ("wait", " ", "keypress"),
    ("input", "_", "executor"),
    ("planner",),
    ("llm",),
    ("manager",),
    ("body",),
    ("bridge",),
    ("ocr",),
    ("parser",),
    ("rl",),
    ("training",),
    ("tor", "ch"),
    ("stable", "_", "baselines", "3"),
)
FORBIDDEN_HIDDEN_FIELDS: tuple[str, ...] = (
    "map_id",
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


class ControlledLiveSmokeValidationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    check_count: int
    error_count: int


class ControlledLiveSmokeValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    severity: ValidationSeverity
    message: str


class ControlledLiveSmokeValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validation_report_version: str = VALIDATION_REPORT_VERSION
    created_at: datetime
    source_report_path: Path
    events_jsonl_path: Path | None = None
    expected_frame_count: int | None = None
    min_frame_count: int | None = None
    max_frame_count: int | None = None
    status: ControlledLiveSmokeValidationStatus
    checks: tuple[ControlledLiveSmokeValidationCheck, ...]

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def read_controlled_live_smoke_report(
    path: Path,
) -> tuple[dict[str, object], ControlledLiveSmokeReport | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"invalid controlled smoke report: {path}: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"invalid controlled smoke report: {path}: expected object"
        raise ValueError(msg)
    try:
        model = ControlledLiveSmokeReport.model_validate(payload)
    except ValidationError:
        model = None
    return payload, model


def validate_controlled_live_smoke_artifacts(
    *,
    report_path: Path,
    expected_frame_count: int | None = 1,
    min_frame_count: int | None = None,
    max_frame_count: int | None = None,
    events_jsonl_path: Path | None = None,
    created_at: datetime | None = None,
) -> ControlledLiveSmokeValidationReport:
    payload, model = read_controlled_live_smoke_report(report_path)
    events = _read_events(events_jsonl_path) if events_jsonl_path is not None else []
    captured_frame_count = _int_value(payload, "captured_frame_count")
    status = _object_value(payload, "status")
    action_logging_mode = _action_logging_mode(payload)
    dryrun_orchestration_mode = _dryrun_orchestration_mode(payload)
    real_input_mode = _real_input_mode(payload)
    no_real_input_mode = real_input_mode == "disabled"
    checks = [
        _check(
            "report_model_valid",
            model is not None,
            "report validates against ControlledLiveSmokeReport",
            "report does not validate against ControlledLiveSmokeReport",
        ),
        _check(
            "runtime_mode_observation_only",
            payload.get("runtime_mode") == "observation_only",
            "runtime_mode is observation_only",
            "runtime_mode must be observation_only",
        ),
        _check(
            "mode_official_screen_only",
            payload.get("mode") == "official_screen_only",
            "mode is official_screen_only",
            "mode must be official_screen_only",
        ),
        _check(
            "no_input_sent",
            (payload.get("no_input_sent") is True) if no_real_input_mode else True,
            "no_input_sent is true or a real input mode permits input",
            "no_input_sent must be true unless a real input mode permits input",
        ),
        _check(
            "inputs_sent_zero",
            (_int_value(payload, "inputs_sent") == 0) if no_real_input_mode else True,
            "inputs_sent is zero or a real input mode permits input",
            "inputs_sent must be zero unless a real input mode permits input",
        ),
        _check_expected_frame_count(
            captured_frame_count=captured_frame_count,
            expected_frame_count=expected_frame_count,
        ),
        _check_frame_count_range(
            captured_frame_count=captured_frame_count,
            min_frame_count=min_frame_count,
            max_frame_count=max_frame_count,
        ),
        _check_screenshot_paths(payload),
        _check_evidence_ids(payload),
        _check_dryrun_orchestration_mode(dryrun_orchestration_mode),
        _check_real_input_mode(real_input_mode),
        _check_count_matches(
            "screenshot_count_matches_frame_count",
            len(_list_value(payload, "screenshot_paths")),
            captured_frame_count,
            "screenshot_count",
        ),
        _check_count_matches(
            "evidence_count_matches_frame_count",
            len(_list_value(payload, "evidence_ids")),
            captured_frame_count,
            "evidence_count",
        ),
        _check_action_logging_mode(action_logging_mode),
        _check_actions_requested_policy(
            payload,
            status,
            action_logging_mode,
            dryrun_orchestration_mode,
            real_input_mode,
        ),
        _check_requested_actions(
            payload,
            status,
            action_logging_mode,
            dryrun_orchestration_mode,
            real_input_mode,
        ),
        _check_executed_actions(payload, real_input_mode),
        _check_dryrun_tasks(payload, dryrun_orchestration_mode),
        _check_real_wait_only_input_safety(payload, status, real_input_mode),
        _check_single_directional_tap_input_safety(payload, status, real_input_mode),
        _check_single_directional_tap_pre_post_screenshot_evidence(payload, real_input_mode),
        _check(
            "stop_reason_max_frames_reached",
            status.get("stop_reason") == "max_frames_reached",
            "stop_reason is max_frames_reached",
            "stop_reason must be max_frames_reached",
        ),
        _check_autonomy_flags(payload),
        _check_event_kinds(events),
        _check_frame_events(events),
        _check_forbidden_markers(payload, events),
        _check_hidden_fields(payload, events),
    ]
    error_count = sum(1 for check in checks if not check.passed and check.severity == "error")
    return ControlledLiveSmokeValidationReport(
        created_at=created_at or datetime.now(UTC),
        source_report_path=report_path,
        events_jsonl_path=events_jsonl_path,
        expected_frame_count=expected_frame_count,
        min_frame_count=min_frame_count,
        max_frame_count=max_frame_count,
        status=ControlledLiveSmokeValidationStatus(
            passed=error_count == 0,
            check_count=len(checks),
            error_count=error_count,
        ),
        checks=tuple(checks),
    )


def write_controlled_live_smoke_validation_report(
    report: ControlledLiveSmokeValidationReport,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    if path.exists() and not overwrite:
        msg = f"controlled smoke validation report already exists: {path}"
        raise FileExistsError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_deterministic_json() + "\n", encoding="utf-8")
    return path


def default_validation_report_path(report_path: Path) -> Path:
    return report_path.with_name(f"{report_path.stem}_validation.json")


def _check(
    name: str,
    passed: bool,
    passed_message: str,
    failed_message: str,
) -> ControlledLiveSmokeValidationCheck:
    return ControlledLiveSmokeValidationCheck(
        name=name,
        passed=passed,
        severity="info" if passed else "error",
        message=passed_message if passed else failed_message,
    )


def _check_expected_frame_count(
    *,
    captured_frame_count: int,
    expected_frame_count: int | None,
) -> ControlledLiveSmokeValidationCheck:
    if expected_frame_count is None:
        return _check(
            "captured_frame_count",
            True,
            "captured_frame_count exact check not requested",
            "unreachable",
        )
    return _check(
        "captured_frame_count",
        captured_frame_count == expected_frame_count,
        f"captured_frame_count is {expected_frame_count}",
        f"captured_frame_count must be {expected_frame_count}",
    )


def _check_frame_count_range(
    *,
    captured_frame_count: int,
    min_frame_count: int | None,
    max_frame_count: int | None,
) -> ControlledLiveSmokeValidationCheck:
    if min_frame_count is None and max_frame_count is None:
        return _check(
            "captured_frame_count_in_range",
            True,
            "captured_frame_count range check not requested",
            "unreachable",
        )
    min_ok = min_frame_count is None or captured_frame_count >= min_frame_count
    max_ok = max_frame_count is None or captured_frame_count <= max_frame_count
    bounds = _format_bounds(min_frame_count=min_frame_count, max_frame_count=max_frame_count)
    return _check(
        "captured_frame_count_in_range",
        min_ok and max_ok,
        f"captured_frame_count is in range {bounds}",
        f"captured_frame_count must be in range {bounds}",
    )


def _check_count_matches(
    name: str,
    actual: int,
    expected: int,
    label: str,
) -> ControlledLiveSmokeValidationCheck:
    return _check(
        name,
        actual == expected,
        f"{label} matches captured_frame_count",
        f"{label} must match captured_frame_count",
    )


def _check_autonomy_flags(payload: dict[str, object]) -> ControlledLiveSmokeValidationCheck:
    active = [
        field
        for field in (
            "autonomous_planner_active",
            "manager_orchestration_active",
            "body_control_active",
            "learning_active",
            "bridge_active",
            "ocr_active",
        )
        if payload.get(field) is True
    ]
    return _check(
        "autonomy_flags_inactive",
        not active,
        "planner, manager, body, learning, bridge, and OCR flags are inactive",
        f"autonomy/runtime flags must be inactive: {', '.join(active)}",
    )


def _check_screenshot_paths(payload: dict[str, object]) -> ControlledLiveSmokeValidationCheck:
    paths = payload.get("screenshot_paths")
    valid = (
        isinstance(paths, list) and bool(paths) and all(Path(str(path)).is_file() for path in paths)
    )
    return _check(
        "screenshot_paths_exist",
        valid,
        "all screenshot_paths exist",
        "screenshot_paths must be non-empty and point to existing files",
    )


def _check_single_directional_tap_pre_post_screenshot_evidence(
    payload: dict[str, object],
    real_input_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    if real_input_mode != "single_directional_tap":
        return _check(
            "single_directional_tap_pre_post_screenshot_evidence",
            True,
            "single directional tap pre/post screenshot evidence check is disabled",
            "unreachable",
        )
    failures = _pre_post_screenshot_evidence_failures(payload)
    return _check(
        "single_directional_tap_pre_post_screenshot_evidence",
        not failures,
        "pre/post screenshot evidence exists and target window dimensions match",
        "; ".join(failures),
    )


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
            referenced_evidence.append((label, evidence_id, dimensions))

    pre_dimensions = {
        dimensions
        for label, _evidence_id, dimensions in referenced_evidence
        if label == "pre-input"
    }
    post_dimensions = {
        dimensions
        for label, _evidence_id, dimensions in referenced_evidence
        if label == "post-input"
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


def _action_logging_mode(payload: dict[str, object]) -> str:
    value = payload.get("action_logging_mode")
    return value if isinstance(value, str) else "disabled"


def _dryrun_orchestration_mode(payload: dict[str, object]) -> str:
    value = payload.get("dryrun_orchestration_mode")
    return value if isinstance(value, str) else "disabled"


def _real_input_mode(payload: dict[str, object]) -> str:
    value = payload.get("real_input_mode")
    return value if isinstance(value, str) else "disabled"


def _format_bounds(*, min_frame_count: int | None, max_frame_count: int | None) -> str:
    lower = "*" if min_frame_count is None else str(min_frame_count)
    upper = "*" if max_frame_count is None else str(max_frame_count)
    return f"{lower}..{upper}"


def _check_evidence_ids(payload: dict[str, object]) -> ControlledLiveSmokeValidationCheck:
    evidence_ids = payload.get("evidence_ids")
    valid = (
        isinstance(evidence_ids, list)
        and bool(evidence_ids)
        and all(isinstance(value, str) and value for value in evidence_ids)
    )
    return _check(
        "evidence_ids_present",
        valid,
        "evidence_ids are present",
        "evidence_ids must be non-empty strings",
    )


def _check_action_logging_mode(mode: str) -> ControlledLiveSmokeValidationCheck:
    return _check(
        "action_logging_mode_allowed",
        mode in {"disabled", "wait_only_noop"},
        "action_logging_mode is allowed",
        "action_logging_mode must be disabled or wait_only_noop",
    )


def _check_dryrun_orchestration_mode(mode: str) -> ControlledLiveSmokeValidationCheck:
    return _check(
        "dryrun_orchestration_mode_allowed",
        mode in {"disabled", "wait_only"},
        "dryrun_orchestration_mode is allowed",
        "dryrun_orchestration_mode must be disabled or wait_only",
    )


def _check_real_input_mode(mode: str) -> ControlledLiveSmokeValidationCheck:
    return _check(
        "real_input_mode_allowed",
        mode in {"disabled", "wait_only_noop", "single_directional_tap"},
        "real_input_mode is allowed",
        "real_input_mode must be disabled, wait_only_noop, or single_directional_tap",
    )


def _check_actions_requested_policy(
    payload: dict[str, object],
    status: dict[str, object],
    action_logging_mode: str,
    dryrun_orchestration_mode: str,
    real_input_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    actions_requested = _int_value(status, "actions_requested")
    if real_input_mode == "wait_only_noop":
        return _check(
            "actions_requested_policy",
            actions_requested > 0
            and actions_requested == len(_list_value(payload, "requested_actions")),
            "actions_requested matches real wait no-op intents",
            "actions_requested must match requested_actions in real wait-only mode",
        )
    if real_input_mode == "single_directional_tap":
        return _check(
            "actions_requested_policy",
            actions_requested == 1 and len(_list_value(payload, "requested_actions")) == 1,
            "actions_requested matches the single directional tap",
            "actions_requested must be exactly one in single directional tap mode",
        )
    if dryrun_orchestration_mode == "wait_only":
        return _check(
            "actions_requested_policy",
            actions_requested > 0
            and actions_requested == len(_list_value(payload, "requested_actions")),
            "actions_requested matches requested dry-run wait intents",
            "actions_requested must match requested_actions in wait_only dry-run mode",
        )
    if action_logging_mode == "wait_only_noop":
        return _check(
            "actions_requested_policy",
            actions_requested == len(_list_value(payload, "requested_actions")),
            "actions_requested matches requested wait intents",
            "actions_requested must match requested_actions in wait_only_noop mode",
        )
    return _check(
        "actions_requested_zero",
        actions_requested == 0,
        "actions_requested is zero",
        "actions_requested must be zero unless wait_only_noop is enabled",
    )


def _check_requested_actions(
    payload: dict[str, object],
    status: dict[str, object],
    action_logging_mode: str,
    dryrun_orchestration_mode: str,
    real_input_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    requested_actions = _list_value(payload, "requested_actions")
    if real_input_mode == "wait_only_noop":
        return _check_real_wait_only_requested_actions(payload, status)
    if real_input_mode == "single_directional_tap":
        return _check_single_directional_tap_requested_actions(payload, status)
    if action_logging_mode == "disabled" and dryrun_orchestration_mode == "disabled":
        return _check(
            "requested_actions_empty",
            not requested_actions,
            "requested_actions is empty",
            "requested_actions must be empty when action logging is disabled",
        )
    invalid: list[str] = []
    for index, action in enumerate(requested_actions):
        if not isinstance(action, dict):
            invalid.append(f"{index}:not_object")
            continue
        if action.get("action") != "wait":
            invalid.append(f"{index}:action")
        if action.get("requested") is not True:
            invalid.append(f"{index}:requested")
        if action.get("executed") is not False:
            invalid.append(f"{index}:executed")
        if action.get("input_sent") is not False:
            invalid.append(f"{index}:input_sent")
        expected_reason = (
            "dryrun_orchestration_wait_only"
            if dryrun_orchestration_mode == "wait_only"
            else "noop_action_logging"
        )
        if action.get("reason") != expected_reason:
            invalid.append(f"{index}:reason")
    actions_requested = _int_value(status, "actions_requested")
    valid = bool(requested_actions) and not invalid and actions_requested == len(requested_actions)
    check_name = (
        "dryrun_wait_only_requested_actions_safe"
        if dryrun_orchestration_mode == "wait_only"
        else "wait_only_noop_requested_actions_safe"
    )
    return _check(
        check_name,
        valid,
        "requested actions are non-executed wait intents",
        f"requested actions must be non-executed wait intents: {', '.join(invalid)}",
    )


def _check_real_wait_only_requested_actions(
    payload: dict[str, object],
    status: dict[str, object],
) -> ControlledLiveSmokeValidationCheck:
    requested_actions = _list_value(payload, "requested_actions")
    invalid: list[str] = []
    for index, action in enumerate(requested_actions):
        if not isinstance(action, dict):
            invalid.append(f"{index}:not_object")
            continue
        if action.get("action") != "wait":
            invalid.append(f"{index}:action")
        if action.get("requested") is not True:
            invalid.append(f"{index}:requested")
        if action.get("executed") is not True:
            invalid.append(f"{index}:executed")
        if action.get("input_sent") is not True:
            invalid.append(f"{index}:input_sent")
        if action.get("reason") != "real_wait_only_noop":
            invalid.append(f"{index}:reason")
    actions_requested = _int_value(status, "actions_requested")
    valid = bool(requested_actions) and not invalid and actions_requested == len(requested_actions)
    return _check(
        "real_wait_only_requested_actions_safe",
        valid,
        "requested actions are executed wait no-ops",
        f"requested actions must be executed wait no-ops: {', '.join(invalid)}",
    )


def _check_single_directional_tap_requested_actions(
    payload: dict[str, object],
    status: dict[str, object],
) -> ControlledLiveSmokeValidationCheck:
    requested_actions = _list_value(payload, "requested_actions")
    invalid: list[str] = []
    for index, action in enumerate(requested_actions):
        if not isinstance(action, dict):
            invalid.append(f"{index}:not_object")
            continue
        if action.get("action") != SINGLE_DIRECTIONAL_TAP_ACTION:
            invalid.append(f"{index}:action")
        if action.get("requested") is not True:
            invalid.append(f"{index}:requested")
        if action.get("executed") is not True:
            invalid.append(f"{index}:executed")
        if action.get("input_sent") is not True:
            invalid.append(f"{index}:input_sent")
        if action.get("reason") != "single_directional_tap":
            invalid.append(f"{index}:reason")
    actions_requested = _int_value(status, "actions_requested")
    valid = len(requested_actions) == 1 and not invalid and actions_requested == 1
    return _check(
        "single_directional_tap_requested_action_safe",
        valid,
        "requested action is one executed move_right_short",
        f"requested action must be one executed move_right_short: {', '.join(invalid)}",
    )


def _check_executed_actions(
    payload: dict[str, object],
    real_input_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    executed_actions = _list_value(payload, "executed_actions")
    if real_input_mode == "wait_only_noop":
        invalid = [
            f"{index}:action"
            for index, action in enumerate(executed_actions)
            if not isinstance(action, dict)
            or action.get("action") != "wait"
            or action.get("executed") is not True
            or action.get("input_sent") is not True
            or action.get("reason") != "real_wait_only_noop"
        ]
        return _check(
            "executed_actions_wait_only",
            bool(executed_actions) and not invalid,
            "executed actions are wait no-ops",
            f"executed actions must be wait no-ops: {', '.join(invalid)}",
        )
    if real_input_mode == "single_directional_tap":
        invalid = [
            f"{index}:action"
            for index, action in enumerate(executed_actions)
            if not isinstance(action, dict)
            or action.get("action") != SINGLE_DIRECTIONAL_TAP_ACTION
            or action.get("executed") is not True
            or action.get("input_sent") is not True
            or action.get("reason") != "single_directional_tap"
        ]
        return _check(
            "executed_actions_single_directional_tap",
            len(executed_actions) == 1 and not invalid,
            "executed action is one move_right_short",
            f"executed action must be one move_right_short: {', '.join(invalid)}",
        )
    return _check(
        "executed_actions_empty",
        not executed_actions,
        "executed_actions is empty",
        "executed_actions must remain empty",
    )


def _check_real_wait_only_input_safety(
    payload: dict[str, object],
    status: dict[str, object],
    real_input_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    if real_input_mode != "wait_only_noop":
        return _check(
            "real_wait_only_input_safety",
            True,
            "real wait-only mode is disabled",
            "unreachable",
        )
    inputs_sent = _int_value(payload, "inputs_sent")
    actions_requested = _int_value(status, "actions_requested")
    executed_action_count = _int_value(payload, "executed_action_count")
    executed_wait_count = _int_value(payload, "executed_wait_count")
    allowed_input_count = _int_value(payload, "allowed_input_count")
    forbidden_input_count = _int_value(payload, "forbidden_input_count")
    forbidden_executed_action_count = _int_value(payload, "forbidden_executed_action_count")
    focus_guard_check_count = _int_value(payload, "focus_guard_check_count")
    focus_guard_pre_input_pass_count = _int_value(payload, "focus_guard_pre_input_pass_count")
    emergency_stop_check_count = _int_value(payload, "emergency_stop_check_count")
    emergency_stop_pre_input_clear_count = _int_value(
        payload,
        "emergency_stop_pre_input_clear_count",
    )
    capture_script = payload.get("capture_script")
    checks = {
        "allow_real_input_true": payload.get("allow_real_input") is True,
        "real_wait_only_active": payload.get("real_wait_only_active") is True,
        "official_screen_only": payload.get("official_screen_only") is True,
        "inputs_sent_positive": inputs_sent > 0,
        "no_input_sent_false": payload.get("no_input_sent") is False,
        "actions_requested_match_inputs": actions_requested == inputs_sent,
        "executed_action_count_match": executed_action_count == inputs_sent,
        "executed_wait_count_match": executed_wait_count == inputs_sent,
        "allowed_input_count_match": allowed_input_count == inputs_sent,
        "forbidden_input_count_zero": forbidden_input_count == 0,
        "forbidden_executed_action_count_zero": forbidden_executed_action_count == 0,
        "focus_guard_checked": focus_guard_check_count >= inputs_sent,
        "focus_guard_passed": focus_guard_pre_input_pass_count >= inputs_sent,
        "emergency_stop_checked": emergency_stop_check_count >= inputs_sent,
        "emergency_stop_clear": emergency_stop_pre_input_clear_count >= inputs_sent,
        "rate_limit_enabled": payload.get("rate_limit_enabled") is True,
        "max_input_count_positive": _int_value(payload, "max_input_count") > 0,
        "max_input_count_not_exceeded": payload.get("max_input_count_exceeded") is False,
        "capture_script_versioned": (
            isinstance(capture_script, str)
            and "capture_active_window_ppm.sh" in capture_script
            and "capture_one_frame_ppm.sh" not in capture_script
        ),
        "hidden_state_violation_count_zero": _int_value(
            payload,
            "hidden_state_violation_count",
        )
        == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return _check(
        "real_wait_only_input_safety",
        not failed,
        "real wait-only input safety checks passed",
        f"real wait-only input safety checks failed: {', '.join(failed)}",
    )


def _check_single_directional_tap_input_safety(
    payload: dict[str, object],
    status: dict[str, object],
    real_input_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    if real_input_mode != "single_directional_tap":
        return _check(
            "single_directional_tap_input_safety",
            True,
            "single directional tap mode is disabled",
            "unreachable",
        )
    requested_actions = _list_value(payload, "requested_actions")
    executed_actions = _list_value(payload, "executed_actions")
    pre_input_evidence = _list_value(payload, "pre_input_evidence_ids")
    post_input_evidence = _list_value(payload, "post_input_evidence_ids")
    checks = {
        "mode_official_screen_only": payload.get("mode") == "official_screen_only",
        "official_screen_only": payload.get("official_screen_only") is True,
        "allow_real_input_true": payload.get("allow_real_input") is True,
        "allowed_real_primitives_exact": payload.get("allowed_real_primitives")
        == [SINGLE_DIRECTIONAL_TAP_ACTION],
        "inputs_sent_one": _int_value(payload, "inputs_sent") == 1,
        "no_input_sent_false": payload.get("no_input_sent") is False,
        "actions_requested_one": _int_value(status, "actions_requested") == 1,
        "requested_action_count_one": len(requested_actions) == 1,
        "executed_action_count_one": _int_value(payload, "executed_action_count") == 1,
        "executed_actions_len_one": len(executed_actions) == 1,
        "executed_action_names_exact": _action_names(executed_actions)
        == [SINGLE_DIRECTIONAL_TAP_ACTION],
        "executed_wait_count_zero": _int_value(payload, "executed_wait_count") == 0,
        "allowed_input_count_one": _int_value(payload, "allowed_input_count") == 1,
        "forbidden_input_count_zero": _int_value(payload, "forbidden_input_count") == 0,
        "forbidden_executed_action_count_zero": _int_value(
            payload,
            "forbidden_executed_action_count",
        )
        == 0,
        "focus_guard_check_count_one": _int_value(payload, "focus_guard_check_count") == 1,
        "focus_guard_pre_input_pass_count_one": _int_value(
            payload,
            "focus_guard_pre_input_pass_count",
        )
        == 1,
        "emergency_stop_check_count_one": _int_value(payload, "emergency_stop_check_count") == 1,
        "emergency_stop_pre_input_clear_count_one": _int_value(
            payload,
            "emergency_stop_pre_input_clear_count",
        )
        == 1,
        "max_input_count_one": _int_value(payload, "max_input_count") == 1,
        "max_input_count_not_exceeded": payload.get("max_input_count_exceeded") is False,
        "pre_input_evidence_present": bool(pre_input_evidence)
        and all(isinstance(value, str) and value for value in pre_input_evidence),
        "post_input_evidence_present": bool(post_input_evidence)
        and all(isinstance(value, str) and value for value in post_input_evidence),
        "capture_script_active_window": payload.get("capture_script")
        == "./scripts/capture_active_window_ppm.sh",
        "subsystems_inactive": all(
            payload.get(field) is False
            for field in (
                "autonomous_planner_active",
                "manager_orchestration_active",
                "body_control_active",
                "bridge_active",
                "ocr_active",
                "learning_active",
            )
        ),
        "hidden_state_violation_count_zero": _int_value(
            payload,
            "hidden_state_violation_count",
        )
        == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return _check(
        "single_directional_tap_input_safety",
        not failed,
        "single directional tap input safety checks passed",
        f"single directional tap input safety checks failed: {', '.join(failed)}",
    )


def _check_dryrun_tasks(
    payload: dict[str, object],
    dryrun_orchestration_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    dryrun_tasks = _list_value(payload, "dryrun_tasks")
    task_count = _int_value(payload, "dryrun_task_count")
    skill_count = _int_value(payload, "dryrun_skill_count")
    if dryrun_orchestration_mode == "disabled":
        valid = not dryrun_tasks and task_count == 0 and skill_count == 0
        return _check(
            "dryrun_tasks_disabled",
            valid,
            "dry-run tasks are disabled",
            "dry-run tasks must be empty when dryrun orchestration is disabled",
        )

    invalid: list[str] = []
    for index, task in enumerate(dryrun_tasks):
        if not isinstance(task, dict):
            invalid.append(f"{index}:not_object")
            continue
        if task.get("static_goal") != "maintain_observation_without_input":
            invalid.append(f"{index}:static_goal")
        if task.get("selected_skill") != "wait":
            invalid.append(f"{index}:selected_skill")
        action_intent = task.get("action_intent")
        if not isinstance(action_intent, dict):
            invalid.append(f"{index}:action_intent")
            continue
        if action_intent.get("action") != "wait":
            invalid.append(f"{index}:action")
        if action_intent.get("requested") is not True:
            invalid.append(f"{index}:requested")
        if action_intent.get("executed") is not False:
            invalid.append(f"{index}:executed")
        if action_intent.get("input_sent") is not False:
            invalid.append(f"{index}:input_sent")
        if action_intent.get("reason") != "dryrun_orchestration_wait_only":
            invalid.append(f"{index}:reason")
    valid = (
        bool(dryrun_tasks)
        and not invalid
        and task_count == len(dryrun_tasks)
        and skill_count == len(dryrun_tasks)
    )
    return _check(
        "dryrun_wait_only_tasks_safe",
        valid,
        "dry-run wait-only tasks are safe",
        f"dry-run wait-only tasks must be static wait tasks: {', '.join(invalid)}",
    )


def _check_event_kinds(events: list[dict[str, object]]) -> ControlledLiveSmokeValidationCheck:
    if not events:
        return _check("event_kinds_allowed", True, "no external events provided", "unreachable")
    invalid = [
        str(event.get("event_type"))
        for event in events
        if event.get("event_type") not in ALLOWED_RUNTIME_EVENT_KINDS
    ]
    return _check(
        "event_kinds_allowed",
        not invalid,
        "event kinds are allowed",
        f"event kinds are not allowed: {', '.join(invalid)}",
    )


def _check_frame_events(events: list[dict[str, object]]) -> ControlledLiveSmokeValidationCheck:
    frame_events = [event for event in events if event.get("event_type") == "frame_captured"]
    if not frame_events:
        return _check(
            "frame_events_have_evidence",
            True,
            "no external frame events provided",
            "unreachable",
        )
    valid = all(event.get("evidence_id") and event.get("screenshot_path") for event in frame_events)
    return _check(
        "frame_events_have_evidence",
        valid,
        "frame events include evidence_id and screenshot_path",
        "frame events must include evidence_id and screenshot_path",
    )


def _check_forbidden_markers(
    payload: dict[str, object],
    events: list[dict[str, object]],
) -> ControlledLiveSmokeValidationCheck:
    markers = tuple(
        marker
        for marker in ("".join(parts) for parts in FORBIDDEN_MARKER_PARTS)
        if not (
            payload.get("real_input_mode") == "single_directional_tap"
            and marker == SINGLE_DIRECTIONAL_TAP_ACTION
        )
    )
    found = sorted(set(_find_forbidden_markers({"report": payload, "events": events}, markers)))
    return _check(
        "forbidden_runtime_markers_absent",
        not found,
        "forbidden runtime markers are absent",
        f"forbidden runtime markers found: {', '.join(found)}",
    )


def _check_hidden_fields(
    payload: dict[str, object],
    events: list[dict[str, object]],
) -> ControlledLiveSmokeValidationCheck:
    found = sorted(set(_find_forbidden_keys({"report": payload, "events": events})))
    return _check(
        "hidden_state_fields_absent",
        not found,
        "hidden-state fields are absent",
        f"hidden-state fields found: {', '.join(found)}",
    )


def _action_names(actions: list[object]) -> list[str]:
    names: list[str] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        name = action.get("action")
        if isinstance(name, str):
            names.append(name)
    return names


def _find_forbidden_keys(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_HIDDEN_FIELDS:
                found.append(key)
            found.extend(_find_forbidden_keys(child))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_forbidden_keys(item))
    return found


def _find_forbidden_markers(value: object, markers: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        lowered = value.lower()
        found.extend(marker for marker in markers if marker in lowered)
    elif isinstance(value, dict):
        for child in value.values():
            found.extend(_find_forbidden_markers(child, markers))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_forbidden_markers(item, markers))
    return found


def _read_events(path: Path) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if isinstance(event, dict):
            events.append(event)
    return events
