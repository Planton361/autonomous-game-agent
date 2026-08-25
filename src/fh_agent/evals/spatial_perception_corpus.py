"""Versioned, no-spoiler contracts for offline spatial-perception corpora."""

import json
from collections.abc import Iterable
from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
)
from fh_agent.perception.visual_hash import load_ppm_frame

CorpusSplit = Literal["train", "validation", "test"]
CorpusIntegrityIssueCode = Literal[
    "missing_file",
    "sha256_mismatch",
    "frame_decode_failed",
    "dimension_mismatch",
]


class SpatialPerceptionCorpusFrame(BaseModel):
    """One externally stored visible frame, without semantic game-state metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    frame_id: str = Field(min_length=1)
    sequence_id: str = Field(min_length=1)
    relative_frame_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    evidence_id: str = Field(min_length=1)
    frame_index: int = Field(ge=0)
    captured_at: datetime | None = None

    @field_validator("relative_frame_path")
    @classmethod
    def frame_path_must_be_relative_to_corpus_root(cls, value: str) -> str:
        posix_path = PurePosixPath(value)
        windows_path = PureWindowsPath(value)
        if posix_path.is_absolute() or windows_path.is_absolute():
            msg = "relative_frame_path must be relative to the corpus root"
            raise ValueError(msg)
        if ".." in posix_path.parts or ".." in windows_path.parts:
            msg = "relative_frame_path must not escape the corpus root"
            raise ValueError(msg)
        return value

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            msg = "captured_at must be timezone-aware when supplied"
            raise ValueError(msg)
        return value


class SpatialPerceptionCorpusSequence(BaseModel):
    """A temporally ordered frame sequence assigned to exactly one dataset split."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    sequence_id: str = Field(min_length=1)
    split: CorpusSplit
    frames: tuple[SpatialPerceptionCorpusFrame, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sequence_frames(self) -> "SpatialPerceptionCorpusSequence":
        mismatched_sequence_ids = sorted(
            frame.frame_id for frame in self.frames if frame.sequence_id != self.sequence_id
        )
        if mismatched_sequence_ids:
            msg = "every corpus frame sequence_id must match its containing sequence"
            raise ValueError(msg)
        frame_indices = [frame.frame_index for frame in self.frames]
        if len(frame_indices) != len(set(frame_indices)):
            msg = "frame_index values must be unique within a sequence"
            raise ValueError(msg)
        return self

    def ordered_frames(self) -> tuple[SpatialPerceptionCorpusFrame, ...]:
        """Return frames in deterministic temporal order."""

        return tuple(sorted(self.frames, key=lambda frame: (frame.frame_index, frame.frame_id)))


class SpatialPerceptionCorpusManifest(BaseModel):
    """Strict manifest binding external frames to canonical point annotations."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    corpus_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    sequences: tuple[SpatialPerceptionCorpusSequence, ...] = Field(min_length=1)
    annotations: SpatialPerceptionDataset

    @model_validator(mode="after")
    def validate_manifest_references(self) -> "SpatialPerceptionCorpusManifest":
        sequence_ids = [sequence.sequence_id for sequence in self.sequences]
        if len(sequence_ids) != len(set(sequence_ids)):
            msg = "a sequence_id must appear in only one corpus split"
            raise ValueError(msg)
        annotation_sequence_ids = [sequence.sequence_id for sequence in self.annotations.sequences]
        if len(annotation_sequence_ids) != len(set(annotation_sequence_ids)):
            msg = "annotation sequence_id values must be unique within a corpus"
            raise ValueError(msg)
        if set(sequence_ids) != set(annotation_sequence_ids):
            msg = "corpus sequence_ids and annotation sequence_ids must match exactly"
            raise ValueError(msg)

        frames = tuple(self.iter_frames())
        frame_ids = [frame.frame_id for frame in frames]
        if len(frame_ids) != len(set(frame_ids)):
            msg = "frame_id values must be globally unique within a corpus"
            raise ValueError(msg)

        self._validate_cross_split_hash_leakage()
        self._validate_annotation_references(frames)
        return self

    def iter_frames(self) -> Iterable[SpatialPerceptionCorpusFrame]:
        """Yield all corpus frames in deterministic sequence and temporal order."""

        for sequence in sorted(self.sequences, key=lambda item: item.sequence_id):
            yield from sequence.ordered_frames()

    def canonical_payload(self) -> dict[str, object]:
        """Return a recursively ordered, JSON-compatible representation of this manifest."""

        annotations_by_frame_id = {
            annotation.frame_id: annotation
            for sequence in self.annotations.sequences
            for annotation in sequence.frames
        }
        sequences = []
        for sequence in sorted(self.sequences, key=lambda item: item.sequence_id):
            sequences.append(
                {
                    "sequence_id": sequence.sequence_id,
                    "split": sequence.split,
                    "frames": [
                        {
                            "frame": frame.model_dump(mode="json"),
                            "annotation": _canonical_annotation_payload(
                                annotations_by_frame_id[frame.frame_id]
                            ),
                        }
                        for frame in sequence.ordered_frames()
                    ],
                }
            )
        return {
            "corpus_id": self.corpus_id,
            "schema_version": self.schema_version,
            "corpus_version": self.corpus_version,
            "annotation_dataset_version": self.annotations.dataset_version,
            "sequences": sequences,
        }

    def canonical_json(self) -> str:
        """Serialize manifest content deterministically for experiment provenance."""

        return json.dumps(
            self.canonical_payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    def fingerprint(self) -> str:
        """Return the SHA-256 of the complete canonical logical corpus manifest."""

        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def _validate_cross_split_hash_leakage(self) -> None:
        splits_by_sha256: dict[str, set[CorpusSplit]] = {}
        for sequence in self.sequences:
            for frame in sequence.frames:
                splits_by_sha256.setdefault(frame.sha256, set()).add(sequence.split)
        leaked_hashes = sorted(
            frame_hash for frame_hash, splits in splits_by_sha256.items() if len(splits) > 1
        )
        if leaked_hashes:
            msg = "the same frame sha256 must not appear in more than one corpus split"
            raise ValueError(msg)

    def _validate_annotation_references(
        self, frames: tuple[SpatialPerceptionCorpusFrame, ...]
    ) -> None:
        annotations_by_frame_id = {
            annotation.frame_id: (sequence.sequence_id, annotation)
            for sequence in self.annotations.sequences
            for annotation in sequence.frames
        }
        frame_ids = {frame.frame_id for frame in frames}
        annotation_ids = set(annotations_by_frame_id)
        if frame_ids != annotation_ids:
            msg = "corpus frame_ids and annotation frame_ids must match exactly"
            raise ValueError(msg)

        for frame in frames:
            annotation_sequence_id, annotation = annotations_by_frame_id[frame.frame_id]
            if annotation_sequence_id != frame.sequence_id:
                msg = "corpus frame and annotation sequence_id must match"
                raise ValueError(msg)
            if annotation.evidence_id != frame.evidence_id:
                msg = "corpus frame and annotation evidence_id must match"
                raise ValueError(msg)


class SpatialPerceptionCorpusIntegrityIssue(BaseModel):
    """One deterministic file-integrity failure suitable for experiment gating."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: CorpusIntegrityIssueCode
    frame_id: str = Field(min_length=1)
    relative_frame_path: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class SpatialPerceptionCorpusIntegrityResult(BaseModel):
    """Structured result of validating externally stored corpus frame files."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    corpus_id: str = Field(min_length=1)
    manifest_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    checked_frame_count: int = Field(ge=0)
    valid: bool
    issues: tuple[SpatialPerceptionCorpusIntegrityIssue, ...] = ()


def validate_spatial_perception_corpus_files(
    manifest: SpatialPerceptionCorpusManifest,
    corpus_root: Path,
) -> SpatialPerceptionCorpusIntegrityResult:
    """Validate external PPM frame files without adding an image-library dependency."""

    issues: list[SpatialPerceptionCorpusIntegrityIssue] = []
    frames = tuple(manifest.iter_frames())
    for frame in frames:
        path = corpus_root / frame.relative_frame_path
        if not path.is_file():
            issues.append(
                _integrity_issue(
                    "missing_file",
                    frame,
                    "frame file does not exist under the supplied corpus root",
                )
            )
            continue

        if _sha256_file(path) != frame.sha256:
            issues.append(
                _integrity_issue(
                    "sha256_mismatch",
                    frame,
                    "frame file SHA-256 does not match the manifest",
                )
            )
        try:
            loaded_frame = load_ppm_frame(path)
        except (OSError, ValueError) as error:
            issues.append(_integrity_issue("frame_decode_failed", frame, str(error)))
            continue
        if (loaded_frame.width, loaded_frame.height) != (frame.width, frame.height):
            issues.append(
                _integrity_issue(
                    "dimension_mismatch",
                    frame,
                    "decoded frame dimensions do not match the manifest",
                )
            )

    ordered_issues = tuple(
        sorted(issues, key=lambda issue: (issue.frame_id, issue.code, issue.relative_frame_path))
    )
    return SpatialPerceptionCorpusIntegrityResult(
        corpus_id=manifest.corpus_id,
        manifest_fingerprint=manifest.fingerprint(),
        checked_frame_count=len(frames),
        valid=not ordered_issues,
        issues=ordered_issues,
    )


def _integrity_issue(
    code: CorpusIntegrityIssueCode,
    frame: SpatialPerceptionCorpusFrame,
    detail: str,
) -> SpatialPerceptionCorpusIntegrityIssue:
    return SpatialPerceptionCorpusIntegrityIssue(
        code=code,
        frame_id=frame.frame_id,
        relative_frame_path=frame.relative_frame_path,
        detail=detail,
    )


def _canonical_annotation_payload(
    annotation: SpatialPerceptionFrameAnnotation,
) -> dict[str, object]:
    payload = annotation.model_dump(mode="json")
    payload["visible_sprite_positions"] = sorted(payload["visible_sprite_positions"])
    return payload


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
