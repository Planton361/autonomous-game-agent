from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.memory.db import MemoryDB
from fh_agent.observation.schemas import SkillResult


class SkillResultRecord(BaseModel):
    """One persisted skill result with storage metadata."""

    model_config = ConfigDict(frozen=True)

    skill_result_id: str
    run_id: str
    created_at: datetime
    skill_name: str
    success: bool
    reward: float | None = None
    steps: int | None = None
    result: SkillResult


class SkillStats(BaseModel):
    """Aggregate history for one reusable skill."""

    model_config = ConfigDict(frozen=True)

    skill_name: str
    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    average_reward: float | None = None
    average_steps: float | None = None
    last_used_at: datetime | None = None
    failure_reason_counts: dict[str, int] = Field(default_factory=dict)


class SkillRegistry:
    """Read-only skill history aggregation backed by MemoryDB skill_results."""

    def __init__(self, db: MemoryDB) -> None:
        self.db = db

    def get_skill_stats(self, skill_name: str) -> SkillStats:
        rows = self._skill_rows(skill_name=skill_name)
        if not rows:
            return SkillStats(skill_name=skill_name)
        return _stats_from_rows(skill_name, rows)

    def list_skill_stats(self) -> list[SkillStats]:
        rows = self.db.conn.execute(
            """
            SELECT DISTINCT skill_name
            FROM skill_results
            ORDER BY skill_name
            """,
        ).fetchall()
        return [self.get_skill_stats(row["skill_name"]) for row in rows]

    def recent_results(self, skill_name: str, limit: int = 10) -> list[SkillResultRecord]:
        if limit < 0:
            msg = "limit must be greater than or equal to 0"
            raise ValueError(msg)
        rows = self._skill_rows(skill_name=skill_name, limit=limit, newest_first=True)
        return [_record_from_row(row) for row in rows]

    def _skill_rows(
        self,
        *,
        skill_name: str,
        limit: int | None = None,
        newest_first: bool = False,
    ) -> list[dict[str, object]]:
        order = "DESC" if newest_first else "ASC"
        query = f"""
            SELECT
                skill_result_id,
                run_id,
                created_at,
                skill_name,
                success,
                reward,
                steps,
                skill_result_json
            FROM skill_results
            WHERE skill_name = ?
            ORDER BY created_at {order}, skill_result_id {order}
        """
        params: tuple[object, ...]
        if limit is None:
            params = (skill_name,)
        else:
            query = f"{query} LIMIT ?"
            params = (skill_name, limit)
        rows = self.db.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def _stats_from_rows(skill_name: str, rows: list[dict[str, object]]) -> SkillStats:
    total_runs = len(rows)
    success_count = sum(1 for row in rows if bool(row["success"]))
    failure_count = total_runs - success_count
    rewards = [float(row["reward"]) for row in rows if row["reward"] is not None]
    steps = [int(row["steps"]) for row in rows if row["steps"] is not None]
    failure_reason_counts: dict[str, int] = {}

    for row in rows:
        result = SkillResult.model_validate_json(str(row["skill_result_json"]))
        if not result.success and result.failure_reason is not None:
            failure_reason_counts[result.failure_reason] = (
                failure_reason_counts.get(result.failure_reason, 0) + 1
            )

    return SkillStats(
        skill_name=skill_name,
        total_runs=total_runs,
        success_count=success_count,
        failure_count=failure_count,
        success_rate=success_count / total_runs,
        average_reward=_average(rewards),
        average_steps=_average(steps),
        last_used_at=datetime.fromisoformat(str(rows[-1]["created_at"])),
        failure_reason_counts=failure_reason_counts,
    )


def _record_from_row(row: dict[str, object]) -> SkillResultRecord:
    return SkillResultRecord(
        skill_result_id=str(row["skill_result_id"]),
        run_id=str(row["run_id"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        skill_name=str(row["skill_name"]),
        success=bool(row["success"]),
        reward=float(row["reward"]) if row["reward"] is not None else None,
        steps=int(row["steps"]) if row["steps"] is not None else None,
        result=SkillResult.model_validate_json(str(row["skill_result_json"])),
    )


def _average(values: list[int] | list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
