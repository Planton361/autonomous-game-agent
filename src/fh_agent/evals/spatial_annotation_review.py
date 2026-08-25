"""Pure annotation revision, review, and corpus-freeze workflow contracts."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fh_agent.evals.spatial_perception_corpus import (
    SpatialPerceptionCorpusIntegrityResult,
    SpatialPerceptionCorpusManifest,
)
from fh_agent.evals.spatial_perception_dataset import (
    SpatialPerceptionDataset,
    SpatialPerceptionFrameAnnotation,
    SpatialPerceptionSequence,
)

AnnotationReviewStatus = Literal["passed", "needs_revision"]
CorpusIntegrityStatus = Literal["passed", "failed", "stale"]
CorpusFreezeStatus = Literal["ready", "blocked", "frozen"]


class SpatialAnnotationReviewRecord(BaseModel):
    """Audit record bound to one exact point-annotation revision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    frame_id: str = Field(min_length=1)
    annotation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: AnnotationReviewStatus
    reviewer_id: str | None = Field(default=None, min_length=1)
    reviewed_at: datetime
    notes: str | None = None

    @field_validator("reviewed_at")
    @classmethod
    def reviewed_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "reviewed_at must be timezone-aware"
            raise ValueError(msg)
        return value


class SpatialPerceptionCorpusFreezeRecord(BaseModel):
    """Immutable provenance record for a corpus version approved for later gating."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    corpus_id: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_at: datetime

    @field_validator("frozen_at")
    @classmethod
    def frozen_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "frozen_at must be timezone-aware"
            raise ValueError(msg)
        return value


class SpatialAnnotationWorkflow(BaseModel):
    """Immutable offline state that prevents revisions after a corpus freeze."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    manifest: SpatialPerceptionCorpusManifest
    reviews: tuple[SpatialAnnotationReviewRecord, ...] = ()
    freeze_record: SpatialPerceptionCorpusFreezeRecord | None = None


class SpatialCorpusReadinessSummary(BaseModel):
    """Deterministic corpus gate summary for offline researcher workflows."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    corpus_id: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    total_sequence_count: int = Field(ge=0)
    train_sequence_count: int = Field(ge=0)
    validation_sequence_count: int = Field(ge=0)
    test_sequence_count: int = Field(ge=0)
    total_frame_count: int = Field(ge=0)
    usable_annotation_count: int = Field(ge=0)
    uncertain_annotation_count: int = Field(ge=0)
    exclude_annotation_count: int = Field(ge=0)
    usable_annotations_with_valid_passed_review: int = Field(ge=0)
    usable_annotations_lacking_review: int = Field(ge=0)
    usable_annotations_without_valid_passed_review: int = Field(ge=0)
    obsolete_review_count: int = Field(ge=0)
    corpus_integrity_status: CorpusIntegrityStatus
    freeze_ready: bool
    freeze_status: CorpusFreezeStatus
    blocked_reasons: tuple[str, ...] = ()


def annotation_canonical_json(annotation: SpatialPerceptionFrameAnnotation) -> str:
    """Serialize an annotation deterministically, independent of sprite-point order."""

    payload = annotation.model_dump(mode="json")
    payload["visible_sprite_positions"] = sorted(payload["visible_sprite_positions"])
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def annotation_fingerprint(annotation: SpatialPerceptionFrameAnnotation) -> str:
    """Return the SHA-256 identity of the complete point-only annotation revision."""

    return sha256(annotation_canonical_json(annotation).encode("utf-8")).hexdigest()


def record_spatial_annotation(
    workflow: SpatialAnnotationWorkflow,
    annotation: SpatialPerceptionFrameAnnotation,
    *,
    overwrite: bool = False,
) -> SpatialAnnotationWorkflow:
    """Create an explicit annotation revision without silently overwriting prior data."""

    _assert_mutable(workflow)
    previous = _annotation_by_frame_id(workflow.manifest).get(annotation.frame_id)
    if previous is None:
        msg = "annotation frame_id is not present in the corpus"
        raise ValueError(msg)
    if annotation.evidence_id != previous.evidence_id:
        msg = "annotation evidence_id must match the existing corpus frame evidence_id"
        raise ValueError(msg)
    if not overwrite:
        msg = "annotation already exists; set overwrite=True for an intentional revision"
        raise ValueError(msg)

    replacement_sequences = tuple(
        SpatialPerceptionSequence(
            sequence_id=sequence.sequence_id,
            frames=tuple(
                annotation if item.frame_id == annotation.frame_id else item
                for item in sequence.frames
            ),
        )
        for sequence in workflow.manifest.annotations.sequences
    )
    replacement_manifest = workflow.manifest.model_copy(
        update={
            "annotations": SpatialPerceptionDataset(
                dataset_version=workflow.manifest.annotations.dataset_version,
                sequences=replacement_sequences,
            )
        }
    )
    return SpatialAnnotationWorkflow(
        manifest=replacement_manifest,
        reviews=workflow.reviews,
    )


def create_annotation_review(
    workflow: SpatialAnnotationWorkflow,
    *,
    frame_id: str,
    status: AnnotationReviewStatus,
    reviewer_id: str | None = None,
    notes: str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> SpatialAnnotationWorkflow:
    """Append a review bound to the annotation bytes present at review time."""

    annotation = _annotation_by_frame_id(workflow.manifest)[frame_id]
    review = SpatialAnnotationReviewRecord(
        frame_id=frame_id,
        annotation_fingerprint=annotation_fingerprint(annotation),
        status=status,
        reviewer_id=reviewer_id,
        reviewed_at=(clock or (lambda: datetime.now(UTC)))(),
        notes=notes,
    )
    return workflow.model_copy(update={"reviews": (*workflow.reviews, review)})


def review_is_current(
    review: SpatialAnnotationReviewRecord,
    manifest: SpatialPerceptionCorpusManifest,
) -> bool:
    """Return whether a review still refers to the current annotation revision."""

    annotation = _annotation_by_frame_id(manifest).get(review.frame_id)
    return annotation is not None and review.annotation_fingerprint == annotation_fingerprint(
        annotation
    )


def assess_spatial_corpus_readiness(
    workflow: SpatialAnnotationWorkflow,
    integrity_result: SpatialPerceptionCorpusIntegrityResult,
) -> SpatialCorpusReadinessSummary:
    """Summarize deterministic freeze gates without mutating corpus state."""

    manifest = workflow.manifest
    annotations = tuple(_annotation_by_frame_id(manifest).values())
    current_reviews = tuple(
        review for review in workflow.reviews if review_is_current(review, manifest)
    )
    passed_review_frame_ids = {
        review.frame_id for review in current_reviews if review.status == "passed"
    }
    reviewed_frame_ids = {review.frame_id for review in current_reviews}
    usable_annotations = tuple(
        annotation for annotation in annotations if annotation.status == "usable"
    )
    usable_frame_ids = {annotation.frame_id for annotation in usable_annotations}
    usable_passed_count = len(usable_frame_ids & passed_review_frame_ids)
    usable_lacking_review_count = len(usable_frame_ids - reviewed_frame_ids)
    usable_without_passed_count = len(usable_frame_ids - passed_review_frame_ids)
    obsolete_review_count = len(workflow.reviews) - len(current_reviews)
    integrity_status = _integrity_status(integrity_result, manifest)

    blocked_reasons: list[str] = []
    if integrity_status != "passed":
        blocked_reasons.append("corpus_file_integrity_not_passed")
    if usable_without_passed_count:
        blocked_reasons.append("usable_annotations_lack_valid_passed_review")
    if obsolete_review_count:
        blocked_reasons.append("obsolete_annotation_review_present")
    if workflow.freeze_record is not None:
        blocked_reasons.append("corpus_version_already_frozen")

    freeze_ready = not blocked_reasons
    freeze_status: CorpusFreezeStatus
    if workflow.freeze_record is not None:
        freeze_status = "frozen"
    elif freeze_ready:
        freeze_status = "ready"
    else:
        freeze_status = "blocked"
    return SpatialCorpusReadinessSummary(
        corpus_id=manifest.corpus_id,
        corpus_version=manifest.corpus_version,
        total_sequence_count=len(manifest.sequences),
        train_sequence_count=sum(sequence.split == "train" for sequence in manifest.sequences),
        validation_sequence_count=sum(
            sequence.split == "validation" for sequence in manifest.sequences
        ),
        test_sequence_count=sum(sequence.split == "test" for sequence in manifest.sequences),
        total_frame_count=sum(len(sequence.frames) for sequence in manifest.sequences),
        usable_annotation_count=len(usable_annotations),
        uncertain_annotation_count=sum(
            annotation.status == "uncertain" for annotation in annotations
        ),
        exclude_annotation_count=sum(annotation.status == "exclude" for annotation in annotations),
        usable_annotations_with_valid_passed_review=usable_passed_count,
        usable_annotations_lacking_review=usable_lacking_review_count,
        usable_annotations_without_valid_passed_review=usable_without_passed_count,
        obsolete_review_count=obsolete_review_count,
        corpus_integrity_status=integrity_status,
        freeze_ready=freeze_ready,
        freeze_status=freeze_status,
        blocked_reasons=tuple(blocked_reasons),
    )


def freeze_spatial_corpus(
    workflow: SpatialAnnotationWorkflow,
    integrity_result: SpatialPerceptionCorpusIntegrityResult,
    *,
    clock: Callable[[], datetime] | None = None,
) -> SpatialAnnotationWorkflow:
    """Freeze exactly one valid corpus version after successful file-integrity validation."""

    if workflow.freeze_record is not None:
        msg = "corpus version is already frozen; create a new corpus version for further changes"
        raise ValueError(msg)
    if not integrity_result.valid:
        msg = "cannot freeze a corpus with failed file-integrity validation"
        raise ValueError(msg)
    if integrity_result.corpus_id != workflow.manifest.corpus_id:
        msg = "integrity result corpus_id does not match the workflow manifest"
        raise ValueError(msg)
    if integrity_result.manifest_fingerprint != workflow.manifest.fingerprint():
        msg = "integrity result does not match the current workflow manifest"
        raise ValueError(msg)

    freeze_record = SpatialPerceptionCorpusFreezeRecord(
        corpus_id=workflow.manifest.corpus_id,
        corpus_version=workflow.manifest.corpus_version,
        schema_version=workflow.manifest.schema_version,
        corpus_fingerprint=workflow.manifest.fingerprint(),
        split_fingerprint=split_fingerprint(workflow.manifest),
        frozen_at=(clock or (lambda: datetime.now(UTC)))(),
    )
    return workflow.model_copy(update={"freeze_record": freeze_record})


def split_fingerprint(manifest: SpatialPerceptionCorpusManifest) -> str:
    """Fingerprint the sequence-level split assignment and exact selected frame content."""

    payload = [
        {
            "sequence_id": sequence.sequence_id,
            "split": sequence.split,
            "frames": [
                {"frame_id": frame.frame_id, "sha256": frame.sha256}
                for frame in sequence.ordered_frames()
            ],
        }
        for sequence in sorted(manifest.sequences, key=lambda item: item.sequence_id)
    ]
    canonical_json = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def _assert_mutable(workflow: SpatialAnnotationWorkflow) -> None:
    if workflow.freeze_record is not None:
        msg = "corpus version is frozen; create a new corpus version before revising annotations"
        raise ValueError(msg)


def _annotation_by_frame_id(
    manifest: SpatialPerceptionCorpusManifest,
) -> dict[str, SpatialPerceptionFrameAnnotation]:
    return {
        annotation.frame_id: annotation
        for sequence in manifest.annotations.sequences
        for annotation in sequence.frames
    }


def _integrity_status(
    integrity_result: SpatialPerceptionCorpusIntegrityResult,
    manifest: SpatialPerceptionCorpusManifest,
) -> CorpusIntegrityStatus:
    if (
        integrity_result.corpus_id != manifest.corpus_id
        or integrity_result.manifest_fingerprint != manifest.fingerprint()
    ):
        return "stale"
    return "passed" if integrity_result.valid else "failed"
