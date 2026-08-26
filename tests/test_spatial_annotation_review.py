from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.evals.spatial_annotation_review import (
    SpatialAnnotationWorkflow,
    annotation_fingerprint,
    assess_spatial_corpus_readiness,
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


def write_ppm(root: Path, relative_path: str, *, rgb: bytes = b"\x01\x02\x03") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        ScreenFrame(
            width=2,
            height=1,
            rgb=rgb * 2,
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


def three_split_workflow(root: Path) -> SpatialAnnotationWorkflow:
    sources = []
    for index, split in enumerate(("train", "validation", "test"), start=1):
        sequence_id = f"sequence-{split}"
        write_ppm(root, f"{sequence_id}/00-reviewed.ppm", rgb=bytes((index, index, index)))
        write_ppm(
            root,
            f"{sequence_id}/01-unscored.ppm",
            rgb=bytes((index, index, index + 10)),
        )
        sources.append(
            SpatialCorpusSequenceSource(
                sequence_id=sequence_id,
                relative_directory=sequence_id,
                split=split,
            )
        )
    manifest = assemble_spatial_perception_corpus(
        root,
        corpus_id="visible-corpus",
        schema_version="1",
        corpus_version="0.1.0",
        annotation_dataset_version="0.1.0",
        sequence_sources=tuple(sources),
    )
    return SpatialAnnotationWorkflow(manifest=manifest)


def annotation_by_split(
    state: SpatialAnnotationWorkflow,
) -> dict[str, SpatialPerceptionFrameAnnotation]:
    annotations_by_sequence_id = {
        sequence.sequence_id: sequence.frames for sequence in state.manifest.annotations.sequences
    }
    return {
        sequence.split: annotations_by_sequence_id[sequence.sequence_id][0]
        for sequence in state.manifest.sequences
    }


def reviewed_usable_workflow(
    state: SpatialAnnotationWorkflow,
    *,
    omit_split: str | None = None,
) -> SpatialAnnotationWorkflow:
    revised = state
    for split, annotation in annotation_by_split(state).items():
        if split == omit_split:
            continue
        revised = record_spatial_annotation(
            revised,
            revised_annotation(annotation),
            overwrite=True,
        )
    for split, annotation in annotation_by_split(revised).items():
        if split == omit_split:
            continue
        revised = create_annotation_review(
            revised,
            frame_id=annotation.frame_id,
            status="passed",
            clock=lambda: datetime(2026, 8, 25, tzinfo=UTC),
        )
    return revised


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


def test_all_uncertain_corpus_is_not_freeze_ready_and_direct_freeze_cannot_bypass_gate(
    tmp_path: Path,
) -> None:
    state = three_split_workflow(tmp_path)
    integrity = validate_spatial_perception_corpus_files(state.manifest, tmp_path)
    readiness = assess_spatial_corpus_readiness(state, integrity)

    assert readiness.freeze_ready is False
    assert readiness.blocked_reasons == (
        "train_split_has_no_reviewed_usable_annotation",
        "validation_split_has_no_reviewed_usable_annotation",
        "test_split_has_no_reviewed_usable_annotation",
    )
    with pytest.raises(ValueError, match="train_split_has_no_reviewed_usable_annotation"):
        freeze_spatial_corpus(state, integrity)


@pytest.mark.parametrize("missing_split", ["train", "validation", "test"])
def test_missing_reviewed_usable_coverage_in_any_split_blocks_freeze(
    tmp_path: Path,
    missing_split: str,
) -> None:
    state = reviewed_usable_workflow(three_split_workflow(tmp_path), omit_split=missing_split)
    integrity = validate_spatial_perception_corpus_files(state.manifest, tmp_path)
    readiness = assess_spatial_corpus_readiness(state, integrity)

    assert readiness.freeze_ready is False
    assert f"{missing_split}_split_has_no_reviewed_usable_annotation" in readiness.blocked_reasons


def test_reviewed_usable_coverage_in_every_split_permits_uncertain_and_exclude_frames(
    tmp_path: Path,
) -> None:
    initial = three_split_workflow(tmp_path)
    excluded = (
        initial.manifest.annotations.sequences[0].frames[1].model_copy(update={"status": "exclude"})
    )
    with_excluded_frame = record_spatial_annotation(initial, excluded, overwrite=True)
    state = reviewed_usable_workflow(with_excluded_frame)
    integrity = validate_spatial_perception_corpus_files(state.manifest, tmp_path)
    readiness = assess_spatial_corpus_readiness(state, integrity)

    assert readiness.freeze_ready is True
    assert readiness.uncertain_annotation_count == 2
    assert readiness.exclude_annotation_count == 1
    assert readiness.usable_annotations_with_valid_passed_review == 3


def test_usable_annotation_without_current_passed_review_still_blocks_freeze(
    tmp_path: Path,
) -> None:
    state = three_split_workflow(tmp_path)
    usable = revised_annotation(annotation_by_split(state)["train"])
    state = record_spatial_annotation(state, usable, overwrite=True)
    integrity = validate_spatial_perception_corpus_files(state.manifest, tmp_path)
    readiness = assess_spatial_corpus_readiness(state, integrity)

    assert readiness.freeze_ready is False
    assert "usable_annotations_lack_valid_passed_review" in readiness.blocked_reasons


def test_ready_corpus_freezes_and_remains_immutable(tmp_path: Path) -> None:
    state = reviewed_usable_workflow(three_split_workflow(tmp_path))
    integrity = validate_spatial_perception_corpus_files(state.manifest, tmp_path)
    frozen = freeze_spatial_corpus(
        state,
        integrity,
        clock=lambda: datetime(2026, 8, 25, tzinfo=UTC),
    )

    assert frozen.freeze_record is not None
    assert frozen.freeze_record.corpus_fingerprint == frozen.manifest.fingerprint()
    assert len(frozen.freeze_record.split_fingerprint) == 64
    with pytest.raises(ValueError, match="frozen"):
        record_spatial_annotation(
            frozen,
            revised_annotation(annotation_by_split(frozen)["test"]),
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
