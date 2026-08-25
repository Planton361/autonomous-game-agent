from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.evals.spatial_annotation_review import (
    SpatialAnnotationWorkflow,
    annotation_fingerprint,
    create_annotation_review,
    freeze_spatial_corpus,
    record_spatial_annotation,
    review_is_current,
)
from fh_agent.evals.spatial_corpus_assembler import (
    SpatialCorpusSequenceSource,
    assemble_spatial_perception_corpus,
)
from fh_agent.evals.spatial_perception_corpus import validate_spatial_perception_corpus_files
from fh_agent.evals.spatial_perception_dataset import SpatialPerceptionFrameAnnotation
from fh_agent.perception.screen_capture import ScreenFrame


def write_ppm(root: Path, relative_path: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        ScreenFrame(
            width=2,
            height=1,
            rgb=b"\x01\x02\x03\x04\x05\x06",
            captured_at=datetime(2026, 8, 24, tzinfo=UTC),
        ).to_ppm_bytes()
    )


def workflow(root: Path) -> SpatialAnnotationWorkflow:
    write_ppm(root, "sequence-a/frame.ppm")
    manifest = assemble_spatial_perception_corpus(
        root,
        corpus_id="visible-corpus",
        schema_version="1",
        corpus_version="0.1.0",
        annotation_dataset_version="0.1.0",
        sequence_sources=(
            SpatialCorpusSequenceSource(
                sequence_id="sequence-a", relative_directory="sequence-a", split="test"
            ),
        ),
    )
    return SpatialAnnotationWorkflow(manifest=manifest)


def revised_annotation(
    current: SpatialPerceptionFrameAnnotation,
) -> SpatialPerceptionFrameAnnotation:
    return SpatialPerceptionFrameAnnotation(
        frame_id=current.frame_id,
        evidence_id=current.evidence_id,
        status="usable",
        player_screen_position=(0, 0),
        visible_sprite_positions=((1, 0),),
    )


def current_annotation(state: SpatialAnnotationWorkflow) -> SpatialPerceptionFrameAnnotation:
    return state.manifest.annotations.sequences[0].frames[0]


def test_annotation_recording_preserves_point_only_statuses_and_requires_explicit_overwrite(
    tmp_path: Path,
) -> None:
    state = workflow(tmp_path)
    replacement = revised_annotation(current_annotation(state))

    with pytest.raises(ValueError, match="overwrite=True"):
        record_spatial_annotation(state, replacement)

    revised = record_spatial_annotation(state, replacement, overwrite=True)

    assert current_annotation(revised).status == "usable"
    excluded_annotation = replacement.model_copy(update={"status": "exclude"})
    excluded = record_spatial_annotation(revised, excluded_annotation, overwrite=True)
    assert current_annotation(excluded).status == "exclude"
    assert current_annotation(excluded).visible_sprite_positions == ((1, 0),)


def test_annotation_fingerprint_is_deterministic_and_changes_with_content(tmp_path: Path) -> None:
    state = workflow(tmp_path)
    original = current_annotation(state)
    changed = revised_annotation(original)
    ordered_points = changed.model_copy(update={"visible_sprite_positions": ((0, 0), (1, 0))})
    reversed_points = changed.model_copy(update={"visible_sprite_positions": ((1, 0), (0, 0))})

    assert annotation_fingerprint(original) == annotation_fingerprint(original)
    assert annotation_fingerprint(original) != annotation_fingerprint(changed)
    assert annotation_fingerprint(ordered_points) == annotation_fingerprint(reversed_points)


def test_review_binds_to_exact_annotation_and_is_invalidated_by_revision(tmp_path: Path) -> None:
    initial = workflow(tmp_path)
    state = record_spatial_annotation(
        initial,
        revised_annotation(current_annotation(initial)),
        overwrite=True,
    )
    reviewed = create_annotation_review(
        state,
        frame_id=current_annotation(state).frame_id,
        status="passed",
        reviewer_id="reviewer-1",
        clock=lambda: datetime(2026, 8, 24, tzinfo=UTC),
    )
    review = reviewed.reviews[0]

    assert review.annotation_fingerprint == annotation_fingerprint(current_annotation(reviewed))
    assert review_is_current(review, reviewed.manifest) is True

    revised = record_spatial_annotation(
        reviewed,
        current_annotation(reviewed).model_copy(update={"visible_sprite_positions": ((0, 0),)}),
        overwrite=True,
    )

    assert review_is_current(review, revised.manifest) is False


def test_freeze_blocks_mutating_the_frozen_test_corpus_version(tmp_path: Path) -> None:
    state = workflow(tmp_path)
    integrity = validate_spatial_perception_corpus_files(state.manifest, tmp_path)
    frozen = freeze_spatial_corpus(
        state,
        integrity,
        clock=lambda: datetime(2026, 8, 24, tzinfo=UTC),
    )

    assert frozen.freeze_record is not None
    assert frozen.freeze_record.corpus_fingerprint == frozen.manifest.fingerprint()
    assert len(frozen.freeze_record.split_fingerprint) == 64
    with pytest.raises(ValueError, match="frozen"):
        record_spatial_annotation(
            frozen,
            revised_annotation(current_annotation(frozen)),
            overwrite=True,
        )


def test_semantic_and_hidden_state_annotation_fields_remain_impossible() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        SpatialPerceptionFrameAnnotation.model_validate(
            {
                "frame_id": "frame-1",
                "evidence_id": "evidence-1",
                "status": "usable",
                "enemy_label": "forbidden",
            }
        )
    with pytest.raises(ValidationError, match="Extra inputs"):
        SpatialPerceptionFrameAnnotation.model_validate(
            {
                "frame_id": "frame-1",
                "evidence_id": "evidence-1",
                "status": "usable",
                "map_id": "forbidden",
            }
        )
