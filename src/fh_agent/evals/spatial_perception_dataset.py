"""Offline, no-spoiler annotation contracts for spatial-perception benchmarks."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ScreenCoordinate = Annotated[int, Field(ge=0)]
ScreenPosition = tuple[ScreenCoordinate, ScreenCoordinate]
AnnotationStatus = Literal["usable", "uncertain", "exclude"]


class SpatialPerceptionFrameAnnotation(BaseModel):
    """Point-only visible annotations for one frame, without semantic object labels."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    frame_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    status: AnnotationStatus
    player_screen_position: ScreenPosition | None = None
    visible_sprite_positions: tuple[ScreenPosition, ...] = ()


class SpatialPerceptionSequence(BaseModel):
    """Ordered frame annotations retained for future sequence-aware benchmarks."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    sequence_id: str = Field(min_length=1)
    frames: tuple[SpatialPerceptionFrameAnnotation, ...]

    @model_validator(mode="after")
    def frame_ids_must_be_unique(self) -> "SpatialPerceptionSequence":
        frame_ids = [frame.frame_id for frame in self.frames]
        if len(frame_ids) != len(set(frame_ids)):
            msg = "frame_id values must be unique within a sequence"
            raise ValueError(msg)
        return self


class SpatialPerceptionDataset(BaseModel):
    """Versioned collection of point-only annotated frame sequences."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    dataset_version: str = Field(min_length=1)
    sequences: tuple[SpatialPerceptionSequence, ...]

    @model_validator(mode="after")
    def frame_ids_must_be_globally_unique(self) -> "SpatialPerceptionDataset":
        frame_ids = [frame.frame_id for sequence in self.sequences for frame in sequence.frames]
        if len(frame_ids) != len(set(frame_ids)):
            msg = "frame_id values must be unique within a dataset"
            raise ValueError(msg)
        return self
