"""Typed terminal control stops owned by the Manager/runtime layer."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.verifier.schemas import FailureKind


class ManagerStopResult(BaseModel):
    """A terminal Manager/runtime control condition, separate from verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_kind: FailureKind
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    trigger_event_id: str | None = None

    @field_validator("trigger_event_id")
    @classmethod
    def trigger_event_id_must_not_be_empty(cls, value: str | None) -> str | None:
        if value == "":
            msg = "trigger_event_id must be non-empty when provided"
            raise ValueError(msg)
        return value
