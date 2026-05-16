import inspect

from fh_agent.manager import event_sink as event_sink_module
from fh_agent.manager.event_sink import InMemoryManagerEventSink
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskStatus
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
            "memory_updates_requested": [],
        }
    )


def started_orchestrator(
    *,
    sink: InMemoryManagerEventSink | None = None,
    task_id: str = "task-1",
    goal: str = "Continue the visible dialogue until the message changes.",
) -> ManagerOrchestrator:
    orchestrator = ManagerOrchestrator(event_sink=sink)
    orchestrator.submit_planner_output(
        valid_planner_output(goal=goal),
        task_id=task_id,
    )
    orchestrator.start_next()
    return orchestrator


def test_orchestrator_without_sink_behaves_like_before() -> None:
    orchestrator = started_orchestrator()

    event = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert event.status == TaskStatus.SUCCEEDED
    assert orchestrator.event_sink is None


def test_orchestrator_with_sink_records_succeeded_event() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)

    event = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert sink.list_task_completions() == [event]
    assert event.status == TaskStatus.SUCCEEDED


def test_orchestrator_with_sink_records_failed_event() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)

    event = orchestrator.mark_failure(
        run_id="run-1",
        event_id="event-1",
        condition="death_screen",
        reason="visible failure state",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert sink.list_task_completions() == [event]
    assert event.status == TaskStatus.FAILED


def test_orchestrator_with_sink_records_cancelled_event() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)

    event = orchestrator.cancel_current(
        run_id="run-1",
        event_id="event-1",
        reason="superseded by test",
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert sink.list_task_completions() == [event]
    assert event.status == TaskStatus.CANCELLED


def test_orchestrator_with_sink_records_timed_out_event_from_tick() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)

    event = None
    for _ in range(6):
        event = orchestrator.tick(
            run_id="run-1",
            event_id="event-timeout",
            created_at="2026-05-16T12:00:00+00:00",
        )

    assert event is not None
    assert event.status == TaskStatus.TIMED_OUT
    assert sink.list_task_completions() == [event]


def test_returned_event_and_recorded_event_are_equal() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)

    returned = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
    )
    recorded = sink.list_task_completions()[0]

    assert returned == recorded


def test_multiple_completion_events_are_recorded_in_order() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink, task_id="task-1", goal="First goal.")
    first = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
    )

    orchestrator.submit_planner_output(
        valid_planner_output(goal="Second goal."),
        task_id="task-2",
    )
    orchestrator.start_next()
    second = orchestrator.mark_failure(
        run_id="run-1",
        event_id="event-2",
        condition="death_screen",
    )

    assert sink.list_task_completions() == [first, second]


def test_list_task_completions_returns_copy() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)
    event = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
    )

    listed = sink.list_task_completions()
    listed.clear()

    assert listed == []
    assert sink.list_task_completions() == [event]


def test_in_memory_sink_clear_removes_recorded_events() -> None:
    sink = InMemoryManagerEventSink()
    orchestrator = started_orchestrator(sink=sink)
    orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
    )

    sink.clear()

    assert sink.list_task_completions() == []


def test_event_sink_module_has_no_forbidden_imports() -> None:
    source = inspect.getsource(event_sink_module)

    assert "fh_agent.memory" not in source
    assert "sqlite" not in source.lower()
    assert "jsonl" not in source.lower()
    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source
    assert "fh_agent.bridge" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source
