from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ScreenCoordinate = Annotated[int, Field(ge=0)]
ScreenPosition = tuple[ScreenCoordinate, ScreenCoordinate]
EvidenceId = Annotated[str, Field(min_length=1)]
EvidenceIds = Annotated[tuple[EvidenceId, ...], Field(min_length=1)]

TargetType = Literal["visible_screen_point", "visible_object"]
GroundingStatus = Literal["grounded", "grounding_failed"]
GroundingFailureReason = Literal[
    "no_visible_candidate",
    "ambiguous_candidates",
    "insufficient_evidence",
    "insufficient_confidence",
    "unsupported_target_type",
    "stale_evidence",
]


class _GroundedTargetBase(BaseModel):
    """Shared visible-evidence fields for an executable Manager target."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    target_id: str = Field(min_length=1)
    target_type: TargetType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: EvidenceIds


class VisibleScreenPointTarget(_GroundedTargetBase):
    """A non-semantic point grounded in visible screen coordinates."""

    target_type: Literal["visible_screen_point"] = "visible_screen_point"
    screen_position: ScreenPosition


class VisibleObjectTarget(_GroundedTargetBase):
    """A visible object reference without inferred game semantics."""

    target_type: Literal["visible_object"] = "visible_object"
    screen_position: ScreenPosition
    visual_hash: str | None = Field(default=None, min_length=1)


GroundedTarget = Annotated[
    VisibleScreenPointTarget | VisibleObjectTarget,
    Field(discriminator="target_type"),
]


class GroundingResult(BaseModel):
    """Auditable outcome of a grounding attempt, without grounding behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: GroundingStatus
    target: GroundedTarget | None = None
    failure_reason: GroundingFailureReason | None = None
    evidence_ids: tuple[EvidenceId, ...] = ()

    @model_validator(mode="after")
    def enforce_status_contract(self) -> "GroundingResult":
        if self.status == "grounded":
            if self.target is None:
                msg = "grounded result requires a target"
                raise ValueError(msg)
            if self.failure_reason is not None:
                msg = "grounded result must not contain a failure_reason"
                raise ValueError(msg)
            return self

        if self.target is not None:
            msg = "grounding_failed result must not contain a target"
            raise ValueError(msg)
        if self.failure_reason is None:
            msg = "grounding_failed result requires a failure_reason"
            raise ValueError(msg)
        return self
