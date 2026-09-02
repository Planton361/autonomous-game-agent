import json

import pytest
from pydantic import ValidationError

from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def test_verifier_result_accepts_success() -> None:
    result = VerifierResult(status=VerifierStatus.SUCCESS)

    assert result.status is VerifierStatus.SUCCESS
    assert result.failure_kind is None
    assert result.evidence_ids == []


def test_verifier_result_accepts_progress() -> None:
    result = VerifierResult(status="progress", evidence_ids=["evidence-1"])

    assert result.status is VerifierStatus.PROGRESS
    assert result.failure_kind is None
    assert result.evidence_ids == ["evidence-1"]


def test_verifier_result_accepts_failure_with_failure_kind() -> None:
    result = VerifierResult(
        status=VerifierStatus.FAILURE,
        failure_kind=FailureKind.TIMEOUT,
        evidence_ids=["evidence-1"],
    )

    assert result.status is VerifierStatus.FAILURE
    assert result.failure_kind is FailureKind.TIMEOUT


def test_verifier_result_accepts_abstain() -> None:
    result = VerifierResult(status=VerifierStatus.ABSTAIN)

    assert result.status is VerifierStatus.ABSTAIN
    assert result.failure_kind is None


@pytest.mark.parametrize("failure_kind", list(FailureKind))
def test_every_canonical_failure_kind_can_be_represented(failure_kind: FailureKind) -> None:
    result = VerifierResult(status=VerifierStatus.FAILURE, failure_kind=failure_kind)

    assert result.failure_kind is failure_kind


def test_failure_without_failure_kind_is_rejected() -> None:
    with pytest.raises(ValidationError, match="requires a failure_kind"):
        VerifierResult(status="failure")


@pytest.mark.parametrize("status", ["success", "progress", "abstain"])
def test_non_failure_statuses_reject_failure_kind(status: str) -> None:
    with pytest.raises(ValidationError, match="only failure status"):
        VerifierResult(status=status, failure_kind="timeout")


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VerifierResult.model_validate({"status": "unknown"})


def test_unknown_failure_kind_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VerifierResult.model_validate({"status": "failure", "failure_kind": "unknown"})


def test_perceptual_change_labels_are_not_failure_kinds() -> None:
    for label in ("screen_signature_changed", "screenshot_changed", "new_evidence"):
        with pytest.raises(ValidationError):
            VerifierResult.model_validate({"status": "failure", "failure_kind": label})


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        VerifierResult.model_validate({"status": "success", "unexpected": "value"})


def test_empty_evidence_ids_are_valid() -> None:
    result = VerifierResult(status="success", evidence_ids=[])

    assert result.evidence_ids == []


def test_non_empty_evidence_ids_are_preserved() -> None:
    result = VerifierResult(status="success", evidence_ids=["evidence-1", "evidence-2"])

    assert result.evidence_ids == ["evidence-1", "evidence-2"]


def test_json_compatible_dump_round_trip_preserves_outcome_and_evidence() -> None:
    original = VerifierResult(
        status=VerifierStatus.FAILURE,
        failure_kind=FailureKind.TARGET_LOST,
        evidence_ids=["evidence-1", "evidence-2"],
    )

    json_compatible = original.model_dump(mode="json")
    restored = VerifierResult.model_validate(json.loads(json.dumps(json_compatible)))

    assert restored.status is VerifierStatus.FAILURE
    assert restored.failure_kind is FailureKind.TARGET_LOST
    assert restored.evidence_ids == ["evidence-1", "evidence-2"]


def test_verifier_result_has_no_reward_scalar_field() -> None:
    assert "reward" not in VerifierResult.model_fields


def test_verifier_result_has_no_primitive_action_or_key_field() -> None:
    field_names = VerifierResult.model_fields

    assert "primitive_action" not in field_names
    assert "action" not in field_names
    assert "key" not in field_names
    assert "key_sequence" not in field_names
    assert "input_timing" not in field_names


def test_verifier_result_has_no_hidden_state_or_game_engine_identifier_field() -> None:
    field_names = set(VerifierResult.model_fields)

    forbidden_fields = {
        "map_id",
        "event_id",
        "switches",
        "variables",
        "savegame_state",
        "process_state",
        "ram_state",
        "enemy_id",
        "item_id",
        "quest_flag",
        "ending_flag",
    }

    assert field_names.isdisjoint(forbidden_fields)
