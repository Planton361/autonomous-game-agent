import json
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from fh_agent.manager.runtime_stop import ManagerStopResult
    from fh_agent.manager.verified_reward import VerifiedRewardBreakdown
    from fh_agent.observation.schemas import ActionResult, SkillResult
    from fh_agent.verifier.schemas import VerifierResult


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

    def append_action_result(
        self,
        result: "ActionResult",
        *,
        skill_name: str,
        step_index: int,
        before_observation_id: str | None,
        after_observation_id: str | None,
        before_evidence_ids: Iterable[str] = (),
        after_evidence_ids: Iterable[str] = (),
    ) -> EventRecord:
        """Append one canonical action attempt with local transition references."""
        if step_index < 0:
            msg = "step_index must be non-negative"
            raise ValueError(msg)

        return self.append(
            "action_result",
            payload={
                "skill_name": skill_name,
                "step_index": step_index,
                "before_observation_id": before_observation_id,
                "after_observation_id": after_observation_id,
                "before_evidence_ids": list(before_evidence_ids),
                "after_evidence_ids": list(after_evidence_ids),
                "action_result": result.model_dump(mode="json"),
            },
            evidence_ids=result.evidence_ids,
        )

    def append_manager_stop(
        self,
        result: "ManagerStopResult",
        *,
        skill_name: str,
        steps_taken: int,
    ) -> EventRecord:
        """Append one terminal Manager/runtime control condition."""
        if steps_taken < 0:
            msg = "steps_taken must be non-negative"
            raise ValueError(msg)

        return self.append(
            "manager_stop",
            payload={
                "skill_name": skill_name,
                "steps_taken": steps_taken,
                "manager_stop": result.model_dump(mode="json"),
            },
            evidence_ids=result.evidence_ids,
        )

    def append_verifier_result(
        self,
        result: "VerifierResult",
        *,
        skill_name: str,
        steps_taken: int,
        before_observation_id: str | None,
        after_observation_id: str | None,
    ) -> EventRecord:
        """Append one canonical verifier outcome with its local evaluation context."""
        if steps_taken < 0:
            msg = "steps_taken must be non-negative"
            raise ValueError(msg)

        return self.append(
            "verifier_result",
            payload={
                "skill_name": skill_name,
                "steps_taken": steps_taken,
                "before_observation_id": before_observation_id,
                "after_observation_id": after_observation_id,
                "verifier_result": result.model_dump(mode="json"),
            },
            evidence_ids=result.evidence_ids,
        )

    def append_verified_reward(
        self,
        reward: "VerifiedRewardBreakdown",
        *,
        skill_name: str,
        verifier_event_id: str,
    ) -> EventRecord:
        """Append a reward derived from one canonical verifier outcome."""
        if not verifier_event_id:
            msg = "verifier_event_id must be non-empty"
            raise ValueError(msg)

        return self.append(
            "verified_reward",
            payload={
                "skill_name": skill_name,
                "verifier_event_id": verifier_event_id,
                "verified_reward": reward.model_dump(mode="json"),
            },
            evidence_ids=reward.verifier_result.evidence_ids,
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
