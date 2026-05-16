from pathlib import Path

import pytest

from fh_agent.memory.db import MemoryDB
from fh_agent.memory.facts import FactStore, StoredFact

FORBIDDEN_FACT_FIELDS = {
    "map_id",
    "event_name",
    "game_switches",
    "game_variables",
    "enemy_hp",
    "enemy_database",
    "item_database_effects",
    "savegame_variables",
}


@pytest.fixture
def fact_store(tmp_path: Path) -> FactStore:
    with MemoryDB(tmp_path / "memory.sqlite3") as db:
        db.initialize_schema()
        yield FactStore(db)


def test_create_get_list_and_update_fact(fact_store: FactStore) -> None:
    fact = fact_store.create_fact(
        claim="A visible object was observed.",
        subject="visible-object",
        predicate="was_observed",
        status="hypothesis",
        confidence=0.4,
        evidence_ids=["evidence-1"],
    )

    assert isinstance(fact, StoredFact)
    assert fact.status == "hypothesis"
    assert fact.confidence == 0.4
    assert fact.evidence_ids == ["evidence-1"]
    assert fact.fact is not None
    assert fact.fact.claim == "A visible object was observed."

    updated_status = fact_store.update_fact_status(fact.fact_id, "observed_fact")
    updated_confidence = fact_store.update_fact_confidence(fact.fact_id, 0.8)
    fetched = fact_store.get_fact(fact.fact_id)
    listed = fact_store.list_facts(status="observed_fact")

    assert updated_status.status == "observed_fact"
    assert updated_confidence.confidence == 0.8
    assert fetched is not None
    assert fetched.status == "observed_fact"
    assert fetched.confidence == 0.8
    assert [item.fact_id for item in listed] == [fact.fact_id]


def test_create_fact_requires_evidence_ids(fact_store: FactStore) -> None:
    with pytest.raises(ValueError, match="evidence_id"):
        fact_store.create_fact(
            claim="A visible object was observed.",
            evidence_ids=[],
        )

    assert fact_store.list_facts() == []


def test_invalid_status_is_rejected(fact_store: FactStore) -> None:
    with pytest.raises(ValueError, match="status"):
        fact_store.create_fact(
            claim="A visible object was observed.",
            status="active",  # type: ignore[arg-type]
            evidence_ids=["evidence-1"],
        )

    fact = fact_store.create_fact(
        claim="A visible object was observed.",
        evidence_ids=["evidence-1"],
    )
    with pytest.raises(ValueError, match="status"):
        fact_store.update_fact_status(fact.fact_id, "active")  # type: ignore[arg-type]


def test_invalid_confidence_is_rejected(fact_store: FactStore) -> None:
    with pytest.raises(ValueError, match="confidence"):
        fact_store.create_fact(
            claim="A visible object was observed.",
            confidence=1.1,
            evidence_ids=["evidence-1"],
        )

    fact = fact_store.create_fact(
        claim="A visible object was observed.",
        evidence_ids=["evidence-1"],
    )
    with pytest.raises(ValueError, match="confidence"):
        fact_store.update_fact_confidence(fact.fact_id, -0.1)


def test_append_evidence_is_idempotent(fact_store: FactStore) -> None:
    fact = fact_store.create_fact(
        claim="A visible object was observed.",
        evidence_ids=["evidence-1"],
    )

    fact_store.append_evidence(fact.fact_id, "evidence-2")
    updated = fact_store.append_evidence(fact.fact_id, "evidence-2")

    assert updated.evidence_ids == ["evidence-1", "evidence-2"]


def test_failed_create_leaves_no_partial_fact(fact_store: FactStore) -> None:
    with pytest.raises(ValueError):
        fact_store.create_fact(
            claim="A visible object was observed.",
            confidence=-1.0,
            evidence_ids=["evidence-1"],
        )

    assert fact_store.list_facts() == []


def test_mark_contradicted(fact_store: FactStore) -> None:
    fact = fact_store.create_fact(
        claim="A visible object was observed.",
        evidence_ids=["evidence-1"],
    )

    contradicted = fact_store.mark_contradicted(fact.fact_id)

    assert contradicted.status == "contradicted"


def test_fact_api_exposes_no_hidden_state_fields(fact_store: FactStore) -> None:
    fact = fact_store.create_fact(
        claim="A visible object was observed.",
        evidence_ids=["evidence-1"],
    )

    exposed_fields = set(fact.model_dump())
    assert FORBIDDEN_FACT_FIELDS.isdisjoint(exposed_fields)

    table_names = [
        row["name"]
        for row in fact_store.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    ]
    column_names: set[str] = set()
    for table_name in table_names:
        column_names.update(
            row["name"]
            for row in fact_store.db.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        )

    assert FORBIDDEN_FACT_FIELDS.isdisjoint(column_names)
