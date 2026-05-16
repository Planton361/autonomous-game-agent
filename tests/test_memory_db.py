from pathlib import Path

import pytest

from fh_agent.memory.db import MemoryDB
from fh_agent.observation.schemas import (
    ActionResult,
    KnowledgeFact,
    Observation,
    SkillResult,
)

FORBIDDEN_SCHEMA_COLUMNS = {
    "map_id",
    "event_name",
    "event_comments",
    "event_trigger_conditions",
    "game_switches",
    "game_variables",
    "enemy_database",
    "enemy_hp",
    "item_database_effects",
    "ending_flags",
    "savegame_variables",
}


@pytest.fixture
def db(tmp_path: Path) -> MemoryDB:
    with MemoryDB(tmp_path / "memory.sqlite3") as memory_db:
        memory_db.initialize_schema()
        yield memory_db


def test_schema_initializes_successfully(db: MemoryDB) -> None:
    table_names = {
        row["name"]
        for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    }

    assert {
        "observations",
        "actions",
        "skill_results",
        "facts",
        "fact_evidence",
    }.issubset(table_names)


def test_observation_insert_read_roundtrip(db: MemoryDB) -> None:
    observation = Observation(
        run_id="run-1",
        ui_state="dialogue",
        screenshot_id="evidence-1",
        visible_message_text="Visible text",
        evidence_ids=["evidence-1"],
    )

    observation_id = db.insert_observation(observation)
    stored = db.get_observation(observation_id)

    assert stored is not None
    assert stored.observation_id == observation_id
    assert stored.run_id == "run-1"
    assert stored.ui_state == "dialogue"
    assert stored.evidence_ids == ["evidence-1"]


def test_skill_result_insert_read_roundtrip(db: MemoryDB) -> None:
    result = SkillResult(
        skill_name="continue_dialogue",
        success=True,
        reward=0.25,
        evidence_ids=["evidence-1"],
    )

    skill_result_id = db.insert_skill_result("run-1", result, steps=2)
    stored = db.get_skill_result(skill_result_id)
    row = db.conn.execute(
        "SELECT steps FROM skill_results WHERE skill_result_id = ?",
        (skill_result_id,),
    ).fetchone()

    assert stored == result
    assert row["steps"] == 2


def test_action_insert_read_roundtrip(db: MemoryDB) -> None:
    observation_id = db.insert_observation(Observation(run_id="run-1"))
    action = ActionResult(
        action="wait",
        executed=True,
        evidence_ids=["evidence-1"],
    )

    action_id = db.insert_action("run-1", action, related_observation_id=observation_id)
    stored = db.get_action(action_id)
    row = db.conn.execute(
        """
        SELECT primitive_action, related_observation_id
        FROM actions
        WHERE action_id = ?
        """,
        (action_id,),
    ).fetchone()

    assert stored == action
    assert row["primitive_action"] == "wait"
    assert row["related_observation_id"] == observation_id


def test_fact_insert_with_evidence_ids_works(db: MemoryDB) -> None:
    fact = KnowledgeFact(
        subject="visible-object",
        predicate="appeared_near",
        value="doorway",
        claim="A visible object appeared near a doorway.",
        confidence=0.75,
        evidence_ids=["evidence-1", "evidence-2"],
    )

    fact_id = db.insert_fact(fact)
    stored = db.get_fact(fact_id)

    assert stored is not None
    assert stored["fact_id"] == fact_id
    assert stored["claim"] == "A visible object appeared near a doorway."
    assert stored["status"] == "hypothesis"
    assert stored["confidence"] == 0.75
    assert stored["evidence_ids"] == ["evidence-1", "evidence-2"]


def test_fact_insert_without_evidence_ids_raises_value_error(db: MemoryDB) -> None:
    with pytest.raises(ValueError, match="evidence_id"):
        db.insert_fact("A visible object appeared near a doorway.", evidence_ids=[])

    rows = db.conn.execute("SELECT fact_id FROM facts").fetchall()
    assert rows == []


def test_fact_evidence_links_are_stored(db: MemoryDB) -> None:
    fact_id = db.insert_fact(
        "A visible object appeared near a doorway.",
        evidence_ids=["evidence-2", "evidence-1"],
    )

    rows = db.conn.execute(
        """
        SELECT fact_id, evidence_id
        FROM fact_evidence
        WHERE fact_id = ?
        ORDER BY evidence_id
        """,
        (fact_id,),
    ).fetchall()

    assert [(row["fact_id"], row["evidence_id"]) for row in rows] == [
        (fact_id, "evidence-1"),
        (fact_id, "evidence-2"),
    ]


def test_list_facts_includes_evidence_ids(db: MemoryDB) -> None:
    first_id = db.insert_fact("First visible claim.", evidence_ids=["evidence-1"])
    second_id = db.insert_fact("Second visible claim.", evidence_ids=["evidence-2"])

    facts = db.list_facts()

    assert [fact["fact_id"] for fact in facts] == [first_id, second_id]
    assert [fact["evidence_ids"] for fact in facts] == [["evidence-1"], ["evidence-2"]]


def test_forbidden_hidden_state_columns_are_not_present(db: MemoryDB) -> None:
    table_names = [
        row["name"]
        for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    ]
    column_names: set[str] = set()
    for table_name in table_names:
        column_names.update(
            row["name"] for row in db.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        )

    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(column_names)
