import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.memory.db import MemoryDB
from fh_agent.observation.schemas import KnowledgeFact

FactStatus = Literal["hypothesis", "observed_fact", "validated_rule", "contradicted"]

ALLOWED_FACT_STATUSES: frozenset[str] = frozenset(
    {"hypothesis", "observed_fact", "validated_rule", "contradicted"}
)


class StoredFact(BaseModel):
    """Typed view of one persisted evidence-backed fact."""

    model_config = ConfigDict(frozen=True)

    fact_id: str
    claim: str
    status: FactStatus
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime
    evidence_ids: list[str] = Field(min_length=1)
    fact: KnowledgeFact | None = None


class FactStore:
    """Typed KnowledgeFact API backed by the MemoryDB facts tables."""

    def __init__(self, db: MemoryDB) -> None:
        self.db = db

    def create_fact(
        self,
        *,
        claim: str,
        evidence_ids: Sequence[str],
        subject: str = "visible_observation",
        predicate: str = "observed",
        value: str | int | float | bool | None = None,
        status: FactStatus = "hypothesis",
        confidence: float | None = None,
        source: Literal["visible_observation", "observed_outcome", "sanitized_bridge"] = (
            "visible_observation"
        ),
    ) -> StoredFact:
        self._validate_status(status)
        self._validate_confidence(confidence)
        if not evidence_ids:
            msg = "facts require at least one evidence_id"
            raise ValueError(msg)

        fact = KnowledgeFact(
            subject=subject,
            predicate=predicate,
            value=value,
            claim=claim,
            source=source,
            confidence=confidence,
            evidence_ids=list(evidence_ids),
        )
        fact_id = self.db.insert_fact(fact, status=status)
        stored = self.get_fact(fact_id)
        if stored is None:
            msg = f"created fact could not be read back: {fact_id}"
            raise RuntimeError(msg)
        return stored

    def get_fact(self, fact_id: str) -> StoredFact | None:
        row = self.db.get_fact(fact_id)
        if row is None:
            return None
        return _stored_fact_from_row(row)

    def list_facts(self, *, status: FactStatus | None = None) -> list[StoredFact]:
        if status is not None:
            self._validate_status(status)
        facts = [_stored_fact_from_row(row) for row in self.db.list_facts()]
        if status is None:
            return facts
        return [fact for fact in facts if fact.status == status]

    def update_fact_status(self, fact_id: str, status: FactStatus) -> StoredFact:
        self._validate_status(status)
        self.db.conn.execute(
            """
            UPDATE facts
            SET status = ?, updated_at = ?
            WHERE fact_id = ?
            """,
            (status, _utc_now_iso(), fact_id),
        )
        self.db.conn.commit()
        return self._required_fact(fact_id)

    def update_fact_confidence(self, fact_id: str, confidence: float) -> StoredFact:
        self._validate_confidence(confidence)
        self.db.conn.execute(
            """
            UPDATE facts
            SET confidence = ?, updated_at = ?
            WHERE fact_id = ?
            """,
            (confidence, _utc_now_iso(), fact_id),
        )
        self.db.conn.commit()
        return self._required_fact(fact_id)

    def append_evidence(self, fact_id: str, evidence_id: str) -> StoredFact:
        if not evidence_id:
            msg = "evidence_id must not be empty"
            raise ValueError(msg)
        if self.get_fact(fact_id) is None:
            msg = f"fact does not exist: {fact_id}"
            raise KeyError(msg)

        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT OR IGNORE INTO fact_evidence (fact_id, evidence_id)
                VALUES (?, ?)
                """,
                (fact_id, evidence_id),
            )
            self.db.conn.execute(
                """
                UPDATE facts
                SET updated_at = ?
                WHERE fact_id = ?
                """,
                (_utc_now_iso(), fact_id),
            )
        return self._required_fact(fact_id)

    def mark_contradicted(self, fact_id: str) -> StoredFact:
        return self.update_fact_status(fact_id, "contradicted")

    def _required_fact(self, fact_id: str) -> StoredFact:
        fact = self.get_fact(fact_id)
        if fact is None:
            msg = f"fact does not exist: {fact_id}"
            raise KeyError(msg)
        return fact

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in ALLOWED_FACT_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_FACT_STATUSES))
            msg = f"status must be one of: {allowed}"
            raise ValueError(msg)

    @staticmethod
    def _validate_confidence(confidence: float | None) -> None:
        if confidence is None:
            return
        if not 0.0 <= confidence <= 1.0:
            msg = "confidence must be between 0.0 and 1.0"
            raise ValueError(msg)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _stored_fact_from_row(row: dict[str, Any]) -> StoredFact:
    fact = _knowledge_fact_from_json(row["fact_json"])
    return StoredFact(
        fact_id=row["fact_id"],
        claim=row["claim"],
        status=row["status"],
        confidence=row["confidence"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        evidence_ids=row["evidence_ids"],
        fact=fact,
    )


def _knowledge_fact_from_json(payload: str | None) -> KnowledgeFact | None:
    if payload is None:
        return None
    return KnowledgeFact.model_validate(json.loads(payload))
