import inspect

from fh_agent.observation.schemas import Observation, VisibleTextSpan
from fh_agent.verifier import dialogue as dialogue_module
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierStatus


def observation(
    *,
    ui_state: str = "dialogue",
    message: str | None = None,
    spans: list[VisibleTextSpan] | None = None,
    evidence_ids: list[str] | None = None,
    message_window_visible: bool | None = None,
    death_screen_visible: bool | None = None,
    screen_signature: str | None = None,
    screenshot_id: str | None = None,
) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state=ui_state,  # type: ignore[arg-type]
        visible_message_text=message,
        visible_text_spans=[] if spans is None else spans,
        message_window_visible=message_window_visible,
        death_screen_visible=death_screen_visible,
        screen_signature=screen_signature,
        screenshot_id=screenshot_id,
        evidence_ids=[] if evidence_ids is None else evidence_ids,
    )


def test_visible_dialogue_text_change_with_evidence_is_success() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="First", evidence_ids=["before-1"]),
        observation(message="Second", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.SUCCESS
    assert result.failure_kind is None


def test_visible_text_spans_can_establish_dialogue_text_change() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(spans=[VisibleTextSpan(text="First")], evidence_ids=["before-1"]),
        observation(spans=[VisibleTextSpan(text="Second")], evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.SUCCESS


def test_visible_dialogue_close_with_evidence_is_success() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Done", evidence_ids=["before-1"]),
        observation(ui_state="field", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.SUCCESS


def test_identical_visible_dialogue_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Same", evidence_ids=["before-1"]),
        observation(message="Same", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_new_evidence_alone_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Same", evidence_ids=["before-1"]),
        observation(message="Same", evidence_ids=["new-evidence"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_changed_screen_signature_alone_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Same", evidence_ids=["before-1"], screen_signature="first"),
        observation(message="Same", evidence_ids=["after-1"], screen_signature="second"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_changed_screenshot_id_alone_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Same", evidence_ids=["before-1"], screenshot_id="first"),
        observation(message="Same", evidence_ids=["after-1"], screenshot_id="second"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_before_not_dialogue_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(ui_state="field", evidence_ids=["before-1"]),
        observation(message="New dialogue", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_text_change_without_before_evidence_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="First"),
        observation(message="Second", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_text_change_without_after_evidence_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="First", evidence_ids=["before-1"]),
        observation(message="Second"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_dialogue_close_without_before_evidence_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Done"),
        observation(ui_state="field", evidence_ids=["after-1"]),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_dialogue_close_without_after_evidence_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Done", evidence_ids=["before-1"]),
        observation(ui_state="field"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_visible_death_with_evidence_is_failure() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Done", evidence_ids=["before-1"]),
        observation(ui_state="death", evidence_ids=["death-evidence"]),
    )

    assert result.status is VerifierStatus.FAILURE
    assert result.failure_kind is FailureKind.DEATH
    assert result.evidence_ids == ["death-evidence"]


def test_visible_death_without_evidence_is_abstain() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Done", evidence_ids=["before-1"]),
        observation(ui_state="death"),
    )

    assert result.status is VerifierStatus.ABSTAIN


def test_visible_death_takes_priority_over_dialogue_close() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="Done", evidence_ids=["before-1"]),
        observation(ui_state="death", evidence_ids=["death-evidence"]),
    )

    assert result.status is VerifierStatus.FAILURE
    assert result.failure_kind is FailureKind.DEATH


def test_success_evidence_preserves_before_then_after_order() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="First", evidence_ids=["before-1", "before-2"]),
        observation(message="Second", evidence_ids=["after-1", "after-2"]),
    )

    assert result.evidence_ids == ["before-1", "before-2", "after-1", "after-2"]


def test_success_evidence_deduplicates_deterministically() -> None:
    result = ContinueDialogueVerifier().verify(
        observation(message="First", evidence_ids=["shared", "before-2"]),
        observation(message="Second", evidence_ids=["shared", "after-1", "shared"]),
    )

    assert result.evidence_ids == ["shared", "before-2", "after-1"]


def test_verifier_has_no_reward_or_primitive_action_authority() -> None:
    verifier = ContinueDialogueVerifier()

    assert not hasattr(verifier, "reward")
    assert not hasattr(verifier, "next_action")
    assert not hasattr(verifier, "propose_action")
    assert "fh_agent.body" not in inspect.getsource(dialogue_module)
    assert "PrimitiveAction" not in inspect.getsource(dialogue_module)


def test_identical_inputs_produce_identical_output() -> None:
    verifier = ContinueDialogueVerifier()
    before = observation(message="First", evidence_ids=["before-1"])
    after = observation(message="Second", evidence_ids=["after-1"])

    assert verifier.verify(before, after) == verifier.verify(before, after)
