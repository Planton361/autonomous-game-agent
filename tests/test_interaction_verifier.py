import inspect

import pytest

from fh_agent.manager.target_ref import VisibleObjectTarget, VisibleScreenPointTarget
from fh_agent.observation.schemas import ActionResult, Observation, VisibleTextSpan
from fh_agent.verifier import interaction as interaction_module
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.interaction import InteractVisibleObjectVerifier
from fh_agent.verifier.ports import OutcomeVerifier
from fh_agent.verifier.reach_target import ReachTargetVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def observation(
    *,
    ui_state: str = "field",
    message: str | None = None,
    spans: list[VisibleTextSpan] | None = None,
    evidence_ids: list[str] | None = None,
    death_screen_visible: bool | None = None,
    screen_signature: str | None = None,
    screenshot_id: str | None = None,
    last_action_result: ActionResult | None = None,
    visible_sprite_visual_hashes: list[str] | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state=ui_state,  # type: ignore[arg-type]
        visible_message_text=message,
        visible_text_spans=[] if spans is None else spans,
        death_screen_visible=death_screen_visible,
        screen_signature=screen_signature,
        screenshot_id=screenshot_id,
        last_action_result=last_action_result,
        visible_sprite_visual_hashes=(
            [] if visible_sprite_visual_hashes is None else visible_sprite_visual_hashes
        ),
        evidence_ids=[] if evidence_ids is None else evidence_ids,
    )


def target(*, evidence_ids: tuple[str, ...] = ("target-1",)) -> VisibleObjectTarget:
    return VisibleObjectTarget(
        target_id="visible-object-1",
        confidence=0.9,
        evidence_ids=evidence_ids,
        screen_position=(10, 20),
        visual_hash="visible-hash",
    )


def point_target() -> VisibleScreenPointTarget:
    return VisibleScreenPointTarget(
        target_id="visible-point-1",
        confidence=0.9,
        evidence_ids=("point-target-1",),
        screen_position=(10, 20),
    )


def run_verifier(
    verifier: OutcomeVerifier,
    before: Observation,
    after: Observation,
) -> VerifierResult:
    return verifier.verify(before, after)


def test_supported_ui_transitions_with_evidence_are_success() -> None:
    verifier = InteractVisibleObjectVerifier()
    before = observation(evidence_ids=["before-1"])

    for ui_state in ("dialogue", "menu", "combat"):
        result = verifier.verify(before, observation(ui_state=ui_state, evidence_ids=["after-1"]))

        assert result.status is VerifierStatus.SUCCESS
        assert result.failure_kind is None


def test_unchanged_state_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_first_visible_message_text_with_evidence_is_success() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(message="Visible outcome", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.SUCCESS


def test_first_visible_text_span_with_evidence_is_success() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(spans=[VisibleTextSpan(text="Visible outcome")], evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.SUCCESS


def test_existing_visible_text_replacement_alone_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(message="A", evidence_ids=["before-1"]),
        observation(message="B", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_new_evidence_alone_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_changed_screen_signature_alone_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"], screen_signature="first"),
        observation(evidence_ids=["after-1"], screen_signature="second"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_changed_screenshot_id_alone_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"], screenshot_id="first"),
        observation(evidence_ids=["after-1"], screenshot_id="second"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_executed_action_alone_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(
            evidence_ids=["after-1"],
            last_action_result=ActionResult(action="confirm", executed=True),
        ),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_executed_action_and_new_evidence_alone_abstain() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(
            evidence_ids=["new-evidence"],
            last_action_result=ActionResult(action="confirm", executed=True),
        ),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_visual_hash_change_alone_abstains() -> None:
    result = InteractVisibleObjectVerifier(target()).verify(
        observation(evidence_ids=["before-1"], visible_sprite_visual_hashes=["before-hash"]),
        observation(evidence_ids=["after-1"], visible_sprite_visual_hashes=["after-hash"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_missing_before_or_after_evidence_prevents_ui_transition_success() -> None:
    verifier = InteractVisibleObjectVerifier()

    assert (
        verifier.verify(
            observation(), observation(ui_state="dialogue", evidence_ids=["after-1"])
        ).status
        is VerifierStatus.ABSTAIN
    )
    assert (
        verifier.verify(
            observation(evidence_ids=["before-1"]), observation(ui_state="dialogue")
        ).status
        is VerifierStatus.ABSTAIN
    )


def test_visible_death_with_after_evidence_is_failure() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(ui_state="death", evidence_ids=["death-1", "death-1"]),
    )

    assert result.status is VerifierStatus.FAILURE
    assert result.failure_kind is FailureKind.DEATH
    assert result.evidence_ids == ["death-1"]


def test_visible_death_without_after_evidence_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]), observation(ui_state="death")
    )

    assert result.status is VerifierStatus.ABSTAIN
    assert result.failure_kind is None


def test_visible_death_takes_priority_over_apparent_interaction_success() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(
            ui_state="dialogue",
            death_screen_visible=True,
            message="Visible outcome",
            evidence_ids=["death-1"],
        ),
    )

    assert result.status is VerifierStatus.FAILURE
    assert result.failure_kind is FailureKind.DEATH


def test_explicit_target_success_evidence_is_target_before_after_deduplicated() -> None:
    result = InteractVisibleObjectVerifier(target(evidence_ids=("target-1", "shared"))).verify(
        observation(evidence_ids=["shared", "before-2"]),
        observation(ui_state="menu", evidence_ids=["shared", "after-1", "after-1"]),
    )

    assert result.evidence_ids == ["target-1", "shared", "before-2", "after-1"]


def test_targetless_success_evidence_is_before_then_after_deduplicated() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["shared", "before-2"]),
        observation(ui_state="combat", evidence_ids=["shared", "after-1", "after-1"]),
    )

    assert result.evidence_ids == ["shared", "before-2", "after-1"]


def test_unrelated_ui_change_abstains() -> None:
    result = InteractVisibleObjectVerifier().verify(
        observation(evidence_ids=["before-1"]),
        observation(ui_state="unknown", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_verifier_has_no_reward_or_primitive_action_authority() -> None:
    verifier = InteractVisibleObjectVerifier()

    assert "reward" not in type(verifier.verify(observation(), observation())).model_fields
    assert not hasattr(verifier, "next_action")
    assert not hasattr(verifier, "propose_action")
    source = inspect.getsource(interaction_module)
    assert "fh_agent.body" not in source


def test_identical_inputs_produce_identical_results() -> None:
    verifier = InteractVisibleObjectVerifier(target())
    before = observation(evidence_ids=["before-1"])
    after = observation(ui_state="dialogue", evidence_ids=["after-1"])

    assert verifier.verify(before, after) == verifier.verify(before, after)


def test_all_current_verifiers_use_the_common_outcome_verifier_port() -> None:
    interaction_before = observation(evidence_ids=["interaction-before"])
    interaction_after = observation(ui_state="dialogue", evidence_ids=["interaction-after"])
    dialogue_before = observation(
        ui_state="dialogue", message="First", evidence_ids=["dialogue-before"]
    )
    dialogue_after = observation(
        ui_state="dialogue", message="Second", evidence_ids=["dialogue-after"]
    )
    reach_before = observation(evidence_ids=["reach-before"])
    reach_after = Observation(
        run_id="run-1",
        player_screen_position=(10, 20),
        evidence_ids=["reach-after"],
    )

    results = [
        run_verifier(ReachTargetVerifier(point_target()), reach_before, reach_after),
        run_verifier(ContinueDialogueVerifier(), dialogue_before, dialogue_after),
        run_verifier(
            InteractVisibleObjectVerifier(target()),
            interaction_before,
            interaction_after,
        ),
        run_verifier(InteractVisibleObjectVerifier(), interaction_before, interaction_after),
    ]

    assert all(isinstance(result, VerifierResult) for result in results)
    assert all(result.status is VerifierStatus.SUCCESS for result in results)


def test_targets_are_bound_and_not_accepted_by_verify() -> None:
    before = observation(evidence_ids=["before-1"])
    after = observation(ui_state="dialogue", evidence_ids=["after-1"])

    with pytest.raises(TypeError):
        ReachTargetVerifier(point_target()).verify(before, after, point_target())
    with pytest.raises(TypeError):
        InteractVisibleObjectVerifier(target()).verify(before, after, target=target())


def test_outcome_verifier_port_has_no_action_reward_or_input_surface() -> None:
    assert not hasattr(OutcomeVerifier, "next_action")
    assert not hasattr(OutcomeVerifier, "reward")
    assert not hasattr(OutcomeVerifier, "execute")
