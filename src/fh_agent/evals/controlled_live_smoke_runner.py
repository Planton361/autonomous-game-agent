import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from fh_agent.evals.live_audit_pipeline import LiveAuditPipelineResult
from fh_agent.evals.live_run_manifest import ManifestMode
from fh_agent.evals.live_smoke_plan import LiveSmokeRunPlan
from fh_agent.evals.live_smoke_report import read_live_smoke_plan

RUNNER_REPORT_VERSION = "1"
CONTROLLED_LIVE_SMOKE_MAX_FRAMES = 30

RuntimeEventType = Literal[
    "runtime_start",
    "frame_captured",
    "noop_action_intent",
    "wait_intent",
    "stop_condition_triggered",
    "runtime_end",
]
StopReason = Literal[
    "completed",
    "focus_lost",
    "emergency_stop_triggered",
    "max_frames_reached",
    "max_duration_reached",
    "max_actions_reached",
    "capture_error",
    "hidden_state_violation",
]


class FocusCheck(Protocol):
    def __call__(self) -> bool: ...


class EmergencyStopAvailableCheck(Protocol):
    def __call__(self) -> bool: ...


class EmergencyStopTriggeredCheck(Protocol):
    def __call__(self) -> bool: ...


class CaptureFrame(Protocol):
    def __call__(self) -> "ControlledLiveSmokeFrame": ...


class EventLogger(Protocol):
    def __call__(self, event: "ControlledLiveSmokeEvent") -> None: ...


class ControlledLiveSmokeFrame(BaseModel):
    """Frame metadata returned by an injected capture adapter."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    screenshot_path: Path | None = None
    timestamp: datetime | None = None
    width: int | None = None
    height: int | None = None
    sha256: str | None = None


class ControlledLiveSmokeEvidence(BaseModel):
    """Screenshot evidence metadata captured by the observation-only runner."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    screenshot_path: Path | None = None
    timestamp: datetime | None = None
    width: int | None = None
    height: int | None = None
    sha256: str | None = None


class PpmHeaderParseDiagnostic(BaseModel):
    """Non-image PPM header parse details for capture failures."""

    model_config = ConfigDict(extra="forbid")

    present: bool
    valid: bool
    width: int | None = None
    height: int | None = None
    max_value: int | None = None
    error: str | None = None


class CaptureErrorDiagnostic(BaseModel):
    """Capture failure diagnostics safe for JSON reports."""

    model_config = ConfigDict(extra="forbid")

    command: tuple[str, ...] = ()
    return_code: int | None = None
    stderr_excerpt: str = ""
    stdout_byte_count: int = 0
    ppm_header: PpmHeaderParseDiagnostic | None = None
    exception_message: str


class ControlledLiveSmokeStatus(BaseModel):
    """Final skeleton-run status."""

    model_config = ConfigDict(extra="forbid")

    started: bool
    finished: bool
    stop_reason: StopReason
    frames_captured: int = 0
    actions_requested: int = 0


class ControlledLiveSmokeEvent(BaseModel):
    """Structured event emitted by the controlled smoke skeleton."""

    model_config = ConfigDict(extra="forbid")

    event_type: RuntimeEventType
    created_at: datetime
    message: str
    frame_index: int | None = None
    evidence_id: str | None = None
    screenshot_path: Path | None = None
    stop_reason: StopReason | None = None


class ControlledLiveSmokeResult(BaseModel):
    """In-memory result for a user-started controlled smoke skeleton."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: datetime
    user_started: bool
    allow_real_input: bool = False
    official_run_allowed: bool
    execution_enabled: bool = False
    mode: ManifestMode
    status: ControlledLiveSmokeStatus
    events: tuple[ControlledLiveSmokeEvent, ...]
    report_path: Path

    @model_validator(mode="after")
    def execution_must_stay_disabled(self) -> "ControlledLiveSmokeResult":
        if self.execution_enabled:
            msg = "controlled smoke skeleton must not enable autonomous execution"
            raise ValueError(msg)
        return self


class ControlledLiveSmokeReport(BaseModel):
    """Final report for a controlled live-smoke skeleton run."""

    model_config = ConfigDict(extra="forbid")

    report_version: str = RUNNER_REPORT_VERSION
    run_id: str
    created_at: datetime
    user_started: bool
    allow_real_input: bool = False
    execution_enabled: bool = False
    official_run_allowed: bool
    mode: ManifestMode
    status: ControlledLiveSmokeStatus
    event_count: int
    runtime_mode: Literal["observation_only"] = "observation_only"
    no_input_sent: bool = True
    captured_frame_count: int
    evidence_ids: tuple[str, ...] = ()
    screenshot_paths: tuple[Path, ...] = ()
    screenshot_evidence: tuple[ControlledLiveSmokeEvidence, ...] = ()
    capture_error_diagnostic: CaptureErrorDiagnostic | None = None
    autonomous_planner_active: bool = False
    manager_orchestration_active: bool = False
    body_control_active: bool = False
    learning_active: bool = False

    @model_validator(mode="after")
    def report_must_not_claim_autonomy(self) -> "ControlledLiveSmokeReport":
        if self.execution_enabled:
            msg = "controlled smoke report must not enable autonomous execution"
            raise ValueError(msg)
        if not self.no_input_sent:
            msg = "controlled smoke report must not claim input was sent"
            raise ValueError(msg)
        if (
            self.autonomous_planner_active
            or self.manager_orchestration_active
            or self.body_control_active
            or self.learning_active
        ):
            msg = "controlled smoke report must not claim autonomous control"
            raise ValueError(msg)
        return self

    def to_deterministic_json(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def read_live_audit_pipeline_result(path: Path) -> LiveAuditPipelineResult:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return LiveAuditPipelineResult.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"invalid live-audit pipeline summary: {path}: {exc}"
        raise ValueError(msg) from exc


def run_controlled_live_smoke(
    *,
    user_started: bool,
    pipeline_summary_path: Path | None = None,
    smoke_plan_path: Path | None = None,
    focus_check: FocusCheck,
    emergency_stop_available: EmergencyStopAvailableCheck,
    emergency_stop_triggered: EmergencyStopTriggeredCheck,
    capture_frame: CaptureFrame,
    log_event: EventLogger,
    allow_real_input: bool = False,
    max_frames: int | None = None,
    clock: Callable[[], float] = monotonic,
    now: Callable[[], datetime] | None = None,
    report_path: Path | None = None,
    output_run_dir: Path | None = None,
    overwrite: bool = False,
) -> ControlledLiveSmokeResult:
    """Run a user-started observation-only smoke skeleton through injected adapters."""

    timestamp = (now or _utc_now)()
    if not user_started:
        msg = "controlled live smoke requires user_started=True"
        raise ValueError(msg)

    plan = _load_allowed_plan(
        pipeline_summary_path=pipeline_summary_path,
        smoke_plan_path=smoke_plan_path,
    )
    if not focus_check():
        msg = "focus check failed before controlled live smoke start"
        raise ValueError(msg)
    if not emergency_stop_available():
        msg = "emergency stop check is unavailable"
        raise ValueError(msg)
    if emergency_stop_triggered():
        msg = "emergency stop is already triggered"
        raise ValueError(msg)
    if allow_real_input and not focus_check():
        msg = "focus check failed with allow_real_input=True"
        raise ValueError(msg)

    effective_run_id = output_run_dir.name if output_run_dir is not None else plan.run_id
    resolved_report_path = _resolve_report_path(
        plan=plan,
        report_path=report_path,
        output_run_dir=output_run_dir,
    )
    events: list[ControlledLiveSmokeEvent] = []
    frames: list[ControlledLiveSmokeFrame] = []
    capture_error_diagnostic: CaptureErrorDiagnostic | None = None
    frame_count = 0
    action_count = 0
    start = clock()
    effective_max_frames = (
        min(plan.safety_limits.max_frames, max_frames)
        if max_frames is not None
        else min(plan.safety_limits.max_frames, CONTROLLED_LIVE_SMOKE_MAX_FRAMES)
    )
    if max_frames is not None and not 1 <= max_frames <= CONTROLLED_LIVE_SMOKE_MAX_FRAMES:
        msg = (
            "controlled live smoke max_frames must be between "
            f"1 and {CONTROLLED_LIVE_SMOKE_MAX_FRAMES}"
        )
        raise ValueError(msg)

    _emit(
        events,
        log_event,
        ControlledLiveSmokeEvent(
            event_type="runtime_start",
            created_at=timestamp,
            message="controlled smoke skeleton started",
        ),
    )

    stop_reason: StopReason = "completed"
    while True:
        elapsed = clock() - start
        stop_reason = _pre_capture_stop_reason(
            focus_ok=focus_check(),
            emergency_triggered=emergency_stop_triggered(),
            elapsed=elapsed,
            max_duration_seconds=plan.safety_limits.max_duration_seconds,
            frame_count=frame_count,
            max_frames=effective_max_frames,
            action_count=action_count,
            max_actions=plan.safety_limits.max_actions,
        )
        if stop_reason != "completed":
            break

        try:
            frame = capture_frame()
        except Exception as exc:
            capture_error_diagnostic = _diagnostic_from_exception(exc)
            stop_reason = "capture_error"
            break
        frame_count += 1
        frames.append(frame)
        _emit(
            events,
            log_event,
            ControlledLiveSmokeEvent(
                event_type="frame_captured",
                created_at=(now or _utc_now)(),
                message="frame metadata captured by injected adapter",
                frame_index=frame_count - 1,
                evidence_id=frame.evidence_id,
                screenshot_path=frame.screenshot_path,
            ),
        )

        if frame_count >= effective_max_frames:
            stop_reason = "max_frames_reached"
            break
        if clock() - start >= plan.safety_limits.max_duration_seconds:
            stop_reason = "max_duration_reached"
            break

    _emit(
        events,
        log_event,
        ControlledLiveSmokeEvent(
            event_type="stop_condition_triggered",
            created_at=(now or _utc_now)(),
            message=f"controlled smoke skeleton stopped: {stop_reason}",
            stop_reason=stop_reason,
        ),
    )
    _emit(
        events,
        log_event,
        ControlledLiveSmokeEvent(
            event_type="runtime_end",
            created_at=(now or _utc_now)(),
            message="controlled smoke skeleton ended",
            stop_reason=stop_reason,
        ),
    )

    status = ControlledLiveSmokeStatus(
        started=True,
        finished=True,
        stop_reason=stop_reason,
        frames_captured=frame_count,
        actions_requested=action_count,
    )
    result = ControlledLiveSmokeResult(
        run_id=effective_run_id,
        created_at=timestamp,
        user_started=user_started,
        allow_real_input=allow_real_input,
        official_run_allowed=plan.official_run_allowed,
        mode=plan.mode,
        status=status,
        events=tuple(events),
        report_path=resolved_report_path,
    )
    report = ControlledLiveSmokeReport(
        run_id=result.run_id,
        created_at=result.created_at,
        user_started=result.user_started,
        allow_real_input=result.allow_real_input,
        official_run_allowed=result.official_run_allowed,
        mode=result.mode,
        status=result.status,
        event_count=len(result.events),
        captured_frame_count=result.status.frames_captured,
        evidence_ids=tuple(frame.evidence_id for frame in frames),
        screenshot_paths=tuple(
            frame.screenshot_path for frame in frames if frame.screenshot_path is not None
        ),
        screenshot_evidence=tuple(
            ControlledLiveSmokeEvidence(
                evidence_id=frame.evidence_id,
                screenshot_path=frame.screenshot_path,
                timestamp=frame.timestamp,
                width=frame.width,
                height=frame.height,
                sha256=frame.sha256,
            )
            for frame in frames
        ),
        capture_error_diagnostic=capture_error_diagnostic,
    )
    write_controlled_live_smoke_report(report, resolved_report_path, overwrite=overwrite)
    return result


def _resolve_report_path(
    *,
    plan: LiveSmokeRunPlan,
    report_path: Path | None,
    output_run_dir: Path | None,
) -> Path:
    if report_path is not None:
        return report_path
    if output_run_dir is not None:
        return output_run_dir / "reports" / "live_smoke_report.json"
    return plan.expected_outputs.final_report_path


def _diagnostic_from_exception(exc: Exception) -> CaptureErrorDiagnostic:
    diagnostic = getattr(exc, "diagnostic", None)
    if isinstance(diagnostic, CaptureErrorDiagnostic):
        return diagnostic
    return CaptureErrorDiagnostic(exception_message=str(exc) or exc.__class__.__name__)


def write_controlled_live_smoke_report(
    report: ControlledLiveSmokeReport,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    if path.exists() and not overwrite:
        msg = f"controlled smoke report already exists: {path}"
        raise FileExistsError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_deterministic_json() + "\n", encoding="utf-8")
    return path


def _load_allowed_plan(
    *,
    pipeline_summary_path: Path | None,
    smoke_plan_path: Path | None,
) -> LiveSmokeRunPlan:
    if pipeline_summary_path is None and smoke_plan_path is None:
        msg = "pipeline_summary_path or smoke_plan_path is required"
        raise ValueError(msg)
    if pipeline_summary_path is not None:
        summary = read_live_audit_pipeline_result(pipeline_summary_path)
        if not summary.official_run_allowed:
            msg = "pipeline summary does not allow an official run"
            raise ValueError(msg)
        plan_path = summary.smoke_plan_path
    else:
        plan_path = smoke_plan_path
    if plan_path is None:
        msg = "smoke plan path is required"
        raise ValueError(msg)
    plan = read_live_smoke_plan(plan_path)
    if not plan.official_run_allowed:
        msg = "smoke plan does not allow an official run"
        raise ValueError(msg)
    return plan


def _pre_capture_stop_reason(
    *,
    focus_ok: bool,
    emergency_triggered: bool,
    elapsed: float,
    max_duration_seconds: int,
    frame_count: int,
    max_frames: int,
    action_count: int,
    max_actions: int,
) -> StopReason:
    if not focus_ok:
        return "focus_lost"
    if emergency_triggered:
        return "emergency_stop_triggered"
    if elapsed >= max_duration_seconds:
        return "max_duration_reached"
    if frame_count >= max_frames:
        return "max_frames_reached"
    if max_actions > 0 and action_count >= max_actions:
        return "max_actions_reached"
    return "completed"


def _emit(
    events: list[ControlledLiveSmokeEvent],
    log_event: EventLogger,
    event: ControlledLiveSmokeEvent,
) -> None:
    events.append(event)
    log_event(event)


def _utc_now() -> datetime:
    return datetime.now(UTC)
