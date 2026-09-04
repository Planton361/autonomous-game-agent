import inspect
import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import fh_agent.manager.replan_loop as replan_loop_module
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
from fh_agent.manager.hierarchical_step import HierarchicalTaskStepRunner
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.replan_loop import (
    HierarchicalReplanLoopRunner,
    ReplanLoopError,
    ReplanLoopStepIds,
)
from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.manager.scheduler import TaskStatus
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.manager.task_executor import ManagerTaskExecutor
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSourceExhausted
from fh_agent.planner.cortex import Cortex
from fh_agent.planner.llm_client import FakeLLMClient
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def verifier_completion(
    *,
    task_id: str,
    selected_skill: str = "continue_dialogue",
    status: VerifierStatus = VerifierStatus.SUCCESS,
    evidence_ids: list[str] | None = None,
) -> TaskCompletionEvent:
    verifier_result = VerifierResult(
        status=status,
        failure_kind=FailureKind.NO_PROGRESS if status is VerifierStatus.FAILURE else None,
        evidence_ids=evidence_ids if evidence_ids is not None else [f"{task_id}-evidence"],
    )
    return TaskCompletionEvent(
        event_id=f"{task_id}-completion",
        run_id="run-1",
        task_id=task_id,
        selected_skill=selected_skill,
        goal="Use the selected universal skill.",
        target=None,
        status=TaskStatus.SUCCEEDED if status is VerifierStatus.SUCCESS else TaskStatus.FAILED,
        condition="verified_condition",
        elapsed_steps=1,
        timeout_steps=3,
        completion_evidence_ids=list(verifier_result.evidence_ids),
        verifier_result=verifier_result,
        verifier_event_id=f"{task_id}-verifier",
        created_at="2026-09-04T12:00:00+00:00",
    )


def manager_stop_completion(task_id: str) -> TaskCompletionEvent:
    manager_stop = ManagerStopResult(
        failure_kind=FailureKind.FOCUS_LOST,
        reason="target window is not focused",
        evidence_ids=[f"{task_id}-stop"],
    )
    return TaskCompletionEvent(
        event_id=f"{task_id}-completion",
        run_id="run-1",
        task_id=task_id,
        selected_skill="continue_dialogue",
        goal="Continue visible dialogue.",
        target=None,
        status=TaskStatus.FAILED,
        condition="focus_lost",
        elapsed_steps=0,
        timeout_steps=3,
        manager_stop_result=manager_stop,
        manager_stop_event_id=f"{task_id}-stop-event",
        created_at="2026-09-04T12:00:00+00:00",
    )


class RecordingStepRunner:
    def __init__(self, *completions: TaskCompletionEvent | None) -> None:
        self._completions = completions
        self.calls: list[dict[str, object]] = []
        self.results: list[object] = []

    def run_once(self, *args: object, **kwargs: object) -> object:
        index = len(self.calls)
        self.calls.append({"args": args, **kwargs})
        completion = self._completions[index]
        result = SimpleNamespace(execution_result=SimpleNamespace(completion_event=completion))
        self.results.append(result)
        return result


class SequenceObservationSource:
    def __init__(self, *observations: Observation) -> None:
        self._observations = observations
        self._index = 0

    def observe(self) -> Observation:
        if self._index >= len(self._observations):
            raise ObservationSourceExhausted
        observation = self._observations[self._index]
        self._index += 1
        return observation


def dummy_input_executor() -> InputExecutor:
    return InputExecutor(
        target=WindowTarget(title="M-013 dry-run window"),
        focus_guard=FakeFocusGuard(focused=True),
        backend=DryRunInputBackend(),
        min_interval_seconds=0.0,
    )


def step_ids(*task_ids: str) -> tuple[ReplanLoopStepIds, ...]:
    return tuple(
        ReplanLoopStepIds(task_id=task_id, completion_event_id=f"{task_id}-completion")
        for task_id in task_ids
    )


def test_empty_budget_rejects_before_step_runner_or_input_activity() -> None:
    step_runner = RecordingStepRunner()

    with pytest.raises(ReplanLoopError, match="at least one step ID"):
        HierarchicalReplanLoopRunner(step_runner).run_bounded(  # type: ignore[arg-type]
            ManagerOrchestrator(),
            object(),  # type: ignore[arg-type]
            dummy_input_executor(),
            {},
            run_id="run-1",
            step_ids=(),
        )

    assert step_runner.calls == []


def test_verifier_success_updates_context_and_final_budget_result() -> None:
    completion = verifier_completion(task_id="task-1")
    step_runner = RecordingStepRunner(completion)
    base = {"known_facts": [{"claim": "Existing fact.", "evidence_ids": ["old"]}]}

    result = HierarchicalReplanLoopRunner(step_runner).run_bounded(  # type: ignore[arg-type]
        ManagerOrchestrator(),
        object(),  # type: ignore[arg-type]
        dummy_input_executor(),
        base,
        run_id="run-1",
        step_ids=step_ids("task-1"),
    )

    assert step_runner.calls[0]["args"][3] is base
    assert result.step_results == (step_runner.results[0],)
    assert result.stop_reason == "budget_exhausted"
    assert result.final_memory_summary["known_facts"] is base["known_facts"]
    assert result.final_memory_summary["recent_skill_outcomes"][0]["evidence_ids"] == [
        "task-1-evidence"
    ]
    assert base.get("recent_skill_outcomes") is None


def test_verifier_failure_is_eligible_for_next_step_with_updated_context() -> None:
    first = verifier_completion(task_id="task-1", status=VerifierStatus.FAILURE)
    second = verifier_completion(task_id="task-2")
    step_runner = RecordingStepRunner(first, second)

    result = HierarchicalReplanLoopRunner(step_runner).run_bounded(  # type: ignore[arg-type]
        ManagerOrchestrator(),
        object(),  # type: ignore[arg-type]
        dummy_input_executor(),
        {"custom": "preserved"},
        run_id="run-1",
        step_ids=step_ids("task-1", "task-2"),
    )

    second_memory = step_runner.calls[1]["args"][3]
    assert isinstance(second_memory, Mapping)
    assert second_memory["recent_skill_outcomes"] == [
        {
            "status": "observed_fact",
            "note": "Skill continue_dialogue completed with verifier failure no_progress.",
            "evidence_ids": ["task-1-evidence"],
        }
    ]
    assert result.stop_reason == "budget_exhausted"
    assert len(result.final_memory_summary["recent_skill_outcomes"]) == 2


def test_nonterminal_and_manager_stop_halt_without_context_append() -> None:
    for completion, expected_reason in (
        (None, "nonterminal"),
        (manager_stop_completion("task-1"), "manager_stop"),
    ):
        step_runner = RecordingStepRunner(completion)
        result = HierarchicalReplanLoopRunner(step_runner).run_bounded(  # type: ignore[arg-type]
            ManagerOrchestrator(),
            object(),  # type: ignore[arg-type]
            dummy_input_executor(),
            {"recent_skill_outcomes": [{"note": "prior"}]},
            run_id="run-1",
            step_ids=step_ids("task-1", "task-2"),
        )

        assert result.stop_reason == expected_reason
        assert len(step_runner.calls) == 1
        assert result.final_memory_summary["recent_skill_outcomes"] == [{"note": "prior"}]


def test_terminal_completion_without_verifier_or_manager_stop_fails_closed() -> None:
    completion = TaskCompletionEvent(
        event_id="completion-1",
        run_id="run-1",
        task_id="task-1",
        selected_skill="continue_dialogue",
        goal="Continue visible dialogue.",
        target=None,
        status=TaskStatus.FAILED,
        condition="legacy_failure",
        elapsed_steps=1,
        timeout_steps=3,
        created_at="2026-09-04T12:00:00+00:00",
    )

    with pytest.raises(ReplanLoopError, match="verifier or ManagerStop"):
        HierarchicalReplanLoopRunner(RecordingStepRunner(completion)).run_bounded(  # type: ignore[arg-type]
            ManagerOrchestrator(),
            object(),  # type: ignore[arg-type]
            dummy_input_executor(),
            {},
            run_id="run-1",
            step_ids=step_ids("task-1"),
        )


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
        screenshot_id = payload["screenshot_id"]
        assert isinstance(screenshot_id, str)
        self._event_logger.append(
            "evidence",
            payload={"kind": "screenshot"},
            evidence_ids=[screenshot_id],
        )
        return payload


def planner_payload(
    *,
    selected_skill: str,
    evidence_ids: list[str],
    next_goal: str,
    success_condition: str,
) -> dict[str, object]:
    return {
        "current_belief_state": [
            {
                "kind": "fact",
                "claim": "Visible evidence supports the selected skill.",
                "evidence_ids": evidence_ids,
            }
        ],
        "open_questions": [],
        "next_goal": next_goal,
        "selected_skill": selected_skill,
        "success_condition": [success_condition],
        "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
        "memory_updates_requested": [],
    }


def dry_run_executor() -> tuple[InputExecutor, DryRunInputBackend]:
    backend = DryRunInputBackend()
    return (
        InputExecutor(
            target=WindowTarget(title="M-013 dry-run window"),
            focus_guard=FakeFocusGuard(focused=True),
            backend=backend,
            min_interval_seconds=0.0,
        ),
        backend,
    )


def dialogue_observation() -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="First visible line.",
        evidence_ids=["shot-1"],
    )


def test_two_step_bridge_assisted_loop_replans_from_verified_outcome(tmp_path: Path) -> None:
    event_logger = EventLogger(tmp_path / "events.jsonl", run_id="run-1")
    payload_source = EvidenceRecordingBridgePayloadSource(
        event_logger,
        {
            "run_mode": "bridge-assisted",
            "ui_state": "field",
            "visible_sprite_screen_positions": [[120, 80]],
            "visible_sprite_visual_hashes": ["dhash:0123456789abcdef"],
            "screenshot_id": "shot-1",
        },
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "First visible line.",
            "screenshot_id": "shot-2",
        },
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "First visible line.",
            "screenshot_id": "shot-3",
        },
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "Second visible line.",
            "screenshot_id": "shot-4",
        },
    )
    source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_logger.path),
    )
    first = planner_payload(
        selected_skill="interact_visible_object",
        evidence_ids=["shot-1"],
        next_goal="Interact with the visible object.",
        success_condition="visible_interaction",
    )
    second = planner_payload(
        selected_skill="continue_dialogue",
        evidence_ids=["shot-2", "shot-3"],
        next_goal="Continue the visible dialogue.",
        success_condition="visible_text_changed",
    )
    client = FakeLLMClient(responses=[json.dumps(first), json.dumps(second)])
    sink = InMemoryManagerEventSink()
    orchestrator = ManagerOrchestrator(event_sink=sink)
    input_executor, backend = dry_run_executor()
    step_runner = HierarchicalTaskStepRunner(
        GroundedCortexTaskSubmitter(Cortex(client)),
        task_executor=ManagerTaskExecutor(skill_runner=SkillRunner(event_logger=event_logger)),
    )

    result = HierarchicalReplanLoopRunner(step_runner).run_bounded(
        orchestrator,
        source,
        input_executor,
        {},
        run_id="run-1",
        step_ids=(
            ReplanLoopStepIds("task-1", "completion-1", "planner-1", "trace-1"),
            ReplanLoopStepIds("task-2", "completion-2", "planner-2", "trace-2"),
        ),
        created_at="2026-09-04T12:00:00+00:00",
    )

    assert payload_source.next_payload_calls == 4
    assert len(client.requests) == 2
    assert [action.value for action in backend.actions] == [
        PrimitiveAction.CONFIRM.value,
        PrimitiveAction.CONFIRM.value,
    ]
    assert len(result.step_results) == 2
    assert result.stop_reason == "budget_exhausted"
    assert (
        result.step_results[0].submission_result.planner_output.selected_skill
        == "interact_visible_object"
    )
    assert (
        result.step_results[1].submission_result.planner_output.selected_skill
        == "continue_dialogue"
    )
    assert result.step_results[0].execution_result.completion_event is not None
    assert result.step_results[1].execution_result.completion_event is not None
    assert result.step_results[0].execution_result.completion_event.verifier_result is not None
    assert (
        result.step_results[0].execution_result.completion_event.verifier_result.status
        is VerifierStatus.SUCCESS
    )
    assert orchestrator.scheduler.current_task is None
    assert len(orchestrator.scheduler.completed_tasks) == 2
    assert len(sink.list_task_completions()) == 2
    assert len(result.final_memory_summary["recent_skill_outcomes"]) == 2
    second_context = json.loads(client.requests[1][1]["content"].split("CortexContext JSON:\n")[1])
    assert second_context["recent_skill_outcomes"][0] == {
        "status": "observed_fact",
        "note": "Skill interact_visible_object completed with verifier status success.",
        "evidence_ids": ["shot-1", "shot-2"],
    }


def test_focus_loss_manager_stop_prevents_a_second_attempt() -> None:
    payload = planner_payload(
        selected_skill="continue_dialogue",
        evidence_ids=["shot-1"],
        next_goal="Continue the visible dialogue.",
        success_condition="visible_text_changed",
    )
    client = FakeLLMClient(responses=[json.dumps(payload), json.dumps(payload)])
    backend = DryRunInputBackend()
    input_executor = InputExecutor(
        target=WindowTarget(title="M-013 focus-loss window"),
        focus_guard=FakeFocusGuard(focused=False),
        backend=backend,
        min_interval_seconds=0.0,
    )

    result = HierarchicalReplanLoopRunner(
        HierarchicalTaskStepRunner(GroundedCortexTaskSubmitter(Cortex(client)))
    ).run_bounded(
        ManagerOrchestrator(),
        SequenceObservationSource(dialogue_observation()),
        input_executor,
        {},
        run_id="run-1",
        step_ids=step_ids("task-1", "task-2"),
    )

    completion = result.step_results[0].execution_result.completion_event
    assert completion is not None
    assert completion.manager_stop_result is not None
    assert len(client.requests) == 1
    assert backend.actions == []
    assert len(result.step_results) == 1
    assert result.stop_reason == "manager_stop"
    assert "recent_skill_outcomes" not in result.final_memory_summary


def test_post_action_exhaustion_stops_as_nonterminal_without_second_attempt() -> None:
    payload = planner_payload(
        selected_skill="continue_dialogue",
        evidence_ids=["shot-1"],
        next_goal="Continue the visible dialogue.",
        success_condition="visible_text_changed",
    )
    client = FakeLLMClient(responses=[json.dumps(payload), json.dumps(payload)])
    input_executor, backend = dry_run_executor()
    orchestrator = ManagerOrchestrator()

    result = HierarchicalReplanLoopRunner(
        HierarchicalTaskStepRunner(GroundedCortexTaskSubmitter(Cortex(client)))
    ).run_bounded(
        orchestrator,
        SequenceObservationSource(dialogue_observation()),
        input_executor,
        {},
        run_id="run-1",
        step_ids=step_ids("task-1", "task-2"),
    )

    assert result.step_results[0].execution_result.completion_event is None
    assert len(client.requests) == 1
    assert [action.value for action in backend.actions] == [PrimitiveAction.CONFIRM.value]
    assert result.stop_reason == "nonterminal"
    assert orchestrator.scheduler.current_task is not None


def test_module_has_only_finite_composition_dependencies() -> None:
    source = inspect.getsource(replan_loop_module)

    for forbidden in (
        "Cortex",
        "LLMClient",
        "GroundedCortexTaskSubmitter",
        "ManagerTaskExecutor",
        "SkillRunner",
        "SkillCatalog",
        "VerifierCatalog",
        "PrimitiveAction",
        "GroundingService",
        "MemoryDB",
        "EventLogger",
        "while True",
        ".execute(",
        ".verify(",
    ):
        assert forbidden not in source
