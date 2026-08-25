from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fh_agent.observation.schemas import VisibleSprite
from fh_agent.perception.screen_capture import ScreenFrame
from fh_agent.perception.spatial_producer import (
    PlayerScreenPositionPrediction,
    SpatialPerceptionOutput,
    SpatialPerceptionProducer,
)


def frame() -> ScreenFrame:
    return ScreenFrame(
        width=1,
        height=1,
        rgb=b"\x00\x00\x00",
        captured_at=datetime(2026, 5, 16, tzinfo=UTC),
    )


def output(*, evidence_id: str = "shot-1") -> SpatialPerceptionOutput:
    return SpatialPerceptionOutput(
        producer_name="synthetic-spatial-producer",
        producer_version="0.1",
        evidence_id=evidence_id,
        player_prediction=PlayerScreenPositionPrediction(
            screen_position=(5, 6),
            confidence=0.9,
            evidence_id=evidence_id,
        ),
        visible_sprites=(
            VisibleSprite(
                screen_position=(10, 20),
                confidence=0.8,
                evidence_id=evidence_id,
            ),
        ),
    )


def test_spatial_perception_output_uses_canonical_visible_sprites() -> None:
    prediction = output()

    assert prediction.producer_name == "synthetic-spatial-producer"
    assert prediction.visible_sprites[0].screen_position == (10, 20)
    assert prediction.visible_sprites[0].evidence_id == "shot-1"


def test_producer_protocol_accepts_a_frame_and_evidence_id() -> None:
    class StaticSpatialProducer:
        def predict(
            self, captured_frame: ScreenFrame, *, evidence_id: str
        ) -> SpatialPerceptionOutput:
            assert captured_frame == frame()
            return output(evidence_id=evidence_id)

    producer: SpatialPerceptionProducer = StaticSpatialProducer()

    assert producer.predict(frame(), evidence_id="shot-1") == output()


@pytest.mark.parametrize(
    "payload",
    [
        {
            "producer_name": "producer",
            "producer_version": "1",
            "evidence_id": "shot-1",
            "visible_sprites": [{"screen_position": (10, 20), "evidence_id": "shot-1"}],
        },
        {
            "producer_name": "producer",
            "producer_version": "1",
            "evidence_id": "shot-1",
            "visible_sprites": [
                {
                    "screen_position": (-1, 20),
                    "confidence": 0.8,
                    "evidence_id": "shot-1",
                }
            ],
        },
        {
            "producer_name": "producer",
            "producer_version": "1",
            "evidence_id": "shot-1",
            "visible_sprites": [
                {
                    "screen_position": (10, 20),
                    "confidence": 0.8,
                    "evidence_id": "shot-2",
                }
            ],
        },
    ],
)
def test_output_rejects_invalid_sprite_prediction_contract(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SpatialPerceptionOutput.model_validate(payload)


def test_player_prediction_rejects_invalid_confidence_and_coordinates() -> None:
    with pytest.raises(ValidationError):
        PlayerScreenPositionPrediction(
            screen_position=(-1, 0), confidence=0.8, evidence_id="shot-1"
        )
    with pytest.raises(ValidationError):
        PlayerScreenPositionPrediction(screen_position=(1, 0), confidence=1.1, evidence_id="shot-1")
