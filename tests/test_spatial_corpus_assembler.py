from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from fh_agent.evals.spatial_corpus_assembler import (
    SpatialCorpusSequenceSource,
    assemble_spatial_perception_corpus,
)
from fh_agent.perception.screen_capture import ScreenFrame


def write_ppm(root: Path, relative_path: str, *, width: int = 2, height: int = 1) -> str:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = sha256(relative_path.encode("utf-8")).digest()[:3]
    path.write_bytes(
        ScreenFrame(
            width=width,
            height=height,
            rgb=rgb * width * height,
            captured_at=datetime(2026, 8, 24, tzinfo=UTC),
        ).to_ppm_bytes()
    )
    return sha256(path.read_bytes()).hexdigest()


def assemble(root: Path):
    return assemble_spatial_perception_corpus(
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


def test_sequence_assembly_is_deterministic_and_uses_sequence_level_splits(tmp_path: Path) -> None:
    write_ppm(tmp_path, "sequence-a/frame-10.ppm")
    write_ppm(tmp_path, "sequence-a/frame-02.ppm")
    write_ppm(tmp_path, "sequence-b/frame-00.ppm")

    first = assemble(tmp_path)
    second = assemble(tmp_path)

    assert first == second
    assert [sequence.sequence_id for sequence in first.sequences] == ["sequence-a", "sequence-b"]
    assert [frame.frame_index for frame in first.sequences[0].frames] == [0, 1]
    assert [frame.relative_frame_path for frame in first.sequences[0].frames] == [
        "sequence-a/frame-02.ppm",
        "sequence-a/frame-10.ppm",
    ]
    assert [sequence.split for sequence in first.sequences] == ["train", "test"]


def test_assembly_generates_deterministic_ids_hashes_dimensions_and_uncertain_annotations(
    tmp_path: Path,
) -> None:
    expected_hash = write_ppm(tmp_path, "sequence-a/frame.ppm", width=3, height=2)
    write_ppm(tmp_path, "sequence-b/frame.ppm")

    corpus = assemble(tmp_path)
    frame = corpus.sequences[0].frames[0]
    annotation = corpus.annotations.sequences[0].frames[0]

    assert frame.frame_id.startswith("frame-")
    assert frame.evidence_id.startswith("evidence-")
    assert frame.sha256 == expected_hash
    assert (frame.width, frame.height) == (3, 2)
    assert frame.relative_frame_path == "sequence-a/frame.ppm"
    assert annotation.frame_id == frame.frame_id
    assert annotation.evidence_id == frame.evidence_id
    assert annotation.status == "uncertain"


def test_assembly_requires_explicit_sequence_directories_and_splits(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        assemble_spatial_perception_corpus(
            tmp_path,
            corpus_id="visible-corpus",
            schema_version="1",
            corpus_version="0.1.0",
            annotation_dataset_version="0.1.0",
            sequence_sources=(
                SpatialCorpusSequenceSource(
                    sequence_id="sequence-a", relative_directory="missing", split="validation"
                ),
            ),
        )
