from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation


def dialogue_observation(text: str, evidence_id: str) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        message_window_visible=True,
        visible_message_text=text,
        evidence_ids=[evidence_id],
    )


def field_observation(evidence_id: str = "field-evidence") -> Observation:
    return Observation(run_id="run-1", ui_state="field", evidence_ids=[evidence_id])


def test_runner_rejects_continue_dialogue_when_start_observation_is_not_dialogue() -> None:
    run = SkillRunner().run(ContinueDialogueSkill(), [field_observation()])

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "precondition_failed"
    assert run.steps == []


def test_runner_returns_success_when_dialogue_text_changes() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        [
            dialogue_observation("First", "e1"),
            dialogue_observation("Second", "e2"),
        ],
    )

    assert run.skill_result.success
    assert run.skill_result.failure_reason is None
    assert run.skill_result.evidence_ids == ["e1", "e2"]


def test_runner_returns_success_when_dialogue_ends() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        [
            dialogue_observation("Done", "e1"),
            field_observation("e2"),
        ],
    )

    assert run.skill_result.success
    assert run.skill_result.failure_reason is None


def test_runner_returns_timeout_failure_at_max_steps() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=2),
        [
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
        ],
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "timeout"
    assert len(run.steps) == 2


def test_runner_stops_when_observation_sequence_is_exhausted_after_start() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=3), [dialogue_observation("Only", "e1")]
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "observation_sequence_exhausted"
    assert len(run.steps) == 1


def test_runner_logs_skill_result_to_event_log_path(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    runner = SkillRunner(event_log_path=event_log_path, run_id="run-1")

    run = runner.run(
        ContinueDialogueSkill(),
        [
            dialogue_observation("First", "e1"),
            dialogue_observation("Second", "e2"),
        ],
    )

    records = EventLogger(event_log_path, run_id="run-1").read_all()
    assert run.event_record is not None
    assert len(records) == 1
    assert records[0].event_type == "skill_result"
    assert records[0].payload["skill_name"] == "continue_dialogue"
    assert records[0].evidence_ids == ["e1", "e2"]


def test_runner_collects_declarative_primitive_actions_without_execution() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=2),
        [
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
        ],
    )

    assert [step.action for step in run.steps] == [
        PrimitiveAction.CONFIRM,
        PrimitiveAction.CONFIRM,
    ]
    assert all("key_sequence" not in step.model_dump() for step in run.steps)
