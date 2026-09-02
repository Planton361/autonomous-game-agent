import inspect

import pytest

from fh_agent.manager.target_ref import VisibleScreenPointTarget
from fh_agent.observation.schemas import Observation
from fh_agent.verifier import reach_target as reach_target_module
from fh_agent.verifier.reach_target import ReachTargetVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierStatus


def target(*, evidence_ids: tuple[str, ...] = ("target-evidence",)) -> VisibleScreenPointTarget:
    return VisibleScreenPointTarget(
        target_id="visible-point-1",
        confidence=0.9,
        evidence_ids=evidence_ids,
        screen_position=(10, 10),
    )


def observation(
    *,
    position: tuple[int, int] | None,
    evidence_ids: list[str] | None = None,
    ui_state: str = "field",
    death_screen_visible: bool | None = None,
    screen_signature: str | None = None,
    visible_message_text: str | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state=ui_state,  # type: ignore[arg-type]
        player_screen_position=position,
        death_screen_visible=death_screen_visible,
        screen_signature=screen_signature,
        visible_message_text=visible_message_text,
        evidence_ids=evidence_ids or [],
    )


def before_observation() -> Observation:
    return Observation(run_id="run-1")


def test_exact_target_position_with_outcome_evidence_is_success() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(), observation(position=(10, 10), evidence_ids=["after-1"])
    )

    assert result.status is VerifierStatus.SUCCESS
    assert result.failure_kind is None


def test_position_within_tolerance_is_success() -> None:
    result = ReachTargetVerifier(target(), tolerance_px=3.0).verify(
        before_observation(), observation(position=(12, 11), evidence_ids=["after-1"])
    )

    assert result.status is VerifierStatus.SUCCESS


def test_position_on_tolerance_boundary_is_success() -> None:
    result = ReachTargetVerifier(target(), tolerance_px=5.0).verify(
        before_observation(), observation(position=(13, 14), evidence_ids=["after-1"])
    )

    assert result.status is VerifierStatus.SUCCESS


def test_position_outside_tolerance_is_abstain() -> None:
    result = ReachTargetVerifier(target(), tolerance_px=2.0).verify(
        before_observation(), observation(position=(13, 10), evidence_ids=["after-1"])
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_missing_player_position_is_abstain() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(), observation(position=None, evidence_ids=["after-1"])
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_reached_position_without_outcome_evidence_is_abstain() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(), observation(position=(10, 10))
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_visible_death_with_evidence_is_failure() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(),
        observation(position=(0, 0), ui_state="death", evidence_ids=["death-evidence"]),
    )

    assert result.status is VerifierStatus.FAILURE
    assert result.failure_kind is FailureKind.DEATH
    assert result.evidence_ids == ["death-evidence"]


def test_visible_death_without_evidence_is_abstain() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(), observation(position=(0, 0), ui_state="death")
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_visible_death_takes_priority_over_apparent_target_reach() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(),
        observation(position=(10, 10), death_screen_visible=True, evidence_ids=["death-evidence"]),
    )

    assert result.status is VerifierStatus.FAILURE
    assert result.failure_kind is FailureKind.DEATH


def test_success_preserves_target_then_outcome_evidence_in_order() -> None:
    result = ReachTargetVerifier(target(evidence_ids=("target-1", "target-2"))).verify(
        before_observation(),
        observation(position=(10, 10), evidence_ids=["outcome-1", "outcome-2"]),
    )

    assert result.evidence_ids == ["target-1", "target-2", "outcome-1", "outcome-2"]


def test_success_does_not_duplicate_evidence_ids() -> None:
    result = ReachTargetVerifier(target(evidence_ids=("shared", "target-2"))).verify(
        before_observation(),
        observation(position=(10, 10), evidence_ids=["shared", "outcome-1", "shared"]),
    )

    assert result.evidence_ids == ["shared", "target-2", "outcome-1"]


def test_changed_screen_signature_outside_target_is_abstain() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(),
        observation(position=(0, 0), evidence_ids=["after-1"], screen_signature="changed"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_new_evidence_alone_outside_target_is_abstain() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(), observation(position=(0, 0), evidence_ids=["new-evidence"])
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_visible_text_and_ui_changes_outside_target_are_abstain() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(),
        observation(
            position=(0, 0),
            evidence_ids=["after-1"],
            ui_state="dialogue",
            visible_message_text="Changed visible text",
        ),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_verifier_result_has_no_reward_field() -> None:
    result = ReachTargetVerifier(target()).verify(
        before_observation(), observation(position=(10, 10), evidence_ids=["after-1"])
    )

    assert "reward" not in type(result).model_fields


def test_verifier_does_not_propose_primitive_actions() -> None:
    verifier = ReachTargetVerifier(target())

    assert not hasattr(verifier, "next_action")
    assert not hasattr(verifier, "propose_action")
    assert "fh_agent.body" not in inspect.getsource(reach_target_module)
    assert "PrimitiveAction" not in inspect.getsource(reach_target_module)


def test_negative_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ReachTargetVerifier(target(), tolerance_px=-0.1)


def test_identical_inputs_produce_identical_results() -> None:
    verifier = ReachTargetVerifier(target(), tolerance_px=2.0)
    before = before_observation()
    after = observation(position=(11, 11), evidence_ids=["after-1"])

    assert verifier.verify(before, after) == verifier.verify(before, after)
