import inspect
from dataclasses import dataclass

import pytest

from fh_agent.manager import orchestrator as orchestrator_module
from fh_agent.manager.event_sink import InMemoryManagerEventSink
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskSchedulerError, TaskStatus
from fh_agent.manager.skill_runner import SkillRunResult
from fh_agent.manager.target_ref import GroundingResult, VisibleScreenPointTarget
from fh_agent.manager.task_manager import ManagerGroundingError, TaskManagerError
from fh_agent.observation.schemas import SkillResult
from fh_agent.planner.planner_output import PlannerOutput
from fh_agent.skill_capabilities import SkillCapabilityContract
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def valid_planner_output(
    *,
    goal: str = "Continue the visible dialogue until the message changes.",
    selected_skill: str = "continue_dialogue",
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
            "selected_skill": selected_skill,
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


def started_orchestrator(
    task_id: str = "task-1",
    *,
    sink: InMemoryManagerEventSink | None = None,
) -> ManagerOrchestrator:
    orchestrator = ManagerOrchestrator(event_sink=sink)
    orchestrator.submit_planner_output(valid_planner_output(), task_id=task_id)
    orchestrator.start_next()
    return orchestrator


@dataclass(frozen=True)
class VerifierEventRecord:
    event_id: str
    run_id: str = "run-1"
    event_type: str = "verifier_result"


def skill_run_result(
    *,
    verifier_result: VerifierResult | None,
    legacy_success: bool,
    skill_name: str = "continue_dialogue",
    verifier_event_ids: tuple[str, ...] = (),
) -> SkillRunResult:
    return SkillRunResult(
        skill_result=SkillResult(
            skill_name=skill_name,
            success=legacy_success,
            failure_reason="legacy_compatibility_result",
            evidence_ids=["legacy-evidence"],
            reward=None,
        ),
        verifier_result=verifier_result,
        verifier_event_records=[VerifierEventRecord(event_id) for event_id in verifier_event_ids],
    )


def test_submit_planner_output_creates_queued_scheduled_task() -> None:
    orchestrator = ManagerOrchestrator()

    scheduled = orchestrator.submit_planner_output(
        valid_planner_output(),
        task_id="task-1",
    )

    assert scheduled.status == TaskStatus.PENDING
    assert scheduled.task_spec.task_id == "task-1"
    assert orchestrator.scheduler.queued_tasks == (scheduled,)


def test_orchestrator_injects_runtime_capabilities_into_internal_task_manager() -> None:
    capabilities = SkillCapabilityContract(available_skills=("continue_dialogue",))
    orchestrator = ManagerOrchestrator(runtime_capabilities=capabilities)

    with pytest.raises(TaskManagerError, match="not available.*basic_reach_target"):
        orchestrator.submit_planner_output(
            valid_planner_output(selected_skill="basic_reach_target"),
            task_id="task-1",
        )

    assert orchestrator.task_manager.runtime_capabilities is capabilities
    assert orchestrator.scheduler.queued_tasks == ()


def test_orchestrator_forwards_grounding_result_to_task_manager() -> None:
    orchestrator = ManagerOrchestrator()
    grounding = GroundingResult(
        status="grounded",
        target=VisibleScreenPointTarget(
            target_id="point-1",
            confidence=0.9,
            evidence_ids=("target-shot-1",),
            screen_position=(120, 80),
        ),
        evidence_ids=("grounding-shot-1",),
    )

    scheduled = orchestrator.submit_planner_output(
        valid_planner_output(selected_skill="basic_reach_target"),
        task_id="task-1",
        grounding_result=grounding,
    )

    assert scheduled.task_spec.target == grounding.target
    assert scheduled.task_spec.source_evidence_ids == [
        "source-shot-1",
        "source-shot-2",
        "target-shot-1",
        "grounding-shot-1",
    ]


def test_orchestrator_does_not_enqueue_failed_grounding() -> None:
    orchestrator = ManagerOrchestrator()
    grounding = GroundingResult(
        status="grounding_failed",
        failure_reason="no_visible_candidate",
        evidence_ids=("grounding-shot-1",),
    )

    with pytest.raises(ManagerGroundingError) as error:
        orchestrator.submit_planner_output(
            valid_planner_output(selected_skill="basic_reach_target"),
            task_id="task-1",
            grounding_result=grounding,
        )

    assert error.value.failure_reason == "no_visible_candidate"
    assert error.value.evidence_ids == ("grounding-shot-1",)
    assert orchestrator.scheduler.queued_tasks == ()


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


def test_complete_from_skill_run_closes_from_canonical_success_not_legacy_result() -> None:
    orchestrator = started_orchestrator()
    assert orchestrator.scheduler.current_task is not None
    assert orchestrator.scheduler.current_task.task_spec.success_conditions == ["new_visible_text"]
    verifier_result = VerifierResult(
        status=VerifierStatus.SUCCESS,
        evidence_ids=["verifier-evidence-1", "verifier-evidence-2"],
    )
    run = skill_run_result(
        verifier_result=verifier_result,
        legacy_success=False,
        verifier_event_ids=("verifier-event-1", "verifier-event-2"),
    )

    event = orchestrator.complete_from_skill_run(
        run,
        task_id="task-1",
        run_id="run-1",
        event_id="completion-event-1",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert event is not None
    assert event.status == TaskStatus.SUCCEEDED
    assert event.condition == "success"
    assert event.completion_evidence_ids == ["verifier-evidence-1", "verifier-evidence-2"]
    assert event.verifier_result == verifier_result
    assert event.verifier_event_id == "verifier-event-2"
    assert orchestrator.scheduler.current_task is None


def test_complete_from_skill_run_closes_from_canonical_failure_not_legacy_result() -> None:
    orchestrator = started_orchestrator()
    assert orchestrator.scheduler.current_task is not None
    assert "death_screen" in orchestrator.scheduler.current_task.task_spec.failure_conditions
    verifier_result = VerifierResult(
        status=VerifierStatus.FAILURE,
        failure_kind=FailureKind.DEATH,
        evidence_ids=["death-evidence"],
    )
    run = skill_run_result(verifier_result=verifier_result, legacy_success=True)

    event = orchestrator.complete_from_skill_run(
        run,
        task_id="task-1",
        run_id="run-1",
        event_id="completion-event-1",
    )

    assert event is not None
    assert event.status == TaskStatus.FAILED
    assert event.condition == "death"
    assert event.condition != "death_screen"
    assert event.verifier_result == verifier_result
    assert event.verifier_event_id is None
    assert orchestrator.scheduler.current_task is None


@pytest.mark.parametrize(
    "verifier_result",
    [
        None,
        VerifierResult(status=VerifierStatus.ABSTAIN),
        VerifierResult(status=VerifierStatus.PROGRESS),
    ],
)
def test_non_terminal_or_missing_verifier_result_keeps_task_running(
    verifier_result: VerifierResult | None,
) -> None:
    orchestrator = started_orchestrator()
    before = orchestrator.scheduler.current_task
    run = skill_run_result(verifier_result=verifier_result, legacy_success=True)

    event = orchestrator.complete_from_skill_run(
        run,
        task_id="task-1",
        run_id="run-1",
        event_id="completion-event-1",
    )

    assert event is None
    assert orchestrator.scheduler.current_task == before
    assert orchestrator.scheduler.completed_tasks == ()


def test_complete_from_skill_run_rejects_stale_task_or_skill_identity() -> None:
    orchestrator = started_orchestrator()
    run = skill_run_result(
        verifier_result=VerifierResult(status=VerifierStatus.SUCCESS),
        legacy_success=True,
    )

    with pytest.raises(TaskSchedulerError, match="task_id does not match"):
        orchestrator.complete_from_skill_run(
            run,
            task_id="stale-task",
            run_id="run-1",
            event_id="completion-event-1",
        )
    with pytest.raises(TaskSchedulerError, match="skill name does not match"):
        orchestrator.complete_from_skill_run(
            skill_run_result(
                verifier_result=VerifierResult(status=VerifierStatus.SUCCESS),
                legacy_success=True,
                skill_name="interact_visible_object",
            ),
            task_id="task-1",
            run_id="run-1",
            event_id="completion-event-1",
        )


def test_complete_from_skill_run_requires_a_running_task() -> None:
    with pytest.raises(TaskSchedulerError, match="no running task"):
        ManagerOrchestrator().complete_from_skill_run(
            skill_run_result(
                verifier_result=VerifierResult(status=VerifierStatus.SUCCESS),
                legacy_success=True,
            ),
            task_id="task-1",
            run_id="run-1",
            event_id="completion-event-1",
        )


def test_canonical_task_completion_records_only_terminal_events_in_sink() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)
    success = skill_run_result(
        verifier_result=VerifierResult(status=VerifierStatus.SUCCESS),
        legacy_success=False,
    )

    event = orchestrator.complete_from_skill_run(
        success,
        task_id="task-1",
        run_id="run-1",
        event_id="completion-event-1",
    )

    assert event is not None
    assert sink.list_task_completions() == [event]

    non_terminal_sink = InMemoryManagerEventSink()
    non_terminal = started_orchestrator(sink=non_terminal_sink)
    result = non_terminal.complete_from_skill_run(
        skill_run_result(
            verifier_result=VerifierResult(status=VerifierStatus.ABSTAIN),
            legacy_success=True,
        ),
        task_id="task-1",
        run_id="run-1",
        event_id="completion-event-2",
    )

    assert result is None
    assert non_terminal_sink.list_task_completions() == []


def test_orchestrator_module_has_no_forbidden_imports() -> None:
    source = inspect.getsource(orchestrator_module)

    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.memory" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
    assert "VerifierCatalog" not in source
    assert ".verify(" not in source
    assert "sqlite" not in source.lower()
    assert "jsonl" not in source.lower()
