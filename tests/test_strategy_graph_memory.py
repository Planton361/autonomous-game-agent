from pathlib import Path

import pytest

from fh_agent.memory.db import MemoryDB
from fh_agent.memory.strategy_graph import StrategyGraphStore

FORBIDDEN_SCHEMA_COLUMNS = {
    "map_id",
    "event_name",
    "event_comments",
    "event_trigger_conditions",
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
def strategy_graph(tmp_path: Path) -> StrategyGraphStore:
    with MemoryDB(tmp_path / "memory.sqlite3") as db:
        db.initialize_schema()
        yield StrategyGraphStore(db)


def test_create_get_and_list_strategy(strategy_graph: StrategyGraphStore) -> None:
    strategy = strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
        confidence=0.6,
        metadata={"ui_state": "field"},
    )

    assert strategy.strategy_key == "strategy:visible-exit"
    assert strategy.title == "Try a generic visible exit."
    assert strategy.status == "hypothesis"
    assert strategy.confidence == 0.6
    assert strategy.evidence_ids == ["evidence-1"]
    assert strategy.metadata == {"ui_state": "field"}
    assert strategy_graph.get_strategy("strategy:visible-exit") == strategy
    assert strategy_graph.list_strategies() == [strategy]
    assert strategy_graph.list_strategies(status="hypothesis") == [strategy]
    assert strategy_graph.list_strategies(status="tested") == []


def test_create_strategy_requires_evidence_and_leaves_no_partial_row(
    strategy_graph: StrategyGraphStore,
) -> None:
    with pytest.raises(ValueError, match="evidence_id"):
        strategy_graph.create_strategy("strategy:visible-exit", "Try a generic visible exit.", [])

    assert strategy_graph.get_strategy("strategy:visible-exit") is None
    assert strategy_graph.list_strategies() == []


def test_invalid_status_is_rejected(strategy_graph: StrategyGraphStore) -> None:
    with pytest.raises(ValueError, match="status"):
        strategy_graph.create_strategy(
            "strategy:visible-exit",
            "Try a generic visible exit.",
            ["evidence-1"],
            status="active",  # type: ignore[arg-type]
        )

    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )
    with pytest.raises(ValueError, match="status"):
        strategy_graph.update_status(
            "strategy:visible-exit",
            "active",  # type: ignore[arg-type]
            ["evidence-2"],
        )


def test_invalid_outcome_is_rejected(strategy_graph: StrategyGraphStore) -> None:
    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )

    with pytest.raises(ValueError, match="outcome"):
        strategy_graph.record_outcome(
            "strategy:visible-exit",
            "guaranteed_spoiler_success",  # type: ignore[arg-type]
            ["evidence-2"],
        )

    assert strategy_graph.list_outcomes("strategy:visible-exit") == []


def test_invalid_confidence_is_rejected(strategy_graph: StrategyGraphStore) -> None:
    with pytest.raises(ValueError, match="confidence"):
        strategy_graph.create_strategy(
            "strategy:visible-exit",
            "Try a generic visible exit.",
            ["evidence-1"],
            confidence=1.1,
        )

    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )
    with pytest.raises(ValueError, match="confidence"):
        strategy_graph.record_outcome(
            "strategy:visible-exit",
            "success",
            ["evidence-2"],
            confidence=-0.1,
        )


def test_append_evidence_is_idempotent(strategy_graph: StrategyGraphStore) -> None:
    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )

    strategy_graph.append_evidence("strategy:visible-exit", ["evidence-2"])
    updated = strategy_graph.append_evidence(
        "strategy:visible-exit",
        ["evidence-2", "evidence-1"],
    )

    assert updated.evidence_ids == ["evidence-1", "evidence-2"]


def test_update_status_requires_evidence(strategy_graph: StrategyGraphStore) -> None:
    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )

    with pytest.raises(ValueError, match="evidence_id"):
        strategy_graph.update_status("strategy:visible-exit", "tested", [])

    assert strategy_graph.get_strategy("strategy:visible-exit").status == "hypothesis"  # type: ignore[union-attr]


def test_update_status_with_evidence(strategy_graph: StrategyGraphStore) -> None:
    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )

    updated = strategy_graph.update_status("strategy:visible-exit", "tested", ["evidence-2"])

    assert updated.status == "tested"
    assert updated.evidence_ids == ["evidence-1", "evidence-2"]


def test_record_outcome_requires_evidence_and_leaves_no_partial_row(
    strategy_graph: StrategyGraphStore,
) -> None:
    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )

    with pytest.raises(ValueError, match="evidence_id"):
        strategy_graph.record_outcome("strategy:visible-exit", "success", [])

    assert strategy_graph.list_outcomes("strategy:visible-exit") == []


def test_record_and_list_outcomes(strategy_graph: StrategyGraphStore) -> None:
    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )

    first = strategy_graph.record_outcome(
        "strategy:visible-exit",
        "success",
        ["evidence-2"],
        confidence=0.8,
        metadata={"reward_delta": 0.5},
    )
    second = strategy_graph.record_outcome(
        "strategy:visible-exit",
        "inconclusive",
        ["evidence-3", "evidence-2"],
        confidence=0.4,
    )

    assert first.strategy_key == "strategy:visible-exit"
    assert first.outcome == "success"
    assert first.confidence == 0.8
    assert first.evidence_ids == ["evidence-2"]
    assert first.metadata == {"reward_delta": 0.5}
    assert strategy_graph.list_outcomes("strategy:visible-exit") == [first, second]
    assert strategy_graph.list_outcomes("missing") == []


def test_hidden_state_metadata_is_rejected(strategy_graph: StrategyGraphStore) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        strategy_graph.create_strategy(
            "strategy:visible-exit",
            "Try a generic visible exit.",
            ["evidence-1"],
            metadata={"map_id": 7},
        )

    strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )
    with pytest.raises(ValueError, match="forbidden"):
        strategy_graph.record_outcome(
            "strategy:visible-exit",
            "failure",
            ["evidence-2"],
            metadata={"nested": {"enemy_hp": 100}},
        )

    assert strategy_graph.list_outcomes("strategy:visible-exit") == []


def test_no_forbidden_no_spoiler_columns_or_fields_are_introduced(
    strategy_graph: StrategyGraphStore,
) -> None:
    strategy = strategy_graph.create_strategy(
        "strategy:visible-exit",
        "Try a generic visible exit.",
        ["evidence-1"],
    )
    outcome = strategy_graph.record_outcome("strategy:visible-exit", "mixed", ["evidence-2"])

    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(strategy.model_dump())
    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(outcome.model_dump())

    table_names = [
        row["name"]
        for row in strategy_graph.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        ).fetchall()
    ]
    column_names: set[str] = set()
    for table_name in table_names:
        column_names.update(
            row["name"]
            for row in strategy_graph.db.conn.execute(f"PRAGMA table_info({table_name})")
        )

    assert FORBIDDEN_SCHEMA_COLUMNS.isdisjoint(column_names)
