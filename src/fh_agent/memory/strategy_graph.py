import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.memory.db import MemoryDB

StrategyStatus = Literal["hypothesis", "tested", "promoted", "deprecated", "contradicted"]
StrategyOutcome = Literal["success", "failure", "mixed", "inconclusive"]

ALLOWED_STRATEGY_STATUSES: frozenset[str] = frozenset(
    {"hypothesis", "tested", "promoted", "deprecated", "contradicted"}
)
ALLOWED_STRATEGY_OUTCOMES: frozenset[str] = frozenset(
    {"success", "failure", "mixed", "inconclusive"}
)

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "map_id",
        "event_id",
        "event_name",
        "event_comments",
        "event_trigger_conditions",
        "tile_coordinates",
        "rpg_maker_tile_coordinates",
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
)


class StrategyRecord(BaseModel):
    """Evidence-backed strategy hypothesis stored for later planner use."""

    model_config = ConfigDict(frozen=True)

    strategy_key: str
    title: str
    status: StrategyStatus
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyOutcomeRecord(BaseModel):
    """One observed outcome for a strategy hypothesis."""

    model_config = ConfigDict(frozen=True)

    outcome_key: str
    strategy_key: str
    outcome: StrategyOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyGraphStore:
    """Persistence for evidence-backed strategy hypotheses and outcomes."""

    def __init__(self, db: MemoryDB) -> None:
        self.db = db

    def create_strategy(
        self,
        strategy_key: str,
        title: str,
        evidence_ids: list[str],
        status: StrategyStatus = "hypothesis",
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> StrategyRecord:
        self._validate_strategy_key(strategy_key)
        if not title:
            msg = "title must not be empty"
            raise ValueError(msg)
        self._validate_evidence(evidence_ids)
        self._validate_status(status)
        self._validate_confidence(confidence)
        clean_metadata = _validated_metadata(metadata)
        now = _utc_now_iso()

        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT INTO strategies (
                    strategy_key,
                    title,
                    status,
                    confidence,
                    created_at,
                    updated_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_key,
                    title,
                    status,
                    confidence,
                    now,
                    now,
                    _metadata_json(clean_metadata),
                ),
            )
            self._insert_strategy_evidence(strategy_key, evidence_ids)

        strategy = self.get_strategy(strategy_key)
        if strategy is None:
            msg = f"strategy could not be read after create: {strategy_key}"
            raise RuntimeError(msg)
        return strategy

    def get_strategy(self, strategy_key: str) -> StrategyRecord | None:
        row = self.db.conn.execute(
            """
            SELECT
                strategy_key,
                title,
                status,
                confidence,
                created_at,
                updated_at,
                metadata_json
            FROM strategies
            WHERE strategy_key = ?
            """,
            (strategy_key,),
        ).fetchone()
        if row is None:
            return None
        return self._strategy_from_row(dict(row))

    def list_strategies(self, status: str | None = None) -> list[StrategyRecord]:
        if status is not None:
            self._validate_status(status)
            rows = self.db.conn.execute(
                """
                SELECT
                    strategy_key,
                    title,
                    status,
                    confidence,
                    created_at,
                    updated_at,
                    metadata_json
                FROM strategies
                WHERE status = ?
                ORDER BY strategy_key
                """,
                (status,),
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                """
                SELECT
                    strategy_key,
                    title,
                    status,
                    confidence,
                    created_at,
                    updated_at,
                    metadata_json
                FROM strategies
                ORDER BY strategy_key
                """,
            ).fetchall()
        return [self._strategy_from_row(dict(row)) for row in rows]

    def append_evidence(self, strategy_key: str, evidence_ids: list[str]) -> StrategyRecord:
        self._validate_evidence(evidence_ids)
        if self.get_strategy(strategy_key) is None:
            msg = f"strategy does not exist: {strategy_key}"
            raise KeyError(msg)

        with self.db.conn:
            self._insert_strategy_evidence(strategy_key, evidence_ids)
            self.db.conn.execute(
                """
                UPDATE strategies
                SET updated_at = ?
                WHERE strategy_key = ?
                """,
                (_utc_now_iso(), strategy_key),
            )
        return self._required_strategy(strategy_key)

    def update_status(
        self,
        strategy_key: str,
        status: StrategyStatus,
        evidence_ids: list[str],
    ) -> StrategyRecord:
        self._validate_status(status)
        self._validate_evidence(evidence_ids)
        if self.get_strategy(strategy_key) is None:
            msg = f"strategy does not exist: {strategy_key}"
            raise KeyError(msg)

        with self.db.conn:
            self.db.conn.execute(
                """
                UPDATE strategies
                SET status = ?, updated_at = ?
                WHERE strategy_key = ?
                """,
                (status, _utc_now_iso(), strategy_key),
            )
            self._insert_strategy_evidence(strategy_key, evidence_ids)
        return self._required_strategy(strategy_key)

    def record_outcome(
        self,
        strategy_key: str,
        outcome: StrategyOutcome,
        evidence_ids: list[str],
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> StrategyOutcomeRecord:
        self._validate_outcome(outcome)
        self._validate_evidence(evidence_ids)
        self._validate_confidence(confidence)
        clean_metadata = _validated_metadata(metadata)
        if self.get_strategy(strategy_key) is None:
            msg = f"strategy does not exist: {strategy_key}"
            raise KeyError(msg)

        outcome_key = f"strategy-outcome-{uuid4().hex}"
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT INTO strategy_outcomes (
                    outcome_key,
                    strategy_key,
                    outcome,
                    confidence,
                    created_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome_key,
                    strategy_key,
                    outcome,
                    confidence,
                    _utc_now_iso(),
                    _metadata_json(clean_metadata),
                ),
            )
            self.db.conn.executemany(
                """
                INSERT OR IGNORE INTO strategy_outcome_evidence (outcome_key, evidence_id)
                VALUES (?, ?)
                """,
                [(outcome_key, evidence_id) for evidence_id in evidence_ids],
            )

        stored = self._get_outcome(outcome_key)
        if stored is None:
            msg = f"outcome could not be read after create: {outcome_key}"
            raise RuntimeError(msg)
        return stored

    def list_outcomes(self, strategy_key: str) -> list[StrategyOutcomeRecord]:
        rows = self.db.conn.execute(
            """
            SELECT outcome_key
            FROM strategy_outcomes
            WHERE strategy_key = ?
            ORDER BY created_at, outcome_key
            """,
            (strategy_key,),
        ).fetchall()
        return [
            outcome
            for row in rows
            if (outcome := self._get_outcome(row["outcome_key"])) is not None
        ]

    def _get_outcome(self, outcome_key: str) -> StrategyOutcomeRecord | None:
        row = self.db.conn.execute(
            """
            SELECT
                outcome_key,
                strategy_key,
                outcome,
                confidence,
                created_at,
                metadata_json
            FROM strategy_outcomes
            WHERE outcome_key = ?
            """,
            (outcome_key,),
        ).fetchone()
        if row is None:
            return None
        return self._outcome_from_row(dict(row))

    def _strategy_from_row(self, row: dict[str, Any]) -> StrategyRecord:
        return StrategyRecord(
            strategy_key=row["strategy_key"],
            title=row["title"],
            status=row["status"],
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            evidence_ids=self._strategy_evidence_ids(row["strategy_key"]),
            metadata=_metadata_from_json(row["metadata_json"]),
        )

    def _outcome_from_row(self, row: dict[str, Any]) -> StrategyOutcomeRecord:
        return StrategyOutcomeRecord(
            outcome_key=row["outcome_key"],
            strategy_key=row["strategy_key"],
            outcome=row["outcome"],
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
            evidence_ids=self._outcome_evidence_ids(row["outcome_key"]),
            metadata=_metadata_from_json(row["metadata_json"]),
        )

    def _strategy_evidence_ids(self, strategy_key: str) -> list[str]:
        rows = self.db.conn.execute(
            """
            SELECT evidence_id
            FROM strategy_evidence
            WHERE strategy_key = ?
            ORDER BY evidence_id
            """,
            (strategy_key,),
        ).fetchall()
        return [row["evidence_id"] for row in rows]

    def _outcome_evidence_ids(self, outcome_key: str) -> list[str]:
        rows = self.db.conn.execute(
            """
            SELECT evidence_id
            FROM strategy_outcome_evidence
            WHERE outcome_key = ?
            ORDER BY evidence_id
            """,
            (outcome_key,),
        ).fetchall()
        return [row["evidence_id"] for row in rows]

    def _insert_strategy_evidence(self, strategy_key: str, evidence_ids: list[str]) -> None:
        self.db.conn.executemany(
            """
            INSERT OR IGNORE INTO strategy_evidence (strategy_key, evidence_id)
            VALUES (?, ?)
            """,
            [(strategy_key, evidence_id) for evidence_id in evidence_ids],
        )

    def _required_strategy(self, strategy_key: str) -> StrategyRecord:
        strategy = self.get_strategy(strategy_key)
        if strategy is None:
            msg = f"strategy does not exist: {strategy_key}"
            raise KeyError(msg)
        return strategy

    @staticmethod
    def _validate_strategy_key(strategy_key: str) -> None:
        if not strategy_key:
            msg = "strategy_key must not be empty"
            raise ValueError(msg)

    @staticmethod
    def _validate_evidence(evidence_ids: list[str]) -> None:
        if not evidence_ids:
            msg = "strategy graph updates require at least one evidence_id"
            raise ValueError(msg)

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in ALLOWED_STRATEGY_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_STRATEGY_STATUSES))
            msg = f"status must be one of: {allowed}"
            raise ValueError(msg)

    @staticmethod
    def _validate_outcome(outcome: str) -> None:
        if outcome not in ALLOWED_STRATEGY_OUTCOMES:
            allowed = ", ".join(sorted(ALLOWED_STRATEGY_OUTCOMES))
            msg = f"outcome must be one of: {allowed}"
            raise ValueError(msg)

    @staticmethod
    def _validate_confidence(confidence: float) -> None:
        if not 0.0 <= confidence <= 1.0:
            msg = "confidence must be between 0.0 and 1.0"
            raise ValueError(msg)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _validated_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    _reject_forbidden_metadata_keys(metadata)
    return metadata


def _reject_forbidden_metadata_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_METADATA_KEYS:
                msg = f"metadata contains forbidden hidden-state key: {key}"
                raise ValueError(msg)
            _reject_forbidden_metadata_keys(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_metadata_keys(item)


def _metadata_json(metadata: dict[str, Any]) -> str | None:
    if not metadata:
        return None
    return json.dumps(metadata, sort_keys=True, separators=(",", ":"))


def _metadata_from_json(payload: str | None) -> dict[str, Any]:
    if payload is None:
        return {}
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        return {}
    return loaded
