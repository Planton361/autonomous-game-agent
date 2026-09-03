import inspect

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import BlockedReason, DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
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
from fh_agent.observation.schemas import ActionResult, Observation
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


class ManualClock:
    def __init__(self, timestamp: float = 100.0) -> None:
        self.timestamp = timestamp

    def __call__(self) -> float:
        return self.timestamp


def make_input_executor(
    *,
    focused: bool = True,
    min_interval_seconds: float = 0.0,
    clock: ManualClock | None = None,
) -> tuple[InputExecutor, DryRunInputBackend, ManualClock]:
    manual_clock = clock or ManualClock()
    backend = DryRunInputBackend()
    executor = InputExecutor(
        target=WindowTarget(title="C3 test window"),
        focus_guard=FakeFocusGuard(focused=focused),
        backend=backend,
        min_interval_seconds=min_interval_seconds,
        clock=manual_clock,
    )
    return executor, backend, manual_clock


def focused_input_executor() -> InputExecutor:
    return make_input_executor()[0]


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


class PostActionObservationSource(RecordingObservationSource):
    def __init__(self, backend: DryRunInputBackend, *observations: Observation) -> None:
        super().__init__(*observations)
        self._backend = backend

    def observe(self) -> Observation:
        if self.observe_calls > 0:
            assert self._backend.actions
        return super().observe()


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


class DisallowedActionSkill(NoEvaluateSkill):
    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        return SkillStep(
            skill_name=self.contract.skill_name,
            action=PrimitiveAction.CONFIRM,
            step_index=step_index,
            reason="disallowed_action",
            evidence_ids=observation.evidence_ids,
        )


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
        input_executor=focused_input_executor(),
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "precondition_failed"
    assert run.steps == []
    assert run.verifier_result is None
    assert source.observe_calls == 1
    assert verifier.calls == []
    assert run.verified_reward_breakdowns == []
    assert run.action_execution_results == []


def test_runner_preserves_empty_sequence_compatibility_without_verification() -> None:
    source = RecordingObservationSource()
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        source,
        verifier=verifier,
        input_executor=focused_input_executor(),
    )

    assert run.skill_result.failure_reason == "empty_observation_sequence"
    assert run.verifier_result is None
    assert source.observe_calls == 1
    assert verifier.calls == []
    assert run.verified_reward_breakdowns == []
    assert run.action_execution_results == []


def test_runner_executes_before_post_action_observation_without_prefetching() -> None:
    start = field_observation("start")
    after = field_observation("after")
    input_executor, backend, _clock = make_input_executor()
    source = PostActionObservationSource(backend, start, after, field_observation("unused"))
    skill = RecordingSkill()
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))

    run = SkillRunner().run(
        skill,
        source,
        verifier=verifier,
        input_executor=input_executor,
    )

    assert run.skill_result.success
    assert source.observe_calls == 2
    assert skill.can_start_observations[0] is start
    assert skill.next_action_observations[0] is start
    assert verifier.calls[0][0] is start
    verifier_after = verifier.calls[0][1]
    action_result = run.action_execution_results[0]
    assert isinstance(action_result, ActionResult)
    assert verifier_after is not after
    assert verifier_after.last_action_result == action_result
    assert action_result.action == PrimitiveAction.WAIT.value
    assert action_result.executed
    assert action_result.blocked_reason is None
    assert action_result.evidence_ids == ["start", "after"]
    assert after.last_action_result is None
    assert backend.actions == [PrimitiveAction.WAIT]
    assert [result.executed for result in run.action_execution_results] == [True]


def test_runner_uses_executor_result_over_source_supplied_action_result() -> None:
    start = field_observation("before")
    stale_action_result = ActionResult(
        action=PrimitiveAction.CONFIRM.value,
        executed=True,
        evidence_ids=["stale"],
    )
    source_after = field_observation("after").model_copy(
        update={"last_action_result": stale_action_result}
    )
    source = RecordingObservationSource(start, source_after)
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))

    run = SkillRunner().run(
        NoEvaluateSkill(),
        source,
        verifier=verifier,
        input_executor=focused_input_executor(),
    )

    linked_action_result = run.action_execution_results[0]
    assert source_after.last_action_result is stale_action_result
    assert verifier.calls[0][1].last_action_result == linked_action_result
    assert linked_action_result.action == PrimitiveAction.WAIT.value
    assert linked_action_result.evidence_ids == ["before", "after"]


def test_runner_stops_pulling_after_terminal_failure() -> None:
    start = field_observation("start")
    after = field_observation("after")
    source = RecordingObservationSource(start, after, field_observation("unused"))
    verifier = FixedVerifier(
        VerifierResult(status=VerifierStatus.FAILURE, failure_kind=FailureKind.SKILL_FAILED)
    )

    run = SkillRunner().run(
        NoEvaluateSkill(),
        source,
        verifier=verifier,
        input_executor=focused_input_executor(),
    )

    assert run.skill_result.failure_reason == "skill_failed"
    assert source.observe_calls == 2
    assert verifier.calls[0][0] is start
    assert verifier.calls[0][1] is not after
    assert verifier.calls[0][1].last_action_result is not None
    assert len(run.action_execution_results) == 1


def test_runner_does_not_verify_executed_action_without_post_action_observation() -> None:
    start = field_observation("start")
    source = RecordingObservationSource(start)
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN))

    run = SkillRunner().run(
        NoEvaluateSkill(),
        source,
        verifier=verifier,
        input_executor=focused_input_executor(),
    )

    assert run.skill_result.failure_reason == "observation_sequence_exhausted"
    assert source.observe_calls == 2
    assert verifier.calls == []
    assert run.verifier_result is None
    assert run.verified_reward_breakdowns == []
    assert run.action_execution_results[0].executed
    assert run.action_execution_results[0].evidence_ids == ["start"]


def test_runner_preserves_earlier_verification_when_later_action_lacks_observation() -> None:
    source = RecordingObservationSource(
        field_observation("start"),
        field_observation("after-first"),
    )
    verifier = SequenceVerifier([VerifierResult(status=VerifierStatus.PROGRESS)])

    run = SkillRunner().run(
        NoEvaluateSkill(max_steps=2),
        source,
        verifier=verifier,
        input_executor=focused_input_executor(),
    )

    assert run.skill_result.failure_reason == "observation_sequence_exhausted"
    assert run.verifier_result == verifier.results[0]
    assert len(verifier.calls) == 1
    assert len(run.verified_reward_breakdowns) == 1
    assert len(run.action_execution_results) == 2


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
    input_executor, backend, _clock = make_input_executor()
    verifier = SequenceVerifier(
        [
            VerifierResult(status=VerifierStatus.ABSTAIN),
            VerifierResult(status=VerifierStatus.PROGRESS),
        ]
    )

    run = SkillRunner().run(
        skill,
        source,
        verifier=verifier,
        input_executor=input_executor,
    )

    assert run.skill_result.failure_reason == "timeout"
    assert source.observe_calls == 3
    assert len(verifier.calls) == 2
    assert skill.next_action_observations[0] is start
    second_step_observation = skill.next_action_observations[1]
    assert second_step_observation is not first
    assert second_step_observation.last_action_result == run.action_execution_results[0]
    assert second_step_observation.last_action_result.evidence_ids == ["start", "first"]
    assert first.last_action_result is None
    assert backend.actions == [PrimitiveAction.WAIT, PrimitiveAction.WAIT]
    assert len(run.action_execution_results) == 2
    assert all(isinstance(result, ActionResult) for result in run.action_execution_results)


def test_runner_has_no_precomputed_observation_sequence_dependency() -> None:
    source = inspect.getsource(SkillRunner)

    assert "Sequence[Observation]" not in source
    assert "len(observations)" not in source
    assert "observations[" not in source
    assert "SequenceObservationSource" not in source
    assert "InputBackend" not in source
    assert "DryRunInputBackend" not in source
    assert ".backend" not in source
    assert ".focus_guard" not in source
    assert "clear_emergency_stop" not in source


def test_runner_requires_guarded_input_executor() -> None:
    parameter = inspect.signature(SkillRunner.run).parameters["input_executor"]

    assert parameter.default is inspect.Parameter.empty
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_runner_rejects_disallowed_action_without_execution_or_verification() -> None:
    source = RecordingObservationSource(field_observation("start"), field_observation("unused"))
    input_executor, backend, _clock = make_input_executor()
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))

    run = SkillRunner().run(
        DisallowedActionSkill(),
        source,
        verifier=verifier,
        input_executor=input_executor,
    )

    assert run.skill_result.failure_reason == "action_not_allowed"
    assert len(run.steps) == 1
    assert run.action_execution_results == []
    assert backend.actions == []
    assert source.observe_calls == 1
    assert verifier.calls == []
    assert run.verified_reward_breakdowns == []


def test_runner_stops_when_input_executor_blocks_wrong_window() -> None:
    source = RecordingObservationSource(field_observation("start"), field_observation("unused"))
    input_executor, backend, _clock = make_input_executor(focused=False)
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))

    run = SkillRunner().run(
        NoEvaluateSkill(),
        source,
        verifier=verifier,
        input_executor=input_executor,
    )

    assert run.skill_result.failure_reason == BlockedReason.NOT_FOCUSED
    assert backend.actions == []
    assert source.observe_calls == 1
    assert verifier.calls == []
    assert run.verified_reward_breakdowns == []
    assert run.action_execution_results[0].blocked_reason == BlockedReason.NOT_FOCUSED
    assert run.action_execution_results[0].evidence_ids == ["start"]


def test_runner_stops_when_emergency_stop_blocks_action() -> None:
    source = RecordingObservationSource(field_observation("start"), field_observation("unused"))
    input_executor, backend, _clock = make_input_executor()
    input_executor.enable_emergency_stop()
    verifier = FixedVerifier(VerifierResult(status=VerifierStatus.SUCCESS))

    run = SkillRunner().run(
        NoEvaluateSkill(),
        source,
        verifier=verifier,
        input_executor=input_executor,
    )

    assert run.skill_result.failure_reason == BlockedReason.EMERGENCY_STOP
    assert backend.actions == []
    assert source.observe_calls == 1
    assert verifier.calls == []
    assert run.verified_reward_breakdowns == []
    assert run.action_execution_results[0].blocked_reason == BlockedReason.EMERGENCY_STOP
    assert run.action_execution_results[0].evidence_ids == ["start"]


def test_runner_preserves_first_transition_when_second_action_is_rate_limited() -> None:
    clock = ManualClock()
    input_executor, backend, _clock = make_input_executor(
        min_interval_seconds=1.0,
        clock=clock,
    )
    source = RecordingObservationSource(
        field_observation("start"),
        field_observation("after-first"),
        field_observation("unused"),
    )
    verifier = SequenceVerifier([VerifierResult(status=VerifierStatus.PROGRESS)])

    run = SkillRunner().run(
        NoEvaluateSkill(max_steps=2),
        source,
        verifier=verifier,
        input_executor=input_executor,
    )

    assert run.skill_result.failure_reason == BlockedReason.RATE_LIMITED
    assert backend.actions == [PrimitiveAction.WAIT]
    assert source.observe_calls == 2
    assert len(verifier.calls) == 1
    assert len(run.verified_reward_breakdowns) == 1
    assert [result.executed for result in run.action_execution_results] == [True, False]
    assert run.action_execution_results[0].evidence_ids == ["start", "after-first"]
    assert run.action_execution_results[-1].blocked_reason == BlockedReason.RATE_LIMITED
    assert run.action_execution_results[-1].evidence_ids == ["after-first"]


def test_runner_returns_success_when_dialogue_text_changes() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        observation_source(
            dialogue_observation("First", "e1"),
            dialogue_observation("Second", "e2"),
        ),
        verifier=ContinueDialogueVerifier(),
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
    )

    assert not run.skill_result.success
    assert run.skill_result.failure_reason == "timeout"
    assert len(run.steps) == 2


def test_runner_stops_when_observation_sequence_is_exhausted_after_start() -> None:
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=3),
        observation_source(dialogue_observation("Only", "e1")),
        verifier=ContinueDialogueVerifier(),
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
            input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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


def test_runner_logs_no_verifier_result_when_executed_action_lacks_observation(tmp_path) -> None:
    event_log_path = tmp_path / "run-1" / "events.jsonl"
    verifier_result = VerifierResult(status=VerifierStatus.ABSTAIN, evidence_ids=["latest"])

    run = SkillRunner(event_log_path=event_log_path, run_id="run-1").run(
        NoEvaluateSkill(),
        observation_source(field_observation("only")),
        verifier=FixedVerifier(verifier_result),
        input_executor=focused_input_executor(),
    )
    records = EventLogger(event_log_path, run_id="run-1").read_all()

    assert [record.event_type for record in records] == ["skill_result"]
    assert run.verifier_event_records == []
    assert run.reward_event_records == []
    assert run.verified_reward_breakdowns == []
    assert run.verifier_result is None
    assert run.skill_result.failure_reason == "observation_sequence_exhausted"
    assert run.skill_result.reward is None


def test_runner_logs_no_verifier_result_before_empty_or_precondition_failure(tmp_path) -> None:
    empty_path = tmp_path / "empty.jsonl"
    precondition_path = tmp_path / "precondition.jsonl"

    empty_run = SkillRunner(event_log_path=empty_path, run_id="run-1").run(
        ContinueDialogueSkill(),
        observation_source(),
        verifier=ContinueDialogueVerifier(),
        input_executor=focused_input_executor(),
    )
    precondition_run = SkillRunner(event_log_path=precondition_path, run_id="run-1").run(
        ContinueDialogueSkill(),
        observation_source(field_observation()),
        verifier=ContinueDialogueVerifier(),
        input_executor=focused_input_executor(),
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


def test_runner_collects_executed_primitive_actions_without_key_sequences() -> None:
    input_executor, backend, _clock = make_input_executor()
    run = SkillRunner().run(
        ContinueDialogueSkill(max_steps=2),
        observation_source(
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
            dialogue_observation("Same", "e1"),
        ),
        verifier=ContinueDialogueVerifier(),
        input_executor=input_executor,
    )

    assert [step.action for step in run.steps] == [
        PrimitiveAction.CONFIRM,
        PrimitiveAction.CONFIRM,
    ]
    assert backend.actions == [PrimitiveAction.CONFIRM, PrimitiveAction.CONFIRM]
    assert [result.action for result in run.action_execution_results] == [
        action.value for action in backend.actions
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
    )
    death_failure = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(
            VerifierResult(status=VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH)
        ),
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
    )
    progress_run = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(*observations),
        verifier=progress_verifier,
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
    )
    abstain_exhaustion = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(*exhaustion_observations),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
        input_executor=focused_input_executor(),
    )
    progress_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        observation_source(*timeout_observations),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS)),
        input_executor=focused_input_executor(),
    )
    progress_exhaustion = SkillRunner().run(
        NoEvaluateSkill(),
        observation_source(*exhaustion_observations),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS)),
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
    )
    ui_state_change = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        observation_source(dialogue_observation("Before", "before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
        input_executor=focused_input_executor(),
    )
    new_evidence = SkillRunner().run(
        NoEvaluateSkill(max_steps=1),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
            input_executor=focused_input_executor(),
        )

        assert run.verified_reward_breakdowns[0].total == expected_total
        assert run.skill_result.reward is None


def test_runner_legacy_timeout_and_exhaustion_cannot_create_reward() -> None:
    profile = reward_profile(("avoid_timeout", 10.0), ("skill_success", 4.0))
    abstain_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1, reward_profile=profile),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
        input_executor=focused_input_executor(),
    )
    progress_timeout = SkillRunner().run(
        NoEvaluateSkill(max_steps=1, reward_profile=profile),
        observation_source(field_observation("before"), field_observation("after")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.PROGRESS)),
        input_executor=focused_input_executor(),
    )
    exhaustion = SkillRunner().run(
        NoEvaluateSkill(reward_profile=profile),
        observation_source(field_observation("only")),
        verifier=FixedVerifier(VerifierResult(status=VerifierStatus.ABSTAIN)),
        input_executor=focused_input_executor(),
    )

    assert [run.skill_result.failure_reason for run in (abstain_timeout, progress_timeout)] == [
        "timeout",
        "timeout",
    ]
    assert exhaustion.skill_result.failure_reason == "observation_sequence_exhausted"
    assert all(
        run.verified_reward_breakdowns[0].total == 0.0
        for run in (abstain_timeout, progress_timeout)
    )
    assert exhaustion.verified_reward_breakdowns == []


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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
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
        input_executor=focused_input_executor(),
    )
    precondition = SkillRunner().run(
        ContinueDialogueSkill(),
        observation_source(field_observation()),
        verifier=ContinueDialogueVerifier(),
        input_executor=focused_input_executor(),
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
