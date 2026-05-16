import inspect
import json

import pytest
from pydantic import ValidationError

from fh_agent.manager import task_events as task_events_module
from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.scheduler import TaskCompletion, TaskScheduler, TaskStatus
from fh_agent.manager.task_events import TaskCompletionEvent, task_completion_to_event
from fh_agent.manager.task_spec import TaskSpec


def make_task_spec(task_id: str = "task-1", *, timeout_steps: int = 3) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        selected_skill="continue_dialogue",
        goal=f"Run {task_id}.",
        target={"description": f"target for {task_id}"},
        constraints={"avoid_known_dangers": True, "max_danger_score": 0.4},
        success_conditions=["new_visible_text"],
        failure_conditions=["death_screen", "timeout"],
        timeout_steps=timeout_steps,
        reward_profile=default_reward_profile_for_skill("continue_dialogue"),
        source_evidence_ids=["source-shot-1"],
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
    )


def completion_for_status(status: TaskStatus) -> TaskCompletion:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec(timeout_steps=2))
    scheduler.start_next()

    if status == TaskStatus.SUCCEEDED:
        return scheduler.mark_success("new_visible_text", evidence_ids=["completion-shot-1"])
    if status == TaskStatus.FAILED:
        return scheduler.mark_failure(
            "death_screen",
            evidence_ids=["completion-shot-2"],
            reason="visible failure state",
        )
    if status == TaskStatus.TIMED_OUT:
        scheduler.tick()
        scheduler.tick()
        completed = scheduler.completed_tasks[-1]
        assert completed.completion is not None
        return completed.completion
    if status == TaskStatus.CANCELLED:
        return scheduler.cancel_current("superseded by newer task")

    raise AssertionError(f"unsupported status: {status}")


def event_for_status(status: TaskStatus) -> TaskCompletionEvent:
    return task_completion_to_event(
        completion_for_status(status),
        run_id="run-1",
        event_id=f"event-{status}",
        created_at="2026-05-16T12:00:00+00:00",
    )


def test_succeeded_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    assert event.event_type == "task_completion"
    assert event.status == TaskStatus.SUCCEEDED
    assert event.condition == "new_visible_text"
    assert event.reason is None
    assert event.completion_evidence_ids == ["completion-shot-1"]


def test_failed_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.FAILED)

    assert event.status == TaskStatus.FAILED
    assert event.condition == "death_screen"
    assert event.reason == "visible failure state"
    assert event.completion_evidence_ids == ["completion-shot-2"]


def test_timed_out_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.TIMED_OUT)

    assert event.status == TaskStatus.TIMED_OUT
    assert event.condition == "timeout"
    assert event.reason == "timeout"
    assert event.elapsed_steps == 2
    assert event.timeout_steps == 2


def test_cancelled_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.CANCELLED)

    assert event.status == TaskStatus.CANCELLED
    assert event.condition == "cancelled"
    assert event.reason == "superseded by newer task"


def test_event_preserves_task_completion_core_fields() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    assert event.event_id == "event-succeeded"
    assert event.run_id == "run-1"
    assert event.task_id == "task-1"
    assert event.selected_skill == "continue_dialogue"
    assert event.goal == "Run task-1."
    assert event.target == {"description": "target for task-1"}
    assert event.elapsed_steps == 0
    assert event.created_at == "2026-05-16T12:00:00+00:00"


def test_event_preserves_planner_ids() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    assert event.planner_output_id == "planner-output-1"
    assert event.planner_trace_id == "planner-trace-1"


def test_event_separates_source_and_completion_evidence_ids() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    assert event.source_evidence_ids == ["source-shot-1"]
    assert event.completion_evidence_ids == ["completion-shot-1"]


def test_event_includes_reward_term_names_without_reward_calculation() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    assert event.reward_terms == [
        "new_visible_text",
        "skill_success",
        "avoid_timeout",
        "avoid_repeated_no_progress",
    ]


def test_event_json_serialization_works() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    payload = json.loads(event.model_dump_json())

    assert payload["event_type"] == "task_completion"
    assert payload["status"] == "succeeded"
    assert payload["reward_terms"] == event.reward_terms


def test_empty_run_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        task_completion_to_event(
            completion_for_status(TaskStatus.SUCCEEDED),
            run_id="",
            event_id="event-1",
            created_at="2026-05-16T12:00:00+00:00",
        )


def test_empty_event_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        task_completion_to_event(
            completion_for_status(TaskStatus.SUCCEEDED),
            run_id="run-1",
            event_id="",
            created_at="2026-05-16T12:00:00+00:00",
        )


def test_created_at_defaults_to_utc_iso_timestamp() -> None:
    event = task_completion_to_event(
        completion_for_status(TaskStatus.SUCCEEDED),
        run_id="run-1",
        event_id="event-1",
    )

    assert event.created_at.endswith("+00:00")


def test_task_events_module_has_no_forbidden_module_dependencies() -> None:
    source = inspect.getsource(task_events_module)

    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.memory" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
    assert "sqlite" not in source.lower()
    assert "jsonl" not in source.lower()
