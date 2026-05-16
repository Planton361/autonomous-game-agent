import inspect

import pytest

from fh_agent.manager import scheduler as scheduler_module
from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.scheduler import TaskScheduler, TaskSchedulerError, TaskStatus
from fh_agent.manager.task_spec import TaskSpec


def make_task_spec(
    task_id: str = "task-1",
    *,
    timeout_steps: int = 3,
    success_conditions: list[str] | None = None,
    failure_conditions: list[str] | None = None,
) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        selected_skill="continue_dialogue",
        goal=f"Run {task_id}.",
        target={"description": f"target for {task_id}"},
        constraints={"avoid_known_dangers": True, "max_danger_score": 0.4},
        success_conditions=["new_visible_text"]
        if success_conditions is None
        else success_conditions,
        failure_conditions=(
            ["timeout", "death_screen"] if failure_conditions is None else failure_conditions
        ),
        timeout_steps=timeout_steps,
        reward_profile=default_reward_profile_for_skill("continue_dialogue"),
        source_evidence_ids=["shot-1"],
    )


def test_enqueue_sets_status_pending() -> None:
    scheduler = TaskScheduler()
    scheduled = scheduler.enqueue(make_task_spec())

    assert scheduled.status == TaskStatus.PENDING
    assert scheduler.queued_tasks == (scheduled,)
    assert scheduler.current_task is None


def test_start_next_sets_first_task_running() -> None:
    scheduler = TaskScheduler()
    task = scheduler.enqueue(make_task_spec())

    started = scheduler.start_next()

    assert started is not None
    assert started.task_spec.task_id == task.task_spec.task_id
    assert started.status == TaskStatus.RUNNING
    assert scheduler.current_task == started


def test_fifo_order_is_preserved() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec("task-1"))
    scheduler.enqueue(make_task_spec("task-2"))

    first = scheduler.start_next()
    assert first is not None
    scheduler.mark_success("new_visible_text")
    second = scheduler.start_next()

    assert second is not None
    assert first.task_spec.task_id == "task-1"
    assert second.task_spec.task_id == "task-2"


def test_second_task_cannot_start_while_one_is_running() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec("task-1"))
    scheduler.enqueue(make_task_spec("task-2"))

    first = scheduler.start_next()
    second = scheduler.start_next()

    assert first is not None
    assert second is None
    assert scheduler.current_task is first
    assert [task.task_spec.task_id for task in scheduler.queued_tasks] == ["task-2"]


def test_tick_increments_elapsed_steps() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec(timeout_steps=3))
    scheduler.start_next()

    ticked = scheduler.tick()

    assert ticked is not None
    assert ticked.elapsed_steps == 1
    assert scheduler.current_task == ticked


def test_timeout_steps_complete_as_timed_out() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec(timeout_steps=2))
    scheduler.start_next()

    first_tick = scheduler.tick()
    timeout_task = scheduler.tick()

    assert first_tick is not None
    assert first_tick.status == TaskStatus.RUNNING
    assert timeout_task is not None
    assert timeout_task.status == TaskStatus.TIMED_OUT
    assert timeout_task.completion is not None
    assert timeout_task.completion.condition == "timeout"
    assert timeout_task.completion.reason == "timeout"
    assert scheduler.current_task is None
    assert scheduler.completed_tasks[-1].status == TaskStatus.TIMED_OUT


def test_mark_success_completes_with_succeeded() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec())
    scheduler.start_next()

    completion = scheduler.mark_success("new_visible_text", evidence_ids=["shot-2"])

    assert completion.status == TaskStatus.SUCCEEDED
    assert completion.condition == "new_visible_text"
    assert completion.evidence_ids == ["shot-2"]
    assert scheduler.completed_tasks[-1].completion == completion
    assert scheduler.current_task is None


def test_mark_failure_completes_with_failed() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec())
    scheduler.start_next()

    completion = scheduler.mark_failure("death_screen", reason="visible failure state")

    assert completion.status == TaskStatus.FAILED
    assert completion.condition == "death_screen"
    assert completion.reason == "visible failure state"
    assert scheduler.completed_tasks[-1].status == TaskStatus.FAILED
    assert scheduler.current_task is None


def test_cancel_current_completes_with_cancelled() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec())
    scheduler.start_next()

    completion = scheduler.cancel_current("superseded by newer task")

    assert completion.status == TaskStatus.CANCELLED
    assert completion.condition == "cancelled"
    assert completion.reason == "superseded by newer task"
    assert scheduler.completed_tasks[-1].status == TaskStatus.CANCELLED
    assert scheduler.current_task is None


def test_invalid_success_condition_is_rejected() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec(success_conditions=["screen_transition"]))
    scheduler.start_next()

    with pytest.raises(TaskSchedulerError, match="invalid success condition"):
        scheduler.mark_success("new_visible_text")


def test_invalid_failure_condition_is_rejected() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec(failure_conditions=["timeout"]))
    scheduler.start_next()

    with pytest.raises(TaskSchedulerError, match="invalid failure condition"):
        scheduler.mark_failure("death_screen")


def test_empty_condition_lists_allow_explicit_completion_conditions() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(
        make_task_spec(
            success_conditions=[],
            failure_conditions=[],
        )
    )
    scheduler.start_next()

    completion = scheduler.mark_success("observed_external_success")

    assert completion.status == TaskStatus.SUCCEEDED
    assert completion.condition == "observed_external_success"


def test_completed_task_lands_in_completed_tasks_and_clears_current() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec())
    scheduler.start_next()

    completion = scheduler.mark_success("new_visible_text")

    assert scheduler.completed_tasks
    assert scheduler.completed_tasks[-1].completion == completion
    assert scheduler.completed_tasks[-1].task_spec.task_id == "task-1"
    assert scheduler.current_task is None


def test_tick_without_current_task_returns_none() -> None:
    assert TaskScheduler().tick() is None


def test_completion_without_running_task_is_rejected() -> None:
    with pytest.raises(TaskSchedulerError, match="no running task"):
        TaskScheduler().mark_success("new_visible_text")


def test_scheduler_state_is_serializable_snapshot() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec("task-1"))
    scheduler.enqueue(make_task_spec("task-2"))

    state = scheduler.state()

    assert state.current_task is None
    assert [task.task_spec.task_id for task in state.queued_tasks] == ["task-1", "task-2"]
    assert state.completed_tasks == ()


def test_scheduler_imports_no_body_inputexecutor_memory_game_bridge_or_llm_modules() -> None:
    source = inspect.getsource(scheduler_module)

    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.memory" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
