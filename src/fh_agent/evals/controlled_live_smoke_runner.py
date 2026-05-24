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
    "action_request",
    "input_executed",
    "dryrun_task_intent",
    "stop_condition_triggered",
    "runtime_end",
]
ActionLoggingMode = Literal["disabled", "wait_only_noop"]
DryRunOrchestrationMode = Literal["disabled", "wait_only"]
RealInputMode = Literal["disabled", "wait_only_noop", "single_directional_tap"]
SINGLE_DIRECTIONAL_TAP_ACTION = "move_right_short"
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


class WaitNoopSender(Protocol):
    def __call__(self) -> bool: ...


class RealPrimitiveSender(Protocol):
    def __call__(self, action: str) -> bool: ...


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


class ControlledLiveSmokeActionIntent(BaseModel):
    """A requested but not executed action intent for no-op logging."""

    model_config = ConfigDict(extra="forbid")

    action: str
    requested: bool
    executed: bool
    input_sent: bool
    reason: str
    frame_index: int | None = None
    blocked_reason: str | None = None


class ControlledLiveSmokeDryRunTask(BaseModel):
    """A static dry-run task/skill path that may request only a non-executed wait intent."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    static_goal: Literal["maintain_observation_without_input"]
    selected_skill: Literal["wait"]
    action_intent: ControlledLiveSmokeActionIntent


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
    action_intent: ControlledLiveSmokeActionIntent | None = None
    dryrun_task: ControlledLiveSmokeDryRunTask | None = None
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
    inputs_sent: int = 0
    action_logging_mode: ActionLoggingMode = "disabled"
    dryrun_orchestration_mode: DryRunOrchestrationMode = "disabled"
    real_input_mode: RealInputMode = "disabled"
    real_wait_only_active: bool = False
    allowed_real_primitives: tuple[str, ...] = ()
    input_attempt_count: int = 0
    allowed_input_count: int = 0
    forbidden_input_count: int = 0
    executed_action_count: int = 0
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
    dryrun_task_count: int = 0
    dryrun_skill_count: int = 0
    dryrun_tasks: tuple[ControlledLiveSmokeDryRunTask, ...] = ()
    manager_dryrun_active: bool = False
    body_dryrun_active: bool = False
    requested_actions: tuple[ControlledLiveSmokeActionIntent, ...] = ()
    executed_actions: tuple[ControlledLiveSmokeActionIntent, ...] = ()
    captured_frame_count: int
    evidence_ids: tuple[str, ...] = ()
    pre_input_evidence_ids: tuple[str, ...] = ()
    post_input_evidence_ids: tuple[str, ...] = ()
    screenshot_paths: tuple[Path, ...] = ()
    screenshot_evidence: tuple[ControlledLiveSmokeEvidence, ...] = ()
    capture_error_diagnostic: CaptureErrorDiagnostic | None = None
    autonomous_planner_active: bool = False
    manager_orchestration_active: bool = False
    body_control_active: bool = False
    bridge_active: bool = False
    ocr_active: bool = False
    learning_active: bool = False
    hidden_state_violation_count: int = 0

    @model_validator(mode="after")
    def report_must_not_claim_autonomy(self) -> "ControlledLiveSmokeReport":
        if self.execution_enabled:
            msg = "controlled smoke report must not enable autonomous execution"
            raise ValueError(msg)
        if self.real_input_mode == "disabled":
            if self.real_wait_only_active:
                msg = "disabled real input mode must not be active"
                raise ValueError(msg)
            if not self.no_input_sent:
                msg = "controlled smoke report must not claim input was sent"
                raise ValueError(msg)
            if self.inputs_sent != 0:
                msg = "controlled smoke report must not claim inputs were sent"
                raise ValueError(msg)
            if self.executed_actions:
                msg = "controlled smoke report must not claim actions were executed"
                raise ValueError(msg)
        elif self.real_input_mode == "wait_only_noop":
            if not self.allow_real_input:
                msg = "wait-only real input mode requires allow_real_input"
                raise ValueError(msg)
            if not self.real_wait_only_active:
                msg = "wait-only real input mode must be active"
                raise ValueError(msg)
            if self.mode != "official_screen_only" or not self.official_screen_only:
                msg = "wait-only real input mode requires official_screen_only"
                raise ValueError(msg)
            if (
                self.action_logging_mode != "disabled"
                or self.dryrun_orchestration_mode != "disabled"
            ):
                msg = "wait-only real input mode cannot combine with logging or dry-run"
                raise ValueError(msg)
            if self.rate_limit_enabled is not True or self.max_input_count <= 0:
                msg = "wait-only real input mode requires input limits"
                raise ValueError(msg)
            if self.max_input_count_exceeded:
                msg = "wait-only real input mode must not exceed max_input_count"
                raise ValueError(msg)
            if self.inputs_sent <= 0 or self.no_input_sent:
                msg = "wait-only real input mode must report sent wait no-ops"
                raise ValueError(msg)
            unsafe_actions = [
                action
                for action in self.executed_actions
                if action.action != "wait" or not action.executed or not action.input_sent
            ]
            if unsafe_actions:
                msg = "wait-only real input mode may only execute wait no-ops"
                raise ValueError(msg)
            if self.executed_action_count != len(self.executed_actions):
                msg = "executed_action_count must match executed_actions"
                raise ValueError(msg)
            if self.executed_wait_count != self.executed_action_count:
                msg = "executed_wait_count must match executed wait actions"
                raise ValueError(msg)
            if self.inputs_sent != self.executed_wait_count:
                msg = "inputs_sent must match executed wait no-ops"
                raise ValueError(msg)
            if self.forbidden_input_count != 0 or self.forbidden_executed_action_count != 0:
                msg = "wait-only real input mode must not report forbidden inputs"
                raise ValueError(msg)
            if (
                self.focus_guard_check_count < self.inputs_sent
                or self.emergency_stop_check_count < self.inputs_sent
            ):
                msg = "wait-only real input mode requires pre-input gate checks"
                raise ValueError(msg)
        elif self.real_input_mode == "single_directional_tap":
            if not self.allow_real_input:
                msg = "single directional tap mode requires allow_real_input"
                raise ValueError(msg)
            if self.mode != "official_screen_only" or not self.official_screen_only:
                msg = "single directional tap mode requires official_screen_only"
                raise ValueError(msg)
            if self.allowed_real_primitives != (SINGLE_DIRECTIONAL_TAP_ACTION,):
                msg = "single directional tap mode allows only move_right_short"
                raise ValueError(msg)
            if (
                self.action_logging_mode != "disabled"
                or self.dryrun_orchestration_mode != "disabled"
            ):
                msg = "single directional tap mode cannot combine with logging or dry-run"
                raise ValueError(msg)
            if self.max_input_count != 1 or self.max_input_count_exceeded:
                msg = "single directional tap mode requires exactly one allowed input"
                raise ValueError(msg)
            if self.inputs_sent != 1 or self.no_input_sent:
                msg = "single directional tap mode must report exactly one sent input"
                raise ValueError(msg)
            if len(self.executed_actions) != 1:
                msg = "single directional tap mode must report one executed action"
                raise ValueError(msg)
            executed = self.executed_actions[0]
            if (
                executed.action != SINGLE_DIRECTIONAL_TAP_ACTION
                or not executed.executed
                or not executed.input_sent
            ):
                msg = "single directional tap mode may only execute move_right_short"
                raise ValueError(msg)
            if self.executed_action_count != 1:
                msg = "executed_action_count must be one in single directional tap mode"
                raise ValueError(msg)
            if self.executed_wait_count != 0:
                msg = "single directional tap mode must not execute wait"
                raise ValueError(msg)
            if self.forbidden_input_count != 0 or self.forbidden_executed_action_count != 0:
                msg = "single directional tap mode must not report forbidden inputs"
                raise ValueError(msg)
            if (
                self.focus_guard_check_count != 1
                or self.focus_guard_pre_input_pass_count != 1
                or self.emergency_stop_check_count != 1
                or self.emergency_stop_pre_input_clear_count != 1
            ):
                msg = "single directional tap mode requires exact pre-input gate checks"
                raise ValueError(msg)
            if not self.pre_input_evidence_ids or not self.post_input_evidence_ids:
                msg = "single directional tap mode requires pre and post evidence"
                raise ValueError(msg)
        if self.dryrun_orchestration_mode == "disabled":
            if (
                self.dryrun_task_count != 0
                or self.dryrun_skill_count != 0
                or self.dryrun_tasks
                or self.manager_dryrun_active
                or self.body_dryrun_active
            ):
                msg = "disabled dry-run orchestration must not report dry-run tasks"
                raise ValueError(msg)
        elif self.dryrun_orchestration_mode == "wait_only":
            if not self.dryrun_tasks:
                msg = "wait-only dry-run orchestration must report dry-run tasks"
                raise ValueError(msg)
            if self.dryrun_task_count != len(self.dryrun_tasks):
                msg = "dryrun_task_count must match dryrun_tasks"
                raise ValueError(msg)
            if self.dryrun_skill_count != len(self.dryrun_tasks):
                msg = "dryrun_skill_count must match dryrun_tasks"
                raise ValueError(msg)
            if not self.manager_dryrun_active or not self.body_dryrun_active:
                msg = "wait-only dry-run orchestration must mark dry-run layers active"
                raise ValueError(msg)
            unsafe_tasks = [
                task
                for task in self.dryrun_tasks
                if task.action_intent.action != "wait"
                or task.action_intent.executed
                or task.action_intent.input_sent
            ]
            if unsafe_tasks:
                msg = "wait-only dry-run orchestration may only report non-executed wait intents"
                raise ValueError(msg)
        if (
            self.autonomous_planner_active
            or self.manager_orchestration_active
            or self.body_control_active
            or self.bridge_active
            or self.ocr_active
            or self.learning_active
        ):
            msg = "controlled smoke report must not claim autonomous control"
            raise ValueError(msg)
        if self.hidden_state_violation_count != 0:
            msg = "controlled smoke report must not claim hidden-state access"
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
    action_logging_mode: ActionLoggingMode = "disabled",
    dryrun_orchestration_mode: DryRunOrchestrationMode = "disabled",
    real_input_mode: RealInputMode = "disabled",
    send_wait_noop: WaitNoopSender | None = None,
    send_real_primitive: RealPrimitiveSender | None = None,
    allowed_real_primitives: tuple[str, ...] = (),
    max_input_count: int = 0,
    input_rate_limit_seconds: float = 0.0,
    capture_script: str | None = None,
    noop_action_frequency: int = 1,
    overwrite: bool = False,
) -> ControlledLiveSmokeResult:
    """Run a user-started observation-only smoke skeleton through injected adapters."""

    timestamp = (now or _utc_now)()
    if not user_started:
        msg = "controlled live smoke requires user_started=True"
        raise ValueError(msg)
    if action_logging_mode not in ("disabled", "wait_only_noop"):
        msg = "action_logging_mode must be disabled or wait_only_noop"
        raise ValueError(msg)
    if dryrun_orchestration_mode not in ("disabled", "wait_only"):
        msg = "dryrun_orchestration_mode must be disabled or wait_only"
        raise ValueError(msg)
    if real_input_mode not in ("disabled", "wait_only_noop", "single_directional_tap"):
        msg = "real_input_mode must be disabled, wait_only_noop, or single_directional_tap"
        raise ValueError(msg)
    if dryrun_orchestration_mode == "wait_only" and action_logging_mode != "disabled":
        msg = "dryrun wait_only orchestration cannot be combined with wait_only_noop logging"
        raise ValueError(msg)
    if real_input_mode == "wait_only_noop":
        if not allow_real_input:
            msg = "real_input_mode wait_only_noop requires allow_real_input=True"
            raise ValueError(msg)
        if action_logging_mode != "disabled" or dryrun_orchestration_mode != "disabled":
            msg = "real_input_mode wait_only_noop cannot be combined with logging or dry-run"
            raise ValueError(msg)
        if send_wait_noop is None:
            msg = "real_input_mode wait_only_noop requires a wait no-op sender"
            raise ValueError(msg)
        if max_input_count < 1:
            msg = "real_input_mode wait_only_noop requires max_input_count >= 1"
            raise ValueError(msg)
        if input_rate_limit_seconds < 0:
            msg = "input_rate_limit_seconds must be non-negative"
            raise ValueError(msg)
    elif real_input_mode == "single_directional_tap":
        if not allow_real_input:
            msg = "real_input_mode single_directional_tap requires allow_real_input=True"
            raise ValueError(msg)
        if action_logging_mode != "disabled" or dryrun_orchestration_mode != "disabled":
            msg = (
                "real_input_mode single_directional_tap cannot be combined with logging or dry-run"
            )
            raise ValueError(msg)
        if send_real_primitive is None:
            msg = "real_input_mode single_directional_tap requires a real primitive sender"
            raise ValueError(msg)
        if allowed_real_primitives != (SINGLE_DIRECTIONAL_TAP_ACTION,):
            msg = "real_input_mode single_directional_tap allows only move_right_short"
            raise ValueError(msg)
        if max_input_count != 1:
            msg = "real_input_mode single_directional_tap requires max_input_count == 1"
            raise ValueError(msg)
        if max_frames is not None and max_frames < 2:
            msg = "real_input_mode single_directional_tap requires at least two frames"
            raise ValueError(msg)
        if input_rate_limit_seconds < 0:
            msg = "input_rate_limit_seconds must be non-negative"
            raise ValueError(msg)
    elif allow_real_input:
        msg = "allow_real_input requires a real_input_mode"
        raise ValueError(msg)
    if noop_action_frequency < 1:
        msg = "noop_action_frequency must be at least 1"
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
    requested_actions: list[ControlledLiveSmokeActionIntent] = []
    executed_actions: list[ControlledLiveSmokeActionIntent] = []
    dryrun_tasks: list[ControlledLiveSmokeDryRunTask] = []
    pre_input_evidence_ids: list[str] = []
    post_input_evidence_ids: list[str] = []
    capture_error_diagnostic: CaptureErrorDiagnostic | None = None
    frame_count = 0
    action_count = 0
    input_attempt_count = 0
    inputs_sent = 0
    allowed_input_count = 0
    forbidden_input_count = 0
    executed_wait_count = 0
    forbidden_executed_action_count = 0
    focus_guard_check_count = 0
    focus_guard_pre_input_pass_count = 0
    emergency_stop_check_count = 0
    emergency_stop_pre_input_clear_count = 0
    max_input_count_exceeded = False
    last_input_time: float | None = None
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
    if real_input_mode == "single_directional_tap" and effective_max_frames < 2:
        msg = "real_input_mode single_directional_tap requires at least two effective frames"
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
        if real_input_mode == "single_directional_tap":
            if inputs_sent == 0 and input_attempt_count == 0:
                pre_input_evidence_ids.append(frame.evidence_id)
            elif inputs_sent == 1:
                post_input_evidence_ids.append(frame.evidence_id)
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
        if action_logging_mode == "wait_only_noop" and frame_count % noop_action_frequency == 0:
            intent = ControlledLiveSmokeActionIntent(
                action="wait",
                requested=True,
                executed=False,
                input_sent=False,
                reason="noop_action_logging",
                frame_index=frame_count - 1,
            )
            requested_actions.append(intent)
            action_count += 1
            _emit(
                events,
                log_event,
                ControlledLiveSmokeEvent(
                    event_type="wait_intent",
                    created_at=(now or _utc_now)(),
                    message="wait action intent logged without execution",
                    frame_index=frame_count - 1,
                    action_intent=intent,
                ),
            )
        if dryrun_orchestration_mode == "wait_only" and frame_count % noop_action_frequency == 0:
            intent = ControlledLiveSmokeActionIntent(
                action="wait",
                requested=True,
                executed=False,
                input_sent=False,
                reason="dryrun_orchestration_wait_only",
                frame_index=frame_count - 1,
            )
            task = ControlledLiveSmokeDryRunTask(
                task_id=f"dryrun-wait-{len(dryrun_tasks)}",
                static_goal="maintain_observation_without_input",
                selected_skill="wait",
                action_intent=intent,
            )
            dryrun_tasks.append(task)
            requested_actions.append(intent)
            action_count += 1
            _emit(
                events,
                log_event,
                ControlledLiveSmokeEvent(
                    event_type="dryrun_task_intent",
                    created_at=(now or _utc_now)(),
                    message="dryrun wait task intent logged without execution",
                    frame_index=frame_count - 1,
                    action_intent=intent,
                    dryrun_task=task,
                ),
            )
        if real_input_mode == "wait_only_noop" and frame_count % noop_action_frequency == 0:
            input_attempt_count += 1
            action_count += 1
            blocked_reason: str | None = None
            sent = False

            focus_guard_check_count += 1
            if focus_check():
                focus_guard_pre_input_pass_count += 1
            else:
                blocked_reason = "focus_lost"
                stop_reason = "focus_lost"

            emergency_stop_check_count += 1
            if emergency_stop_triggered():
                if blocked_reason is None:
                    blocked_reason = "emergency_stop_triggered"
                    stop_reason = "emergency_stop_triggered"
            else:
                emergency_stop_pre_input_clear_count += 1

            input_time = clock()
            if blocked_reason is None and input_attempt_count > max_input_count:
                blocked_reason = "max_input_count_exceeded"
                max_input_count_exceeded = True
                stop_reason = "max_actions_reached"
            if (
                blocked_reason is None
                and last_input_time is not None
                and input_time - last_input_time < input_rate_limit_seconds
            ):
                blocked_reason = "rate_limited"
                stop_reason = "max_actions_reached"
            if blocked_reason is None:
                sent = bool(send_wait_noop and send_wait_noop())
                if sent:
                    inputs_sent += 1
                    allowed_input_count += 1
                    executed_wait_count += 1
                    last_input_time = input_time
                else:
                    blocked_reason = "wait_noop_not_sent"
                    stop_reason = "max_actions_reached"

            if blocked_reason is not None:
                forbidden_input_count += 1
            intent = ControlledLiveSmokeActionIntent(
                action="wait",
                requested=True,
                executed=sent,
                input_sent=sent,
                reason="real_wait_only_noop",
                frame_index=frame_count - 1,
                blocked_reason=blocked_reason,
            )
            requested_actions.append(intent)
            if sent:
                executed_actions.append(intent)
            _emit(
                events,
                log_event,
                ControlledLiveSmokeEvent(
                    event_type="wait_intent",
                    created_at=(now or _utc_now)(),
                    message="wait no-op intent processed through real wait-only mode",
                    frame_index=frame_count - 1,
                    action_intent=intent,
                ),
            )
            if blocked_reason is not None:
                break

        if (
            real_input_mode == "single_directional_tap"
            and frame_count == 1
            and input_attempt_count == 0
        ):
            input_attempt_count += 1
            action_count += 1
            blocked_reason = None
            sent = False

            focus_guard_check_count += 1
            if focus_check():
                focus_guard_pre_input_pass_count += 1
            else:
                blocked_reason = "focus_lost"
                stop_reason = "focus_lost"

            emergency_stop_check_count += 1
            if emergency_stop_triggered():
                if blocked_reason is None:
                    blocked_reason = "emergency_stop_triggered"
                    stop_reason = "emergency_stop_triggered"
            else:
                emergency_stop_pre_input_clear_count += 1

            if blocked_reason is None and input_attempt_count > max_input_count:
                blocked_reason = "max_input_count_exceeded"
                max_input_count_exceeded = True
                stop_reason = "max_actions_reached"
            if blocked_reason is None:
                sent = bool(
                    send_real_primitive and send_real_primitive(SINGLE_DIRECTIONAL_TAP_ACTION)
                )
                if sent:
                    inputs_sent += 1
                    allowed_input_count += 1
                    last_input_time = clock()
                else:
                    blocked_reason = "directional_tap_not_sent"
                    stop_reason = "max_actions_reached"

            if blocked_reason is not None:
                forbidden_input_count += 1
            intent = ControlledLiveSmokeActionIntent(
                action=SINGLE_DIRECTIONAL_TAP_ACTION,
                requested=True,
                executed=sent,
                input_sent=sent,
                reason="single_directional_tap",
                frame_index=frame_count - 1,
                blocked_reason=blocked_reason,
            )
            requested_actions.append(intent)
            _emit(
                events,
                log_event,
                ControlledLiveSmokeEvent(
                    event_type="action_request",
                    created_at=(now or _utc_now)(),
                    message="single directional tap action requested",
                    frame_index=frame_count - 1,
                    action_intent=intent,
                ),
            )
            if sent:
                executed_actions.append(intent)
                _emit(
                    events,
                    log_event,
                    ControlledLiveSmokeEvent(
                        event_type="input_executed",
                        created_at=(now or _utc_now)(),
                        message="single directional tap input executed",
                        frame_index=frame_count - 1,
                        action_intent=intent,
                    ),
                )
            if blocked_reason is not None:
                break

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
        no_input_sent=inputs_sent == 0,
        inputs_sent=inputs_sent,
        action_logging_mode=action_logging_mode,
        dryrun_orchestration_mode=dryrun_orchestration_mode,
        real_input_mode=real_input_mode,
        real_wait_only_active=real_input_mode == "wait_only_noop",
        allowed_real_primitives=allowed_real_primitives,
        input_attempt_count=input_attempt_count,
        allowed_input_count=allowed_input_count,
        forbidden_input_count=forbidden_input_count,
        executed_action_count=len(executed_actions),
        executed_wait_count=executed_wait_count,
        forbidden_executed_action_count=forbidden_executed_action_count,
        focus_guard_check_count=focus_guard_check_count,
        focus_guard_pre_input_pass_count=focus_guard_pre_input_pass_count,
        emergency_stop_check_count=emergency_stop_check_count,
        emergency_stop_pre_input_clear_count=emergency_stop_pre_input_clear_count,
        rate_limit_enabled=real_input_mode == "wait_only_noop",
        max_input_count=max_input_count,
        max_input_count_exceeded=max_input_count_exceeded,
        capture_script=capture_script,
        official_screen_only=result.mode == "official_screen_only",
        dryrun_task_count=len(dryrun_tasks),
        dryrun_skill_count=len(dryrun_tasks),
        dryrun_tasks=tuple(dryrun_tasks),
        manager_dryrun_active=dryrun_orchestration_mode == "wait_only",
        body_dryrun_active=dryrun_orchestration_mode == "wait_only",
        requested_actions=tuple(requested_actions),
        executed_actions=tuple(executed_actions),
        captured_frame_count=result.status.frames_captured,
        evidence_ids=tuple(frame.evidence_id for frame in frames),
        pre_input_evidence_ids=tuple(pre_input_evidence_ids),
        post_input_evidence_ids=tuple(post_input_evidence_ids),
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
