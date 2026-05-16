import inspect

import pytest

from fh_agent.manager import orchestrator as orchestrator_module
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskSchedulerError, TaskStatus
from fh_agent.planner.planner_output import PlannerOutput


def valid_planner_output(
    *,
    goal: str = "Continue the visible dialogue until the message changes.",
) -> PlannerOutput:
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
            "next_goal": goal,
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


def started_orchestrator(task_id: str = "task-1") -> ManagerOrchestrator:
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(valid_planner_output(), task_id=task_id)
    orchestrator.start_next()
    return orchestrator


def test_submit_planner_output_creates_queued_scheduled_task() -> None:
    orchestrator = ManagerOrchestrator()

    scheduled = orchestrator.submit_planner_output(
        valid_planner_output(),
        task_id="task-1",
    )

    assert scheduled.status == TaskStatus.PENDING
    assert scheduled.task_spec.task_id == "task-1"
    assert orchestrator.scheduler.queued_tasks == (scheduled,)


def test_start_next_starts_queued_task() -> None:
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(valid_planner_output(), task_id="task-1")

    started = orchestrator.start_next()

    assert started is not None
    assert started.status == TaskStatus.RUNNING
    assert started.task_spec.task_id == "task-1"
    assert orchestrator.scheduler.current_task == started


def test_mark_success_returns_task_completion_event_with_succeeded() -> None:
    orchestrator = started_orchestrator()

    event = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
        evidence_ids=["completion-shot-1"],
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert event.status == TaskStatus.SUCCEEDED
    assert event.event_type == "task_completion"
    assert event.task_id == "task-1"
    assert event.completion_evidence_ids == ["completion-shot-1"]


def test_mark_failure_returns_task_completion_event_with_failed() -> None:
    orchestrator = started_orchestrator()

    event = orchestrator.mark_failure(
        run_id="run-1",
        event_id="event-1",
        condition="death_screen",
        evidence_ids=["completion-shot-2"],
        reason="visible failure state",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert event.status == TaskStatus.FAILED
    assert event.condition == "death_screen"
    assert event.reason == "visible failure state"
    assert event.completion_evidence_ids == ["completion-shot-2"]


def test_cancel_current_returns_task_completion_event_with_cancelled() -> None:
    orchestrator = started_orchestrator()

    event = orchestrator.cancel_current(
        run_id="run-1",
        event_id="event-1",
        reason="superseded by newer task",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert event.status == TaskStatus.CANCELLED
    assert event.condition == "cancelled"
    assert event.reason == "superseded by newer task"


def test_tick_returns_none_before_timeout() -> None:
    orchestrator = started_orchestrator()

    event = orchestrator.tick(
        run_id="run-1",
        event_id="event-1",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert event is None
    assert orchestrator.scheduler.current_task is not None
    assert orchestrator.scheduler.current_task.elapsed_steps == 1


def test_tick_returns_task_completion_event_with_timed_out_at_timeout() -> None:
    orchestrator = started_orchestrator()

    event = None
    for _ in range(6):
        event = orchestrator.tick(
            run_id="run-1",
            event_id="event-timeout",
            created_at="2026-05-16T12:00:00+00:00",
        )

    assert event is not None
    assert event.status == TaskStatus.TIMED_OUT
    assert event.condition == "timeout"
    assert event.reason == "timeout"
    assert event.elapsed_steps == 6
    assert orchestrator.scheduler.current_task is None


def test_fifo_ordering_works_through_orchestrator() -> None:
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(
        valid_planner_output(goal="First visible goal."),
        task_id="task-1",
    )
    orchestrator.submit_planner_output(
        valid_planner_output(goal="Second visible goal."),
        task_id="task-2",
    )

    first = orchestrator.start_next()
    assert first is not None
    orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
    )
    second = orchestrator.start_next()

    assert first.task_spec.task_id == "task-1"
    assert second is not None
    assert second.task_spec.task_id == "task-2"


def test_event_preserves_planner_output_id_and_planner_trace_id() -> None:
    orchestrator = ManagerOrchestrator()
    orchestrator.submit_planner_output(
        valid_planner_output(),
        task_id="task-1",
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
    )
    orchestrator.start_next()

    event = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
    )

    assert event.planner_output_id == "planner-output-1"
    assert event.planner_trace_id == "planner-trace-1"


def test_event_preserves_source_and_completion_evidence_ids() -> None:
    orchestrator = started_orchestrator()

    event = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
        evidence_ids=["completion-shot-1"],
    )

    assert event.source_evidence_ids == ["source-shot-1", "source-shot-2"]
    assert event.completion_evidence_ids == ["completion-shot-1"]


def test_invalid_success_condition_propagates_scheduler_validation_error() -> None:
    orchestrator = started_orchestrator()

    with pytest.raises(TaskSchedulerError, match="invalid success condition"):
        orchestrator.mark_success(
            run_id="run-1",
            event_id="event-1",
            condition="screen_transition",
        )


def test_invalid_failure_condition_propagates_scheduler_validation_error() -> None:
    orchestrator = started_orchestrator()

    with pytest.raises(TaskSchedulerError, match="invalid failure condition"):
        orchestrator.mark_failure(
            run_id="run-1",
            event_id="event-1",
            condition="invalid_failure",
        )


def test_orchestrator_module_has_no_forbidden_imports() -> None:
    source = inspect.getsource(orchestrator_module)

    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.memory" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
    assert "sqlite" not in source.lower()
    assert "jsonl" not in source.lower()
