"""D6 composition for a bounded local bridge-assisted hierarchy runtime."""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.bridge_snapshot_observation import (
    BoundedBridgeSnapshotResponseWaiter,
    BridgeSnapshotObservationSource,
    BridgeSnapshotResponseWaiter,
)
from fh_agent.game.emergency_stop import StopFileEmergencyStopCheck
from fh_agent.game.focus_guard import FakeFocusGuard, FocusGuard
from fh_agent.game.input_executor import DryRunInputBackend, InputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.game.xdotool_adapters import XdotoolFocusGuard, XdotoolInputBackend
from fh_agent.manager.event_sink import InMemoryManagerEventSink, ManagerEventSink
from fh_agent.manager.grounded_cortex_submission import GroundedCortexTaskSubmitter
from fh_agent.manager.hierarchical_step import HierarchicalTaskStepRunner
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.replan_loop import (
    HierarchicalReplanLoopResult,
    HierarchicalReplanLoopRunner,
    ReplanLoopStepIds,
)
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.task_executor import ManagerTaskExecutor
from fh_agent.memory.event_log import EventLogger
from fh_agent.memory.evidence import EvidenceStore
from fh_agent.observation.schemas import ActionResult, Observation
from fh_agent.observation.source import ObservationSource
from fh_agent.perception.screen_capture import ScreenCapture
from fh_agent.planner.cortex import Cortex
from fh_agent.planner.llm_client import LLMClient, OpenAICompatibleLLMClient

BRIDGE_ASSISTED_RUN_MODE: Literal["bridge-assisted"] = "bridge-assisted"


class BridgeAssistedRuntimeError(RuntimeError):
    """Base error for D6 assembly or bounded execution failures."""


class BridgeAssistedRuntimeBudgetExceeded(BridgeAssistedRuntimeError):
    """Raised before a configured task, action, or snapshot budget is exceeded."""


class PrimitiveActionExecutor(Protocol):
    """Minimal primitive-action surface consumed by the existing SkillRunner."""

    def execute(self, action: PrimitiveAction) -> ActionResult: ...


@dataclass(frozen=True, slots=True)
class BridgeAssistedRuntimeLimits:
    """Finite D6 runtime budgets, independent of individual Skill Contracts."""

    max_task_attempts: int = 3
    max_action_attempts: int = 25
    max_snapshot_attempts: int = 40

    def __post_init__(self) -> None:
        for name, value in (
            ("max_task_attempts", self.max_task_attempts),
            ("max_action_attempts", self.max_action_attempts),
            ("max_snapshot_attempts", self.max_snapshot_attempts),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class BridgeAssistedRuntimeConfig:
    """Construction-only configuration for one local bridge-assisted runtime."""

    run_id: str
    exchange_directory: Path
    feed_path: Path
    event_log_path: Path
    screenshots_root: Path
    stop_file_path: Path
    local_llm_base_url: str
    local_llm_model: str
    target_window: WindowTarget
    limits: BridgeAssistedRuntimeLimits = field(default_factory=BridgeAssistedRuntimeLimits)
    key_bindings: Mapping[PrimitiveAction, str] = field(default_factory=dict)
    allow_real_input: bool = False
    llm_timeout_seconds: float = 30.0
    bridge_response_timeout_seconds: float = 2.0
    bridge_poll_interval_seconds: float = 0.02
    input_min_interval_seconds: float = 0.05
    xdotool_executable: str = "xdotool"

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        if not self.local_llm_model.strip():
            raise ValueError("local_llm_model must not be blank")
        if not self.target_window.title:
            raise ValueError("target_window title must not be empty")
        if not self.xdotool_executable:
            raise ValueError("xdotool_executable must not be empty")
        for name, value in (
            ("llm_timeout_seconds", self.llm_timeout_seconds),
            ("bridge_response_timeout_seconds", self.bridge_response_timeout_seconds),
            ("bridge_poll_interval_seconds", self.bridge_poll_interval_seconds),
        ):
            _require_positive_finite(name, value)
        if (
            isinstance(self.input_min_interval_seconds, bool)
            or not isinstance(self.input_min_interval_seconds, int | float)
            or not math.isfinite(self.input_min_interval_seconds)
            or self.input_min_interval_seconds < 0
        ):
            raise ValueError("input_min_interval_seconds must be finite and non-negative")
        if self.allow_real_input:
            invalid_bindings = [
                action.value
                for action, key in self.key_bindings.items()
                if action is not PrimitiveAction.WAIT and not key
            ]
            if invalid_bindings:
                joined = ", ".join(sorted(invalid_bindings))
                raise ValueError(f"real-input key bindings must be non-empty: {joined}")


class BoundedPrimitiveActionExecutor:
    """Fail closed before delegating more primitive action attempts than allowed."""

    def __init__(self, executor: InputExecutor, *, max_attempts: int) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.executor = executor
        self.max_attempts = max_attempts
        self.attempt_count = 0

    def execute(self, action: PrimitiveAction) -> ActionResult:
        if self.attempt_count >= self.max_attempts:
            raise BridgeAssistedRuntimeBudgetExceeded("primitive action budget exhausted")
        self.attempt_count += 1
        return self.executor.execute(action)


class BoundedSnapshotObservationSource:
    """Fail closed before requesting more bridge snapshots than configured."""

    def __init__(self, source: ObservationSource, *, max_attempts: int) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.source = source
        self.max_attempts = max_attempts
        self.attempt_count = 0

    def observe(self) -> Observation:
        if self.attempt_count >= self.max_attempts:
            raise BridgeAssistedRuntimeBudgetExceeded("snapshot budget exhausted")
        self.attempt_count += 1
        return self.source.observe()


@dataclass(frozen=True, slots=True)
class BridgeAssistedRuntimeExecutionResult:
    """One bounded D6 execution plus exact runtime-level budget accounting."""

    run_id: str
    run_mode: Literal["bridge-assisted"]
    loop_result: HierarchicalReplanLoopResult
    task_attempts: int
    action_attempts: int
    snapshot_attempts: int


@dataclass(slots=True)
class BridgeAssistedRuntime:
    """Fully assembled D6 hierarchy. Construction itself performs no live activity."""

    config: BridgeAssistedRuntimeConfig
    observation_source: BoundedSnapshotObservationSource
    input_executor: BoundedPrimitiveActionExecutor
    input_backend: InputBackend
    focus_guard: FocusGuard
    llm_client: LLMClient
    event_logger: EventLogger
    evidence_store: EvidenceStore
    manager_event_sink: ManagerEventSink
    orchestrator: ManagerOrchestrator
    loop_runner: HierarchicalReplanLoopRunner
    run_mode: Literal["bridge-assisted"] = BRIDGE_ASSISTED_RUN_MODE

    def run_bounded(
        self,
        initial_memory_summary: Mapping[str, Any],
        *,
        step_ids: Sequence[ReplanLoopStepIds],
        created_at: str | None = None,
    ) -> BridgeAssistedRuntimeExecutionResult:
        """Run only within the caller-supplied finite task-attempt contract."""

        task_attempts = len(step_ids)
        if task_attempts > self.config.limits.max_task_attempts:
            raise BridgeAssistedRuntimeBudgetExceeded("task-attempt budget exhausted")
        if not step_ids:
            raise ValueError("step_ids must contain at least one bounded task attempt")

        loop_result = self.loop_runner.run_bounded(  # type: ignore[arg-type]
            self.orchestrator,
            self.observation_source,
            self.input_executor,
            initial_memory_summary,
            run_id=self.config.run_id,
            step_ids=step_ids,
            created_at=created_at,
        )
        return BridgeAssistedRuntimeExecutionResult(
            run_id=self.config.run_id,
            run_mode=self.run_mode,
            loop_result=loop_result,
            task_attempts=task_attempts,
            action_attempts=self.input_executor.attempt_count,
            snapshot_attempts=self.observation_source.attempt_count,
        )


def assemble_bridge_assisted_runtime(
    config: BridgeAssistedRuntimeConfig,
    *,
    capture: ScreenCapture,
    llm_client: LLMClient | None = None,
    response_waiter: BridgeSnapshotResponseWaiter | None = None,
    manager_event_sink: ManagerEventSink | None = None,
    evidence_store: EvidenceStore | None = None,
    event_logger: EventLogger | None = None,
    request_id_factory: Callable[[], str] | None = None,
) -> BridgeAssistedRuntime:
    """Compose the D6 runtime without launching a game or executing any input."""

    _require_loopback_llm_endpoint(config.local_llm_base_url)

    resolved_event_logger = event_logger or EventLogger(
        config.event_log_path,
        run_id=config.run_id,
    )
    resolved_evidence_store = evidence_store or EvidenceStore(
        config.screenshots_root,
        run_id=config.run_id,
    )
    if resolved_event_logger.run_id != config.run_id:
        raise ValueError("event_logger run_id must match runtime config")
    if resolved_evidence_store.run_id != config.run_id:
        raise ValueError("evidence_store run_id must match runtime config")

    resolved_response_waiter = response_waiter or BoundedBridgeSnapshotResponseWaiter(
        timeout_seconds=config.bridge_response_timeout_seconds,
        poll_interval_seconds=config.bridge_poll_interval_seconds,
    )
    synchronized_source = BridgeSnapshotObservationSource(
        capture,
        resolved_evidence_store,
        resolved_event_logger,
        resolved_response_waiter,
        run_id=config.run_id,
        exchange_directory=config.exchange_directory,
        feed_path=config.feed_path,
        request_id_factory=request_id_factory,
    )
    observation_source = BoundedSnapshotObservationSource(
        synchronized_source,
        max_attempts=config.limits.max_snapshot_attempts,
    )

    resolved_llm_client = llm_client or OpenAICompatibleLLMClient(
        base_url=config.local_llm_base_url,
        model=config.local_llm_model,
        timeout_seconds=config.llm_timeout_seconds,
    )
    cortex = Cortex(resolved_llm_client)
    sink = manager_event_sink or InMemoryManagerEventSink()
    orchestrator = ManagerOrchestrator(event_sink=sink)
    task_executor = ManagerTaskExecutor(
        skill_runner=SkillRunner(event_logger=resolved_event_logger)
    )
    loop_runner = HierarchicalReplanLoopRunner(
        HierarchicalTaskStepRunner(
            GroundedCortexTaskSubmitter(cortex),
            task_executor=task_executor,
        )
    )

    focus_guard, input_backend = _build_guarded_input_components(config)
    guarded_executor = InputExecutor(
        target=config.target_window,
        focus_guard=focus_guard,
        backend=input_backend,
        min_interval_seconds=config.input_min_interval_seconds,
        emergency_stop_check=StopFileEmergencyStopCheck(config.stop_file_path),
    )
    input_executor = BoundedPrimitiveActionExecutor(
        guarded_executor,
        max_attempts=config.limits.max_action_attempts,
    )

    return BridgeAssistedRuntime(
        config=config,
        observation_source=observation_source,
        input_executor=input_executor,
        input_backend=input_backend,
        focus_guard=focus_guard,
        llm_client=resolved_llm_client,
        event_logger=resolved_event_logger,
        evidence_store=resolved_evidence_store,
        manager_event_sink=sink,
        orchestrator=orchestrator,
        loop_runner=loop_runner,
    )


def _build_guarded_input_components(
    config: BridgeAssistedRuntimeConfig,
) -> tuple[FocusGuard, InputBackend]:
    if not config.allow_real_input:
        return FakeFocusGuard(focused=True), DryRunInputBackend()

    return (
        XdotoolFocusGuard(executable=config.xdotool_executable),
        XdotoolInputBackend(
            config.key_bindings,
            executable=config.xdotool_executable,
        ),
    )


def _require_loopback_llm_endpoint(base_url: str) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("local_llm_base_url must be an absolute HTTP(S) URL")

    hostname = parsed.hostname.lower()
    if hostname == "localhost":
        return
    try:
        if ip_address(hostname).is_loopback:
            return
    except ValueError:
        pass
    raise ValueError("local_llm_base_url must resolve syntactically to a loopback host")


def _require_positive_finite(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a positive finite number")
