import ast
import inspect
from pathlib import Path

import pytest

from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.scheduler import TaskStatus
from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.memory.db import MemoryDB
from fh_agent.memory.manager_event_log import SQLiteManagerEventSink
from fh_agent.planner.planner_output import PlannerOutput


@pytest.fixture
def db(tmp_path: Path) -> MemoryDB:
    with MemoryDB(tmp_path / "memory.sqlite3") as memory_db:
        memory_db.initialize_schema()
        yield memory_db


@pytest.fixture
def sink(db: MemoryDB) -> SQLiteManagerEventSink:
    return SQLiteManagerEventSink(db)


def task_completion_event(
    event_id: str = "event-1",
    *,
    run_id: str = "run-1",
    created_at: str = "2026-05-16T12:00:00+00:00",
) -> TaskCompletionEvent:
    return TaskCompletionEvent(
        event_id=event_id,
        run_id=run_id,
        task_id="task-1",
        selected_skill="continue_dialogue",
        goal="Continue visible dialogue.",
        target={"description": "visible dialogue target"},
        status=TaskStatus.SUCCEEDED,
        condition="new_visible_text",
        reason=None,
        elapsed_steps=2,
        timeout_steps=6,
        planner_output_id="planner-output-1",
        planner_trace_id="planner-trace-1",
        source_evidence_ids=["source-shot-1", "source-shot-2"],
        completion_evidence_ids=["completion-shot-1"],
        reward_terms=[
            "new_visible_text",
            "skill_success",
            "avoid_timeout",
        ],
        created_at=created_at,
    )


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
            "memory_updates_requested": [],
        }
    )


def test_record_and_read_task_completion_roundtrip(sink: SQLiteManagerEventSink) -> None:
    event = task_completion_event()

    sink.record_task_completion(event)

    assert sink.get_task_completion("event-1") == event
    assert sink.list_task_completions() == [event]


def test_source_evidence_ids_roundtrip(sink: SQLiteManagerEventSink) -> None:
    event = task_completion_event()

    sink.record_task_completion(event)

    stored = sink.get_task_completion(event.event_id)
    assert stored is not None
    assert stored.source_evidence_ids == ["source-shot-1", "source-shot-2"]


def test_completion_evidence_ids_roundtrip(sink: SQLiteManagerEventSink) -> None:
    event = task_completion_event()

    sink.record_task_completion(event)

    stored = sink.get_task_completion(event.event_id)
    assert stored is not None
    assert stored.completion_evidence_ids == ["completion-shot-1"]


def test_reward_terms_roundtrip(sink: SQLiteManagerEventSink) -> None:
    event = task_completion_event()

    sink.record_task_completion(event)

    stored = sink.get_task_completion(event.event_id)
    assert stored is not None
    assert stored.reward_terms == ["new_visible_text", "skill_success", "avoid_timeout"]


def test_planner_ids_roundtrip(sink: SQLiteManagerEventSink) -> None:
    event = task_completion_event()

    sink.record_task_completion(event)

    stored = sink.get_task_completion(event.event_id)
    assert stored is not None
    assert stored.planner_output_id == "planner-output-1"
    assert stored.planner_trace_id == "planner-trace-1"


def test_target_roundtrips_over_json(sink: SQLiteManagerEventSink) -> None:
    event = task_completion_event()

    sink.record_task_completion(event)

    stored = sink.get_task_completion(event.event_id)
    assert stored is not None
    assert stored.target == {"description": "visible dialogue target"}


def test_run_id_filter_returns_only_matching_events(sink: SQLiteManagerEventSink) -> None:
    first = task_completion_event("event-1", run_id="run-1")
    second = task_completion_event("event-2", run_id="run-2")
    sink.record_task_completion(first)
    sink.record_task_completion(second)

    assert sink.list_task_completions(run_id="run-1") == [first]
    assert sink.list_task_completions(run_id="run-2") == [second]


def test_multiple_events_are_listed_deterministically(sink: SQLiteManagerEventSink) -> None:
    later = task_completion_event(
        "event-b",
        created_at="2026-05-16T12:00:01+00:00",
    )
    earlier_b = task_completion_event(
        "event-bb",
        created_at="2026-05-16T12:00:00+00:00",
    )
    earlier_a = task_completion_event(
        "event-aa",
        created_at="2026-05-16T12:00:00+00:00",
    )
    sink.record_task_completion(later)
    sink.record_task_completion(earlier_b)
    sink.record_task_completion(earlier_a)

    assert [event.event_id for event in sink.list_task_completions()] == [
        "event-aa",
        "event-bb",
        "event-b",
    ]


def test_duplicate_event_id_is_rejected(sink: SQLiteManagerEventSink) -> None:
    event = task_completion_event()
    sink.record_task_completion(event)

    with pytest.raises(ValueError, match="already exists"):
        sink.record_task_completion(event)


def test_get_task_completion_returns_none_for_missing_event(
    sink: SQLiteManagerEventSink,
) -> None:
    assert sink.get_task_completion("missing-event") is None


def test_sqlite_sink_can_be_injected_into_orchestrator_for_success_event(
    sink: SQLiteManagerEventSink,
) -> None:
    orchestrator = ManagerOrchestrator(event_sink=sink)
    orchestrator.submit_planner_output(valid_planner_output(), task_id="task-1")
    orchestrator.start_next()

    event = orchestrator.mark_success(
        run_id="run-1",
        event_id="event-1",
        condition="new_visible_text",
        evidence_ids=["completion-shot-1"],
        created_at="2026-05-16T12:00:00+00:00",
    )

    assert sink.get_task_completion("event-1") == event


def test_sqlite_sink_records_timeout_event_from_orchestrator_tick(
    sink: SQLiteManagerEventSink,
) -> None:
    orchestrator = ManagerOrchestrator(event_sink=sink)
    orchestrator.submit_planner_output(valid_planner_output(), task_id="task-1")
    orchestrator.start_next()

    event = None
    for _ in range(6):
        event = orchestrator.tick(
            run_id="run-1",
            event_id="event-timeout",
            created_at="2026-05-16T12:00:00+00:00",
        )

    assert event is not None
    assert event.status == TaskStatus.TIMED_OUT
    assert sink.get_task_completion("event-timeout") == event


def test_memory_adapter_imports_no_body_inputexecutor_game_bridge_or_llm_modules() -> None:
    import fh_agent.memory.manager_event_log as manager_event_log

    source = inspect.getsource(manager_event_log)

    assert "fh_agent.body" not in source
    assert "InputExecutor" not in source
    assert "fh_agent.game" not in source
    assert "fh_agent.bridge" not in source
    assert "LLMClient" not in source
    assert "fh_agent.planner.llm_client" not in source


def test_manager_package_has_no_top_level_memory_imports() -> None:
    manager_dir = Path(__file__).parents[1] / "src" / "fh_agent" / "manager"
    imported_modules: set[str] = set()
    for path in manager_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)

    assert all(not module.startswith("fh_agent.memory") for module in imported_modules)
