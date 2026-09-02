"""Deterministic offline metrics for independently annotated verifier outcomes."""

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fh_agent.memory.event_log import EventRecord
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus

AuditIdentifier = Annotated[str, Field(min_length=1)]
AuditEvidenceIdentifier = Annotated[str, Field(min_length=1)]
AnnotationStatus = Literal["usable", "uncertain", "exclude"]


class VerifierAuditIntegrityError(ValueError):
    """Raised when durable verifier records cannot support a valid audit."""


class VerifierAuditAnnotation(BaseModel):
    """Independent, evidence-backed manual label for one durable verifier event."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    audit_id: AuditIdentifier
    run_id: AuditIdentifier
    verifier_event_id: AuditIdentifier
    skill_name: AuditIdentifier
    annotation_status: AnnotationStatus
    evidence_ids: tuple[AuditEvidenceIdentifier, ...] = Field(min_length=1)
    expected_status: VerifierStatus | None = None
    expected_failure_kind: FailureKind | None = None

    @model_validator(mode="after")
    def expected_outcome_matches_annotation_status(self) -> "VerifierAuditAnnotation":
        if self.annotation_status == "usable":
            if self.expected_status is None:
                msg = "usable annotations require an expected_status"
                raise ValueError(msg)
            if self.expected_status is VerifierStatus.FAILURE:
                if self.expected_failure_kind is None:
                    msg = "usable failure annotations require an expected_failure_kind"
                    raise ValueError(msg)
            elif self.expected_failure_kind is not None:
                msg = "only expected failure annotations may include an expected_failure_kind"
                raise ValueError(msg)
        elif self.expected_status is not None or self.expected_failure_kind is not None:
            msg = "uncertain and exclude annotations must not include an expected outcome"
            raise ValueError(msg)
        return self


class VerifierAuditDataset(BaseModel):
    """Versioned independent labels for a reviewed subset of verifier events."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    dataset_version: AuditIdentifier
    annotations: tuple[VerifierAuditAnnotation, ...]

    @model_validator(mode="after")
    def annotation_identities_must_be_unique(self) -> "VerifierAuditDataset":
        audit_ids = [annotation.audit_id for annotation in self.annotations]
        if len(audit_ids) != len(set(audit_ids)):
            msg = "audit_id values must be unique within a dataset"
            raise ValueError(msg)

        event_references = [
            (annotation.run_id, annotation.verifier_event_id) for annotation in self.annotations
        ]
        if len(event_references) != len(set(event_references)):
            msg = "run_id and verifier_event_id pairs must be unique within a dataset"
            raise ValueError(msg)
        return self


class VerifierAuditMetrics(BaseModel):
    """Aggregate audit metrics over usable independently annotated outcomes."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    evaluated_case_count: int = Field(ge=0)
    skipped_uncertain_count: int = Field(ge=0)
    skipped_exclude_count: int = Field(ge=0)
    exact_status_correct_count: int = Field(ge=0)
    exact_status_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    success_true_positives: int = Field(ge=0)
    success_false_positives: int = Field(ge=0)
    success_false_negatives: int = Field(ge=0)
    success_true_negatives: int = Field(ge=0)
    success_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    success_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    success_f1: float | None = Field(default=None, ge=0.0, le=1.0)
    success_false_positive_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    success_false_negative_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    failure_true_positives: int = Field(ge=0)
    failure_false_positives: int = Field(ge=0)
    failure_false_negatives: int = Field(ge=0)
    failure_true_negatives: int = Field(ge=0)
    failure_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    failure_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    failure_f1: float | None = Field(default=None, ge=0.0, le=1.0)
    failure_false_positive_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    failure_false_negative_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_failure_count: int = Field(ge=0)
    failure_kind_correct_count: int = Field(ge=0)
    failure_kind_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)


def evaluate_verifier_audit(
    dataset: VerifierAuditDataset,
    records: Sequence[EventRecord],
) -> VerifierAuditMetrics:
    """Compare durable canonical outcomes with independent manual audit labels."""

    verifier_events = _verifier_events_by_identity(records)
    evaluated_case_count = 0
    skipped_uncertain_count = 0
    skipped_exclude_count = 0
    exact_status_correct_count = 0
    success_true_positives = 0
    success_false_positives = 0
    success_false_negatives = 0
    success_true_negatives = 0
    failure_true_positives = 0
    failure_false_positives = 0
    failure_false_negatives = 0
    failure_true_negatives = 0
    expected_failure_count = 0
    failure_kind_correct_count = 0

    for annotation in dataset.annotations:
        result = _result_for_annotation(annotation, verifier_events)
        if annotation.annotation_status == "uncertain":
            skipped_uncertain_count += 1
            continue
        if annotation.annotation_status == "exclude":
            skipped_exclude_count += 1
            continue

        expected_status = annotation.expected_status
        if expected_status is None:  # Defensive; the annotation model prevents this.
            msg = "usable annotation is missing an expected_status"
            raise VerifierAuditIntegrityError(msg)

        evaluated_case_count += 1
        exact_status_correct_count += result.status is expected_status
        (
            success_true_positives,
            success_false_positives,
            success_false_negatives,
            success_true_negatives,
        ) = _binary_counts(
            expected_status is VerifierStatus.SUCCESS,
            result.status is VerifierStatus.SUCCESS,
            success_true_positives,
            success_false_positives,
            success_false_negatives,
            success_true_negatives,
        )
        (
            failure_true_positives,
            failure_false_positives,
            failure_false_negatives,
            failure_true_negatives,
        ) = _binary_counts(
            expected_status is VerifierStatus.FAILURE,
            result.status is VerifierStatus.FAILURE,
            failure_true_positives,
            failure_false_positives,
            failure_false_negatives,
            failure_true_negatives,
        )
        if expected_status is VerifierStatus.FAILURE:
            expected_failure_count += 1
            if (
                result.status is VerifierStatus.FAILURE
                and result.failure_kind is annotation.expected_failure_kind
            ):
                failure_kind_correct_count += 1

    return VerifierAuditMetrics(
        evaluated_case_count=evaluated_case_count,
        skipped_uncertain_count=skipped_uncertain_count,
        skipped_exclude_count=skipped_exclude_count,
        exact_status_correct_count=exact_status_correct_count,
        exact_status_accuracy=_ratio(exact_status_correct_count, evaluated_case_count),
        success_true_positives=success_true_positives,
        success_false_positives=success_false_positives,
        success_false_negatives=success_false_negatives,
        success_true_negatives=success_true_negatives,
        success_precision=_ratio(
            success_true_positives, success_true_positives + success_false_positives
        ),
        success_recall=_ratio(
            success_true_positives, success_true_positives + success_false_negatives
        ),
        success_f1=_f1(
            _ratio(success_true_positives, success_true_positives + success_false_positives),
            _ratio(success_true_positives, success_true_positives + success_false_negatives),
        ),
        success_false_positive_rate=_ratio(
            success_false_positives,
            success_false_positives + success_true_negatives,
        ),
        success_false_negative_rate=_ratio(
            success_false_negatives,
            success_false_negatives + success_true_positives,
        ),
        failure_true_positives=failure_true_positives,
        failure_false_positives=failure_false_positives,
        failure_false_negatives=failure_false_negatives,
        failure_true_negatives=failure_true_negatives,
        failure_precision=_ratio(
            failure_true_positives, failure_true_positives + failure_false_positives
        ),
        failure_recall=_ratio(
            failure_true_positives, failure_true_positives + failure_false_negatives
        ),
        failure_f1=_f1(
            _ratio(failure_true_positives, failure_true_positives + failure_false_positives),
            _ratio(failure_true_positives, failure_true_positives + failure_false_negatives),
        ),
        failure_false_positive_rate=_ratio(
            failure_false_positives,
            failure_false_positives + failure_true_negatives,
        ),
        failure_false_negative_rate=_ratio(
            failure_false_negatives,
            failure_false_negatives + failure_true_positives,
        ),
        expected_failure_count=expected_failure_count,
        failure_kind_correct_count=failure_kind_correct_count,
        failure_kind_accuracy=_ratio(failure_kind_correct_count, expected_failure_count),
    )


def _verifier_events_by_identity(
    records: Sequence[EventRecord],
) -> dict[tuple[str, str], EventRecord]:
    verifier_events: dict[tuple[str, str], EventRecord] = {}
    for record in records:
        if record.event_type != "verifier_result":
            continue
        identity = (record.run_id, record.event_id)
        if identity in verifier_events:
            msg = f"duplicate verifier_result event for run_id and event_id: {identity}"
            raise VerifierAuditIntegrityError(msg)
        verifier_events[identity] = record
    return verifier_events


def _result_for_annotation(
    annotation: VerifierAuditAnnotation,
    verifier_events: dict[tuple[str, str], EventRecord],
) -> VerifierResult:
    identity = (annotation.run_id, annotation.verifier_event_id)
    record = verifier_events.get(identity)
    if record is None:
        msg = f"missing verifier_result event for run_id and event_id: {identity}"
        raise VerifierAuditIntegrityError(msg)
    try:
        nested_result = record.payload["verifier_result"]
        result = VerifierResult.model_validate(nested_result)
    except (KeyError, TypeError, ValueError) as error:
        msg = f"malformed verifier_result payload for run_id and event_id: {identity}"
        raise VerifierAuditIntegrityError(msg) from error

    if record.payload.get("skill_name") != annotation.skill_name:
        msg = f"verifier event skill_name does not match annotation: {identity}"
        raise VerifierAuditIntegrityError(msg)
    if record.evidence_ids != result.evidence_ids:
        msg = f"verifier event evidence_ids do not match nested verifier result: {identity}"
        raise VerifierAuditIntegrityError(msg)
    return result


def _binary_counts(
    expected_positive: bool,
    predicted_positive: bool,
    true_positives: int,
    false_positives: int,
    false_negatives: int,
    true_negatives: int,
) -> tuple[int, int, int, int]:
    if expected_positive and predicted_positive:
        true_positives += 1
    elif predicted_positive:
        false_positives += 1
    elif expected_positive:
        false_negatives += 1
    else:
        true_negatives += 1
    return true_positives, false_positives, false_negatives, true_negatives


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)
