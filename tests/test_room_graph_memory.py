from pathlib import Path

import pytest

from fh_agent.memory.db import MemoryDB
from fh_agent.memory.room_graph import RoomGraphStore

FORBIDDEN_SCHEMA_COLUMNS = {
    "map_id",
    "event_id",
    "event_name",
    "event_comments",
    "event_trigger_conditions",
    "game_switches",
    "game_variables",
    "enemy_hp",
    "enemy_database",
    "item_database_effects",
    "savegame_variables",
    "ending_flags",
}


@pytest.fixture
def room_graph(tmp_path: Path) -> RoomGraphStore:
    with MemoryDB(tmp_path / "memory.sqlite3") as db:
        db.initialize_schema()
        yield RoomGraphStore(db)


def test_room_create_with_evidence(room_graph: RoomGraphStore) -> None:
    room = room_graph.upsert_room(
        "screen-signature:a",
        ["evidence-1"],
        confidence=0.8,
        metadata={"ui_state": "field", "visual_signature": "screen-signature:a"},
    )

    assert room.room_signature == "screen-signature:a"
    assert room.confidence == 0.8
    assert room.visit_count == 1
    assert room.evidence_ids == ["evidence-1"]
    assert room.metadata == {"ui_state": "field", "visual_signature": "screen-signature:a"}
    assert room_graph.get_room("screen-signature:a") == room


def test_room_create_requires_evidence_and_leaves_no_partial_row(
    room_graph: RoomGraphStore,
) -> None:
    with pytest.raises(ValueError, match="evidence_id"):
        room_graph.upsert_room("screen-signature:a", [])

    assert room_graph.get_room("screen-signature:a") is None
    assert room_graph.list_rooms() == []


def test_invalid_confidence_is_rejected(room_graph: RoomGraphStore) -> None:
    with pytest.raises(ValueError, match="confidence"):
        room_graph.upsert_room("screen-signature:a", ["evidence-1"], confidence=1.1)

    with pytest.raises(ValueError, match="confidence"):
        room_graph.record_transition(
            "screen-signature:a",
            "screen-signature:b",
            ["evidence-1"],
            confidence=-0.1,
        )

    assert room_graph.list_rooms() == []
    assert room_graph.list_transitions() == []


def test_upsert_room_is_idempotent(room_graph: RoomGraphStore) -> None:
    first = room_graph.upsert_room("screen-signature:a", ["evidence-1"], confidence=0.4)
    second = room_graph.upsert_room(
        "screen-signature:a",
        ["evidence-1", "evidence-2"],
        confidence=0.9,
    )

    assert first.room_signature == second.room_signature
    assert second.visit_count == 2
    assert second.confidence == 0.9
    assert second.evidence_ids == ["evidence-1", "evidence-2"]
    assert len(room_graph.list_rooms()) == 1


def test_record_transition_with_evidence(room_graph: RoomGraphStore) -> None:
    transition = room_graph.record_transition(
        "screen-signature:a",
        "screen-signature:b",
        ["evidence-1"],
        action_id="act-1",
        confidence=0.75,
        metadata={"outcome": "screen_transition"},
    )

    assert transition.from_room_signature == "screen-signature:a"
    assert transition.to_room_signature == "screen-signature:b"
    assert transition.action_id == "act-1"
    assert transition.outcome == "screen_transition"
    assert transition.confidence == 0.75
    assert transition.observed_count == 1
    assert transition.evidence_ids == ["evidence-1"]
    assert room_graph.get_room("screen-signature:a") is not None
    assert room_graph.get_room("screen-signature:b") is not None


def test_record_transition_requires_evidence_and_leaves_no_partial_row(
    room_graph: RoomGraphStore,
) -> None:
    with pytest.raises(ValueError, match="evidence_id"):
        room_graph.record_transition("screen-signature:a", "screen-signature:b", [])

    assert room_graph.list_rooms() == []
    assert room_graph.list_transitions() == []


def test_record_transition_is_idempotent_for_same_from_to_action(
    room_graph: RoomGraphStore,
) -> None:
    first = room_graph.record_transition(
        "screen-signature:a",
        "screen-signature:b",
        ["evidence-1"],
        action_id="act-1",
        confidence=0.6,
    )
    second = room_graph.record_transition(
        "screen-signature:a",
        "screen-signature:b",
        ["evidence-1", "evidence-2"],
        action_id="act-1",
        confidence=0.9,
    )

    assert first.transition_key == second.transition_key
    assert second.observed_count == 2
    assert second.confidence == 0.9
    assert second.evidence_ids == ["evidence-1", "evidence-2"]
    assert len(room_graph.list_transitions()) == 1


def test_get_neighbors_for_known_and_unknown_rooms(room_graph: RoomGraphStore) -> None:
    first = room_graph.record_transition(
        "screen-signature:a",
        "screen-signature:b",
        ["evidence-1"],
        action_id="act-1",
    )
    second = room_graph.record_transition(
        "screen-signature:a",
        "screen-signature:c",
        ["evidence-2"],
        action_id="act-2",
    )

    assert room_graph.get_neighbors("screen-signature:a") == [first, second]
    assert room_graph.get_neighbors("screen-signature:unknown") == []


def test_list_rooms_and_list_transitions(room_graph: RoomGraphStore) -> None:
    room_graph.record_transition("screen-signature:b", "screen-signature:c", ["evidence-1"])
    room_graph.upsert_room("screen-signature:a", ["evidence-2"])

    rooms = room_graph.list_rooms()
    transitions = room_graph.list_transitions()

    assert [room.room_signature for room in rooms] == [
        "screen-signature:a",
        "screen-signature:b",
        "screen-signature:c",
    ]
    assert [(item.from_room_signature, item.to_room_signature) for item in transitions] == [
        ("screen-signature:b", "screen-signature:c")
    ]


def test_hidden_state_metadata_is_rejected(room_graph: RoomGraphStore) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        room_graph.upsert_room(
            "screen-signature:a",
            ["evidence-1"],
            metadata={"map_id": 7},
        )

    with pytest.raises(ValueError, match="forbidden"):
        room_graph.record_transition(
            "screen-signature:a",
            "screen-signature:b",
            ["evidence-1"],
            metadata={"nested": {"enemy_hp": 100}},
        )

    assert room_graph.list_rooms() == []
    assert room_graph.list_transitions() == []


def test_no_forbidden_no_spoiler_columns_or_fields_are_introduced(
    room_graph: RoomGraphStore,
) -> None:
    room = room_graph.upsert_room("screen-signature:a", ["evidence-1"])
    transition = room_graph.record_transition(
        "screen-signature:a",
        "screen-signature:b",
        ["evidence-2"],
    )

    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(room.model_dump())
    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(transition.model_dump())

    table_names = [
        row["name"]
        for row in room_graph.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    ]
    column_names: set[str] = set()
    for table_name in table_names:
        column_names.update(
            row["name"] for row in room_graph.db.conn.execute(f"PRAGMA table_info({table_name})")
        )

    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(column_names)
