from pathlib import Path

import pytest

from fh_agent.memory.db import MemoryDB
from fh_agent.memory.entity_risk import EntityRiskStore

FORBIDDEN_SCHEMA_COLUMNS = {
    "map_id",
    "event_name",
    "event_comments",
    "game_switches",
    "game_variables",
    "enemy_id",
    "enemy_hp",
    "enemy_database",
    "enemy_resistances",
    "item_database_effects",
    "savegame_variables",
    "ending_flags",
}


@pytest.fixture
def risk_store(tmp_path: Path) -> EntityRiskStore:
    with MemoryDB(tmp_path / "memory.sqlite3") as db:
        db.initialize_schema()
        yield EntityRiskStore(db)


def test_unknown_entity_returns_default_risk(risk_store: EntityRiskStore) -> None:
    risk = risk_store.get_risk("visual-hash:abc123")

    assert risk.entity_key == "visual-hash:abc123"
    assert risk.risk_score == 0.0
    assert risk.total_outcomes == 0
    assert risk.last_outcome is None
    assert risk.evidence_ids == []
    assert risk.outcome_counts == {}
    assert risk_store.list_risks() == []


def test_record_outcome_requires_evidence_and_leaves_no_partial_row(
    risk_store: EntityRiskStore,
) -> None:
    with pytest.raises(ValueError, match="evidence_id"):
        risk_store.record_outcome("visual-hash:abc123", "damage_taken", [])

    assert risk_store.get_risk("visual-hash:abc123").total_outcomes == 0
    assert risk_store.list_events("visual-hash:abc123") == []


def test_invalid_confidence_is_rejected(risk_store: EntityRiskStore) -> None:
    with pytest.raises(ValueError, match="confidence"):
        risk_store.record_outcome(
            "visual-hash:abc123",
            "damage_taken",
            ["evidence-1"],
            confidence=1.1,
        )

    with pytest.raises(ValueError, match="confidence"):
        risk_store.record_outcome(
            "visual-hash:abc123",
            "damage_taken",
            ["evidence-1"],
            confidence=-0.1,
        )


def test_invalid_outcome_is_rejected(risk_store: EntityRiskStore) -> None:
    with pytest.raises(ValueError, match="outcome"):
        risk_store.record_outcome(
            "visual-hash:abc123",
            "hidden_enemy_lookup",  # type: ignore[arg-type]
            ["evidence-1"],
        )


def test_death_damage_and_combat_started_raise_risk(risk_store: EntityRiskStore) -> None:
    first = risk_store.record_outcome("visual-hash:abc123", "combat_started", ["evidence-1"])
    second = risk_store.record_outcome("visual-hash:abc123", "damage_taken", ["evidence-2"])
    third = risk_store.record_outcome(
        "visual-hash:abc123",
        "death",
        ["evidence-3"],
        confidence=0.5,
    )

    assert 0.0 < first.risk_score < second.risk_score < third.risk_score
    assert third.total_outcomes == 3
    assert third.last_outcome == "death"
    assert third.outcome_counts == {
        "combat_started": 1,
        "damage_taken": 1,
        "death": 1,
    }


def test_safe_passage_lowers_risk_but_not_below_zero(risk_store: EntityRiskStore) -> None:
    raised = risk_store.record_outcome("visible-entity:frontier", "damage_taken", ["evidence-1"])
    lowered = risk_store.record_outcome("visible-entity:frontier", "safe_passage", ["evidence-2"])

    assert lowered.risk_score < raised.risk_score

    for index in range(10):
        risk = risk_store.record_outcome(
            "visible-entity:frontier",
            "safe_passage",
            [f"safe-evidence-{index}"],
        )

    assert risk.risk_score == 0.0


def test_risk_is_clamped_to_one(risk_store: EntityRiskStore) -> None:
    for index in range(5):
        risk = risk_store.record_outcome(
            "hazard:visible-signal",
            "death",
            [f"evidence-{index}"],
        )

    assert risk.risk_score == 1.0


def test_no_change_keeps_risk_stable(risk_store: EntityRiskStore) -> None:
    raised = risk_store.record_outcome("hazard:visible-signal", "skill_failed", ["evidence-1"])
    unchanged = risk_store.record_outcome("hazard:visible-signal", "no_change", ["evidence-2"])

    assert unchanged.risk_score == raised.risk_score
    assert unchanged.total_outcomes == 2


def test_evidence_history_is_persisted(risk_store: EntityRiskStore) -> None:
    risk_store.record_outcome("visible-entity:key", "skill_failed", ["evidence-2", "evidence-1"])
    risk_store.record_outcome("visible-entity:key", "safe_passage", ["evidence-3"])

    risk = risk_store.get_risk("visible-entity:key")
    events = risk_store.list_events("visible-entity:key")

    assert risk.evidence_ids == ["evidence-1", "evidence-2", "evidence-3"]
    assert [event.evidence_ids for event in events] == [
        ["evidence-1", "evidence-2"],
        ["evidence-3"],
    ]
    assert [event.outcome for event in events] == ["skill_failed", "safe_passage"]


def test_list_risks_is_sorted_by_entity_key(risk_store: EntityRiskStore) -> None:
    risk_store.record_outcome("visible-entity:b", "damage_taken", ["evidence-1"])
    risk_store.record_outcome("visible-entity:a", "safe_passage", ["evidence-2"])

    risks = risk_store.list_risks()

    assert [risk.entity_key for risk in risks] == ["visible-entity:a", "visible-entity:b"]


def test_no_forbidden_no_spoiler_columns_or_fields_are_introduced(
    risk_store: EntityRiskStore,
) -> None:
    risk = risk_store.record_outcome("visual-hash:abc123", "damage_taken", ["evidence-1"])
    event = risk_store.list_events("visual-hash:abc123")[0]

    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(risk.model_dump())
    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(event.model_dump())

    table_names = [
        row["name"]
        for row in risk_store.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    ]
    column_names: set[str] = set()
    for table_name in table_names:
        column_names.update(
            row["name"]
            for row in risk_store.db.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        )

    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(column_names)
