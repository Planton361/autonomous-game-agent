import inspect

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.manager.reward_computer import RewardProfile
from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.skill_contracts import SkillContract, SkillStep
from fh_agent.manager.skill_runner import RunnableSkill, SkillRunner
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.manager.verifier_catalog import VerifierCatalog
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


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


class FixedVerifier:
    def __init__(self, result: VerifierResult) -> None:
        self.result = result
        self.calls: list[tuple[Observation, Observation]] = []

    def verify(self, before: Observation, after: Observation) -> VerifierResult:
        self.calls.append((before, after))
        return self.result


class NoEvaluateSkill:
    def __init__(
        self,
        *,
        max_steps: int = 2,
        reward_profile: RewardProfile | None = None,
        failure_detector: list[str] | None = None,
    ) -> None:
        self._contract = SkillContract(
            skill_name="fake_skill",
            allowed_actions=[PrimitiveAction.WAIT],
            preconditions=["dialogue_visible"],
            success_detector=["dialogue_visible"],
            failure_detector=[] if failure_detector is None else failure_detector,  # type: ignore[arg-type]
            max_steps=max_steps,
            reward_profile=reward_profile or RewardProfile(),
        )

    @property
    def contract(self) -> SkillContract:
        return self._contract

    def can_start(self, observation: Observation) -> bool:
        return True

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        return SkillStep(
            skill_name=self.contract.skill_name,
            action=PrimitiveAction.WAIT,
            step_index=step_index,
            reason="fake_wait",
            evidence_ids=observation.evidence_ids,
        )


class ExplodingEvaluateSkill(NoEvaluateSkill):
    def evaluate(self) -> None:
        raise AssertionError("SkillRunner must not call Body evaluate")


def test_runner_rejects_continue_dialogue_when_start_observation_is_not_dialogue() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        [field_observation()],
        verifier=ContinueDialogueVerifier(),
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "precondition_failed"
    assert run.steps == []
    assert run.verifier_result is None


def test_runner_preserves_empty_sequence_compatibility_without_verification() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        [],
        verifier=ContinueDialogueVerifier(),
    )

    assert run.skill_result.failure_reason == "empty_observation_sequence"
    assert run.verifier_result is None


def test_runner_returns_success_when_dialogue_text_changes() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        [
            dialogue_observation("First", "e1"),
            dialogue_observation("Second", "e2"),
        ],
        verifier=ContinueDialogueVerifier(),
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
        verifier=ContinueDialogueVerifier(),
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
        verifier=ContinueDialogueVerifier(),
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "timeout"
    assert len(run.steps) == 2


def test_runner_stops_when_observation_sequence_is_exhausted_after_start() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=3),
        [dialogue_observation("Only", "e1")],
        verifier=ContinueDialogueVerifier(),
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
        verifier=ContinueDialogueVerifier(),
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
        verifier=ContinueDialogueVerifier(),
    )

    assert [step.action for step in run.steps] == [
        PrimitiveAction.CONFIRM,
        PrimitiveAction.CONFIRM,
    ]
    assert all("key_sequence" not in step.model_dump() for step in run.steps)


def test_runner_succeeds_with_a_skill_that_has_no_evaluate_method() -> None:
    verifier_result = VerifierResult(
        status=VerifierStatus.SUCCESS,
        evidence_ids=["verified-evidence"],
    )
    verifier = FixedVerifier(verifier_result)

    run = SkillRunner().run(
        NoEvaluateSkill(),
        [field_observation("before"), field_observation("after")],
        verifier=verifier,
    )

    assert run.skill_result.success
    assert run.skill_result.evidence_ids == ["verified-evidence"]
    assert run.verifier_result is verifier_result


def test_runner_never_calls_an_exploding_body_evaluate_method() -> None:
    run = SkillRunner().run(
        ExplodingEvaluateSkill(),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS)),
    )

    assert run.skill_result.success


def test_runner_maps_canonical_failure_kinds_to_legacy_reasons() -> None:
    generic_failure = SkillRunner().run(
        NoEvaluateSkill(),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(
            VerifierResult(
                status=VerifierStatus.FAILURE,
                failure_kind=FailureKind.SKILL_FAILED,
                evidence_ids=["failure-evidence"],
            )
        ),
    )
    death_failure = SkillRunner().run(
        NoEvaluateSkill(),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(
            VerifierResult(status=VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH)
        ),
    )

    assert generic_failure.skill_result.failure_reason == "skill_failed"
    assert generic_failure.skill_result.evidence_ids == ["failure-evidence"]
    assert death_failure.skill_result.failure_reason == "death_screen"


def test_runner_abstain_and_progress_are_non_terminal() -> None:
    abstain_verifier = FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN))
    progress_verifier = FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS))
    observations = [
        field_observation("before"),
        field_observation("during"),
        field_observation("after"),
    ]

    abstain_run = SkillRunner().run(NoEvaluateSkill(), observations, verifier=abstain_verifier)
    progress_run = SkillRunner().run(NoEvaluateSkill(), observations, verifier=progress_verifier)

    assert abstain_run.skill_result.failure_reason == "timeout"
    assert progress_run.skill_result.failure_reason == "timeout"
    assert abstain_run.verifier_result is abstain_verifier.result
    assert progress_run.verifier_result is progress_verifier.result
    assert len(abstain_verifier.calls) == 2
    assert len(progress_verifier.calls) == 2


def test_reward_cannot_override_abstain_or_verified_success() -> None:
    positive_abstain = SkillRunner().run(
        NoEvaluateSkill(
            max_steps=1,
            reward_profile=RewardProfile(
                visible_text_changed=3.0,
                failure=0.0,
                timeout=0.0,
                no_change=0.0,
            ),
        ),
        [
            field_observation("before"),
            Observation(
                run_id="run-1",
                ui_state="field",
                visible_message_text="New",
                evidence_ids=["after"],
            ),
        ],
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    negative_success = SkillRunner().run(
        NoEvaluateSkill(reward_profile=RewardProfile(no_change=-3.0)),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS)),
    )

    assert (
        positive_abstain.skill_result.reward is not None
        and positive_abstain.skill_result.reward > 0
    )
    assert not positive_abstain.skill_result.success
    assert (
        negative_success.skill_result.reward is not None
        and negative_success.skill_result.reward < 0
    )
    assert negative_success.skill_result.success


def test_manager_selected_verifier_runs_through_skill_runner() -> None:
    task = TaskSpec(
        task_id="task-1",
        selected_skill="continue_dialogue",
        goal="Continue visible dialogue.",
        timeout_steps=3,
        reward_profile=default_reward_profile_for_skill("continue_dialogue"),
    )
    verifier = VerifierCatalog().for_task(task)

    run = SkillRunner().run(
        ContinueDialogueSkill(),
        [dialogue_observation("First", "before"), dialogue_observation("Second", "after")],
        verifier=verifier,
    )

    assert run.skill_result.success
    assert run.verifier_result is not None


def test_runner_has_no_body_evaluate_dependency() -> None:
    source = inspect.getsource(SkillRunner)

    assert "skill.evaluate(" not in source
    assert "evaluate" not in inspect.getsource(RunnableSkill)
