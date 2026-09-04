import inspect
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

import fh_agent.manager.hierarchical_step as hierarchical_step_module
from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.observation_source import (
    BridgeObservationSource,
    BridgePayloadSourceExhausted,
)
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.event_sink import InMemoryManagerEventSink
from fh_agent.manager.grounded_cortex_submission import GroundedCortexTaskSubmitter
from fh_agent.manager.hierarchical_step import (
    HierarchicalTaskStepError,
    HierarchicalTaskStepRunner,
)
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskStatus
from fh_agent.manager.skill_runner import SkillRunner, SkillRunResult
from fh_agent.manager.target_ref import VisibleObjectTarget
from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.manager.task_executor import ManagerTaskExecutor, TaskExecutionResult
from fh_agent.manager.task_manager import ManagerGroundingError
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.primed_source import PrimedObservationSource
from fh_agent.observation.schemas import Observation, SkillResult, VisibleSprite
from fh_agent.observation.source import ObservationSourceExhausted
from fh_agent.planner.cortex import Cortex
from fh_agent.planner.llm_client import FakeLLMClient
from fh_agent.planner.planner_output import PlannerOutput
from fh_agent.verifier.schemas import FailureKind, VerifierStatus


class RecordingObservationSource:
    def __init__(self, *observations: Observation) -> None:
        self._observations = observations
        self._next_index = 0
        self.observe_calls = 0

    def observe(self) -> Observation:
        self.observe_calls += 1
        if self._next_index >= len(self._observations):
            raise ObservationSourceExhausted
        observation = self._observations[self._next_index]
        self._next_index += 1
        return observation


class EvidenceRecordingBridgePayloadSource:
    def __init__(self, event_logger: EventLogger, *payloads: Mapping[str, Any]) -> None:
        self._event_logger = event_logger
        self._payloads = payloads
        self._next_index = 0
        self.next_payload_calls = 0

    def next_payload(self) -> Mapping[str, Any]:
        self.next_payload_calls += 1
        if self._next_index >= len(self._payloads):
            raise BridgePayloadSourceExhausted
        payload = self._payloads[self._next_index]
        self._next_index += 1
        screenshot_id = payload.get("screenshot_id")
        if isinstance(screenshot_id, str):
            self._event_logger.append(
                "evidence",
                payload={"kind": "screenshot"},
                evidence_ids=[screenshot_id],
            )
        return payload


class RecordingPlanner:
    def __init__(self, output: PlannerOutput) -> None:
        self.output = output
        self.calls: list[tuple[Observation, Mapping[str, Any], Sequence[str] | None]] = []

    def plan_next_goal(
        self,
        observation: Observation,
        memory_summary: Mapping[str, Any],
        *,
        available_skills: Sequence[str] | None = None,
    ) -> PlannerOutput:
        self.calls.append((observation, memory_summary, available_skills))
        return self.output


class RecordingTaskExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[ManagerOrchestrator, object, object, dict[str, object]]] = []
        self.first_execution_observation: Observation | None = None

    def execute_current_task(
        self,
        orchestrator: ManagerOrchestrator,
        observation_source: object,
        input_executor: object,
        **kwargs: object,
    ) -> TaskExecutionResult:
        self.calls.append((orchestrator, observation_source, input_executor, kwargs))
        self.first_execution_observation = observation_source.observe()  # type: ignore[attr-defined]
        current_task = orchestrator.scheduler.current_task
        assert current_task is not None
        return TaskExecutionResult(
            task_id=current_task.task_spec.task_id,
            skill_run_result=SkillRunResult(
                skill_result=SkillResult(
                    skill_name=current_task.task_spec.selected_skill,
                    success=False,
                    failure_reason="nonterminal_test_result",
                )
            ),
            completion_event=None,
        )


def planner_output(
    *,
    selected_skill: str = "continue_dialogue",
    evidence_ids: list[str] | None = None,
    next_goal: str = "Continue the visible dialogue.",
) -> PlannerOutput:
    return PlannerOutput.model_validate(
        {
            "current_belief_state": [
                {
                    "kind": "fact",
                    "claim": "Visible evidence supports the next goal.",
                    "evidence_ids": evidence_ids or ["shot-before"],
                }
            ],
            "open_questions": [],
            "next_goal": next_goal,
            "selected_skill": selected_skill,
            "success_condition": ["visible_change"],
            "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
            "memory_updates_requested": [],
        }
    )


def dialogue_observation() -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="Visible dialogue.",
        evidence_ids=["shot-before"],
    )


def dry_run_input_executor(*, focused: bool = True) -> tuple[InputExecutor, DryRunInputBackend]:
    backend = DryRunInputBackend()
    return (
        InputExecutor(
            target=WindowTarget(title="M-011 dry-run window"),
            focus_guard=FakeFocusGuard(focused=focused),
            backend=backend,
            min_interval_seconds=0.0,
        ),
        backend,
    )


def test_idle_scheduler_rejection_precedes_observation_planning_and_input() -> None:
    planner = RecordingPlanner(planner_output())
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(planner_output(), task_id="existing-task")
    source = RecordingObservationSource(dialogue_observation())
    executor, backend = dry_run_input_executor()

    with pytest.raises(HierarchicalTaskStepError, match="idle Manager scheduler"):
        HierarchicalTaskStepRunner(GroundedCortexTaskSubmitter(planner)).run_once(
            orchestrator,
            source,
            executor,
            {},
            task_id="task-1",
            run_id="run-1",
            completion_event_id="completion-1",
        )

    assert source.observe_calls == 0
    assert planner.calls == []
    assert backend.actions == []


def test_running_scheduler_rejection_precedes_observation_planning_and_input() -> None:
    planner = RecordingPlanner(planner_output())
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(planner_output(), task_id="existing-task")
    assert orchestrator.start_next() is not None
    source = RecordingObservationSource(dialogue_observation())
    executor, backend = dry_run_input_executor()

    with pytest.raises(HierarchicalTaskStepError, match="idle Manager scheduler"):
        HierarchicalTaskStepRunner(GroundedCortexTaskSubmitter(planner)).run_once(
            orchestrator,
            source,
            executor,
            {},
            task_id="task-1",
            run_id="run-1",
            completion_event_id="completion-1",
        )

    assert source.observe_calls == 0
    assert planner.calls == []
    assert backend.actions == []


def test_initial_source_exhaustion_propagates_without_planning_or_submission() -> None:
    planner = RecordingPlanner(planner_output())
    orchestrator = ManagerOrchestrator()
    source = RecordingObservationSource()
    executor, backend = dry_run_input_executor()

    with pytest.raises(ObservationSourceExhausted):
        HierarchicalTaskStepRunner(GroundedCortexTaskSubmitter(planner)).run_once(
            orchestrator,
            source,
            executor,
            {},
            task_id="task-1",
            run_id="run-1",
            completion_event_id="completion-1",
        )

    assert planner.calls == []
    assert orchestrator.scheduler.current_task is None
    assert orchestrator.scheduler.queued_tasks == ()
    assert backend.actions == []


def test_runner_forwards_exact_boundary_inputs_and_primes_execution_observation() -> None:
    output = planner_output()
    planner = RecordingPlanner(output)
    recording_executor = RecordingTaskExecutor()
    orchestrator = ManagerOrchestrator()
    planning_observation = dialogue_observation()
    source = RecordingObservationSource(planning_observation, dialogue_observation())
    executor, _ = dry_run_input_executor()
    memory_summary = {"known_facts": [{"claim": "Visible fact.", "evidence_ids": ["shot-before"]}]}

    result = HierarchicalTaskStepRunner(  # type: ignore[arg-type]
        GroundedCortexTaskSubmitter(planner),
        task_executor=recording_executor,
    ).run_once(
        orchestrator,
        source,
        executor,
        memory_summary,
        task_id="task-1",
        run_id="run-1",
        completion_event_id="completion-1",
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
        created_at="2026-09-04T12:00:00+00:00",
    )

    planned_observation, planned_memory, available_skills = planner.calls[0]
    assert planned_observation is planning_observation
    assert planned_memory is memory_summary
    assert available_skills is orchestrator.task_manager.runtime_capabilities.available_skills
    assert result.planning_observation is planning_observation
    assert result.submission_result.planner_output is output
    assert result.started_task.status is TaskStatus.RUNNING
    assert result.started_task.task_spec.task_id == "task-1"
    assert recording_executor.calls[0][1].__class__ is PrimedObservationSource
    assert recording_executor.first_execution_observation is planning_observation
    assert source.observe_calls == 1
    assert recording_executor.calls[0][2] is executor
    assert recording_executor.calls[0][3] == {
        "run_id": "run-1",
        "completion_event_id": "completion-1",
        "created_at": "2026-09-04T12:00:00+00:00",
    }
    assert result.execution_result.completion_event is None
    assert len(planner.calls) == 1
    assert orchestrator.scheduler.queued_tasks == ()
    assert orchestrator.scheduler.current_task is not None


def test_submission_failure_prevents_execution_and_input() -> None:
    output = planner_output(
        selected_skill="interact_visible_object",
        next_goal="Interact with the visible object.",
    )
    planner = RecordingPlanner(output)
    recording_executor = RecordingTaskExecutor()
    source = RecordingObservationSource(
        Observation(
            run_id="run-1",
            ui_state="field",
            evidence_ids=["shot-before"],
            visible_sprites=[
                VisibleSprite(screen_position=(10, 20), confidence=0.9, evidence_id="sprite-1"),
                VisibleSprite(screen_position=(30, 40), confidence=0.9, evidence_id="sprite-2"),
            ],
        )
    )
    executor, backend = dry_run_input_executor()
    orchestrator = ManagerOrchestrator()

    with pytest.raises(ManagerGroundingError, match="ambiguous_candidates"):
        HierarchicalTaskStepRunner(  # type: ignore[arg-type]
            GroundedCortexTaskSubmitter(planner),
            task_executor=recording_executor,
        ).run_once(
            orchestrator,
            source,
            executor,
            {},
            task_id="task-1",
            run_id="run-1",
            completion_event_id="completion-1",
        )

    assert len(planner.calls) == 1
    assert recording_executor.calls == []
    assert backend.actions == []
    assert orchestrator.scheduler.current_task is None
    assert orchestrator.scheduler.queued_tasks == ()


def test_nonterminal_execution_does_not_replan_or_create_completion() -> None:
    output = planner_output()
    planner = RecordingPlanner(output)
    source = RecordingObservationSource(dialogue_observation())
    executor, backend = dry_run_input_executor()
    orchestrator = ManagerOrchestrator()

    result = HierarchicalTaskStepRunner(GroundedCortexTaskSubmitter(planner)).run_once(
        orchestrator,
        source,
        executor,
        {},
        task_id="task-1",
        run_id="run-1",
        completion_event_id="completion-1",
    )

    assert result.execution_result.completion_event is None
    assert len(planner.calls) == 1
    assert [action.value for action in backend.actions] == [PrimitiveAction.CONFIRM.value]
    assert orchestrator.scheduler.current_task is not None
    assert orchestrator.scheduler.queued_tasks == ()


def test_bridge_assisted_hierarchy_completes_and_preserves_typed_target_event(
    tmp_path: Path,
) -> None:
    event_log_path = tmp_path / "events.jsonl"
    event_logger = EventLogger(event_log_path, run_id="run-1")
    payload_source = EvidenceRecordingBridgePayloadSource(
        event_logger,
        {
            "run_mode": "bridge-assisted",
            "ui_state": "field",
            "visible_sprite_screen_positions": [[120, 80]],
            "visible_sprite_visual_hashes": ["dhash:0123456789abcdef"],
            "screenshot_id": "shot-before",
        },
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "A visible interaction outcome.",
            "screenshot_id": "shot-after",
        },
    )
    source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    )
    output = planner_output(
        selected_skill="interact_visible_object",
        evidence_ids=["shot-before"],
        next_goal="Interact with the visible object.",
    )
    cortex = Cortex(FakeLLMClient(responses=[json.dumps(output.model_dump(mode="json"))]))
    sink = InMemoryManagerEventSink()
    orchestrator = ManagerOrchestrator(event_sink=sink)
    executor, backend = dry_run_input_executor()
    task_executor = ManagerTaskExecutor(skill_runner=SkillRunner(event_logger=event_logger))

    result = HierarchicalTaskStepRunner(
        GroundedCortexTaskSubmitter(cortex),
        task_executor=task_executor,
    ).run_once(
        orchestrator,
        source,
        executor,
        {},
        task_id="task-1",
        run_id="run-1",
        completion_event_id="completion-1",
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
        created_at="2026-09-04T12:00:00+00:00",
    )

    completion = result.execution_result.completion_event
    grounding_result = result.submission_result.grounding_result
    assert completion is not None
    assert grounding_result is not None
    assert payload_source.next_payload_calls == 2
    assert len(cortex.llm_client.requests) == 1
    assert [action.value for action in backend.actions] == [PrimitiveAction.CONFIRM.value]
    assert result.planning_observation.screenshot_id == "shot-before"
    assert result.planning_observation.evidence_ids == ["shot-before"]
    assert result.submission_result.planner_output.selected_skill == "interact_visible_object"
    assert result.submission_result.grounding_request is not None
    assert result.submission_result.grounding_request.evidence_scope_ids == ("shot-before",)
    assert grounding_result.status == "grounded"
    assert isinstance(grounding_result.target, VisibleObjectTarget)
    assert result.submission_result.scheduled_task.status is TaskStatus.PENDING
    assert result.started_task.status is TaskStatus.RUNNING
    assert result.started_task.task_spec.task_id == "task-1"
    assert result.execution_result.skill_run_result.skill_result.success
    assert result.execution_result.skill_run_result.verifier_result is not None
    assert result.execution_result.skill_run_result.verifier_result.status is VerifierStatus.SUCCESS
    assert result.execution_result.skill_run_result.verifier_result.evidence_ids == [
        "shot-before",
        "shot-after",
    ]
    assert result.execution_result.skill_run_result.action_execution_results[0].evidence_ids == [
        "shot-before",
        "shot-after",
    ]
    assert completion.status is TaskStatus.SUCCEEDED
    assert completion.selected_skill == "interact_visible_object"
    assert completion.verifier_result is result.execution_result.skill_run_result.verifier_result
    assert completion.manager_stop_result is None
    assert completion.target is grounding_result.target
    assert isinstance(completion.target, VisibleObjectTarget)
    round_tripped = TaskCompletionEvent.model_validate_json(completion.model_dump_json())
    assert round_tripped == completion
    assert isinstance(round_tripped.target, VisibleObjectTarget)
    assert completion.planner_output_id == "planner-output-1"
    assert completion.planner_trace_id == "planner-trace-1"
    assert orchestrator.scheduler.current_task is None
    assert len(orchestrator.scheduler.completed_tasks) == 1
    assert sink.list_task_completions() == [completion]
    verifier_events = [
        record for record in event_logger.read_all() if record.event_type == "verifier_result"
    ]
    assert len(verifier_events) == 1
    assert completion.verifier_event_id == verifier_events[0].event_id


def test_focus_loss_closes_through_existing_manager_stop_path() -> None:
    output = planner_output()
    cortex = Cortex(FakeLLMClient(responses=[json.dumps(output.model_dump(mode="json"))]))
    source = RecordingObservationSource(dialogue_observation())
    sink = InMemoryManagerEventSink()
    orchestrator = ManagerOrchestrator(event_sink=sink)
    executor, backend = dry_run_input_executor(focused=False)

    result = HierarchicalTaskStepRunner(GroundedCortexTaskSubmitter(cortex)).run_once(
        orchestrator,
        source,
        executor,
        {},
        task_id="task-1",
        run_id="run-1",
        completion_event_id="completion-1",
    )

    completion = result.execution_result.completion_event
    assert completion is not None
    assert len(cortex.llm_client.requests) == 1
    assert backend.actions == []
    assert result.execution_result.skill_run_result.manager_stop_result is not None
    assert (
        result.execution_result.skill_run_result.manager_stop_result.failure_kind
        is FailureKind.FOCUS_LOST
    )
    assert completion.status is TaskStatus.FAILED
    assert completion.verifier_result is None
    assert (
        completion.manager_stop_result
        is result.execution_result.skill_run_result.manager_stop_result
    )
    assert orchestrator.scheduler.current_task is None
    assert sink.list_task_completions() == [completion]


def test_module_has_only_composition_dependencies() -> None:
    source = inspect.getsource(hierarchical_step_module)

    for forbidden in (
        "fh_agent.bridge",
        "fh_agent.body",
        "fh_agent.verifier",
        "SkillRunner",
        "SkillCatalog",
        "VerifierCatalog",
        "PrimitiveAction",
        "EventLogger",
        "fh_agent.planner.cortex",
        "LLMClient",
        ".verify(",
        ".execute(",
    ):
        assert forbidden not in source
    assert source.count("observation_source.observe()") == 1
