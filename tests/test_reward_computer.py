from fh_agent.manager.reward_computer import RewardComputer
from fh_agent.observation.schemas import Observation


def test_reward_computer_rewards_dialogue_progress() -> None:
    before = Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="First line",
        evidence_ids=["e1"],
    )
    after = Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="Second line",
        evidence_ids=["e2"],
    )

    reward = RewardComputer().compute(before, after)

    assert reward.total > 0
    assert "dialogue_continued" in reward.terms
    assert "visible_text_changed" in reward.terms


def test_reward_computer_penalizes_timeout() -> None:
    before = Observation(run_id="run-1", ui_state="dialogue", visible_message_text="Same")
    after = Observation(run_id="run-1", ui_state="dialogue", visible_message_text="Same")

    reward = RewardComputer().compute(before, after, timeout=True)

    assert reward.total < 0
    assert reward.terms["timeout"] < 0
    assert reward.terms["no_change"] < 0


def test_reward_computer_uses_generic_ui_state_changed_term() -> None:
    before = Observation(run_id="run-1", ui_state="dialogue", visible_message_text="Done")
    after = Observation(run_id="run-1", ui_state="field")

    reward = RewardComputer().compute(before, after)

    assert "ui_state_changed" in reward.terms
    assert reward.total > 0
