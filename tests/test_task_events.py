import inspect
import json

import pytest
from pydantic import ValidationError

from fh_agent.manager import task_events as task_events_module
from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.manager.scheduler import TaskCompletion, TaskScheduler, TaskStatus
from fh_agent.manager.target_ref import VisibleObjectTarget, VisibleScreenPointTarget
from fh_agent.manager.task_events import TaskCompletionEvent, task_completion_to_event
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def make_task_spec(task_id: str = "task-1", *, timeout_steps: int = 3) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        selected_skill="continue_dialogue",
        goal=f"Run {task_id}.",
        target=None,
        constraints={"avoid_known_dangers": True, "max_danger_score": 0.4},
        success_conditions=["new_visible_text"],
        failure_conditions=["death_screen", "timeout"],
        timeout_steps=timeout_steps,
        reward_profile=default_reward_profile_for_skill("continue_dialogue"),
        source_evidence_ids=["source-shot-1"],
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
    )


def targeted_task_spec(target: VisibleObjectTarget | VisibleScreenPointTarget) -> TaskSpec:
    return TaskSpec(
        task_id="targeted-task",
        selected_skill=(
            "interact_visible_object"
            if isinstance(target, VisibleObjectTarget)
            else "basic_reach_target"
        ),
        goal="Use the grounded visible target.",
        target=target,
        constraints={"avoid_known_dangers": True},
        success_conditions=["visible_interaction"],
        failure_conditions=[],
        timeout_steps=3,
        reward_profile=default_reward_profile_for_skill(
            "interact_visible_object"
            if isinstance(target, VisibleObjectTarget)
            else "basic_reach_target"
        ),
        source_evidence_ids=["source-shot-1"],
    )


def verifier_completion_for_target(
    target: VisibleObjectTarget | VisibleScreenPointTarget,
) -> TaskCompletion:
    scheduler = TaskScheduler()
    scheduler.enqueue(targeted_task_spec(target))
    scheduler.start_next()
    completion = scheduler.complete_from_verifier(
        VerifierResult(status=VerifierStatus.SUCCESS, evidence_ids=["completion-shot-1"])
    )
    assert completion is not None
    return completion


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


def verifier_completion_event(
    verifier_result: VerifierResult,
    *,
    verifier_event_id: str | None = None,
) -> TaskCompletionEvent:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec())
    scheduler.start_next()
    completion = scheduler.complete_from_verifier(
        verifier_result,
        verifier_event_id=verifier_event_id,
    )
    assert completion is not None
    return task_completion_to_event(
        completion,
        run_id="run-1",
        event_id="event-verifier",
        created_at="2026-05-16T12:00:00+00:00",
    )


def test_succeeded_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    assert event.event_type == "task_completion"
    assert event.status == TaskStatus.SUCCEEDED
    assert event.condition == "new_visible_text"
    assert event.reason is None
    assert event.completion_evidence_ids == ["completion-shot-1"]
    assert event.verifier_result is None
    assert event.verifier_event_id is None


def test_failed_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.FAILED)

    assert event.status == TaskStatus.FAILED
    assert event.condition == "death_screen"
    assert event.reason == "visible failure state"
    assert event.completion_evidence_ids == ["completion-shot-2"]
    assert event.verifier_result is None
    assert event.verifier_event_id is None


def test_timed_out_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.TIMED_OUT)

    assert event.status == TaskStatus.TIMED_OUT
    assert event.condition == "timeout"
    assert event.reason == "timeout"
    assert event.elapsed_steps == 2
    assert event.timeout_steps == 2
    assert event.verifier_result is None
    assert event.verifier_event_id is None


def test_cancelled_completion_converts_correctly() -> None:
    event = event_for_status(TaskStatus.CANCELLED)

    assert event.status == TaskStatus.CANCELLED
    assert event.condition == "cancelled"
    assert event.reason == "superseded by newer task"
    assert event.verifier_result is None
    assert event.verifier_event_id is None


def test_canonical_success_event_preserves_verifier_provenance() -> None:
    verifier_result = VerifierResult(
        status=VerifierStatus.SUCCESS,
        evidence_ids=["verifier-evidence-1", "verifier-evidence-2"],
    )

    event = verifier_completion_event(
        verifier_result,
        verifier_event_id="verifier-event-1",
    )

    assert event.condition == "success"
    assert event.completion_evidence_ids == ["verifier-evidence-1", "verifier-evidence-2"]
    assert event.verifier_result == verifier_result
    assert event.verifier_event_id == "verifier-event-1"
    assert event.manager_stop_result is None
    assert event.manager_stop_event_id is None


def test_canonical_failure_event_preserves_failure_kind_and_json_payload() -> None:
    verifier_result = VerifierResult(
        status=VerifierStatus.FAILURE,
        failure_kind=FailureKind.DEATH,
        evidence_ids=["death-evidence"],
    )

    event = verifier_completion_event(verifier_result)
    payload = json.loads(event.model_dump_json())

    assert event.condition == "death"
    assert event.verifier_result == verifier_result
    assert event.verifier_event_id is None
    assert event.manager_stop_result is None
    assert event.manager_stop_event_id is None
    assert VerifierResult.model_validate(payload["verifier_result"]) == verifier_result


def test_event_preserves_task_completion_core_fields() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    assert event.event_id == "event-succeeded"
    assert event.run_id == "run-1"
    assert event.task_id == "task-1"
    assert event.selected_skill == "continue_dialogue"
    assert event.goal == "Run task-1."
    assert event.target is None
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


@pytest.mark.parametrize(
    "target",
    [
        VisibleObjectTarget(
            target_id="object-1",
            confidence=0.9,
            evidence_ids=("target-shot-1",),
            screen_position=(120, 80),
            visual_hash="dhash:0123456789abcdef",
        ),
        VisibleScreenPointTarget(
            target_id="point-1",
            confidence=0.8,
            evidence_ids=("target-shot-2",),
            screen_position=(240, 160),
        ),
    ],
)
def test_verifier_terminal_targeted_completion_preserves_typed_target_and_roundtrips_json(
    target: VisibleObjectTarget | VisibleScreenPointTarget,
) -> None:
    completion = verifier_completion_for_target(target)

    event = task_completion_to_event(
        completion,
        run_id="run-1",
        event_id=f"event-{target.target_id}",
        created_at="2026-05-16T12:00:00+00:00",
    )
    payload = json.loads(event.model_dump_json())
    round_tripped = TaskCompletionEvent.model_validate_json(event.model_dump_json())

    assert event.status == TaskStatus.SUCCEEDED
    assert event.verifier_result == completion.verifier_result
    assert event.target is target
    assert type(round_tripped.target) is type(target)
    assert round_tripped == event
    assert payload["target"]["evidence_ids"] == list(target.evidence_ids)
    assert payload["target"]["screen_position"] == list(target.screen_position)


def test_targetless_event_json_roundtrip_preserves_none() -> None:
    event = event_for_status(TaskStatus.SUCCEEDED)

    round_tripped = TaskCompletionEvent.model_validate_json(event.model_dump_json())

    assert event.target is None
    assert round_tripped.target is None


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


@pytest.mark.parametrize(
    ("failure_kind", "expected_status"),
    [
        (FailureKind.TIMEOUT, TaskStatus.TIMED_OUT),
        (FailureKind.CAPABILITY_REJECTED, TaskStatus.FAILED),
        (FailureKind.FOCUS_LOST, TaskStatus.FAILED),
        (FailureKind.SAFETY_INTERVENTION, TaskStatus.FAILED),
    ],
)
def test_manager_stop_completion_event_preserves_separate_provenance(
    failure_kind: FailureKind,
    expected_status: TaskStatus,
) -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec())
    scheduler.start_next()
    manager_stop = ManagerStopResult(
        failure_kind=failure_kind,
        reason="manager runtime stop",
        evidence_ids=["stop-evidence-1", "stop-evidence-2"],
        trigger_event_id="action-result-event-1",
    )
    completion = scheduler.complete_from_manager_stop(
        manager_stop,
        manager_stop_event_id="manager-stop-event-1",
    )

    event = task_completion_to_event(
        completion,
        run_id="run-1",
        event_id="completion-event-1",
        created_at="2026-05-16T12:00:00+00:00",
    )
    round_tripped = TaskCompletionEvent.model_validate_json(event.model_dump_json())

    assert event.event_type == "task_completion"
    assert event.status == expected_status
    assert event.condition == failure_kind.value
    assert event.reason == "manager runtime stop"
    assert event.completion_evidence_ids == ["stop-evidence-1", "stop-evidence-2"]
    assert event.manager_stop_result == manager_stop
    assert event.manager_stop_event_id == "manager-stop-event-1"
    assert event.manager_stop_result.trigger_event_id == "action-result-event-1"
    assert event.verifier_result is None
    assert event.verifier_event_id is None
    assert round_tripped == event


def test_task_completion_event_rejects_empty_manager_stop_event_id() -> None:
    scheduler = TaskScheduler()
    scheduler.enqueue(make_task_spec())
    scheduler.start_next()
    completion = scheduler.complete_from_manager_stop(
        ManagerStopResult(failure_kind=FailureKind.FOCUS_LOST, reason="not_focused")
    )
    event = task_completion_to_event(
        completion,
        run_id="run-1",
        event_id="completion-event-1",
        created_at="2026-05-16T12:00:00+00:00",
    )

    with pytest.raises(ValidationError, match="manager_stop_event_id must not be empty"):
        TaskCompletionEvent.model_validate({**event.model_dump(), "manager_stop_event_id": ""})
