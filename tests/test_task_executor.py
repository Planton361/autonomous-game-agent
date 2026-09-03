import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import fh_agent.manager.task_executor as task_executor_module
from fh_agent.body.skills.basic_reach_target import BasicReachTargetSkill
from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.observation_source import (
    BridgeObservationSource,
    BridgePayloadSourceExhausted,
)
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.event_sink import InMemoryManagerEventSink
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskSchedulerError, TaskStatus
from fh_agent.manager.skill_catalog import SkillCatalog
from fh_agent.manager.skill_runner import SkillRunResult
from fh_agent.manager.target_ref import GroundingResult, VisibleScreenPointTarget
from fh_agent.manager.task_executor import ManagerTaskExecutor, TaskExecutionError
from fh_agent.manager.verifier_catalog import VerifierCatalog
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation, SkillResult
from fh_agent.observation.source import ObservationSourceExhausted, SequenceObservationSource
from fh_agent.planner.planner_output import EvidenceBackedClaim, PlannerOutput
from fh_agent.verifier.schemas import FailureKind, VerifierStatus


class RecordingSource:
    def __init__(self) -> None:
        self.observe_calls = 0

    def observe(self) -> Observation:
        self.observe_calls += 1
        raise ObservationSourceExhausted


class EvidenceRecordingBridgePayloadSource:
    def __init__(self, event_logger: EventLogger, *payloads: Mapping[str, Any]) -> None:
        self._event_logger = event_logger
        self._payloads = payloads
        self._index = 0
        self.next_payload_calls = 0

    def next_payload(self) -> Mapping[str, Any]:
        self.next_payload_calls += 1
        if self._index >= len(self._payloads):
            raise BridgePayloadSourceExhausted
        payload = self._payloads[self._index]
        self._index += 1
        screenshot_id = payload.get("screenshot_id")
        if isinstance(screenshot_id, str):
            self._event_logger.append(
                "evidence",
                payload={"kind": "screenshot"},
                evidence_ids=[screenshot_id],
            )
        return payload


class RecordingSkillCatalog:
    def __init__(self, skill: object | None = None) -> None:
        self._catalog = SkillCatalog.default()
        self._skill = skill
        self.calls: list[tuple[str, object | None]] = []

    def get(self, skill_name: str, *, task: object | None = None) -> object:
        self.calls.append((skill_name, task))
        if self._skill is not None:
            return self._skill
        return self._catalog.get(skill_name, task=task)  # type: ignore[arg-type]

    def select(self, **_: object) -> object:
        raise AssertionError("ManagerTaskExecutor must not use heuristic skill selection")


class RecordingVerifierCatalog:
    def __init__(self) -> None:
        self._catalog = VerifierCatalog()
        self.tasks: list[object] = []

    def for_task(self, task_spec: object) -> object:
        self.tasks.append(task_spec)
        return self._catalog.for_task(task_spec)  # type: ignore[arg-type]


class RecordingSkillRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object, object]] = []
        self.result: SkillRunResult | None = None

    def run(
        self,
        skill: object,
        observation_source: object,
        *,
        verifier: object,
        input_executor: object,
    ) -> SkillRunResult:
        self.calls.append((skill, observation_source, verifier, input_executor))
        self.result = SkillRunResult(
            skill_result=SkillResult(
                skill_name=skill.contract.skill_name,  # type: ignore[attr-defined]
                success=False,
                failure_reason="nonterminal_test_result",
            )
        )
        return self.result


def planner_output() -> PlannerOutput:
    return PlannerOutput(
        current_belief_state=[
            EvidenceBackedClaim(
                kind="fact",
                claim="A dialogue is visibly open.",
                evidence_ids=["shot-before"],
            )
        ],
        next_goal="Continue the currently visible dialogue.",
        selected_skill="continue_dialogue",
        success_condition=["visible_text_changed", "dialogue_closed"],
    )


def started_orchestrator(*, sink: InMemoryManagerEventSink | None = None) -> ManagerOrchestrator:
    orchestrator = ManagerOrchestrator(event_sink=sink)
    orchestrator.submit_planner_output(planner_output(), task_id="task-1")
    assert orchestrator.start_next() is not None
    return orchestrator


def input_executor(*, focused: bool = True) -> tuple[InputExecutor, DryRunInputBackend]:
    backend = DryRunInputBackend()
    return (
        InputExecutor(
            target=WindowTarget(title="M-005 test window"),
            focus_guard=FakeFocusGuard(focused=focused),
            backend=backend,
            min_interval_seconds=0.0,
        ),
        backend,
    )


def dialogue_observation(text: str, evidence_id: str) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text=text,
        evidence_ids=[evidence_id],
    )


def test_no_running_task_rejects_before_observation_or_input() -> None:
    source = RecordingSource()
    executor, backend = input_executor()

    with pytest.raises(TaskSchedulerError, match="no running task"):
        ManagerTaskExecutor().execute_current_task(
            ManagerOrchestrator(),
            source,
            executor,
            run_id="run-1",
            completion_event_id="completion-1",
        )

    assert source.observe_calls == 0
    assert backend.actions == []


def test_executor_uses_manager_selected_binding_and_preserves_dependencies() -> None:
    orchestrator = started_orchestrator()
    source = object()
    executor = object()
    catalog = RecordingSkillCatalog()
    verifier_catalog = RecordingVerifierCatalog()
    runner = RecordingSkillRunner()

    result = ManagerTaskExecutor(  # type: ignore[arg-type]
        skill_catalog=catalog,
        verifier_catalog=verifier_catalog,
        skill_runner=runner,
    ).execute_current_task(
        orchestrator,
        source,
        executor,
        run_id="run-1",
        completion_event_id="completion-1",
    )

    current_task = orchestrator.scheduler.current_task
    assert current_task is not None
    assert catalog.calls == [("continue_dialogue", None)]
    assert verifier_catalog.tasks == [current_task.task_spec]
    assert runner.calls[0][1] is source
    assert runner.calls[0][3] is executor
    assert result.task_id == "task-1"
    assert result.skill_run_result is runner.result
    assert result.completion_event is None
    assert orchestrator.scheduler.current_task is not None


def test_catalog_skill_mismatch_fails_before_observation_or_input() -> None:
    orchestrator = started_orchestrator()
    source = RecordingSource()
    executor, backend = input_executor()
    catalog = RecordingSkillCatalog(skill=BasicReachTargetSkill())

    with pytest.raises(TaskExecutionError, match="does not match"):
        ManagerTaskExecutor(skill_catalog=catalog).execute_current_task(  # type: ignore[arg-type]
            orchestrator,
            source,
            executor,
            run_id="run-1",
            completion_event_id="completion-1",
        )

    assert source.observe_calls == 0
    assert backend.actions == []


def test_executor_passes_the_exact_grounded_target_to_the_catalog() -> None:
    target = VisibleScreenPointTarget(
        target_id="visible-point-1",
        confidence=0.9,
        evidence_ids=("shot-before",),
        screen_position=(10, 20),
    )
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(
        planner_output().model_copy(update={"selected_skill": "basic_reach_target"}),
        task_id="task-1",
        grounding_result=GroundingResult(
            status="grounded",
            target=target,
            evidence_ids=("shot-before",),
        ),
    )
    assert orchestrator.start_next() is not None
    catalog = RecordingSkillCatalog()
    runner = RecordingSkillRunner()

    ManagerTaskExecutor(  # type: ignore[arg-type]
        skill_catalog=catalog,
        skill_runner=runner,
    ).execute_current_task(
        orchestrator,
        object(),
        object(),
        run_id="run-1",
        completion_event_id="completion-1",
    )

    assert catalog.calls == [("basic_reach_target", target)]


def test_bridge_assisted_manager_slice_completes_with_independent_verifier(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    event_logger = EventLogger(event_log_path, run_id="run-1")
    payload_source = EvidenceRecordingBridgePayloadSource(
        event_logger,
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "First visible line.",
            "screenshot_id": "shot-before",
        },
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "Second visible line.",
            "screenshot_id": "shot-after",
        },
    )
    source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    )
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)
    executor, backend = input_executor()

    result = ManagerTaskExecutor().execute_current_task(
        orchestrator,
        source,
        executor,
        run_id="run-1",
        completion_event_id="completion-1",
        created_at="2026-09-03T00:00:00+00:00",
    )

    completion = result.completion_event
    assert result.skill_run_result.skill_result.success is True
    assert result.skill_run_result.verifier_result is not None
    assert result.skill_run_result.verifier_result.status is VerifierStatus.SUCCESS
    assert result.skill_run_result.verifier_result.evidence_ids == ["shot-before", "shot-after"]
    assert result.skill_run_result.action_execution_results[0].evidence_ids == [
        "shot-before",
        "shot-after",
    ]
    assert [action.value for action in backend.actions] == ["confirm"]
    assert payload_source.next_payload_calls == 2
    assert completion is not None
    assert completion.status is TaskStatus.SUCCEEDED
    assert completion.task_id == "task-1"
    assert completion.selected_skill == "continue_dialogue"
    assert completion.verifier_result is result.skill_run_result.verifier_result
    assert completion.manager_stop_result is None
    assert completion.manager_stop_event_id is None
    assert orchestrator.scheduler.current_task is None
    assert sink.list_task_completions() == [completion]


def test_manager_stop_is_forwarded_to_existing_orchestrator_closure() -> None:
    orchestrator = started_orchestrator()
    executor, backend = input_executor(focused=False)

    result = ManagerTaskExecutor().execute_current_task(
        orchestrator,
        SequenceObservationSource([dialogue_observation("Visible.", "shot-before")]),
        executor,
        run_id="run-1",
        completion_event_id="completion-1",
    )

    completion = result.completion_event
    assert backend.actions == []
    assert result.skill_run_result.manager_stop_result is not None
    assert result.skill_run_result.manager_stop_result.failure_kind is FailureKind.FOCUS_LOST
    assert result.skill_run_result.verifier_result is None
    assert completion is not None
    assert completion.status is TaskStatus.FAILED
    assert completion.manager_stop_result is result.skill_run_result.manager_stop_result
    assert completion.verifier_result is None
    assert orchestrator.scheduler.current_task is None


def test_nonterminal_skill_run_does_not_fabricate_task_completion() -> None:
    orchestrator = started_orchestrator()
    executor, backend = input_executor()

    result = ManagerTaskExecutor().execute_current_task(
        orchestrator,
        SequenceObservationSource([dialogue_observation("Visible.", "shot-before")]),
        executor,
        run_id="run-1",
        completion_event_id="completion-1",
    )

    assert [action.value for action in backend.actions] == ["confirm"]
    assert result.skill_run_result.verifier_result is None
    assert result.skill_run_result.manager_stop_result is None
    assert result.completion_event is None
    assert orchestrator.scheduler.current_task is not None


def test_executor_does_not_bypass_runtime_authorities() -> None:
    source = inspect.getsource(task_executor_module)

    assert ".observe(" not in source
    assert ".execute(" not in source
    assert "VerifierResult(" not in source
    assert "derive_verified_reward" not in source
    assert ".verify(" not in source
