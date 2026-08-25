from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.evals.spatial_perception_corpus import (
    SpatialPerceptionCorpusFrame,
    SpatialPerceptionCorpusManifest,
    SpatialPerceptionCorpusSequence,
    validate_spatial_perception_corpus_files,
)
from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
    SpatialPerceptionSequence,
)
from fh_agent.perception.screen_capture import ScreenFrame


def write_ppm(root: Path, relative_path: str, *, width: int = 2, height: int = 1) -> str:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = ScreenFrame(
        width=width,
        height=height,
        rgb=bytes([10, 20, 30]) * width * height,
        captured_at=datetime(2026, 8, 24, tzinfo=UTC),
    )
    path.write_bytes(frame.to_ppm_bytes())
    from hashlib import sha256

    return sha256(path.read_bytes()).hexdigest()


def corpus_frame(
    frame_id: str,
    sequence_id: str,
    relative_path: str,
    frame_hash: str,
    *,
    frame_index: int = 0,
    width: int = 2,
    height: int = 1,
) -> SpatialPerceptionCorpusFrame:
    return SpatialPerceptionCorpusFrame(
        frame_id=frame_id,
        sequence_id=sequence_id,
        relative_frame_path=relative_path,
        sha256=frame_hash,
        width=width,
        height=height,
        evidence_id=f"evidence-{frame_id}",
        frame_index=frame_index,
    )


def annotation(
    frame: SpatialPerceptionCorpusFrame, *, status: str = "usable"
) -> SpatialPerceptionFrameAnnotation:
    return SpatialPerceptionFrameAnnotation(
        frame_id=frame.frame_id,
        evidence_id=frame.evidence_id,
        status=status,
        visible_sprite_positions=((1, 0),),
    )


def manifest(
    *sequences: SpatialPerceptionCorpusSequence,
    annotations: SpatialPerceptionDataset | None = None,
) -> SpatialPerceptionCorpusManifest:
    if annotations is None:
        annotations = SpatialPerceptionDataset(
            dataset_version="annotations-v1",
            sequences=tuple(
                SpatialPerceptionSequence(
                    sequence_id=sequence.sequence_id,
                    frames=tuple(annotation(frame) for frame in sequence.frames),
                )
                for sequence in sequences
            ),
        )
    return SpatialPerceptionCorpusManifest(
        corpus_id="visible-spatial-corpus",
        schema_version="1",
        corpus_version="1.0.0",
        sequences=sequences,
        annotations=annotations,
    )


def test_valid_corpus_and_file_integrity_pass(tmp_path: Path) -> None:
    frame_hash = write_ppm(tmp_path, "frames/sequence-a/frame-0.ppm")
    frame = corpus_frame("frame-a", "sequence-a", "frames/sequence-a/frame-0.ppm", frame_hash)
    corpus = manifest(
        SpatialPerceptionCorpusSequence(sequence_id="sequence-a", split="train", frames=(frame,))
    )

    result = validate_spatial_perception_corpus_files(corpus, tmp_path)

    assert result.valid is True
    assert result.checked_frame_count == 1
    assert result.issues == ()
    assert len(result.manifest_fingerprint) == 64


def test_duplicate_frame_ids_are_rejected() -> None:
    frame = corpus_frame("frame-a", "sequence-a", "a.ppm", "a" * 64)
    duplicate = corpus_frame("frame-a", "sequence-a", "b.ppm", "b" * 64, frame_index=1)
    sequence = SpatialPerceptionCorpusSequence(
        sequence_id="sequence-a", split="train", frames=(frame, duplicate)
    )
    annotations = SpatialPerceptionDataset(
        dataset_version="annotations-v1",
        sequences=(
            SpatialPerceptionSequence(sequence_id="sequence-a", frames=(annotation(frame),)),
        ),
    )

    with pytest.raises(ValidationError, match="globally unique"):
        manifest(sequence, annotations=annotations)


@pytest.mark.parametrize("path", ["/absolute/frame.ppm", "C:\\corpus\\frame.ppm", "../escape.ppm"])
def test_absolute_or_root_escaping_frame_paths_are_rejected(path: str) -> None:
    with pytest.raises(ValidationError, match="corpus root"):
        corpus_frame("frame-a", "sequence-a", path, "a" * 64)


def test_missing_files_are_reported_deterministically(tmp_path: Path) -> None:
    frame = corpus_frame("frame-a", "sequence-a", "missing.ppm", "a" * 64)
    corpus = manifest(
        SpatialPerceptionCorpusSequence(sequence_id="sequence-a", split="train", frames=(frame,))
    )

    result = validate_spatial_perception_corpus_files(corpus, tmp_path)

    assert result.valid is False
    assert [(issue.frame_id, issue.code) for issue in result.issues] == [
        ("frame-a", "missing_file")
    ]


def test_wrong_file_sha_is_reported(tmp_path: Path) -> None:
    write_ppm(tmp_path, "frame.ppm")
    frame = corpus_frame("frame-a", "sequence-a", "frame.ppm", "a" * 64)
    corpus = manifest(
        SpatialPerceptionCorpusSequence(sequence_id="sequence-a", split="train", frames=(frame,))
    )

    result = validate_spatial_perception_corpus_files(corpus, tmp_path)

    assert [issue.code for issue in result.issues] == ["sha256_mismatch"]


def test_wrong_dimensions_are_reported(tmp_path: Path) -> None:
    frame_hash = write_ppm(tmp_path, "frame.ppm", width=2, height=1)
    frame = corpus_frame("frame-a", "sequence-a", "frame.ppm", frame_hash, width=3, height=1)
    corpus = manifest(
        SpatialPerceptionCorpusSequence(sequence_id="sequence-a", split="train", frames=(frame,))
    )

    result = validate_spatial_perception_corpus_files(corpus, tmp_path)

    assert [issue.code for issue in result.issues] == ["dimension_mismatch"]


def test_sequence_split_leakage_is_rejected() -> None:
    first = corpus_frame("frame-a", "sequence-a", "a.ppm", "a" * 64)
    second = corpus_frame("frame-b", "sequence-a", "b.ppm", "b" * 64)
    annotations = SpatialPerceptionDataset(
        dataset_version="annotations-v1",
        sequences=(
            SpatialPerceptionSequence(sequence_id="sequence-a", frames=(annotation(first),)),
        ),
    )

    with pytest.raises(ValidationError, match="only one corpus split"):
        manifest(
            SpatialPerceptionCorpusSequence(
                sequence_id="sequence-a", split="train", frames=(first,)
            ),
            SpatialPerceptionCorpusSequence(
                sequence_id="sequence-a", split="test", frames=(second,)
            ),
            annotations=annotations,
        )


def test_exact_content_cross_split_leakage_is_rejected() -> None:
    first = corpus_frame("frame-a", "sequence-a", "a.ppm", "a" * 64)
    second = corpus_frame("frame-b", "sequence-b", "b.ppm", "a" * 64)

    with pytest.raises(ValidationError, match="sha256"):
        manifest(
            SpatialPerceptionCorpusSequence(
                sequence_id="sequence-a", split="train", frames=(first,)
            ),
            SpatialPerceptionCorpusSequence(
                sequence_id="sequence-b", split="validation", frames=(second,)
            ),
        )


def test_frame_ordering_is_deterministic_and_frame_indices_are_unique() -> None:
    first = corpus_frame("frame-1", "sequence-a", "one.ppm", "a" * 64, frame_index=1)
    second = corpus_frame("frame-0", "sequence-a", "zero.ppm", "b" * 64, frame_index=0)
    corpus = manifest(
        SpatialPerceptionCorpusSequence(
            sequence_id="sequence-a", split="train", frames=(first, second)
        )
    )

    assert [frame.frame_id for frame in corpus.iter_frames()] == ["frame-0", "frame-1"]

    duplicate_index = corpus_frame("frame-2", "sequence-a", "two.ppm", "c" * 64, frame_index=0)
    with pytest.raises(ValidationError, match="frame_index"):
        SpatialPerceptionCorpusSequence(
            sequence_id="sequence-a", split="train", frames=(second, duplicate_index)
        )


def test_invalid_annotation_references_are_rejected() -> None:
    frame = corpus_frame("frame-a", "sequence-a", "a.ppm", "a" * 64)
    annotations = SpatialPerceptionDataset(
        dataset_version="annotations-v1",
        sequences=(
            SpatialPerceptionSequence(
                sequence_id="sequence-a",
                frames=(
                    SpatialPerceptionFrameAnnotation(
                        frame_id="other-frame",
                        evidence_id="evidence-other-frame",
                        status="usable",
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(ValidationError, match="frame_ids"):
        manifest(
            SpatialPerceptionCorpusSequence(
                sequence_id="sequence-a", split="train", frames=(frame,)
            ),
            annotations=annotations,
        )


def test_uncertain_and_exclude_annotations_are_retained() -> None:
    uncertain = corpus_frame("frame-uncertain", "sequence-a", "u.ppm", "a" * 64)
    excluded = corpus_frame("frame-exclude", "sequence-a", "e.ppm", "b" * 64, frame_index=1)
    annotations = SpatialPerceptionDataset(
        dataset_version="annotations-v1",
        sequences=(
            SpatialPerceptionSequence(
                sequence_id="sequence-a",
                frames=(
                    annotation(uncertain, status="uncertain"),
                    annotation(excluded, status="exclude"),
                ),
            ),
        ),
    )
    corpus = manifest(
        SpatialPerceptionCorpusSequence(
            sequence_id="sequence-a", split="test", frames=(uncertain, excluded)
        ),
        annotations=annotations,
    )

    assert [item.status for item in corpus.annotations.sequences[0].frames] == [
        "uncertain",
        "exclude",
    ]


@pytest.mark.parametrize("extra_field", ["enemy_label", "map_id"])
def test_semantic_and_hidden_state_fields_are_rejected(extra_field: str) -> None:
    payload = {
        "frame_id": "frame-a",
        "sequence_id": "sequence-a",
        "relative_frame_path": "frame.ppm",
        "sha256": "a" * 64,
        "width": 2,
        "height": 1,
        "evidence_id": "evidence-frame-a",
        "frame_index": 0,
        extra_field: "forbidden",
    }

    with pytest.raises(ValidationError, match="Extra inputs"):
        SpatialPerceptionCorpusFrame.model_validate(payload)


def test_manifest_fingerprint_is_deterministic_independent_of_sequence_order() -> None:
    first = corpus_frame("frame-a", "sequence-a", "a.ppm", "a" * 64)
    second = corpus_frame("frame-b", "sequence-b", "b.ppm", "b" * 64)
    sequence_a = SpatialPerceptionCorpusSequence(
        sequence_id="sequence-a", split="train", frames=(first,)
    )
    sequence_b = SpatialPerceptionCorpusSequence(
        sequence_id="sequence-b", split="test", frames=(second,)
    )
    annotations = SpatialPerceptionDataset(
        dataset_version="annotations-v1",
        sequences=(
            SpatialPerceptionSequence(sequence_id="sequence-b", frames=(annotation(second),)),
            SpatialPerceptionSequence(sequence_id="sequence-a", frames=(annotation(first),)),
        ),
    )

    first_manifest = manifest(sequence_a, sequence_b, annotations=annotations)
    second_manifest = manifest(sequence_b, sequence_a, annotations=annotations)

    assert first_manifest.canonical_json() == second_manifest.canonical_json()
    assert first_manifest.fingerprint() == second_manifest.fingerprint()
