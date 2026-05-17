import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from fh_agent.evals.controlled_live_smoke_runner import ControlledLiveSmokeReport

VALIDATION_REPORT_VERSION = "1"
ValidationSeverity = Literal["info", "error"]
ValidationStatus = Literal["passed", "failed"]

ALLOWED_RUNTIME_EVENT_KINDS: tuple[str, ...] = (
    "runtime_start",
    "frame_captured",
    "noop_action_intent",
    "wait_intent",
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
            payload.get("no_input_sent") is True,
            "no_input_sent is true",
            "no_input_sent must be true",
        ),
        _check(
            "inputs_sent_zero",
            _int_value(payload, "inputs_sent") == 0,
            "inputs_sent is zero",
            "inputs_sent must be zero",
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
        _check_actions_requested_policy(payload, status, action_logging_mode),
        _check_requested_actions(payload, status, action_logging_mode),
        _check_executed_actions(payload),
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
        )
        if payload.get(field) is True
    ]
    return _check(
        "autonomy_flags_inactive",
        not active,
        "planner, manager, body, learning, and bridge flags are inactive",
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


def _object_value(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_value(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) else 0


def _action_logging_mode(payload: dict[str, object]) -> str:
    value = payload.get("action_logging_mode")
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


def _check_actions_requested_policy(
    payload: dict[str, object],
    status: dict[str, object],
    action_logging_mode: str,
) -> ControlledLiveSmokeValidationCheck:
    actions_requested = _int_value(status, "actions_requested")
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
) -> ControlledLiveSmokeValidationCheck:
    requested_actions = _list_value(payload, "requested_actions")
    if action_logging_mode == "disabled":
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
        if action.get("reason") != "noop_action_logging":
            invalid.append(f"{index}:reason")
    actions_requested = _int_value(status, "actions_requested")
    valid = bool(requested_actions) and not invalid and actions_requested == len(requested_actions)
    return _check(
        "wait_only_noop_requested_actions_safe",
        valid,
        "requested actions are non-executed wait intents",
        f"requested actions must be non-executed wait intents: {', '.join(invalid)}",
    )


def _check_executed_actions(payload: dict[str, object]) -> ControlledLiveSmokeValidationCheck:
    executed_actions = _list_value(payload, "executed_actions")
    return _check(
        "executed_actions_empty",
        not executed_actions,
        "executed_actions is empty",
        "executed_actions must remain empty",
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
    markers = tuple("".join(parts) for parts in FORBIDDEN_MARKER_PARTS)
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
