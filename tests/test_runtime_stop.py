import inspect

import pytest
from pydantic import ValidationError

import fh_agent.manager.runtime_stop as runtime_stop
from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.verifier.schemas import FailureKind


def test_manager_stop_result_is_strict_frozen_and_preserves_canonical_fields() -> None:
    result = ManagerStopResult(
        failure_kind=FailureKind.SAFETY_INTERVENTION,
        reason="rate_limited",
        evidence_ids=["before", "after", "before"],
        trigger_event_id="action-event-1",
    )

    assert result.failure_kind is FailureKind.SAFETY_INTERVENTION
    assert result.reason == "rate_limited"
    assert result.evidence_ids == ["before", "after", "before"]
    assert result.trigger_event_id == "action-event-1"
    with pytest.raises(ValidationError):
        result.reason = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ManagerStopResult(
            failure_kind=FailureKind.TIMEOUT,
            reason="timeout",
            unexpected=True,
        )


@pytest.mark.parametrize(
    "values",
    [
        {"failure_kind": FailureKind.TIMEOUT, "reason": ""},
        {
            "failure_kind": FailureKind.TIMEOUT,
            "reason": "timeout",
            "trigger_event_id": "",
        },
    ],
)
def test_manager_stop_result_rejects_empty_required_identifiers(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ManagerStopResult(**values)


def test_manager_stop_result_json_round_trip_is_deterministic() -> None:
    result = ManagerStopResult(
        failure_kind=FailureKind.CAPABILITY_REJECTED,
        reason="action_not_allowed",
        evidence_ids=["first", "shared", "last"],
    )

    serialized = result.model_dump_json()

    assert ManagerStopResult.model_validate_json(serialized) == result
    assert ManagerStopResult.model_validate(result.model_dump(mode="json")) == result


def test_manager_stop_module_has_only_failure_taxonomy_dependency() -> None:
    source = inspect.getsource(runtime_stop)

    for forbidden_dependency in (
        "Observation",
        "SkillResult",
        "VerifierResult",
        "reward",
        "InputExecutor",
        "fh_agent.body",
        "fh_agent.cortex",
    ):
        assert forbidden_dependency not in source
