"""Synthetic RGB-marker spatial producer for offline benchmark fixtures only."""

from collections.abc import Iterable
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fh_agent.observation.schemas import VisibleSprite
from fh_agent.perception.screen_capture import ScreenFrame
from fh_agent.perception.spatial_producer import (
    PlayerScreenPositionPrediction,
    SpatialPerceptionOutput,
)

RgbChannel = Annotated[int, Field(ge=0, le=255)]
RgbMarker = tuple[RgbChannel, RgbChannel, RgbChannel]


class SyntheticReferenceSpatialProducerConfig(BaseModel):
    """Exact RGB markers used only to make synthetic fixtures measurable."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    player_marker: RgbMarker = (255, 0, 255)
    sprite_marker: RgbMarker = (0, 255, 255)

    @model_validator(mode="after")
    def marker_colors_must_differ(self) -> "SyntheticReferenceSpatialProducerConfig":
        if self.player_marker == self.sprite_marker:
            msg = "player_marker and sprite_marker must differ"
            raise ValueError(msg)
        return self


class SyntheticReferenceSpatialProducer:
    """Detect exact synthetic RGB marker components without semantic interpretation.

    A confidence of ``1.0`` means that an exact fixture marker was found.  It is
    not a calibration claim for real screen-derived perception.
    """

    producer_name = "synthetic_reference_rgb_marker"
    producer_version = "1"

    def __init__(
        self,
        config: SyntheticReferenceSpatialProducerConfig | None = None,
    ) -> None:
        self.config = config or SyntheticReferenceSpatialProducerConfig()

    def predict(self, frame: ScreenFrame, *, evidence_id: str) -> SpatialPerceptionOutput:
        """Produce point-only predictions tied to the supplied visible evidence."""

        player_components = _marker_components(frame, self.config.player_marker)
        if len(player_components) > 1:
            msg = "synthetic frame contains more than one player marker component"
            raise ValueError(msg)

        player_prediction = (
            PlayerScreenPositionPrediction(
                screen_position=_component_centroid(player_components[0]),
                confidence=1.0,
                evidence_id=evidence_id,
            )
            if player_components
            else None
        )
        sprite_components = _marker_components(frame, self.config.sprite_marker)
        visible_sprites = tuple(
            VisibleSprite(
                screen_position=_component_centroid(component),
                confidence=1.0,
                evidence_id=evidence_id,
            )
            for component in sprite_components
        )
        return SpatialPerceptionOutput(
            producer_name=self.producer_name,
            producer_version=self.producer_version,
            evidence_id=evidence_id,
            player_prediction=player_prediction,
            visible_sprites=visible_sprites,
        )


ScreenPosition = tuple[int, int]


def _marker_components(
    frame: ScreenFrame, marker: RgbMarker
) -> tuple[tuple[ScreenPosition, ...], ...]:
    marker_positions = {
        (x, y)
        for y in range(frame.height)
        for x in range(frame.width)
        if _pixel_at(frame, x, y) == marker
    }
    components: list[tuple[ScreenPosition, ...]] = []
    while marker_positions:
        start = min(marker_positions, key=lambda position: (position[1], position[0]))
        marker_positions.remove(start)
        component = [start]
        frontier = [start]
        while frontier:
            x, y = frontier.pop()
            for neighbor in _four_neighbors(x, y):
                if neighbor in marker_positions:
                    marker_positions.remove(neighbor)
                    component.append(neighbor)
                    frontier.append(neighbor)
        components.append(tuple(component))

    return tuple(sorted(components, key=_component_sort_key))


def _pixel_at(frame: ScreenFrame, x: int, y: int) -> RgbMarker:
    offset = (y * frame.width + x) * 3
    return (frame.rgb[offset], frame.rgb[offset + 1], frame.rgb[offset + 2])


def _four_neighbors(x: int, y: int) -> Iterable[ScreenPosition]:
    return ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1))


def _component_centroid(component: tuple[ScreenPosition, ...]) -> ScreenPosition:
    """Return the floor of the arithmetic centroid to avoid rounding ambiguity."""

    size = len(component)
    return (
        sum(position[0] for position in component) // size,
        sum(position[1] for position in component) // size,
    )


def _component_sort_key(component: tuple[ScreenPosition, ...]) -> tuple[int, int, int, int]:
    centroid_x, centroid_y = _component_centroid(component)
    top_left_x, top_left_y = min(component, key=lambda position: (position[1], position[0]))
    return (centroid_y, centroid_x, top_left_y, top_left_x)
