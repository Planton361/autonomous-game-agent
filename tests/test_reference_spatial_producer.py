from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fh_agent.evals.reference_spatial_producer import (
    SyntheticReferenceSpatialProducer,
    SyntheticReferenceSpatialProducerConfig,
)
from fh_agent.perception.screen_capture import ScreenFrame

PLAYER = (12, 34, 56)
SPRITE = (78, 90, 123)
BACKGROUND = (0, 0, 0)


def synthetic_frame(
    width: int,
    height: int,
    markers: dict[tuple[int, int], tuple[int, int, int]],
) -> ScreenFrame:
    pixels = [BACKGROUND] * (width * height)
    for (x, y), color in markers.items():
        pixels[y * width + x] = color
    return ScreenFrame(
        width=width,
        height=height,
        rgb=bytes(channel for pixel in pixels for channel in pixel),
        captured_at=datetime(2026, 8, 24, tzinfo=UTC),
    )


def producer() -> SyntheticReferenceSpatialProducer:
    return SyntheticReferenceSpatialProducer(
        SyntheticReferenceSpatialProducerConfig(player_marker=PLAYER, sprite_marker=SPRITE)
    )


def test_detects_player_marker_and_propagates_evidence() -> None:
    prediction = producer().predict(
        synthetic_frame(4, 3, {(1, 1): PLAYER}), evidence_id="frame-evidence"
    )

    assert prediction.player_prediction is not None
    assert prediction.player_prediction.screen_position == (1, 1)
    assert prediction.player_prediction.confidence == 1.0
    assert prediction.player_prediction.evidence_id == "frame-evidence"
    assert prediction.producer_name == "synthetic_reference_rgb_marker"
    assert prediction.producer_version == "1"


def test_detects_one_sprite_marker_component() -> None:
    prediction = producer().predict(
        synthetic_frame(4, 3, {(2, 1): SPRITE}), evidence_id="frame-evidence"
    )

    assert [sprite.screen_position for sprite in prediction.visible_sprites] == [(2, 1)]


def test_detects_connected_sprite_components_with_floor_centroids() -> None:
    prediction = producer().predict(
        synthetic_frame(
            6,
            4,
            {
                (0, 0): SPRITE,
                (1, 0): SPRITE,
                (2, 0): SPRITE,
                (2, 1): SPRITE,
                (5, 3): SPRITE,
            },
        ),
        evidence_id="frame-evidence",
    )

    assert [sprite.screen_position for sprite in prediction.visible_sprites] == [(1, 0), (5, 3)]
    assert all(sprite.confidence == 1.0 for sprite in prediction.visible_sprites)
    assert all(sprite.evidence_id == "frame-evidence" for sprite in prediction.visible_sprites)


def test_sprite_output_order_is_deterministic_and_contains_no_semantic_fields() -> None:
    frame = synthetic_frame(
        5,
        4,
        {(4, 0): SPRITE, (0, 3): SPRITE, (2, 1): SPRITE},
    )

    first = producer().predict(frame, evidence_id="frame-evidence")
    second = producer().predict(frame, evidence_id="frame-evidence")

    assert first == second
    assert [sprite.screen_position for sprite in first.visible_sprites] == [(4, 0), (2, 1), (0, 3)]
    assert set(first.visible_sprites[0].model_dump()) == {
        "screen_position",
        "visual_hash",
        "confidence",
        "evidence_id",
    }


def test_disconnected_player_markers_are_rejected_in_synthetic_fixture_data() -> None:
    frame = synthetic_frame(3, 1, {(0, 0): PLAYER, (2, 0): PLAYER})

    with pytest.raises(ValueError, match="more than one player marker"):
        producer().predict(frame, evidence_id="frame-evidence")


@pytest.mark.parametrize(
    "payload",
    [
        {"player_marker": PLAYER, "sprite_marker": PLAYER},
        {"player_marker": (256, 0, 0), "sprite_marker": SPRITE},
        {"player_marker": (0, 0), "sprite_marker": SPRITE},
    ],
)
def test_reference_marker_config_rejects_invalid_marker_colors(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SyntheticReferenceSpatialProducerConfig.model_validate(payload)
