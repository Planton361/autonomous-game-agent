"""Typed, game-agnostic outcome contracts for independent verifiers."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VerifierStatus(StrEnum):
    """The closed set of canonical verifier outcomes."""

    SUCCESS = "success"
    PROGRESS = "progress"
    FAILURE = "failure"
    ABSTAIN = "abstain"


class FailureKind(StrEnum):
    """The closed, game-agnostic taxonomy for verified failures."""

    PERCEPTION_UNCERTAIN = "perception_uncertain"
    GROUNDING_FAILED = "grounding_failed"
    CAPABILITY_REJECTED = "capability_rejected"
    PLANNING_FAILED = "planning_failed"
    SKILL_FAILED = "skill_failed"
    NO_PROGRESS = "no_progress"
    TIMEOUT = "timeout"
    TARGET_LOST = "target_lost"
    SAFETY_INTERVENTION = "safety_intervention"
    FOCUS_LOST = "focus_lost"
    DEATH = "death"
    REPLAN_REQUIRED = "replan_required"
    CONTAMINATED = "contaminated"


class VerifierResult(BaseModel):
    """Independent verifier outcome with optional failure category and visible evidence links."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: VerifierStatus
    failure_kind: FailureKind | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def failure_kind_matches_status(self) -> "VerifierResult":
        if self.status is VerifierStatus.FAILURE and self.failure_kind is None:
            msg = "failure status requires a failure_kind"
            raise ValueError(msg)
        if self.status is not VerifierStatus.FAILURE and self.failure_kind is not None:
            msg = "only failure status may include a failure_kind"
            raise ValueError(msg)
        return self
