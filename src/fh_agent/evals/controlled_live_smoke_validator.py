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
    expected_frame_count: int
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
    expected_frame_count: int = 1,
    events_jsonl_path: Path | None = None,
    created_at: datetime | None = None,
) -> ControlledLiveSmokeValidationReport:
    payload, model = read_controlled_live_smoke_report(report_path)
    events = _read_events(events_jsonl_path) if events_jsonl_path is not None else []
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
            "no_input_sent",
            payload.get("no_input_sent") is True,
            "no_input_sent is true",
            "no_input_sent must be true",
        ),
        _check(
            "captured_frame_count",
            payload.get("captured_frame_count") == expected_frame_count,
            f"captured_frame_count is {expected_frame_count}",
            f"captured_frame_count must be {expected_frame_count}",
        ),
        _check_screenshot_paths(payload),
        _check_evidence_ids(payload),
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
