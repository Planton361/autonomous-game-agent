from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.memory.db import MemoryDB

RiskOutcome = Literal[
    "death",
    "combat_started",
    "damage_taken",
    "skill_failed",
    "safe_passage",
    "no_change",
]

ALLOWED_RISK_OUTCOMES: frozenset[str] = frozenset(
    {
        "death",
        "combat_started",
        "damage_taken",
        "skill_failed",
        "safe_passage",
        "no_change",
    }
)

OUTCOME_WEIGHTS: dict[RiskOutcome, float] = {
    "death": 0.7,
    "combat_started": 0.25,
    "damage_taken": 0.3,
    "skill_failed": 0.15,
    "safe_passage": -0.1,
    "no_change": 0.0,
}


class EntityRiskEvent(BaseModel):
    """One evidence-backed risk update for a visible entity or hazard signal."""

    model_config = ConfigDict(frozen=True)

    risk_update_id: str
    entity_key: str
    outcome: RiskOutcome
    confidence: float = Field(ge=0.0, le=1.0)
    risk_delta: float
    risk_score_after: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    evidence_ids: list[str] = Field(min_length=1)


class EntityRiskRecord(BaseModel):
    """Current aggregate risk for one visible entity or hazard signal."""

    model_config = ConfigDict(frozen=True)

    entity_key: str
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    total_outcomes: int = Field(default=0, ge=0)
    last_outcome: RiskOutcome | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    outcome_counts: dict[RiskOutcome, int] = Field(default_factory=dict)


class EntityRiskStore:
    """Evidence-based risk aggregation for visible entity or hazard keys."""

    def __init__(self, db: MemoryDB) -> None:
        self.db = db

    def get_risk(self, entity_key: str) -> EntityRiskRecord:
        row = self.db.conn.execute(
            """
            SELECT entity_key, risk_score, total_outcomes, last_outcome, created_at, updated_at
            FROM entity_risks
            WHERE entity_key = ?
            """,
            (entity_key,),
        ).fetchone()
        if row is None:
            return EntityRiskRecord(entity_key=entity_key)

        return EntityRiskRecord(
            entity_key=row["entity_key"],
            risk_score=row["risk_score"],
            total_outcomes=row["total_outcomes"],
            last_outcome=row["last_outcome"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            evidence_ids=self._evidence_ids(entity_key),
            outcome_counts=self._outcome_counts(entity_key),
        )

    def list_risks(self) -> list[EntityRiskRecord]:
        rows = self.db.conn.execute(
            """
            SELECT entity_key
            FROM entity_risks
            ORDER BY entity_key
            """,
        ).fetchall()
        return [self.get_risk(row["entity_key"]) for row in rows]

    def record_outcome(
        self,
        entity_key: str,
        outcome: RiskOutcome,
        evidence_ids: list[str],
        confidence: float = 1.0,
    ) -> EntityRiskRecord:
        if not entity_key:
            msg = "entity_key must not be empty"
            raise ValueError(msg)
        self._validate_outcome(outcome)
        self._validate_confidence(confidence)
        if not evidence_ids:
            msg = "risk outcomes require at least one evidence_id"
            raise ValueError(msg)

        now = _utc_now_iso()
        update_id = f"risk-update-{uuid4().hex}"
        current = self.get_risk(entity_key)
        risk_delta = OUTCOME_WEIGHTS[outcome] * confidence
        next_score = _clamp_risk(current.risk_score + risk_delta)
        created_at = current.created_at.isoformat() if current.created_at is not None else now

        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT INTO entity_risks (
                    entity_key,
                    risk_score,
                    total_outcomes,
                    last_outcome,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_key) DO UPDATE SET
                    risk_score = excluded.risk_score,
                    total_outcomes = excluded.total_outcomes,
                    last_outcome = excluded.last_outcome,
                    updated_at = excluded.updated_at
                """,
                (
                    entity_key,
                    next_score,
                    current.total_outcomes + 1,
                    outcome,
                    created_at,
                    now,
                ),
            )
            self.db.conn.execute(
                """
                INSERT INTO entity_risk_events (
                    risk_update_id,
                    entity_key,
                    outcome,
                    confidence,
                    risk_delta,
                    risk_score_after,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (update_id, entity_key, outcome, confidence, risk_delta, next_score, now),
            )
            self.db.conn.executemany(
                """
                INSERT INTO entity_risk_event_evidence (risk_update_id, evidence_id)
                VALUES (?, ?)
                """,
                [(update_id, evidence_id) for evidence_id in evidence_ids],
            )

        return self.get_risk(entity_key)

    def list_events(self, entity_key: str) -> list[EntityRiskEvent]:
        rows = self.db.conn.execute(
            """
            SELECT
                risk_update_id,
                entity_key,
                outcome,
                confidence,
                risk_delta,
                risk_score_after,
                created_at
            FROM entity_risk_events
            WHERE entity_key = ?
            ORDER BY created_at, risk_update_id
            """,
            (entity_key,),
        ).fetchall()
        return [
            EntityRiskEvent(
                risk_update_id=row["risk_update_id"],
                entity_key=row["entity_key"],
                outcome=row["outcome"],
                confidence=row["confidence"],
                risk_delta=row["risk_delta"],
                risk_score_after=row["risk_score_after"],
                created_at=datetime.fromisoformat(row["created_at"]),
                evidence_ids=self._event_evidence_ids(row["risk_update_id"]),
            )
            for row in rows
        ]

    def _evidence_ids(self, entity_key: str) -> list[str]:
        rows = self.db.conn.execute(
            """
            SELECT DISTINCT evidence.evidence_id
            FROM entity_risk_events AS events
            JOIN entity_risk_event_evidence AS evidence
                ON evidence.risk_update_id = events.risk_update_id
            WHERE events.entity_key = ?
            ORDER BY evidence.evidence_id
            """,
            (entity_key,),
        ).fetchall()
        return [row["evidence_id"] for row in rows]

    def _event_evidence_ids(self, risk_update_id: str) -> list[str]:
        rows = self.db.conn.execute(
            """
            SELECT evidence_id
            FROM entity_risk_event_evidence
            WHERE risk_update_id = ?
            ORDER BY evidence_id
            """,
            (risk_update_id,),
        ).fetchall()
        return [row["evidence_id"] for row in rows]

    def _outcome_counts(self, entity_key: str) -> dict[RiskOutcome, int]:
        rows = self.db.conn.execute(
            """
            SELECT outcome, COUNT(*) AS count
            FROM entity_risk_events
            WHERE entity_key = ?
            GROUP BY outcome
            ORDER BY outcome
            """,
            (entity_key,),
        ).fetchall()
        return {row["outcome"]: row["count"] for row in rows}

    @staticmethod
    def _validate_outcome(outcome: str) -> None:
        if outcome not in ALLOWED_RISK_OUTCOMES:
            allowed = ", ".join(sorted(ALLOWED_RISK_OUTCOMES))
            msg = f"outcome must be one of: {allowed}"
            raise ValueError(msg)

    @staticmethod
    def _validate_confidence(confidence: float) -> None:
        if not 0.0 <= confidence <= 1.0:
            msg = "confidence must be between 0.0 and 1.0"
            raise ValueError(msg)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _clamp_risk(risk_score: float) -> float:
    return min(1.0, max(0.0, risk_score))
