import pytest
from pydantic import ValidationError

from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
    SpatialPerceptionSequence,
)


def frame(
    frame_id: str,
    *,
    status: str = "usable",
) -> SpatialPerceptionFrameAnnotation:
    return SpatialPerceptionFrameAnnotation(
        frame_id=frame_id,
        evidence_id=f"evidence-{frame_id}",
        status=status,
        player_screen_position=(5, 6),
        visible_sprite_positions=((10, 20),),
    )


def test_dataset_represents_ordered_frame_sequences_without_semantic_labels() -> None:
    dataset = SpatialPerceptionDataset(
        dataset_version="synthetic-v1",
        sequences=(
            SpatialPerceptionSequence(
                sequence_id="sequence-1",
                frames=(frame("frame-1"), frame("frame-2", status="uncertain")),
            ),
        ),
    )

    assert [item.frame_id for item in dataset.sequences[0].frames] == ["frame-1", "frame-2"]
    assert dataset.sequences[0].frames[1].status == "uncertain"


def test_frame_ids_must_be_unique_within_sequence_and_dataset() -> None:
    with pytest.raises(ValidationError, match="unique within a sequence"):
        SpatialPerceptionSequence(
            sequence_id="sequence-1",
            frames=(frame("frame-1"), frame("frame-1")),
        )
    with pytest.raises(ValidationError, match="unique within a dataset"):
        SpatialPerceptionDataset(
            dataset_version="synthetic-v1",
            sequences=(
                SpatialPerceptionSequence(sequence_id="sequence-1", frames=(frame("frame-1"),)),
                SpatialPerceptionSequence(sequence_id="sequence-2", frames=(frame("frame-1"),)),
            ),
        )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "frame_id": "frame-1",
            "evidence_id": "evidence-1",
            "status": "usable",
            "visible_sprite_positions": ((-1, 2),),
        },
        {
            "frame_id": "frame-1",
            "evidence_id": "evidence-1",
            "status": "invalid",
        },
        {
            "frame_id": "frame-1",
            "evidence_id": "evidence-1",
            "status": "usable",
            "enemy_label": "not allowed",
        },
    ],
)
def test_invalid_annotations_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SpatialPerceptionFrameAnnotation.model_validate(payload)
