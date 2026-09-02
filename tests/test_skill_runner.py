import inspect

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.skill_contracts import SkillContract, SkillStep
from fh_agent.manager.skill_runner import RunnableSkill, SkillRunner
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.manager.verifier_catalog import VerifierCatalog
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def dialogue_observation(
    text: str,
    evidence_id: str,
    *,
    observation_id: str | None = None,
) -> Observation:
    return Observation(
        observation_id=observation_id,
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


class SequenceVerifier:
    def __init__(self, results: list[VerifierResult]) -> None:
        self.results = results
        self.calls: list[tuple[Observation, Observation]] = []

    def verify(self, before: Observation, after: Observation) -> VerifierResult:
        self.calls.append((before, after))
        return self.results[len(self.calls) - 1]


class NoEvaluateSkill:
    def __init__(
        self,
        *,
        max_steps: int = 2,
        failure_detector: list[str] | None = None,
    ) -> None:
        self._contract = SkillContract(
            skill_name="fake_skill",
            allowed_actions=[PrimitiveAction.WAIT],
            preconditions=["dialogue_visible"],
            success_detector=["dialogue_visible"],
            failure_detector=[] if failure_detector is None else failure_detector,  # type: ignore[arg-type]
            max_steps=max_steps,
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
            dialogue_observation("First", "e1", observation_id="before-observation"),
            dialogue_observation("Second", "e2", observation_id="after-observation"),
        ],
        verifier=ContinueDialogueVerifier(),
    )

    records = EventLogger(event_log_path, run_id="run-1").read_all()
    assert run.event_record is not None
    assert records == [*run.verifier_event_records, run.event_record]
    assert [record.event_type for record in records] == ["verifier_result", "skill_result"]
    assert records[0].payload["verifier_result"] == {
        "status": "success",
        "failure_kind": None,
        "evidence_ids": ["e1", "e2"],
    }
    assert records[0].payload["steps_taken"] == 1
    assert records[0].payload["before_observation_id"] == "before-observation"
    assert records[0].payload["after_observation_id"] == "after-observation"
    assert records[1].payload["skill_name"] == "continue_dialogue"
    assert records[1].evidence_ids == ["e1", "e2"]
    assert run.skill_result.reward is None


def test_runner_logs_terminal_failure_after_its_verifier_event(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    verifier_result = VerifierResult(
        status=VerifierStatus.FAILURE,
        failure_kind=FailureKind.SKILL_FAILED,
        evidence_ids=["failure-evidence"],
    )

    run = SkillRunner(event_log_path=event_log_path, run_id="run-1").run(
        NoEvaluateSkill(),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(verifier_result),
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == ["verifier_result", "skill_result"]
    assert VerifierResult.model_validate(records[0].payload["verifier_result"]) == verifier_result
    assert run.verifier_event_records == [records[0]]
    assert run.event_record == records[1]
    assert run.skill_result.failure_reason == "skill_failed"
    assert run.skill_result.reward is None


def test_runner_logs_non_terminal_abstain_and_progress(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    runner = SkillRunner(event_log_path=event_log_path, run_id="run-1")
    results = [
        VerifierResult(status=VerifierStatus.ABSTAIN),
        VerifierResult(status=VerifierStatus.PROGRESS),
    ]

    runs = [
        runner.run(
            NoEvaluateSkill(max_steps=1),
            [field_observation("before"), field_observation("after")],
            verifier=FixedVerifier(result),
        )
        for result in results
    ]
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == [
        "verifier_result",
        "skill_result",
        "verifier_result",
        "skill_result",
    ]
    assert [
        VerifierResult.model_validate(records[index].payload["verifier_result"]) for index in (0, 2)
    ] == results
    assert all(len(run.verifier_event_records) == 1 for run in runs)
    assert all(run.skill_result.reward is None for run in runs)


def test_runner_logs_each_timeout_verification_in_order(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    verifier = SequenceVerifier(
        [
            VerifierResult(status=VerifierStatus.ABSTAIN, evidence_ids=["first"]),
            VerifierResult(status=VerifierStatus.PROGRESS, evidence_ids=["second"]),
        ]
    )

    run = SkillRunner(event_log_path=event_log_path, run_id="run-1").run(
        NoEvaluateSkill(max_steps=2),
        [field_observation("before"), field_observation("during"), field_observation("after")],
        verifier=verifier,
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == [
        "verifier_result",
        "verifier_result",
        "skill_result",
    ]
    assert [record.payload["steps_taken"] for record in records[:-1]] == [1, 2]
    assert [
        VerifierResult.model_validate(record.payload["verifier_result"]) for record in records[:-1]
    ] == verifier.results
    assert run.verifier_event_records == records[:-1]
    assert run.verifier_result == verifier.results[-1]
    assert run.event_record == records[-1]
    assert run.skill_result.failure_reason == "timeout"
    assert run.skill_result.reward is None


def test_runner_logs_final_non_terminal_verifier_result_before_exhaustion(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    verifier_result = VerifierResult(status=VerifierStatus.ABSTAIN, evidence_ids=["latest"])

    run = SkillRunner(event_log_path=event_log_path, run_id="run-1").run(
        NoEvaluateSkill(),
        [field_observation("only")],
        verifier=FixedVerifier(verifier_result),
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == ["verifier_result", "skill_result"]
    assert run.verifier_event_records == [records[0]]
    assert run.verifier_result == verifier_result
    assert run.skill_result.failure_reason == "observation_sequence_exhausted"
    assert run.skill_result.reward is None


def test_runner_logs_no_verifier_result_before_empty_or_precondition_failure(tmp_path) -> None:
    empty_path = tmp_path / "empty.jsonl"
    precondition_path = tmp_path / "precondition.jsonl"

    empty_run = SkillRunner(event_log_path=empty_path, run_id="run-1").run(
        ContinueDialogueSkill(),
        [],
        verifier=ContinueDialogueVerifier(),
    )
    precondition_run = SkillRunner(event_log_path=precondition_path, run_id="run-1").run(
        ContinueDialogueSkill(),
        [field_observation()],
        verifier=ContinueDialogueVerifier(),
    )

    assert empty_run.verifier_event_records == []
    assert precondition_run.verifier_event_records == []
    assert [record.event_type for record in EventLogger(empty_path, run_id="run-1").read_all()] == [
        "skill_result"
    ]
    assert [
        record.event_type for record in EventLogger(precondition_path, run_id="run-1").read_all()
    ] == ["skill_result"]


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
    assert run.verifier_event_records == []


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


def test_runner_emits_no_reward_for_verified_success_or_failure() -> None:
    success = SkillRunner().run(
        NoEvaluateSkill(),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS)),
    )
    failure = SkillRunner().run(
        NoEvaluateSkill(),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(
            VerifierResult(
                status=VerifierStatus.FAILURE,
                failure_kind=FailureKind.SKILL_FAILED,
            )
        ),
    )

    assert success.skill_result.reward is None
    assert failure.skill_result.reward is None


def test_runner_emits_no_reward_for_abstain_and_progress_timeout_or_exhaustion() -> None:
    timeout_observations = [field_observation("before"), field_observation("after")]
    exhaustion_observations = [field_observation("only")]

    abstain_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        timeout_observations,
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    abstain_exhaustion = SkillRunner().run(
        NoEvaluateSkill(),
        exhaustion_observations,
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    progress_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        timeout_observations,
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS)),
    )
    progress_exhaustion = SkillRunner().run(
        NoEvaluateSkill(),
        exhaustion_observations,
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS)),
    )

    assert abstain_timeout.skill_result.failure_reason == "timeout"
    assert abstain_exhaustion.skill_result.failure_reason == "observation_sequence_exhausted"
    assert progress_timeout.skill_result.failure_reason == "timeout"
    assert progress_exhaustion.skill_result.failure_reason == "observation_sequence_exhausted"
    assert all(
        run.skill_result.reward is None
        for run in (
            abstain_timeout,
            abstain_exhaustion,
            progress_timeout,
            progress_exhaustion,
        )
    )


def test_runner_raw_observation_changes_cannot_create_reward() -> None:
    visible_text_change = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
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
    ui_state_change = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        [dialogue_observation("Before", "before"), field_observation("after")],
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    new_evidence = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        [field_observation("before"), field_observation("after")],
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )

    assert visible_text_change.skill_result.reward is None
    assert ui_state_change.skill_result.reward is None
    assert new_evidence.skill_result.reward is None


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

    assert "RewardComputer" not in source
    assert "VerifierCatalog" not in source
    assert "skill.evaluate(" not in source
    assert "evaluate" not in inspect.getsource(RunnableSkill)
