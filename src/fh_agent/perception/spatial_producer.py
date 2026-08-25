"""Contracts for screen-derived spatial predictions without semantic labels."""

from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fh_agent.observation.schemas import VisibleSprite
from fh_agent.perception.screen_capture import ScreenFrame

ScreenCoordinate = Annotated[int, Field(ge=0)]
ScreenPosition = tuple[ScreenCoordinate, ScreenCoordinate]


class PlayerScreenPositionPrediction(BaseModel):
    """One visible player screen-position prediction for a single evidence item."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    screen_position: ScreenPosition
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_id: str = Field(min_length=1)


class SpatialPerceptionOutput(BaseModel):
    """Canonical spatial predictions for one visible screen frame."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    producer_name: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    player_prediction: PlayerScreenPositionPrediction | None = None
    visible_sprites: tuple[VisibleSprite, ...] = ()

    @model_validator(mode="after")
    def validate_visible_prediction_contract(self) -> "SpatialPerceptionOutput":
        if (
            self.player_prediction is not None
            and self.player_prediction.evidence_id != self.evidence_id
        ):
            msg = "player_prediction evidence_id must match output evidence_id"
            raise ValueError(msg)
        for sprite in self.visible_sprites:
            if sprite.confidence is None:
                msg = "visible sprite predictions require confidence"
                raise ValueError(msg)
            if sprite.evidence_id != self.evidence_id:
                msg = "visible sprite evidence_id must match output evidence_id"
                raise ValueError(msg)
            if any(coordinate < 0 for coordinate in sprite.screen_position):
                msg = "visible sprite predictions require non-negative screen coordinates"
                raise ValueError(msg)
        return self


class SpatialPerceptionProducer(Protocol):
    """Produce canonical spatial predictions from one visible screen frame."""

    def predict(self, frame: ScreenFrame, *, evidence_id: str) -> SpatialPerceptionOutput:
        """Return predictions tied to the supplied visible evidence_id."""
