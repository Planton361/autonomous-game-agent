from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.evals.spatial_annotation_review import (
    SpatialAnnotationWorkflow,
    SpatialPerceptionCorpusFreezeRecord,
    record_spatial_annotation,
)
from fh_agent.evals.spatial_annotation_ui import (
    PpmDisplayTransform,
    SpatialAnnotationSession,
)
from fh_agent.evals.spatial_corpus_assembler import (
    SpatialCorpusSequenceSource,
    assemble_spatial_perception_corpus,
)
from fh_agent.evals.spatial_perception_dataset import SpatialPerceptionFrameAnnotation
from fh_agent.perception.screen_capture import ScreenFrame


def write_ppm(root: Path, relative_path: str, *, rgb: bytes) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        ScreenFrame(
            width=8,
            height=6,
            rgb=rgb * 48,
            captured_at=datetime(2026, 8, 31, tzinfo=UTC),
        ).to_ppm_bytes()
    )


def make_workflow(root: Path) -> SpatialAnnotationWorkflow:
    write_ppm(root, "sequence-b/01.ppm", rgb=b"\x01\x02\x03")
    write_ppm(root, "sequence-a/02.ppm", rgb=b"\x02\x03\x04")
    write_ppm(root, "sequence-a/01.ppm", rgb=b"\x03\x04\x05")
    manifest = assemble_spatial_perception_corpus(
        root,
        corpus_id="visible-corpus",
        schema_version="1",
        corpus_version="0.1.0",
        annotation_dataset_version="0.1.0",
        sequence_sources=(
            SpatialCorpusSequenceSource(
                sequence_id="sequence-b", relative_directory="sequence-b", split="test"
            ),
            SpatialCorpusSequenceSource(
                sequence_id="sequence-a", relative_directory="sequence-a", split="train"
            ),
        ),
    )
    return SpatialAnnotationWorkflow(manifest=manifest)


def current_annotation(session: SpatialAnnotationSession) -> SpatialPerceptionFrameAnnotation:
    return session.current.annotation


def test_native_coordinate_mapping_and_display_boundaries_are_explicit() -> None:
    transform = PpmDisplayTransform(
        original_width=4,
        original_height=3,
        display_x=10,
        display_y=20,
    )

    assert transform.display_to_original((10, 20)) == (0, 0)
    assert transform.display_to_original((13, 22)) == (3, 2)
    assert transform.display_to_original((14, 22)) is None
    assert transform.display_to_original((13, 23)) is None


def test_subsampled_coordinate_mapping_uses_original_ppm_pixels() -> None:
    transform = PpmDisplayTransform(
        original_width=8,
        original_height=6,
        subsample_factor=2,
        display_x=4,
        display_y=7,
    )

    assert (transform.display_width, transform.display_height) == (4, 3)
    assert transform.display_to_original((4, 7)) == (0, 0)
    assert transform.display_to_original((7, 9)) == (6, 4)


def test_subsample_mapping_clamps_the_final_partial_display_pixel_and_rejects_outside() -> None:
    transform = PpmDisplayTransform(original_width=5, original_height=5, subsample_factor=2)

    assert transform.display_to_original((2, 2)) == (4, 4)
    assert transform.display_to_original((-1, 0)) is None
    assert transform.display_to_original((3, 0)) is None
    assert transform.display_to_original((0, 3)) is None


def test_player_sprite_undo_and_removal_are_pure_local_annotation_edits(tmp_path: Path) -> None:
    session = SpatialAnnotationSession(make_workflow(tmp_path))

    session.set_player_point((1, 2))
    session.set_player_point((3, 4))
    assert current_annotation(session).player_screen_position == (3, 4)
    assert session.undo() is True
    assert current_annotation(session).player_screen_position == (1, 2)

    session.add_sprite_point((1, 1))
    session.add_sprite_point((2, 2))
    assert current_annotation(session).visible_sprite_positions == ((1, 1), (2, 2))
    session.remove_sprite_point()
    assert current_annotation(session).visible_sprite_positions == ((1, 1),)
    with pytest.raises(ValueError, match="original PPM"):
        session.add_sprite_point((8, 0))


def test_frame_traversal_is_deterministic_and_keeps_per_frame_drafts(tmp_path: Path) -> None:
    session = SpatialAnnotationSession(make_workflow(tmp_path))

    assert (session.current.sequence_id, session.current.frame_index) == ("sequence-a", 0)
    session.set_player_point((4, 4))
    assert session.next_frame() is True
    assert (session.current.sequence_id, session.current.frame_index) == ("sequence-a", 1)
    assert session.next_frame() is True
    assert (session.current.sequence_id, session.current.frame_index) == ("sequence-b", 0)
    assert session.next_frame() is False
    assert session.previous_frame() is True
    assert session.previous_frame() is True
    assert current_annotation(session).player_screen_position == (4, 4)


def test_existing_annotation_is_exposed_as_overlay_state_when_revisiting(tmp_path: Path) -> None:
    initial = make_workflow(tmp_path)
    annotation = initial.manifest.annotations.sequences[0].frames[0]
    revised = record_spatial_annotation(
        initial,
        SpatialPerceptionFrameAnnotation(
            frame_id=annotation.frame_id,
            evidence_id=annotation.evidence_id,
            status="usable",
            player_screen_position=(2, 3),
            visible_sprite_positions=((4, 5), (6, 1)),
        ),
        overwrite=True,
    )

    session = SpatialAnnotationSession(revised)

    assert session.current.annotation.status == "usable"
    assert session.current.annotation.player_screen_position == (2, 3)
    assert session.current.annotation.visible_sprite_positions == ((4, 5), (6, 1))


@pytest.mark.parametrize("status", ["usable", "uncertain", "exclude"])
def test_status_creation_remains_point_only(tmp_path: Path, status: str) -> None:
    session = SpatialAnnotationSession(make_workflow(tmp_path))

    session.set_status(status)  # type: ignore[arg-type]

    assert session.current.annotation.status == status


def test_save_persists_via_existing_annotation_domain_logic(tmp_path: Path) -> None:
    session = SpatialAnnotationSession(make_workflow(tmp_path))
    session.set_status("usable")
    session.set_player_point((2, 3))
    persisted: list[SpatialAnnotationWorkflow] = []

    saved = session.save_current(persisted.append)

    assert saved is session.workflow
    assert persisted == [saved]
    assert session.has_unsaved_changes is False
    assert saved.manifest.annotations.sequences[0].frames[0].status == "usable"
    assert saved.manifest.annotations.sequences[0].frames[0].player_screen_position == (2, 3)


def test_frozen_workflow_can_be_viewed_but_session_rejects_mutation(tmp_path: Path) -> None:
    initial = make_workflow(tmp_path)
    frozen = initial.model_copy(
        update={
            "freeze_record": SpatialPerceptionCorpusFreezeRecord(
                corpus_id="visible-corpus",
                corpus_version="0.1.0",
                schema_version="1",
                corpus_fingerprint="a" * 64,
                split_fingerprint="b" * 64,
                frozen_at=datetime(2026, 8, 31, tzinfo=UTC),
            )
        }
    )
    session = SpatialAnnotationSession(frozen)

    assert session.current.frame_id
    assert session.can_mutate is False
    with pytest.raises(ValueError, match="frozen"):
        session.set_status("usable")


def test_annotation_schema_has_no_semantic_fields_or_classes() -> None:
    assert set(SpatialPerceptionFrameAnnotation.model_fields) == {
        "frame_id",
        "evidence_id",
        "status",
        "player_screen_position",
        "visible_sprite_positions",
    }
    with pytest.raises(ValidationError, match="Extra inputs"):
        SpatialPerceptionFrameAnnotation.model_validate(
            {
                "frame_id": "frame-1",
                "evidence_id": "evidence-1",
                "status": "usable",
                "sprite_class": "forbidden",
            }
        )


def test_headless_session_logic_never_requires_a_desktop(tmp_path: Path) -> None:
    session = SpatialAnnotationSession(make_workflow(tmp_path))

    session.set_player_point((0, 0))
    session.add_sprite_point((1, 1))

    assert session.current.annotation.visible_sprite_positions == ((1, 1),)
