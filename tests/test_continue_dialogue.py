import json

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation


def dialogue_observation(text: str, evidence_id: str) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text=text,
        message_window_visible=True,
        evidence_ids=[evidence_id],
    )


def test_continue_dialogue_accepts_dialogue_observation() -> None:
    skill = ContinueDialogueSkill()

    assert skill.can_start(dialogue_observation("Hello", "e1"))


def test_continue_dialogue_rejects_field_observation_as_precondition() -> None:
    skill = ContinueDialogueSkill()
    observation = Observation(run_id="run-1", ui_state="field", evidence_ids=["e1"])

    assert not skill.can_start(observation)


def test_continue_dialogue_emits_primitive_action_only() -> None:
    skill = ContinueDialogueSkill()
    step = skill.next_action(dialogue_observation("Hello", "e1"), step_index=0)

    assert step.action is PrimitiveAction.CONFIRM
    assert step.model_dump() == {
        "skill_name": "continue_dialogue",
        "action": "confirm",
        "step_index": 0,
        "reason": "dialogue_visible",
        "evidence_ids": ["e1"],
    }


def test_continue_dialogue_waits_when_precondition_is_not_met() -> None:
    skill = ContinueDialogueSkill()
    step = skill.next_action(Observation(run_id="run-1", ui_state="field"), step_index=0)

    assert step.action is PrimitiveAction.WAIT
    assert step.reason == "precondition_not_met"


def test_continue_dialogue_succeeds_when_visible_text_changes() -> None:
    skill = ContinueDialogueSkill()

    result = skill.evaluate(
        dialogue_observation("First", "e1"),
        dialogue_observation("Second", "e2"),
        steps_taken=1,
    )

    assert result.success
    assert result.failure_reason is None
    assert result.reward is not None
    assert result.reward > 0
    assert result.evidence_ids == ["e1", "e2"]


def test_continue_dialogue_succeeds_when_dialogue_closes() -> None:
    skill = ContinueDialogueSkill()

    result = skill.evaluate(
        dialogue_observation("Done", "e1"),
        Observation(run_id="run-1", ui_state="field", evidence_ids=["e2"]),
        steps_taken=1,
    )

    assert result.success
    assert result.failure_reason is None


def test_continue_dialogue_fails_on_timeout() -> None:
    skill = ContinueDialogueSkill(max_steps=2)
    before = dialogue_observation("Same", "e1")
    after = dialogue_observation("Same", "e1")

    result = skill.evaluate(before, after, steps_taken=2)

    assert not result.success
    assert result.failure_reason == "timeout"
    assert result.reward is not None
    assert result.reward < 0


def test_continue_dialogue_skill_result_is_jsonl_loggable(tmp_path) -> None:
    skill = ContinueDialogueSkill()
    result = skill.evaluate(
        dialogue_observation("First", "e1"),
        dialogue_observation("Second", "e2"),
        steps_taken=1,
    )
    logger = EventLogger(tmp_path / "events.jsonl", run_id="run-1")

    record = logger.append(
        "skill_result",
        payload=json.loads(result.model_dump_json()),
        evidence_ids=result.evidence_ids,
    )

    assert record.event_type == "skill_result"
    assert logger.read_all()[0].payload["skill_name"] == "continue_dialogue"
