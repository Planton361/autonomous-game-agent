import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import fh_agent.evals.verifier_audit as verifier_audit
from fh_agent.evals.verifier_audit import (
    VerifierAuditAnnotation,
    VerifierAuditDataset,
    VerifierAuditIntegrityError,
    evaluate_verifier_audit,
)
from fh_agent.memory.event_log import EventRecord
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "verifier_audit_minimal.json"
FIXED_TIME = datetime(2026, 9, 2, tzinfo=UTC)


def annotation(
    event_id: str,
    *,
    audit_id: str | None = None,
    expected_status: VerifierStatus | None = VerifierStatus.ABSTAIN,
    expected_failure_kind: FailureKind | None = None,
    annotation_status: str = "usable",
    skill_name: str = "continue_dialogue",
) -> VerifierAuditAnnotation:
    return VerifierAuditAnnotation(
        audit_id=audit_id or f"audit-{event_id}",
        run_id="run-1",
        verifier_event_id=event_id,
        skill_name=skill_name,
        annotation_status=annotation_status,
        evidence_ids=(f"audit-evidence-{event_id}",),
        expected_status=expected_status,
        expected_failure_kind=expected_failure_kind,
    )


def dataset(*annotations: VerifierAuditAnnotation) -> VerifierAuditDataset:
    return VerifierAuditDataset(dataset_version="synthetic-v1", annotations=annotations)


def result(
    status: VerifierStatus,
    *,
    failure_kind: FailureKind | None = None,
    evidence_ids: list[str] | None = None,
) -> VerifierResult:
    return VerifierResult(
        status=status,
        failure_kind=failure_kind,
        evidence_ids=evidence_ids or [],
    )


def event(
    event_id: str,
    verifier_result: VerifierResult,
    *,
    run_id: str = "run-1",
    skill_name: str = "continue_dialogue",
    outer_evidence_ids: list[str] | None = None,
) -> EventRecord:
    return EventRecord(
        event_id=event_id,
        run_id=run_id,
        event_type="verifier_result",
        created_at=FIXED_TIME,
        payload={
            "skill_name": skill_name,
            "verifier_result": verifier_result.model_dump(mode="json"),
        },
        evidence_ids=(
            list(verifier_result.evidence_ids) if outer_evidence_ids is None else outer_evidence_ids
        ),
    )


def test_synthetic_fixture_validates_and_is_generic_audit_data() -> None:
    audit_dataset = VerifierAuditDataset.model_validate_json(FIXTURE_PATH.read_text())

    assert audit_dataset.dataset_version == "synthetic-verifier-audit-v1"
    assert [item.annotation_status for item in audit_dataset.annotations] == [
        "usable",
        "usable",
        "usable",
        "uncertain",
        "exclude",
    ]
    assert audit_dataset.annotations[1].expected_failure_kind is FailureKind.DEATH


def test_dataset_rejects_duplicate_audit_ids_and_event_references() -> None:
    with pytest.raises(ValidationError, match="audit_id values must be unique"):
        dataset(annotation("event-1", audit_id="same"), annotation("event-2", audit_id="same"))
    with pytest.raises(ValidationError, match="run_id and verifier_event_id pairs must be unique"):
        dataset(annotation("event-1", audit_id="first"), annotation("event-1", audit_id="second"))


def test_usable_annotation_requires_a_complete_expected_outcome() -> None:
    with pytest.raises(ValidationError, match="require an expected_status"):
        annotation("event-1", expected_status=None)
    with pytest.raises(ValidationError, match="require an expected_failure_kind"):
        annotation("event-1", expected_status=VerifierStatus.FAILURE)
    with pytest.raises(ValidationError, match="only expected failure"):
        annotation(
            "event-1",
            expected_status=VerifierStatus.SUCCESS,
            expected_failure_kind=FailureKind.DEATH,
        )


def test_uncertain_and_exclude_annotations_do_not_force_ground_truth() -> None:
    uncertain = annotation("uncertain", annotation_status="uncertain", expected_status=None)
    exclude = annotation("exclude", annotation_status="exclude", expected_status=None)

    assert uncertain.expected_failure_kind is None
    assert exclude.expected_failure_kind is None
    with pytest.raises(ValidationError, match="must not include an expected outcome"):
        annotation(
            "bad-uncertain",
            annotation_status="uncertain",
            expected_status=VerifierStatus.SUCCESS,
        )


def test_evaluator_requires_referenced_event_and_validates_durable_envelope() -> None:
    item = annotation("missing")
    with pytest.raises(VerifierAuditIntegrityError, match="missing verifier_result event"):
        evaluate_verifier_audit(dataset(item), [])

    with pytest.raises(VerifierAuditIntegrityError, match="skill_name"):
        evaluate_verifier_audit(
            dataset(item),
            [event("missing", result(VerifierStatus.ABSTAIN), skill_name="basic_reach_target")],
        )
    with pytest.raises(VerifierAuditIntegrityError, match="evidence_ids"):
        evaluate_verifier_audit(
            dataset(item),
            [
                event(
                    "missing",
                    result(VerifierStatus.ABSTAIN, evidence_ids=["nested"]),
                    outer_evidence_ids=["outer"],
                )
            ],
        )


def test_evaluator_rejects_duplicate_and_malformed_verifier_events() -> None:
    item = annotation("event-1")
    record = event("event-1", result(VerifierStatus.ABSTAIN))
    with pytest.raises(VerifierAuditIntegrityError, match="duplicate verifier_result event"):
        evaluate_verifier_audit(dataset(item), [record, record])

    malformed = record.model_copy(
        update={
            "payload": {"skill_name": "continue_dialogue", "verifier_result": {"status": "bad"}}
        }
    )
    with pytest.raises(VerifierAuditIntegrityError, match="malformed verifier_result payload"):
        evaluate_verifier_audit(dataset(item), [malformed])


def test_success_binary_counts_and_rates_are_exact() -> None:
    annotations = dataset(
        annotation("success-tp", expected_status=VerifierStatus.SUCCESS),
        annotation("success-fp", expected_status=VerifierStatus.ABSTAIN),
        annotation("success-fn", expected_status=VerifierStatus.SUCCESS),
        annotation("success-tn", expected_status=VerifierStatus.PROGRESS),
    )
    metrics = evaluate_verifier_audit(
        annotations,
        [
            event("success-tp", result(VerifierStatus.SUCCESS)),
            event("success-fp", result(VerifierStatus.SUCCESS)),
            event("success-fn", result(VerifierStatus.ABSTAIN)),
            event("success-tn", result(VerifierStatus.PROGRESS)),
        ],
    )

    assert (
        metrics.success_true_positives,
        metrics.success_false_positives,
        metrics.success_false_negatives,
        metrics.success_true_negatives,
    ) == (1, 1, 1, 1)
    assert metrics.success_precision == 0.5
    assert metrics.success_recall == 0.5
    assert metrics.success_f1 == 0.5
    assert metrics.success_false_positive_rate == 0.5
    assert metrics.success_false_negative_rate == 0.5


def test_failure_binary_counts_rates_and_failure_kind_accuracy_are_exact() -> None:
    annotations = dataset(
        annotation(
            "failure-tp",
            expected_status=VerifierStatus.FAILURE,
            expected_failure_kind=FailureKind.DEATH,
        ),
        annotation("failure-fp", expected_status=VerifierStatus.ABSTAIN),
        annotation(
            "failure-fn",
            expected_status=VerifierStatus.FAILURE,
            expected_failure_kind=FailureKind.TARGET_LOST,
        ),
        annotation("failure-tn", expected_status=VerifierStatus.PROGRESS),
    )
    metrics = evaluate_verifier_audit(
        annotations,
        [
            event("failure-tp", result(VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH)),
            event(
                "failure-fp", result(VerifierStatus.FAILURE, failure_kind=FailureKind.SKILL_FAILED)
            ),
            event("failure-fn", result(VerifierStatus.ABSTAIN)),
            event("failure-tn", result(VerifierStatus.PROGRESS)),
        ],
    )

    assert (
        metrics.failure_true_positives,
        metrics.failure_false_positives,
        metrics.failure_false_negatives,
        metrics.failure_true_negatives,
    ) == (1, 1, 1, 1)
    assert metrics.failure_precision == 0.5
    assert metrics.failure_recall == 0.5
    assert metrics.failure_f1 == 0.5
    assert metrics.failure_false_positive_rate == 0.5
    assert metrics.failure_false_negative_rate == 0.5
    assert metrics.expected_failure_count == 2
    assert metrics.failure_kind_correct_count == 1
    assert metrics.failure_kind_accuracy == 0.5


def test_wrong_or_non_failure_prediction_is_incorrect_for_expected_failure_kind() -> None:
    annotations = dataset(
        annotation(
            "wrong-kind",
            expected_status=VerifierStatus.FAILURE,
            expected_failure_kind=FailureKind.DEATH,
        ),
        annotation(
            "not-failure",
            expected_status=VerifierStatus.FAILURE,
            expected_failure_kind=FailureKind.TARGET_LOST,
        ),
    )
    metrics = evaluate_verifier_audit(
        annotations,
        [
            event(
                "wrong-kind", result(VerifierStatus.FAILURE, failure_kind=FailureKind.TARGET_LOST)
            ),
            event("not-failure", result(VerifierStatus.PROGRESS)),
        ],
    )

    assert metrics.expected_failure_count == 2
    assert metrics.failure_kind_correct_count == 0
    assert metrics.failure_kind_accuracy == 0.0


def test_exact_status_accuracy_compares_all_four_canonical_statuses() -> None:
    annotations = dataset(
        annotation("success", expected_status=VerifierStatus.SUCCESS),
        annotation("progress", expected_status=VerifierStatus.PROGRESS),
        annotation(
            "failure",
            expected_status=VerifierStatus.FAILURE,
            expected_failure_kind=FailureKind.DEATH,
        ),
        annotation("abstain", expected_status=VerifierStatus.ABSTAIN),
    )
    metrics = evaluate_verifier_audit(
        annotations,
        [
            event("success", result(VerifierStatus.SUCCESS)),
            event("progress", result(VerifierStatus.PROGRESS)),
            event("failure", result(VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH)),
            event("abstain", result(VerifierStatus.ABSTAIN)),
        ],
    )

    assert metrics.evaluated_case_count == 4
    assert metrics.exact_status_correct_count == 4
    assert metrics.exact_status_accuracy == 1.0


def test_uncertain_and_exclude_cases_are_retained_but_skipped_from_metrics() -> None:
    annotations = dataset(
        annotation("usable", expected_status=VerifierStatus.ABSTAIN),
        annotation("uncertain", annotation_status="uncertain", expected_status=None),
        annotation("exclude", annotation_status="exclude", expected_status=None),
    )
    metrics = evaluate_verifier_audit(
        annotations,
        [
            event("usable", result(VerifierStatus.ABSTAIN)),
            event("uncertain", result(VerifierStatus.SUCCESS)),
            event("exclude", result(VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH)),
        ],
    )

    assert metrics.evaluated_case_count == 1
    assert metrics.skipped_uncertain_count == 1
    assert metrics.skipped_exclude_count == 1
    assert metrics.success_true_positives == 0
    assert metrics.failure_true_positives == 0


def test_undefined_metric_denominators_are_none() -> None:
    metrics = evaluate_verifier_audit(dataset(), [])

    assert metrics.exact_status_accuracy is None
    assert metrics.success_precision is None
    assert metrics.success_recall is None
    assert metrics.success_f1 is None
    assert metrics.success_false_positive_rate is None
    assert metrics.success_false_negative_rate is None
    assert metrics.failure_precision is None
    assert metrics.failure_recall is None
    assert metrics.failure_f1 is None
    assert metrics.failure_false_positive_rate is None
    assert metrics.failure_false_negative_rate is None
    assert metrics.failure_kind_accuracy is None


def test_extra_records_and_record_order_do_not_change_deterministic_metrics() -> None:
    annotations = dataset(
        annotation("one", expected_status=VerifierStatus.SUCCESS),
        annotation("two", expected_status=VerifierStatus.ABSTAIN),
    )
    matching_records = [
        event("one", result(VerifierStatus.SUCCESS)),
        event("two", result(VerifierStatus.ABSTAIN)),
    ]
    extra = event("unreviewed", result(VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH))

    first = evaluate_verifier_audit(annotations, [*matching_records, extra])
    second = evaluate_verifier_audit(annotations, [extra, *reversed(matching_records)])

    assert first == second


def test_evaluator_has_no_runtime_or_verifier_invocation_dependency() -> None:
    source = inspect.getsource(verifier_audit)

    for forbidden_import in (
        "fh_agent.body",
        "InputExecutor",
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.cortex",
        "fh_agent.rl",
        "SkillResult",
        "TaskCompletion",
    ):
        assert forbidden_import not in source
    assert ".verify(" not in source


def test_deterministic_inputs_produce_identical_metrics() -> None:
    annotations = dataset(annotation("event-1", expected_status=VerifierStatus.SUCCESS))
    records = [event("event-1", result(VerifierStatus.SUCCESS, evidence_ids=["visible-evidence"]))]

    assert evaluate_verifier_audit(annotations, records) == evaluate_verifier_audit(
        annotations, records
    )


def test_fixture_json_is_json_only_synthetic_annotation_data() -> None:
    payload = json.loads(FIXTURE_PATH.read_text())

    assert set(payload) == {"dataset_version", "annotations"}
    assert all("expected_status" in item for item in payload["annotations"])
