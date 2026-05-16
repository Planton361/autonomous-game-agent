import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from fh_agent.observation.schemas import ActionResult, KnowledgeFact, Observation, SkillResult


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def _json_from_model(model: BaseModel) -> str:
    return model.model_dump_json()


def _json_from_payload(payload: BaseModel | dict[str, Any]) -> str:
    if isinstance(payload, BaseModel):
        return _json_from_model(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _first_evidence_id(evidence_ids: Sequence[str]) -> str | None:
    return evidence_ids[0] if evidence_ids else None


class MemoryDB:
    """Small SQLite persistence boundary for visible evidence-backed memory."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.connection: sqlite3.Connection | None = None

    def open(self) -> "MemoryDB":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        return self

    @classmethod
    def connect(cls, path: Path | str) -> "MemoryDB":
        return cls(path).open()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> "MemoryDB":
        return self.open()

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self.connection is None:
            msg = "MemoryDB is not open"
            raise RuntimeError(msg)
        return self.connection

    def initialize_schema(self) -> None:
        schema_path = files("fh_agent.memory").joinpath("schema.sql")
        self.conn.executescript(schema_path.read_text(encoding="utf-8"))
        self.conn.commit()

    def insert_observation(self, observation: Observation) -> str:
        observation_id = observation.observation_id or _new_id("obs")
        stored = observation.model_copy(update={"observation_id": observation_id})
        self.conn.execute(
            """
            INSERT INTO observations (
                observation_id,
                run_id,
                created_at,
                evidence_id,
                ui_state,
                observation_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                observation_id,
                stored.run_id,
                stored.created_at.isoformat(),
                stored.screenshot_id or _first_evidence_id(stored.evidence_ids),
                stored.ui_state,
                _json_from_model(stored),
            ),
        )
        self.conn.commit()
        return observation_id

    def get_observation(self, observation_id: str) -> Observation | None:
        row = self.conn.execute(
            "SELECT observation_json FROM observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        if row is None:
            return None
        return Observation.model_validate_json(row["observation_json"])

    def insert_action(
        self,
        run_id: str,
        action: ActionResult,
        *,
        related_observation_id: str | None = None,
    ) -> str:
        action_id = _new_id("act")
        self.conn.execute(
            """
            INSERT INTO actions (
                action_id,
                run_id,
                created_at,
                primitive_action,
                action_json,
                related_observation_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                run_id,
                action.created_at.isoformat(),
                action.action,
                _json_from_model(action),
                related_observation_id,
            ),
        )
        self.conn.commit()
        return action_id

    def get_action(self, action_id: str) -> ActionResult | None:
        row = self.conn.execute(
            "SELECT action_json FROM actions WHERE action_id = ?",
            (action_id,),
        ).fetchone()
        if row is None:
            return None
        return ActionResult.model_validate_json(row["action_json"])

    def insert_skill_result(
        self,
        run_id: str,
        result: SkillResult,
        *,
        steps: int | None = None,
    ) -> str:
        skill_result_id = _new_id("skill-result")
        self.conn.execute(
            """
            INSERT INTO skill_results (
                skill_result_id,
                run_id,
                created_at,
                skill_name,
                success,
                reward,
                steps,
                skill_result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                skill_result_id,
                run_id,
                result.created_at.isoformat(),
                result.skill_name,
                int(result.success),
                result.reward,
                steps,
                _json_from_model(result),
            ),
        )
        self.conn.commit()
        return skill_result_id

    def get_skill_result(self, skill_result_id: str) -> SkillResult | None:
        row = self.conn.execute(
            "SELECT skill_result_json FROM skill_results WHERE skill_result_id = ?",
            (skill_result_id,),
        ).fetchone()
        if row is None:
            return None
        return SkillResult.model_validate_json(row["skill_result_json"])

    def insert_fact(
        self,
        fact: KnowledgeFact | str,
        *,
        evidence_ids: Sequence[str] | None = None,
        status: str = "hypothesis",
        confidence: float | None = None,
        fact_id: str | None = None,
        fact_json: dict[str, Any] | None = None,
    ) -> str:
        if isinstance(fact, KnowledgeFact):
            stored_fact_id = fact_id or fact.fact_id or _new_id("fact")
            claim = fact.claim
            stored_confidence = fact.confidence if confidence is None else confidence
            stored_evidence_ids = list(fact.evidence_ids if evidence_ids is None else evidence_ids)
            stored_fact_json = _json_from_model(fact.model_copy(update={"fact_id": stored_fact_id}))
        else:
            stored_fact_id = fact_id or _new_id("fact")
            claim = fact
            stored_confidence = confidence
            stored_evidence_ids = list(evidence_ids or [])
            stored_fact_json = _json_from_payload(fact_json) if fact_json is not None else None

        if not stored_evidence_ids:
            msg = "facts require at least one evidence_id"
            raise ValueError(msg)

        timestamp = _utc_now().isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO facts (
                    fact_id,
                    claim,
                    status,
                    confidence,
                    created_at,
                    updated_at,
                    fact_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_fact_id,
                    claim,
                    status,
                    stored_confidence,
                    timestamp,
                    timestamp,
                    stored_fact_json,
                ),
            )
            self.conn.executemany(
                """
                INSERT INTO fact_evidence (fact_id, evidence_id)
                VALUES (?, ?)
                """,
                [(stored_fact_id, evidence_id) for evidence_id in stored_evidence_ids],
            )
        return stored_fact_id

    def get_fact(self, fact_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT fact_id, claim, status, confidence, created_at, updated_at, fact_json
            FROM facts
            WHERE fact_id = ?
            """,
            (fact_id,),
        ).fetchone()
        if row is None:
            return None

        fact = dict(row)
        fact["evidence_ids"] = self._fact_evidence_ids(fact_id)
        return fact

    def list_facts(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT fact_id, claim, status, confidence, created_at, updated_at, fact_json
            FROM facts
            ORDER BY created_at, fact_id
            """,
        ).fetchall()
        facts = [dict(row) for row in rows]
        for fact in facts:
            fact["evidence_ids"] = self._fact_evidence_ids(fact["fact_id"])
        return facts

    def _fact_evidence_ids(self, fact_id: str) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT evidence_id
            FROM fact_evidence
            WHERE fact_id = ?
            ORDER BY evidence_id
            """,
            (fact_id,),
        ).fetchall()
        return [row["evidence_id"] for row in rows]
