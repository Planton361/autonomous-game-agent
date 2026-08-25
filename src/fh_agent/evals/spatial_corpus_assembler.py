"""Deterministic assembly of externally stored PPM sequences into corpus contracts."""

from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.evals.spatial_perception_corpus import (
    CorpusSplit,
    SpatialPerceptionCorpusFrame,
    SpatialPerceptionCorpusManifest,
    SpatialPerceptionCorpusSequence,
)
from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
    SpatialPerceptionSequence,
)
from fh_agent.perception.visual_hash import load_ppm_frame


class SpatialCorpusSequenceSource(BaseModel):
    """One explicit source directory and its sequence-level split assignment."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    sequence_id: str = Field(min_length=1)
    relative_directory: str = Field(min_length=1)
    split: CorpusSplit

    @field_validator("relative_directory")
    @classmethod
    def source_directory_must_be_relative(cls, value: str) -> str:
        posix_path = PurePosixPath(value)
        windows_path = PureWindowsPath(value)
        if posix_path.is_absolute() or windows_path.is_absolute() or ".." in posix_path.parts:
            msg = "relative_directory must be relative to the corpus root"
            raise ValueError(msg)
        if ".." in windows_path.parts:
            msg = "relative_directory must be relative to the corpus root"
            raise ValueError(msg)
        return value


def assemble_spatial_perception_corpus(
    corpus_root: Path,
    *,
    corpus_id: str,
    schema_version: str,
    corpus_version: str,
    annotation_dataset_version: str,
    sequence_sources: tuple[SpatialCorpusSequenceSource, ...],
) -> SpatialPerceptionCorpusManifest:
    """Build a deterministic corpus with uncertain point-annotation placeholders.

    Placeholder annotations preserve the existing annotation schema and cannot be
    scored until a reviewer explicitly revises their status and point fields.
    """

    if not sequence_sources:
        msg = "at least one explicit sequence source is required"
        raise ValueError(msg)

    corpus_sequences = tuple(
        _assemble_sequence(corpus_root, source)
        for source in sorted(sequence_sources, key=lambda item: item.sequence_id)
    )
    annotations = SpatialPerceptionDataset(
        dataset_version=annotation_dataset_version,
        sequences=tuple(
            SpatialPerceptionSequence(
                sequence_id=sequence.sequence_id,
                frames=tuple(
                    SpatialPerceptionFrameAnnotation(
                        frame_id=frame.frame_id,
                        evidence_id=frame.evidence_id,
                        status="uncertain",
                    )
                    for frame in sequence.ordered_frames()
                ),
            )
            for sequence in corpus_sequences
        ),
    )
    return SpatialPerceptionCorpusManifest(
        corpus_id=corpus_id,
        schema_version=schema_version,
        corpus_version=corpus_version,
        sequences=corpus_sequences,
        annotations=annotations,
    )


def _assemble_sequence(
    corpus_root: Path,
    source: SpatialCorpusSequenceSource,
) -> SpatialPerceptionCorpusSequence:
    sequence_directory = corpus_root / source.relative_directory
    if not sequence_directory.is_dir():
        msg = f"sequence directory does not exist: {source.relative_directory}"
        raise FileNotFoundError(msg)

    ppm_paths = tuple(
        sorted(
            (
                path
                for path in sequence_directory.iterdir()
                if path.is_file() and path.suffix == ".ppm"
            ),
            key=lambda path: path.name,
        )
    )
    if not ppm_paths:
        msg = f"sequence directory contains no PPM files: {source.relative_directory}"
        raise ValueError(msg)

    frames = tuple(
        _assemble_frame(corpus_root, source.sequence_id, path, frame_index)
        for frame_index, path in enumerate(ppm_paths)
    )
    return SpatialPerceptionCorpusSequence(
        sequence_id=source.sequence_id,
        split=source.split,
        frames=frames,
    )


def _assemble_frame(
    corpus_root: Path,
    sequence_id: str,
    path: Path,
    frame_index: int,
) -> SpatialPerceptionCorpusFrame:
    relative_path = path.relative_to(corpus_root).as_posix()
    frame_hash = _sha256_file(path)
    decoded_frame = load_ppm_frame(path)
    return SpatialPerceptionCorpusFrame(
        frame_id=_stable_identifier("frame", sequence_id, relative_path, frame_hash),
        sequence_id=sequence_id,
        relative_frame_path=relative_path,
        sha256=frame_hash,
        width=decoded_frame.width,
        height=decoded_frame.height,
        evidence_id=_stable_identifier("evidence", sequence_id, relative_path, frame_hash),
        frame_index=frame_index,
        captured_at=None,
    )


def _stable_identifier(prefix: str, *parts: str) -> str:
    payload = "\0".join(parts).encode("utf-8")
    return f"{prefix}-{sha256(payload).hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
