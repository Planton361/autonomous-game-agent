import json
import sqlite3
from typing import Any

from pydantic import TypeAdapter

from fh_agent.manager.target_ref import GroundedTarget
from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.memory.db import MemoryDB

_GROUNDED_TARGET_ADAPTER = TypeAdapter(GroundedTarget)


class SQLiteManagerEventSink:
    """SQLite-backed adapter for manager task completion events."""

    def __init__(self, db: MemoryDB) -> None:
        self.db = db

    def record_task_completion(self, event: TaskCompletionEvent) -> None:
        target_payload = event.target.model_dump(mode="json") if event.target is not None else None
        try:
            self.db.conn.execute(
                """
                INSERT INTO task_completion_events (
                    event_id,
                    run_id,
                    event_type,
                    task_id,
                    selected_skill,
                    goal,
                    target_json,
                    status,
                    condition,
                    reason,
                    elapsed_steps,
                    timeout_steps,
                    planner_output_id,
                    planner_trace_id,
                    source_evidence_ids_json,
                    completion_evidence_ids_json,
                    reward_terms_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.run_id,
                    event.event_type,
                    event.task_id,
                    event.selected_skill,
                    event.goal,
                    _json_dump(target_payload),
                    event.status,
                    event.condition,
                    event.reason,
                    event.elapsed_steps,
                    event.timeout_steps,
                    event.planner_output_id,
                    event.planner_trace_id,
                    _json_dump(event.source_evidence_ids),
                    _json_dump(event.completion_evidence_ids),
                    _json_dump(event.reward_terms),
                    event.created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            msg = f"task completion event already exists: {event.event_id}"
            raise ValueError(msg) from exc
        self.db.conn.commit()

    def list_task_completions(self, run_id: str | None = None) -> list[TaskCompletionEvent]:
        if run_id is None:
            rows = self.db.conn.execute(
                """
                SELECT *
                FROM task_completion_events
                ORDER BY created_at, event_id
                """,
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                """
                SELECT *
                FROM task_completion_events
                WHERE run_id = ?
                ORDER BY created_at, event_id
                """,
                (run_id,),
            ).fetchall()
        return [_event_from_row(dict(row)) for row in rows]

    def get_task_completion(self, event_id: str) -> TaskCompletionEvent | None:
        row = self.db.conn.execute(
            """
            SELECT *
            FROM task_completion_events
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        return _event_from_row(dict(row))


def _json_dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _json_load(value: str) -> Any:
    return json.loads(value)


def _event_from_row(row: dict[str, object]) -> TaskCompletionEvent:
    target_json = str(row["target_json"])
    target_payload = _json_load(target_json)
    return TaskCompletionEvent(
        event_id=str(row["event_id"]),
        run_id=str(row["run_id"]),
        event_type="task_completion",
        task_id=str(row["task_id"]),
        selected_skill=str(row["selected_skill"]),
        goal=str(row["goal"]),
        target=(
            _GROUNDED_TARGET_ADAPTER.validate_json(target_json)
            if target_payload is not None
            else None
        ),
        status=str(row["status"]),
        condition=str(row["condition"]),
        reason=str(row["reason"]) if row["reason"] is not None else None,
        elapsed_steps=int(row["elapsed_steps"]),
        timeout_steps=int(row["timeout_steps"]),
        planner_output_id=(
            str(row["planner_output_id"]) if row["planner_output_id"] is not None else None
        ),
        planner_trace_id=(
            str(row["planner_trace_id"]) if row["planner_trace_id"] is not None else None
        ),
        source_evidence_ids=_json_load(str(row["source_evidence_ids_json"])),
        completion_evidence_ids=_json_load(str(row["completion_evidence_ids_json"])),
        reward_terms=_json_load(str(row["reward_terms_json"])),
        created_at=str(row["created_at"]),
    )
