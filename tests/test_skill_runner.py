import inspect

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.manager.reward_profiles import (
    RewardProfile,
    RewardTerm,
    default_reward_profile_for_skill,
)
from fh_agent.manager.skill_contracts import SkillContract, SkillStep
from fh_agent.manager.skill_runner import RunnableSkill, SkillRunner
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.manager.verified_reward import VerifiedRewardBreakdown, VerifiedRewardContribution
from fh_agent.manager.verifier_catalog import VerifierCatalog
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import (
    ObservationSourceExhausted,
    SequenceObservationSource,
)
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus

TEST_REWARD_PROFILE = RewardProfile(
    profile_name="test_profile",
    terms=(RewardTerm(name="skill_success", weight=0.0),),
)


def reward_profile(*terms: tuple[str, float]) -> RewardProfile:
    return RewardProfile(
        profile_name="runner_test_profile",
        terms=tuple(RewardTerm(name=name, weight=weight) for name, weight in terms),
    )


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


def observation_source(*observations: Observation) -> SequenceObservationSource:
    return SequenceObservationSource(observations)


class RecordingObservationSource:
    def __init__(self, *observations: Observation) -> None:
        self._observations = observations
        self._next_index = 0
        self.observe_calls = 0

    def observe(self) -> Observation:
        self.observe_calls += 1
        if self._next_index >= len(self._observations):
            raise ObservationSourceExhausted

        observation = self._observations[self._next_index]
        self._next_index += 1
        return observation


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
        reward_profile: RewardProfile = TEST_REWARD_PROFILE,
    ) -> None:
        self._contract = SkillContract(
            skill_name="fake_skill",
            allowed_actions=[PrimitiveAction.WAIT],
            preconditions=["dialogue_visible"],
            success_detector=["dialogue_visible"],
            failure_detector=[] if failure_detector is None else failure_detector,  # type: ignore[arg-type]
            max_steps=max_steps,
            reward_profile=reward_profile,
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


class RecordingSkill(NoEvaluateSkill):
    def __init__(self, *, can_start: bool = True, max_steps: int = 2) -> None:
        super().__init__(max_steps=max_steps)
        self._can_start = can_start
        self.can_start_observations: list[Observation] = []
        self.next_action_observations: list[Observation] = []

    def can_start(self, observation: Observation) -> bool:
        self.can_start_observations.append(observation)
        return self._can_start

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        self.next_action_observations.append(observation)
        return super().next_action(observation, step_index=step_index)


class ExplodingEvaluateSkill(NoEvaluateSkill):
    def evaluate(self) -> None:
        raise AssertionError("SkillRunner must not call Body evaluate")


def test_runner_rejects_continue_dialogue_when_start_observation_is_not_dialogue() -> None:
    source = RecordingObservationSource(
        field_observation(),
        dialogue_observation("unused", "unused"),
    )
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        source,
        verifier=verifier,
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "precondition_failed"
    assert run.steps == []
    assert run.verifier_result is None
    assert source.observe_calls == 1
    assert verifier.calls == []
    assert run.verified_reward_breakdowns == []


def test_runner_preserves_empty_sequence_compatibility_without_verification() -> None:
    source = RecordingObservationSource()
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        source,
        verifier=verifier,
    )

    assert run.skill_result.failure_reason == "empty_observation_sequence"
    assert run.verifier_result is None
    assert source.observe_calls == 1
    assert verifier.calls == []
    assert run.verified_reward_breakdowns == []


def test_runner_pulls_observations_without_prefetching_after_terminal_success() -> None:
    start = field_observation("start")
    after = field_observation("after")
    source = RecordingObservationSource(start, after, field_observation("unused"))
    skill = RecordingSkill()
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))

    run = SkillRunner().run(skill, source, verifier=verifier)

    assert run.skill_result.success
    assert source.observe_calls == 2
    assert skill.can_start_observations[0] is start
    assert skill.next_action_observations[0] is start
    assert verifier.calls[0][0] is start
    assert verifier.calls[0][1] is after


def test_runner_stops_pulling_after_terminal_failure() -> None:
    start = field_observation("start")
    after = field_observation("after")
    source = RecordingObservationSource(start, after, field_observation("unused"))
    verifier = FixedVerifier(
        VerifierResult(status=VerifierStatus.FAILURE, failure_kind=FailureKind.SKILL_FAILED)
    )

    run = SkillRunner().run(NoEvaluateSkill(), source, verifier=verifier)

    assert run.skill_result.failure_reason == "skill_failed"
    assert source.observe_calls == 2
    assert verifier.calls == [(start, after)]


def test_runner_verifies_latest_observation_when_source_exhausts_after_step() -> None:
    start = field_observation("start")
    source = RecordingObservationSource(start)
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN))

    run = SkillRunner().run(NoEvaluateSkill(), source, verifier=verifier)

    assert run.skill_result.failure_reason == "observation_sequence_exhausted"
    assert source.observe_calls == 2
    assert verifier.calls == [(start, start)]
    assert len(run.verified_reward_breakdowns) == 1


def test_runner_preserves_terminal_verifier_results_when_source_exhausts_after_step() -> None:
    cases = [
        (VerifierResult(status=VerifierStatus.SUCCESS), True, None),
        (
            VerifierResult(status=VerifierStatus.FAILURE, failure_kind=FailureKind.SKILL_FAILED),
            False,
            "skill_failed",
        ),
    ]

    for verifier_result, expected_success, expected_reason in cases:
        source = RecordingObservationSource(field_observation("start"))
        run = SkillRunner().run(
            NoEvaluateSkill(),
            source,
            verifier=FixedVerifier(verifier_result),
        )

        assert run.skill_result.success is expected_success
        assert run.skill_result.failure_reason == expected_reason
        assert source.observe_calls == 2


def test_runner_stops_at_max_steps_without_extra_observation_pull() -> None:
    start = field_observation("start")
    first = field_observation("first")
    source = RecordingObservationSource(
        start,
        first,
        field_observation("second"),
        field_observation("unused"),
    )
    skill = RecordingSkill(max_steps=2)
    verifier = SequenceVerifier(
        [
            VerifierResult(status=VerifierStatus.ABSTAIN),
            VerifierResult(status=VerifierStatus.PROGRESS),
        ]
    )

    run = SkillRunner().run(skill, source, verifier=verifier)

    assert run.skill_result.failure_reason == "timeout"
    assert source.observe_calls == 3
    assert len(verifier.calls) == 2
    assert skill.next_action_observations[0] is start
    assert skill.next_action_observations[1] is first


def test_runner_has_no_precomputed_observation_sequence_dependency() -> None:
    source = inspect.getsource(SkillRunner)

    assert "Sequence[Observation]" not in source
    assert "len(observations)" not in source
    assert "observations[" not in source
    assert "SequenceObservationSource" not in source
    assert "InputExecutor" not in source
    assert "DryRunInputBackend" not in source
    assert ".execute(" not in source


def test_runner_returns_success_when_dialogue_text_changes() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        observation_source(
            dialogue_observation("First", "e1"),
            dialogue_observation("Second", "e2"),
        ),
        verifier=ContinueDialogueVerifier(),
    )

    assert run.skill_result.success
    assert run.skill_result.failure_reason is None
    assert run.skill_result.evidence_ids == ["e1", "e2"]


def test_runner_returns_success_when_dialogue_ends() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        observation_source(
            dialogue_observation("Done", "e1"),
            field_observation("e2"),
        ),
        verifier=ContinueDialogueVerifier(),
    )

    assert run.skill_result.success
    assert run.skill_result.failure_reason is None


def test_runner_returns_timeout_failure_at_max_steps() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=2),
        observation_source(
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
        ),
        verifier=ContinueDialogueVerifier(),
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "timeout"
    assert len(run.steps) == 2


def test_runner_stops_when_observation_sequence_is_exhausted_after_start() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=3),
        observation_source(dialogue_observation("Only", "e1")),
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
        observation_source(
            dialogue_observation("First", "e1", observation_id="before-observation"),
            dialogue_observation("Second", "e2", observation_id="after-observation"),
        ),
        verifier=ContinueDialogueVerifier(),
    )

    records = EventLogger(event_log_path, run_id="run-1").read_all()
    assert run.event_record is not None
    assert records == [
        *[
            item
            for pair in zip(run.verifier_event_records, run.reward_event_records, strict=True)
            for item in pair
        ],
        run.event_record,
    ]
    assert [record.event_type for record in records] == [
        "verifier_result",
        "verified_reward",
        "skill_result",
    ]
    assert records[0].payload["verifier_result"] == {
        "status": "success",
        "failure_kind": None,
        "evidence_ids": ["e1", "e2"],
    }
    assert records[0].payload["steps_taken"] == 1
    assert records[0].payload["before_observation_id"] == "before-observation"
    assert records[0].payload["after_observation_id"] == "after-observation"
    assert records[1].payload["verifier_event_id"] == records[0].event_id
    assert records[1].evidence_ids == ["e1", "e2"]
    assert (
        VerifiedRewardBreakdown.model_validate(records[1].payload["verified_reward"])
        == (run.verified_reward_breakdowns[0])
    )
    assert records[2].payload["skill_name"] == "continue_dialogue"
    assert records[2].evidence_ids == ["e1", "e2"]
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
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(verifier_result),
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == [
        "verifier_result",
        "verified_reward",
        "skill_result",
    ]
    assert VerifierResult.model_validate(records[0].payload["verifier_result"]) == verifier_result
    assert run.verifier_event_records == [records[0]]
    assert run.reward_event_records == [records[1]]
    assert run.event_record == records[2]
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
            observation_source(field_observation("before"), field_observation("after")),
            verifier=FixedVerifier(result),
        )
        for result in results
    ]
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == [
        "verifier_result",
        "verified_reward",
        "skill_result",
        "verifier_result",
        "verified_reward",
        "skill_result",
    ]
    assert [
        VerifierResult.model_validate(records[index].payload["verifier_result"]) for index in (0, 3)
    ] == results
    assert all(len(run.verifier_event_records) == 1 for run in runs)
    assert all(len(run.verified_reward_breakdowns) == 1 for run in runs)
    assert all(len(run.reward_event_records) == 1 for run in runs)
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
        observation_source(
            field_observation("before"),
            field_observation("during"),
            field_observation("after"),
        ),
        verifier=verifier,
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == [
        "verifier_result",
        "verified_reward",
        "verifier_result",
        "verified_reward",
        "skill_result",
    ]
    assert [record.payload["steps_taken"] for record in records[::2][:-1]] == [1, 2]
    assert [
        VerifierResult.model_validate(record.payload["verifier_result"])
        for record in records[::2][:-1]
    ] == verifier.results
    assert run.verifier_event_records == [records[0], records[2]]
    assert run.reward_event_records == [records[1], records[3]]
    assert run.verifier_result == verifier.results[-1]
    assert run.event_record == records[-1]
    assert run.skill_result.failure_reason == "timeout"
    assert run.skill_result.reward is None


def test_runner_logs_final_non_terminal_verifier_result_before_exhaustion(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    verifier_result = VerifierResult(status=VerifierStatus.ABSTAIN, evidence_ids=["latest"])

    run = SkillRunner(event_log_path=event_log_path, run_id="run-1").run(
        NoEvaluateSkill(),
        observation_source(field_observation("only")),
        verifier=FixedVerifier(verifier_result),
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == [
        "verifier_result",
        "verified_reward",
        "skill_result",
    ]
    assert run.verifier_event_records == [records[0]]
    assert run.reward_event_records == [records[1]]
    assert run.verifier_result == verifier_result
    assert run.skill_result.failure_reason == "observation_sequence_exhausted"
    assert run.skill_result.reward is None


def test_runner_logs_no_verifier_result_before_empty_or_precondition_failure(tmp_path) -> None:
    empty_path = tmp_path / "empty.jsonl"
    precondition_path = tmp_path / "precondition.jsonl"

    empty_run = SkillRunner(event_log_path=empty_path, run_id="run-1").run(
        ContinueDialogueSkill(),
        observation_source(),
        verifier=ContinueDialogueVerifier(),
    )
    precondition_run = SkillRunner(event_log_path=precondition_path, run_id="run-1").run(
        ContinueDialogueSkill(),
        observation_source(field_observation()),
        verifier=ContinueDialogueVerifier(),
    )

    assert empty_run.verifier_event_records == []
    assert precondition_run.verifier_event_records == []
    assert empty_run.verified_reward_breakdowns == []
    assert precondition_run.verified_reward_breakdowns == []
    assert empty_run.reward_event_records == []
    assert precondition_run.reward_event_records == []
    assert [record.event_type for record in EventLogger(empty_path, run_id="run-1").read_all()] == [
        "skill_result"
    ]
    assert [
        record.event_type for record in EventLogger(precondition_path, run_id="run-1").read_all()
    ] == ["skill_result"]


def test_runner_collects_declarative_primitive_actions_without_execution() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=2),
        observation_source(
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
        ),
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
        observation_source(field_observation("before"), field_observation("after")),
        verifier=verifier,
    )

    assert run.skill_result.success
    assert run.skill_result.evidence_ids == ["verified-evidence"]
    assert run.verifier_result is verifier_result
    assert run.verifier_event_records == []


def test_runner_never_calls_an_exploding_body_evaluate_method() -> None:
    run = SkillRunner().run(
        ExplodingEvaluateSkill(),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS)),
    )

    assert run.skill_result.success


def test_runner_maps_canonical_failure_kinds_to_legacy_reasons() -> None:
    generic_failure = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(field_observation("before"), field_observation("after")),
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
        observation_source(field_observation("before"), field_observation("after")),
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

    abstain_run = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(*observations),
        verifier=abstain_verifier,
    )
    progress_run = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(*observations),
        verifier=progress_verifier,
    )

    assert abstain_run.skill_result.failure_reason == "timeout"
    assert progress_run.skill_result.failure_reason == "timeout"
    assert abstain_run.verifier_result is abstain_verifier.result
    assert progress_run.verifier_result is progress_verifier.result
    assert len(abstain_verifier.calls) == 2
    assert len(progress_verifier.calls) == 2


def test_runner_emits_no_reward_for_verified_success_or_failure() -> None:
    success = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS)),
    )
    failure = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(field_observation("before"), field_observation("after")),
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
        observation_source(*timeout_observations),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    abstain_exhaustion = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(*exhaustion_observations),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    progress_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        observation_source(*timeout_observations),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS)),
    )
    progress_exhaustion = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(*exhaustion_observations),
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
        observation_source(
            field_observation("before"),
            Observation(
                run_id="run-1",
                ui_state="field",
                visible_message_text="New",
                evidence_ids=["after"],
            ),
        ),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    ui_state_change = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        observation_source(dialogue_observation("Before", "before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    new_evidence = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )

    assert visible_text_change.skill_result.reward is None
    assert ui_state_change.skill_result.reward is None
    assert new_evidence.skill_result.reward is None
    assert all(
        run.verified_reward_breakdowns[0].total == 0.0
        for run in (visible_text_change, ui_state_change, new_evidence)
    )


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
        observation_source(
            dialogue_observation("First", "before"),
            dialogue_observation("Second", "after"),
        ),
        verifier=verifier,
    )

    assert run.skill_result.success
    assert run.verifier_result is not None


def test_runner_has_no_body_evaluate_dependency() -> None:
    source = inspect.getsource(SkillRunner)

    assert "VerifierCatalog" not in source
    assert "skill.evaluate(" not in source
    assert "evaluate" not in inspect.getsource(RunnableSkill)


def test_runner_derives_in_memory_reward_from_verified_success_only() -> None:
    run = SkillRunner().run(
        NoEvaluateSkill(reward_profile=reward_profile(("skill_success", 2.5))),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(
            VerifierResult(status=VerifierStatus.SUCCESS, evidence_ids=["verified-evidence"])
        ),
    )

    assert run.verified_reward_breakdowns == [
        VerifiedRewardBreakdown(
            profile_name="runner_test_profile",
            verifier_result=VerifierResult(
                status=VerifierStatus.SUCCESS,
                evidence_ids=["verified-evidence"],
            ),
            contributions=(VerifiedRewardContribution(name="skill_success", value=2.5),),
            total=2.5,
        )
    ]
    assert run.reward_event_records == []
    assert run.skill_result.reward is None


def test_runner_preserves_configured_success_reward_weight() -> None:
    run = SkillRunner().run(
        NoEvaluateSkill(reward_profile=reward_profile(("skill_success", 2.5))),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS)),
    )

    assert run.verified_reward_breakdowns[0].total == 2.5


def test_runner_derives_supported_canonical_failure_rewards() -> None:
    cases = [
        (FailureKind.DEATH, "avoid_death", -3.0),
        (FailureKind.TIMEOUT, "avoid_timeout", -2.0),
        (FailureKind.NO_PROGRESS, "avoid_repeated_no_progress", -1.0),
    ]

    for failure_kind, term_name, expected_total in cases:
        run = SkillRunner().run(
            NoEvaluateSkill(reward_profile=reward_profile((term_name, -expected_total))),
            observation_source(field_observation("before"), field_observation("after")),
            verifier=FixedVerifier(
                VerifierResult(status=VerifierStatus.FAILURE, failure_kind=failure_kind)
            ),
        )

        assert run.verified_reward_breakdowns[0].total == expected_total
        assert run.skill_result.reward is None


def test_runner_legacy_timeout_and_exhaustion_cannot_create_reward() -> None:
    profile = reward_profile(("avoid_timeout", 10.0), ("skill_success", 4.0))
    abstain_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1, reward_profile=profile),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )
    progress_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1, reward_profile=profile),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS)),
    )
    exhaustion = SkillRunner().run(
        NoEvaluateSkill(reward_profile=profile),
        observation_source(field_observation("only")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )

    assert [run.skill_result.failure_reason for run in (abstain_timeout, progress_timeout)] == [
        "timeout",
        "timeout",
    ]
    assert exhaustion.skill_result.failure_reason == "observation_sequence_exhausted"
    assert all(
        run.verified_reward_breakdowns[0].total == 0.0
        for run in (
            abstain_timeout,
            progress_timeout,
            exhaustion,
        )
    )


def test_runner_legacy_combat_compatibility_cannot_activate_avoid_combat() -> None:
    run = SkillRunner().run(
        NoEvaluateSkill(
            max_steps=1,
            failure_detector=["combat_started"],
            reward_profile=reward_profile(("avoid_combat", 100.0)),
        ),
        observation_source(
            field_observation("before"),
            Observation(run_id="run-1", ui_state="combat"),
        ),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
    )

    assert run.skill_result.failure_reason == "combat_started"
    assert run.verified_reward_breakdowns[0].total == 0.0
    assert run.skill_result.reward is None


def test_runner_tracks_reward_breakdowns_and_events_per_verifier_invocation(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    results = [
        VerifierResult(status=VerifierStatus.PROGRESS),
        VerifierResult(status=VerifierStatus.ABSTAIN),
        VerifierResult(status=VerifierStatus.SUCCESS, evidence_ids=["success-evidence"]),
    ]

    run = SkillRunner(event_log_path=event_log_path, run_id="run-1").run(
        NoEvaluateSkill(max_steps=3, reward_profile=reward_profile(("skill_success", 1.5))),
        observation_source(
            field_observation("before"),
            field_observation("first"),
            field_observation("second"),
            field_observation("third"),
        ),
        verifier=SequenceVerifier(results),
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert len(run.verifier_event_records) == len(results)
    assert len(run.verified_reward_breakdowns) == len(results)
    assert len(run.reward_event_records) == len(results)
    assert [breakdown.verifier_result for breakdown in run.verified_reward_breakdowns] == results
    assert [breakdown.total for breakdown in run.verified_reward_breakdowns] == [0.0, 0.0, 1.5]
    assert [record.payload["verifier_event_id"] for record in run.reward_event_records] == [
        record.event_id for record in run.verifier_event_records
    ]
    assert [record.event_type for record in records] == [
        "verifier_result",
        "verified_reward",
        "verifier_result",
        "verified_reward",
        "verifier_result",
        "verified_reward",
        "skill_result",
    ]
    assert run.skill_result.reward is None


def test_runner_skips_reward_derivation_when_no_verifier_runs() -> None:
    empty = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS)),
    )
    precondition = SkillRunner().run(
        ContinueDialogueSkill(),
        observation_source(field_observation()),
        verifier=ContinueDialogueVerifier(),
    )

    assert empty.verified_reward_breakdowns == []
    assert empty.reward_event_records == []
    assert precondition.verified_reward_breakdowns == []
    assert precondition.reward_event_records == []


def test_runner_delegates_all_reward_mapping_to_verified_reward_module() -> None:
    source = inspect.getsource(SkillRunner)

    assert "derive_verified_reward" in source
    assert "avoid_death" not in source
    assert "avoid_timeout" not in source
    assert "avoid_repeated_no_progress" not in source
    assert "FailureKind.TIMEOUT" not in source
    assert "FailureKind.NO_PROGRESS" not in source
