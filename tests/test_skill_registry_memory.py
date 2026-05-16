from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fh_agent.memory.db import MemoryDB
from fh_agent.memory.skill_registry import SkillRegistry
from fh_agent.observation.schemas import SkillResult

FORBIDDEN_SCHEMA_COLUMNS = {
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
def db(tmp_path: Path) -> MemoryDB:
    with MemoryDB(tmp_path / "memory.sqlite3") as memory_db:
        memory_db.initialize_schema()
        yield memory_db


def add_skill_result(
    db: MemoryDB,
    *,
    skill_name: str,
    success: bool,
    created_at: datetime,
    reward: float | None = None,
    steps: int | None = None,
    failure_reason: str | None = None,
) -> str:
    return db.insert_skill_result(
        "run-1",
        SkillResult(
            skill_name=skill_name,
            success=success,
            created_at=created_at,
            reward=reward,
            failure_reason=failure_reason,
            evidence_ids=["evidence-1"],
        ),
        steps=steps,
    )


def test_empty_stats_for_unknown_skill(db: MemoryDB) -> None:
    registry = SkillRegistry(db)

    stats = registry.get_skill_stats("unknown_skill")

    assert stats.skill_name == "unknown_skill"
    assert stats.total_runs == 0
    assert stats.success_count == 0
    assert stats.failure_count == 0
    assert stats.success_rate == 0.0
    assert stats.average_reward is None
    assert stats.average_steps is None
    assert stats.last_used_at is None
    assert stats.failure_reason_counts == {}
    assert registry.recent_results("unknown_skill") == []
    assert registry.list_skill_stats() == []


def test_counts_success_rate_average_reward_and_steps(db: MemoryDB) -> None:
    registry = SkillRegistry(db)
    start = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
    add_skill_result(
        db,
        skill_name="universal_skill",
        success=True,
        created_at=start,
        reward=1.0,
        steps=2,
    )
    add_skill_result(
        db,
        skill_name="universal_skill",
        success=False,
        created_at=start + timedelta(seconds=1),
        reward=-0.5,
        steps=4,
        failure_reason="timeout",
    )
    add_skill_result(
        db,
        skill_name="universal_skill",
        success=False,
        created_at=start + timedelta(seconds=2),
        reward=0.0,
        steps=6,
        failure_reason="timeout",
    )

    stats = registry.get_skill_stats("universal_skill")

    assert stats.total_runs == 3
    assert stats.success_count == 1
    assert stats.failure_count == 2
    assert stats.success_rate == pytest.approx(1 / 3)
    assert stats.average_reward == pytest.approx(0.5 / 3)
    assert stats.average_steps == pytest.approx(4.0)
    assert stats.last_used_at == start + timedelta(seconds=2)
    assert stats.failure_reason_counts == {"timeout": 2}


def test_list_skill_stats_for_multiple_skill_names(db: MemoryDB) -> None:
    registry = SkillRegistry(db)
    start = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
    add_skill_result(
        db,
        skill_name="skill_b",
        success=True,
        created_at=start,
        reward=1.0,
        steps=1,
    )
    add_skill_result(
        db,
        skill_name="skill_a",
        success=False,
        created_at=start + timedelta(seconds=1),
        reward=-1.0,
        steps=3,
    )

    stats = registry.list_skill_stats()

    assert [item.skill_name for item in stats] == ["skill_a", "skill_b"]
    assert [item.total_runs for item in stats] == [1, 1]
    assert [item.success_count for item in stats] == [0, 1]


def test_recent_results_are_sorted_by_newest_entry(db: MemoryDB) -> None:
    registry = SkillRegistry(db)
    start = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
    oldest_id = add_skill_result(
        db,
        skill_name="universal_skill",
        success=True,
        created_at=start,
        reward=1.0,
        steps=1,
    )
    newest_id = add_skill_result(
        db,
        skill_name="universal_skill",
        success=False,
        created_at=start + timedelta(seconds=2),
        reward=-1.0,
        steps=2,
        failure_reason="timeout",
    )
    middle_id = add_skill_result(
        db,
        skill_name="universal_skill",
        success=True,
        created_at=start + timedelta(seconds=1),
        reward=0.5,
        steps=3,
    )

    recent = registry.recent_results("universal_skill", limit=2)

    assert [record.skill_result_id for record in recent] == [newest_id, middle_id]
    assert [record.skill_result_id for record in registry.recent_results("universal_skill")] == [
        newest_id,
        middle_id,
        oldest_id,
    ]
    assert recent[0].result.failure_reason == "timeout"


def test_recent_results_rejects_negative_limit(db: MemoryDB) -> None:
    registry = SkillRegistry(db)

    with pytest.raises(ValueError, match="limit"):
        registry.recent_results("universal_skill", limit=-1)


def test_no_forbidden_no_spoiler_columns_are_introduced(db: MemoryDB) -> None:
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
