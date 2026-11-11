"""Offline debug-replay pilot step through the existing bounded hierarchy (Issue #177).

The replay feeds recorded visible-only bridge payloads and one fixed Cortex response through
``run_bridge_assisted_bounded``. Every primitive action goes to ``DryRunInputBackend``; recorded
after-states are replayed transitions, never effects caused by the current execution.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
from typing import Any, Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fh_agent.bridge.bridge_server import VisibleBridgeAdapter
from fh_agent.bridge_assisted_runtime import (
    BoundedPrimitiveActionExecutor,
    BoundedSnapshotObservationSource,
    BridgeAssistedRuntimeBudgetExceeded,
)
from fh_agent.bridge_runtime import run_bridge_assisted_bounded
from fh_agent.game.authorized_input_gateway import (
    AuthorizedInputGateway,
    ContractBoundPrimitiveActionExecutor,
)
from fh_agent.game.emergency_stop import StopFileEmergencyStopCheck
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.action_authority import ManagerActionAuthority
from fh_agent.manager.event_sink import InMemoryManagerEventSink
from fh_agent.manager.grounded_cortex_submission import GroundedCortexTaskSubmitter
from fh_agent.manager.hierarchical_step import (
    HierarchicalTaskStepResult,
    HierarchicalTaskStepRunner,
)
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.replan_loop import (
    HierarchicalReplanLoopResult,
    HierarchicalReplanLoopRunner,
    ReplanLoopStepIds,
)
from fh_agent.manager.skill_catalog import SkillCatalog
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.task_executor import ManagerTaskExecutor
from fh_agent.memory.event_log import EventLogger
from fh_agent.mission.ledger import (
    CONTRACT_BUDGET,
    GLOBAL_ACTION_BUDGET,
    MissionLedger,
    episode_action_budget,
)
from fh_agent.mission.state import EpisodeState, MissionLedgerError, MissionState
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSource, ObservationSourceExhausted
from fh_agent.planner.cortex import Cortex
from fh_agent.planner.llm_client import FakeLLMClient
from fh_agent.skill_capabilities import SkillCapabilityContract
from fh_agent.verifier.schemas import VerifierStatus

PILOT_STEP_SCENARIO_SCHEMA_VERSION: Literal["1"] = "1"
PILOT_STEP_REPORT_SCHEMA_VERSION = "1"
RESULT_CLASSIFICATION = "debug-replay"
OBSERVATION_PROVENANCE_RUN_MODE = "bridge-assisted"
PILOT_STEP_SKILL = "interact_visible_object"

MAX_TASK_ATTEMPTS = 1
MAX_PRIMITIVE_ACTION_ATTEMPTS = 2
MAX_OBSERVATIONS = 4

VOLATILE_REPORT_KEYS = ("generated_at", "paths")

TransitionKind = Literal["recorded_initial_state", "replayed_transition"]


class PilotStepScenarioError(ValueError):
    """Raised when an offline replay scenario cannot be accepted before execution."""


class PilotStepMissionPreflightError(PilotStepScenarioError):
    """Raised when the opt-in Mission ledger does not match the replay; nothing was written."""


class ReplayFrame(BaseModel):
    """One recorded visible-only bridge payload and its durable screenshot evidence ID."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    screenshot_evidence_id: str = Field(min_length=1)
    payload: dict[str, Any]

    @model_validator(mode="after")
    def payload_must_cite_declared_evidence(self) -> "ReplayFrame":
        if self.payload.get("screenshot_id") != self.screenshot_evidence_id:
            msg = "replay frame payload screenshot_id must equal its screenshot_evidence_id"
            raise ValueError(msg)
        return self


class PilotStepScenario(BaseModel):
    """Versioned offline replay scenario for exactly one visible-object interaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"]
    scenario_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    description: str = ""
    frames: list[ReplayFrame] = Field(min_length=1, max_length=MAX_OBSERVATIONS)
    cortex_response: dict[str, Any]

    @model_validator(mode="after")
    def evidence_ids_must_be_unique(self) -> "PilotStepScenario":
        evidence_ids = [frame.screenshot_evidence_id for frame in self.frames]
        if len(evidence_ids) != len(set(evidence_ids)):
            msg = "replay frame screenshot_evidence_id values must be unique"
            raise ValueError(msg)
        return self


@dataclass(frozen=True, slots=True)
class PilotStepLimits:
    """Pilot budgets; callers may tighten but never widen the hard Issue #177 bounds."""

    max_task_attempts: int = MAX_TASK_ATTEMPTS
    max_action_attempts: int = MAX_PRIMITIVE_ACTION_ATTEMPTS
    max_observations: int = MAX_OBSERVATIONS

    def __post_init__(self) -> None:
        for name, value, ceiling in (
            ("max_task_attempts", self.max_task_attempts, MAX_TASK_ATTEMPTS),
            ("max_action_attempts", self.max_action_attempts, MAX_PRIMITIVE_ACTION_ATTEMPTS),
            ("max_observations", self.max_observations, MAX_OBSERVATIONS),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= ceiling:
                raise ValueError(f"{name} must be an integer between 1 and {ceiling}")


@dataclass(frozen=True, slots=True)
class ConsumedReplayFrame:
    """One replay frame released to the observation boundary."""

    index: int
    screenshot_evidence_id: str
    transition: TransitionKind


class ReplayFrameObservationSource:
    """Release one recorded frame per observation request, then delegate to the bridge source.

    Releasing writes the frame's screenshot evidence record and its payload line, so the
    existing bridge evidence synchronization stays the authority that accepts the payload.
    """

    def __init__(
        self,
        source: ObservationSource,
        frames: list[ReplayFrame],
        *,
        event_logger: EventLogger,
        feed_path: Path,
    ) -> None:
        self._source = source
        self._frames = frames
        self._event_logger = event_logger
        self._feed_path = feed_path
        self.consumed: list[ConsumedReplayFrame] = []

    def observe(self) -> Observation:
        index = len(self.consumed)
        if index >= len(self._frames):
            raise ObservationSourceExhausted
        frame = self._frames[index]
        transition: TransitionKind = (
            "recorded_initial_state" if index == 0 else "replayed_transition"
        )
        self._event_logger.append(
            "evidence",
            payload={
                "kind": "screenshot",
                "source": RESULT_CLASSIFICATION,
                "replay_frame_index": index,
                "transition": transition,
            },
            evidence_ids=[frame.screenshot_evidence_id],
        )
        with self._feed_path.open("ab") as feed:
            feed.write(json.dumps(frame.payload, sort_keys=True).encode("utf-8"))
            feed.write(b"\n")
        self.consumed.append(ConsumedReplayFrame(index, frame.screenshot_evidence_id, transition))
        return self._source.observe()


class _SourceWrappingLoopRunner(HierarchicalReplanLoopRunner):
    """Apply replay and observation-budget wrappers to the source built by the bridge runtime."""

    def __init__(
        self,
        step_runner: HierarchicalTaskStepRunner,
        *,
        wrap_source: Callable[[ObservationSource], ObservationSource],
    ) -> None:
        super().__init__(step_runner)
        self._wrap_source = wrap_source

    def run_bounded(  # type: ignore[override]
        self,
        orchestrator: ManagerOrchestrator,
        observation_source: ObservationSource,
        input_executor: InputExecutor,
        initial_memory_summary: dict[str, Any],
        **kwargs: Any,
    ) -> HierarchicalReplanLoopResult:
        return super().run_bounded(
            orchestrator,
            self._wrap_source(observation_source),
            input_executor,
            initial_memory_summary,
            **kwargs,
        )


@dataclass(slots=True)
class PilotStepRun:
    """Raw records from one pilot step, before report normalization."""

    scenario: PilotStepScenario
    scenario_sha256: str
    limits: PilotStepLimits
    backend: DryRunInputBackend
    llm_client: FakeLLMClient
    replay_source: ReplayFrameObservationSource | None = None
    observation_budget: BoundedSnapshotObservationSource | None = None
    action_budget: BoundedPrimitiveActionExecutor | None = None
    loop_result: HierarchicalReplanLoopResult | None = None
    error: Exception | None = None
    paths: dict[str, str] = field(default_factory=dict)


def load_pilot_step_scenario(path: Path) -> tuple[PilotStepScenario, str]:
    """Load and preflight a scenario; reject it before any runtime activity."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PilotStepScenarioError(f"cannot read scenario: {exc}") from exc
    try:
        scenario = PilotStepScenario.model_validate_json(raw)
    except ValueError as exc:
        raise PilotStepScenarioError(f"invalid scenario: {exc}") from exc

    adapter = VisibleBridgeAdapter()
    for index, frame in enumerate(scenario.frames):
        try:
            receipt = adapter.accept_observation_payload(frame.payload, run_id=scenario.run_id)
        except ValueError as exc:
            raise PilotStepScenarioError(f"replay frame {index} rejected: {exc}") from exc
        if receipt.run_mode != OBSERVATION_PROVENANCE_RUN_MODE:
            msg = f"replay frame {index} run_mode must be {OBSERVATION_PROVENANCE_RUN_MODE!r}"
            raise PilotStepScenarioError(msg)

    return scenario, hashlib.sha256(raw).hexdigest()


def run_pilot_step(
    scenario: PilotStepScenario,
    *,
    scenario_sha256: str,
    run_dir: Path,
    stop_file: Path,
    limits: PilotStepLimits | None = None,
    mission_ledger: MissionLedger | None = None,
) -> PilotStepRun:
    """Execute exactly one bounded DryRun task attempt over the replay scenario.

    With ``mission_ledger`` (MRIC-S0 opt-in), every primitive action is authorized through
    the Mission's Manager contract and gateway; all identity checks run before any write.
    """

    resolved_limits = limits or PilotStepLimits()
    event_log_path = run_dir / "events.jsonl"
    feed_path = run_dir / "feed.jsonl"
    for existing in (event_log_path, feed_path):
        if existing.exists():
            raise PilotStepScenarioError(f"run artifact already exists: {existing}")
    if mission_ledger is not None:
        _preflight_mission_ledger(mission_ledger, scenario, run_dir, resolved_limits)
    run_dir.mkdir(parents=True, exist_ok=True)

    event_ids = count(1)
    event_logger = EventLogger(
        event_log_path,
        run_id=scenario.run_id,
        id_factory=lambda: f"{scenario.run_id}-event-{next(event_ids):04d}",
    )
    backend = DryRunInputBackend()
    llm_client = FakeLLMClient(responses=[json.dumps(scenario.cortex_response, sort_keys=True)])
    run = PilotStepRun(
        scenario=scenario,
        scenario_sha256=scenario_sha256,
        limits=resolved_limits,
        backend=backend,
        llm_client=llm_client,
        paths={
            "run_dir": str(run_dir),
            "event_log": str(event_log_path),
            "feed": str(feed_path),
            "stop_file": str(stop_file),
        },
    )

    def wrap_source(source: ObservationSource) -> ObservationSource:
        run.replay_source = ReplayFrameObservationSource(
            source,
            scenario.frames,
            event_logger=event_logger,
            feed_path=feed_path,
        )
        run.observation_budget = BoundedSnapshotObservationSource(
            run.replay_source,
            max_attempts=resolved_limits.max_observations,
        )
        return run.observation_budget

    orchestrator = ManagerOrchestrator(
        runtime_capabilities=SkillCapabilityContract(available_skills=(PILOT_STEP_SKILL,)),
        event_sink=InMemoryManagerEventSink(),
    )
    input_executor = InputExecutor(
        target=WindowTarget(title="debug-replay (no game window)"),
        focus_guard=FakeFocusGuard(focused=True),
        backend=backend,
        min_interval_seconds=0.0,
        emergency_stop_check=StopFileEmergencyStopCheck(stop_file),
    )
    action_authority = None
    delegate: Any = input_executor
    if mission_ledger is not None:
        action_authority = ManagerActionAuthority(mission_ledger)
        delegate = ContractBoundPrimitiveActionExecutor(
            action_authority, AuthorizedInputGateway(mission_ledger, input_executor)
        )
    loop_runner = _SourceWrappingLoopRunner(
        HierarchicalTaskStepRunner(
            GroundedCortexTaskSubmitter(Cortex(llm_client)),
            task_executor=ManagerTaskExecutor(
                skill_runner=SkillRunner(event_logger=event_logger),
                action_authority=action_authority,
            ),
        ),
        wrap_source=wrap_source,
    )
    run.action_budget = BoundedPrimitiveActionExecutor(
        delegate,
        max_attempts=resolved_limits.max_action_attempts,
    )
    step_ids = tuple(
        ReplanLoopStepIds(
            task_id=f"{scenario.scenario_id}-task-{index}",
            completion_event_id=f"{scenario.run_id}-completion-{index}",
            planner_output_id=f"{scenario.run_id}-planner-{index}",
        )
        for index in range(1, resolved_limits.max_task_attempts + 1)
    )

    try:
        runtime_result = run_bridge_assisted_bounded(
            loop_runner,
            orchestrator,
            run.action_budget,  # type: ignore[arg-type]
            {},
            run_id=scenario.run_id,
            feed_path=feed_path,
            event_log_path=event_log_path,
            step_ids=step_ids,
        )
        run.loop_result = runtime_result.loop_result
    except (ValueError, RuntimeError) as exc:
        run.error = exc
    return run


def _preflight_mission_ledger(
    ledger: MissionLedger,
    scenario: PilotStepScenario,
    run_dir: Path,
    limits: PilotStepLimits,
) -> None:
    """Read-only identity, path, mode, lease, episode and budget checks for the opt-in hook."""

    def refuse(reason: str) -> NoReturn:
        raise PilotStepMissionPreflightError(f"mission preflight failed: {reason}")

    manifest = ledger.manifest
    if not (scenario.run_id == manifest.mission_run_id == ledger.run_id):
        refuse("scenario run_id does not match the Mission run_id")
    stored = ledger.fetch_one("SELECT run_id FROM mission")
    if stored is None or stored[0] != scenario.run_id:
        refuse("ledger-stored run_id does not match the scenario")
    if manifest.run_mode != OBSERVATION_PROVENANCE_RUN_MODE:
        refuse(f"manifest run_mode must be {OBSERVATION_PROVENANCE_RUN_MODE!r}")
    if manifest.execution_class != RESULT_CLASSIFICATION:
        refuse(f"manifest execution_class must be {RESULT_CLASSIFICATION!r}")
    try:
        ledger.verify_writer()
    except MissionLedgerError as exc:
        refuse(f"ledger handle not writable: {exc}")
    if ledger.mission_state() is not MissionState.ACTIVE:
        refuse("Mission is not ACTIVE")
    episode = ledger.active_episode()
    if episode is None or episode.state is not EpisodeState.OPEN:
        refuse("no open Life Episode")

    if run_dir.is_symlink():
        refuse("run_dir must not be a symlink")
    if run_dir.name != ledger.run_id:
        refuse("run_dir is not the Mission-owned directory")
    try:
        parent = run_dir.parent.resolve(strict=True)
        resolved = run_dir.resolve(strict=True)
    except OSError:
        refuse("run_dir does not exist")
    if parent != ledger.runs_root or resolved != ledger.mission_dir:
        refuse("run_dir is not the Mission-owned directory")
    if not (resolved / "mission.sqlite").samefile(ledger.db_path):
        refuse("run_dir does not hold this Mission ledger")

    effective_actions = min(
        limits.max_action_attempts,
        ledger.budget(GLOBAL_ACTION_BUDGET).remaining,
        ledger.budget(episode_action_budget(episode.episode_id)).remaining,
    )
    if effective_actions < 1 or ledger.budget(CONTRACT_BUDGET).remaining < 1:
        refuse("Mission budget cannot cover the bounded replay")


def build_pilot_step_report(run: PilotStepRun) -> dict[str, Any]:
    """Normalize one pilot run into an evidence-linked, explicitly non-official report."""

    step = _single_step(run.loop_result)
    report: dict[str, Any] = {
        "report_schema_version": PILOT_STEP_REPORT_SCHEMA_VERSION,
        "result_classification": RESULT_CLASSIFICATION,
        "official_evidence": False,
        "live_gameplay_verified": False,
        "causal_gameplay_success": False,
        "observation_provenance_run_mode": OBSERVATION_PROVENANCE_RUN_MODE,
        "input_backend": type(run.backend).__name__,
        "scenario": {
            "scenario_id": run.scenario.scenario_id,
            "schema_version": run.scenario.schema_version,
            "sha256": run.scenario_sha256,
            "frame_count": len(run.scenario.frames),
        },
        "run_id": run.scenario.run_id,
        "outcome": _outcome(run, step),
        "stop_reason": _stop_reason(run),
        "error": (
            None
            if run.error is None
            else {"type": type(run.error).__name__, "message": str(run.error)}
        ),
        "budgets": {
            "limits": {
                "task_attempts": run.limits.max_task_attempts,
                "primitive_action_attempts": run.limits.max_action_attempts,
                "observations": run.limits.max_observations,
            },
            "used": {
                "task_attempts": len(run.llm_client.requests),
                "primitive_action_attempts": (
                    run.action_budget.attempt_count if run.action_budget else 0
                ),
                "observations": (
                    run.observation_budget.attempt_count if run.observation_budget else 0
                ),
            },
        },
        "observations": [
            {
                "index": frame.index,
                "screenshot_evidence_id": frame.screenshot_evidence_id,
                "transition": frame.transition,
                "caused_by_current_execution": False,
            }
            for frame in (run.replay_source.consumed if run.replay_source else [])
        ],
        "dry_run_backend_actions": [action.value for action in run.backend.actions],
        "planner": None,
        "grounding": None,
        "task": None,
        "actions": [],
        "verifier": None,
        "completion": None,
    }
    if step is not None:
        report.update(_step_sections(step))
    return report


def write_pilot_step_report(report: dict[str, Any], path: Path) -> None:
    """Write the report with volatile metadata kept apart from the semantic content."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def with_volatile_metadata(report: dict[str, Any], run: PilotStepRun) -> dict[str, Any]:
    """Attach expressly nondeterministic metadata under ``VOLATILE_REPORT_KEYS``."""

    return {
        **report,
        "volatile_metadata_keys": list(VOLATILE_REPORT_KEYS),
        "generated_at": datetime.now(UTC).isoformat(),
        "paths": dict(run.paths),
    }


def semantic_report(report: dict[str, Any]) -> dict[str, Any]:
    """Drop expressly volatile metadata for reproducibility comparisons."""

    excluded = {"volatile_metadata_keys", *VOLATILE_REPORT_KEYS}
    return {key: value for key, value in report.items() if key not in excluded}


def _single_step(
    loop_result: HierarchicalReplanLoopResult | None,
) -> HierarchicalTaskStepResult | None:
    if loop_result is None or not loop_result.step_results:
        return None
    return loop_result.step_results[0]


def _stop_reason(run: PilotStepRun) -> str:
    if isinstance(run.error, BridgeAssistedRuntimeBudgetExceeded):
        return "budget_exceeded"
    if run.error is not None:
        return "rejected"
    assert run.loop_result is not None
    return run.loop_result.stop_reason


def _outcome(run: PilotStepRun, step: HierarchicalTaskStepResult | None) -> str:
    if run.error is not None:
        return "rejected"
    completion = step.execution_result.completion_event if step is not None else None
    if completion is None:
        return "replay_unverified"
    if completion.manager_stop_result is not None:
        return "manager_stop"
    verifier_result = completion.verifier_result
    if verifier_result is not None and verifier_result.status is VerifierStatus.SUCCESS:
        return "replay_local_verifier_success"
    if verifier_result is not None and verifier_result.status is VerifierStatus.FAILURE:
        return "replay_local_verifier_failure"
    return "replay_unverified"


def _step_sections(step: HierarchicalTaskStepResult) -> dict[str, Any]:
    submission = step.submission_result
    planner_output = submission.planner_output
    task_spec = submission.scheduled_task.task_spec
    skill_run = step.execution_result.skill_run_result
    completion = step.execution_result.completion_event
    contract = SkillCatalog.default().get(task_spec.selected_skill, task=task_spec.target).contract
    verifier_result = completion.verifier_result if completion is not None else None

    return {
        "planner": {
            "planning_observation_evidence_ids": list(step.planning_observation.evidence_ids),
            "next_goal": planner_output.next_goal,
            "selected_skill": planner_output.selected_skill,
            "success_condition": list(planner_output.success_condition),
            "cited_evidence_ids": sorted(
                {
                    evidence_id
                    for claim in planner_output.current_belief_state
                    for evidence_id in claim.evidence_ids
                }
            ),
        },
        "grounding": {
            "request": (
                submission.grounding_request.model_dump(mode="json")
                if submission.grounding_request is not None
                else None
            ),
            "result": (
                submission.grounding_result.model_dump(mode="json")
                if submission.grounding_result is not None
                else None
            ),
        },
        "task": {
            "task_id": task_spec.task_id,
            "selected_skill": task_spec.selected_skill,
            "target": (
                task_spec.target.model_dump(mode="json") if task_spec.target is not None else None
            ),
            "source_evidence_ids": list(task_spec.source_evidence_ids),
            "timeout_steps": task_spec.timeout_steps,
            "skill_contract": contract.model_dump(mode="json"),
        },
        "actions": [
            {
                "step_index": skill_step.step_index,
                "proposed_action": skill_step.action.value,
                "reason": skill_step.reason,
                "executed_on_backend": result.executed,
                "blocked_reason": result.blocked_reason,
                "evidence_ids": list(result.evidence_ids),
                "sent_to_game": False,
            }
            for skill_step, result in zip(
                skill_run.steps, skill_run.action_execution_results, strict=False
            )
        ],
        "verifier": (
            None
            if verifier_result is None
            else {
                "scope": "replay-local",
                "status": verifier_result.status.value,
                "failure_kind": (
                    verifier_result.failure_kind.value
                    if verifier_result.failure_kind is not None
                    else None
                ),
                "evidence_ids": list(verifier_result.evidence_ids),
                "verifier_event_id": completion.verifier_event_id if completion else None,
            }
        ),
        "completion": (
            None
            if completion is None
            else {
                "status": completion.status.value,
                "condition": completion.condition,
                "reason": completion.reason,
                "completion_evidence_ids": list(completion.completion_evidence_ids),
                "manager_stop": (
                    completion.manager_stop_result.model_dump(mode="json")
                    if completion.manager_stop_result is not None
                    else None
                ),
            }
        ),
    }
