import inspect

import pytest

from fh_agent.manager import mock_completion as mock_completion_module
from fh_agent.manager.mock_completion import (
    MockSkillCompletionSignal,
    apply_mock_completion_signal,
)
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskSchedulerError, TaskStatus
from fh_agent.planner.planner_output import PlannerOutput


def valid_planner_output() -> PlannerOutput:
    return PlannerOutput.model_validate(
        {
            "current_belief_state": [
                {
                    "kind": "fact",
                    "claim": "A visible message is currently on screen.",
                    "evidence_ids": ["source-shot-1"],
                }
            ],
            "open_questions": ["Will the visible text change?"],
            "next_goal": "Continue the visible dialogue until the message changes.",
            "selected_skill": "continue_dialogue",
            "success_condition": ["new_visible_text"],
            "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
            "memory_updates_requested": [
                {
                    "claim": "A visible message is currently on screen.",
                    "evidence_ids": ["source-shot-2"],
                    "reason": "Observed in the current screenshot.",
                }
            ],
        }
    )


def started_orchestrator() -> ManagerOrchestrator:
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(
        valid_planner_output(),
        task_id="task-1",
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
    )
    orchestrator.start_next()
    return orchestrator


def apply_signal(
    signal: MockSkillCompletionSignal,
    *,
    orchestrator: ManagerOrchestrator | None = None,
):
    return apply_mock_completion_signal(
        orchestrator or started_orchestrator(),
        signal,
        run_id="run-1",
        event_id="event-1",
        created_at="2026-05-16T12:00:00+00:00",
    )


def test_dry_run_succeeded_signal_returns_task_completion_event() -> None:
    event = apply_signal(
        MockSkillCompletionSignal(
            task_id="task-1",
            status="succeeded",
            condition="new_visible_text",
            evidence_ids=["completion-shot-1"],
        )
    )

    assert event.status == TaskStatus.SUCCEEDED
    assert event.task_id == "task-1"
    assert event.condition == "new_visible_text"
    assert event.completion_evidence_ids == ["completion-shot-1"]
    assert event.event_type == "task_completion"


def test_dry_run_failed_signal_returns_failed_event() -> None:
    event = apply_signal(
        MockSkillCompletionSignal(
            task_id="task-1",
            status="failed",
            condition="death_screen",
            reason="visible failure state",
            evidence_ids=["completion-shot-2"],
        )
    )

    assert event.status == TaskStatus.FAILED
    assert event.condition == "death_screen"
    assert event.reason == "visible failure state"
    assert event.completion_evidence_ids == ["completion-shot-2"]


def test_dry_run_cancelled_signal_returns_cancelled_event() -> None:
    event = apply_signal(
        MockSkillCompletionSignal(
            task_id="task-1",
            status="cancelled",
            condition="cancelled",
            reason="superseded by dry-run test",
            evidence_ids=["completion-shot-3"],
        )
    )

    assert event.status == TaskStatus.CANCELLED
    assert event.condition == "cancelled"
    assert event.reason == "superseded by dry-run test"
    assert event.completion_evidence_ids == ["completion-shot-3"]


def test_signal_without_running_task_is_rejected() -> None:
    orchestrator = ManagerOrchestrator()

    with pytest.raises(TaskSchedulerError, match="no running task"):
        apply_signal(
            MockSkillCompletionSignal(
                task_id="task-1",
                status="succeeded",
                condition="new_visible_text",
            ),
            orchestrator=orchestrator,
        )


def test_signal_with_wrong_task_id_is_rejected() -> None:
    with pytest.raises(TaskSchedulerError, match="does not match current task"):
        apply_signal(
            MockSkillCompletionSignal(
                task_id="wrong-task",
                status="succeeded",
                condition="new_visible_text",
            )
        )


def test_invalid_success_condition_is_rejected() -> None:
    with pytest.raises(TaskSchedulerError, match="invalid success condition"):
        apply_signal(
            MockSkillCompletionSignal(
                task_id="task-1",
                status="succeeded",
                condition="screen_transition",
            )
        )


def test_invalid_failure_condition_is_rejected() -> None:
    with pytest.raises(TaskSchedulerError, match="invalid failure condition"):
        apply_signal(
            MockSkillCompletionSignal(
                task_id="task-1",
                status="failed",
                condition="invalid_failure",
            )
        )


def test_signal_evidence_ids_become_completion_evidence_ids() -> None:
    event = apply_signal(
        MockSkillCompletionSignal(
            task_id="task-1",
            status="succeeded",
            condition="new_visible_text",
            evidence_ids=["completion-shot-1", "completion-shot-2"],
        )
    )

    assert event.completion_evidence_ids == ["completion-shot-1", "completion-shot-2"]


def test_event_preserves_planner_output_id_and_planner_trace_id() -> None:
    event = apply_signal(
        MockSkillCompletionSignal(
            task_id="task-1",
            status="succeeded",
            condition="new_visible_text",
        )
    )

    assert event.planner_output_id == "planner-output-1"
    assert event.planner_trace_id == "planner-trace-1"


def test_mock_completion_module_has_no_forbidden_imports() -> None:
    source = inspect.getsource(mock_completion_module)

    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.memory" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
    assert "sqlite" not in source.lower()
    assert "jsonl" not in source.lower()
