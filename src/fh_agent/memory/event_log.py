import json
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from fh_agent.observation.schemas import SkillResult


class EventRecord(BaseModel):
    """Append-only JSONL event record."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    run_id: str
    event_type: str
    created_at: datetime
    payload: dict[str, object] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class EventLogger:
    """Writes and reads JSONL event records in append order."""

    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.path = path
        self.run_id = run_id
        self.clock = clock or (lambda: datetime.now(UTC))
        self.id_factory = id_factory or (lambda: uuid4().hex)

    def append(
        self,
        event_type: str,
        *,
        payload: dict[str, object] | None = None,
        evidence_ids: Iterable[str] = (),
    ) -> EventRecord:
        record = EventRecord(
            event_id=self.id_factory(),
            run_id=self.run_id,
            event_type=event_type,
            created_at=self.clock(),
            payload=payload or {},
            evidence_ids=list(evidence_ids),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(record.model_dump_json())
            file.write("\n")
        return record

    def append_skill_result(self, result: "SkillResult") -> EventRecord:
        """Append a reusable skill result without widening EventRecord."""
        return self.append(
            "skill_result",
            payload=json.loads(result.model_dump_json()),
            evidence_ids=result.evidence_ids,
        )

    def read_all(self) -> list[EventRecord]:
        if not self.path.exists():
            return []

        records: list[EventRecord] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped:
                    records.append(EventRecord.model_validate(json.loads(stripped)))
        return records
