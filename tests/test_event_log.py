from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fh_agent.manager.verified_reward import (
    VerifiedRewardBreakdown,
    VerifiedRewardContribution,
)
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import ActionResult
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


class SequenceFactory:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.count = 0

    def __call__(self) -> str:
        value = f"{self.prefix}-{self.count}"
        self.count += 1
        return value


class ManualClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def test_event_log_appends_and_reads_records_in_order(tmp_path: Path) -> None:
    logger = EventLogger(
        tmp_path / "run.jsonl",
        run_id="run-1",
        clock=ManualClock(),
        id_factory=SequenceFactory("event"),
    )

    observation = logger.append(
        "observation",
        payload={"source": "dummy_capture"},
        evidence_ids=["evidence-0"],
    )
    action = logger.append(
        "action",
        payload={"action": "wait", "executed": False},
    )
    evidence = logger.append(
        "evidence",
        payload={"kind": "screenshot"},
        evidence_ids=["evidence-0"],
    )

    records = logger.read_all()

    assert records == [observation, action, evidence]
    assert [record.event_id for record in records] == ["event-0", "event-1", "event-2"]
    assert [record.event_type for record in records] == ["observation", "action", "evidence"]
    assert records[0].evidence_ids == ["evidence-0"]
    assert records[1].payload == {"action": "wait", "executed": False}


def test_missing_event_log_reads_as_empty_list(tmp_path: Path) -> None:
    logger = EventLogger(tmp_path / "missing.jsonl", run_id="run-1")

    assert logger.read_all() == []


def test_append_verifier_result_persists_canonical_outcome_and_context(tmp_path: Path) -> None:
    logger = EventLogger(
        tmp_path / "run.jsonl",
        run_id="run-1",
        clock=ManualClock(),
        id_factory=SequenceFactory("event"),
    )
    result = VerifierResult(
        status=VerifierStatus.FAILURE,
        failure_kind=FailureKind.TARGET_LOST,
        evidence_ids=["target-evidence", "after-evidence"],
    )

    record = logger.append_verifier_result(
        result,
        skill_name="basic_reach_target",
        steps_taken=2,
        before_observation_id="observation-before",
        after_observation_id="observation-after",
    )
    persisted = logger.read_all()

    assert record.event_type == "verifier_result"
    assert persisted == [record]
    assert record.evidence_ids == ["target-evidence", "after-evidence"]
    assert record.payload["skill_name"] == "basic_reach_target"
    assert record.payload["steps_taken"] == 2
    assert record.payload["before_observation_id"] == "observation-before"
    assert record.payload["after_observation_id"] == "observation-after"
    assert VerifierResult.model_validate(record.payload["verifier_result"]) == result


def test_append_action_result_persists_canonical_transition_context(tmp_path: Path) -> None:
    logger = EventLogger(
        tmp_path / "run.jsonl",
        run_id="run-1",
        clock=ManualClock(),
        id_factory=SequenceFactory("event"),
    )
    result = ActionResult(
        action="confirm",
        executed=True,
        created_at=datetime(2026, 5, 16, 13, 0, tzinfo=UTC),
        evidence_ids=["before", "shared", "after"],
    )

    record = logger.append_action_result(
        result,
        skill_name="continue_dialogue",
        step_index=2,
        before_observation_id="before-observation",
        after_observation_id="after-observation",
        before_evidence_ids=["before", "shared"],
        after_evidence_ids=["shared", "after"],
    )

    assert record.event_type == "action_result"
    assert record.payload["skill_name"] == "continue_dialogue"
    assert record.payload["step_index"] == 2
    assert record.payload["before_observation_id"] == "before-observation"
    assert record.payload["after_observation_id"] == "after-observation"
    assert record.payload["before_evidence_ids"] == ["before", "shared"]
    assert record.payload["after_evidence_ids"] == ["shared", "after"]
    assert ActionResult.model_validate(record.payload["action_result"]) == result
    assert record.evidence_ids == result.evidence_ids
    assert logger.read_all() == [record]


def test_append_action_result_supports_blocked_attempts_and_rejects_negative_steps(
    tmp_path: Path,
) -> None:
    logger = EventLogger(tmp_path / "run.jsonl", run_id="run-1")
    blocked = ActionResult(
        action="wait",
        executed=False,
        blocked_reason="rate_limited",
        evidence_ids=["before"],
    )

    record = logger.append_action_result(
        blocked,
        skill_name="fake_skill",
        step_index=0,
        before_observation_id="before-observation",
        after_observation_id=None,
        before_evidence_ids=["before"],
    )

    assert record.payload["after_observation_id"] is None
    assert record.payload["after_evidence_ids"] == []
    assert ActionResult.model_validate(record.payload["action_result"]) == blocked
    assert record.evidence_ids == ["before"]
    with pytest.raises(ValueError, match="step_index must be non-negative"):
        logger.append_action_result(
            blocked,
            skill_name="fake_skill",
            step_index=-1,
            before_observation_id=None,
            after_observation_id=None,
        )


def test_append_verifier_result_round_trips_every_non_failure_status(tmp_path: Path) -> None:
    logger = EventLogger(
        tmp_path / "run.jsonl",
        run_id="run-1",
        clock=ManualClock(),
        id_factory=SequenceFactory("event"),
    )
    results = [
        VerifierResult(status=VerifierStatus.SUCCESS, evidence_ids=["success-evidence"]),
        VerifierResult(status=VerifierStatus.ABSTAIN),
        VerifierResult(status=VerifierStatus.PROGRESS, evidence_ids=["progress-evidence"]),
    ]

    records = [
        logger.append_verifier_result(
            result,
            skill_name="continue_dialogue",
            steps_taken=index,
            before_observation_id=None,
            after_observation_id=None,
        )
        for index, result in enumerate(results)
    ]

    assert [record.event_type for record in records] == ["verifier_result"] * 3
    assert [record.evidence_ids for record in records] == [
        ["success-evidence"],
        [],
        ["progress-evidence"],
    ]
    assert all(record.payload["before_observation_id"] is None for record in records)
    assert all(record.payload["after_observation_id"] is None for record in records)
    assert [
        VerifierResult.model_validate(record.payload["verifier_result"]) for record in records
    ] == results


def test_verifier_result_append_order_remains_append_only_with_ordinary_events(
    tmp_path: Path,
) -> None:
    logger = EventLogger(
        tmp_path / "run.jsonl",
        run_id="run-1",
        clock=ManualClock(),
        id_factory=SequenceFactory("event"),
    )

    observation = logger.append("observation", payload={"source": "capture"})
    verifier = logger.append_verifier_result(
        VerifierResult(status=VerifierStatus.SUCCESS),
        skill_name="continue_dialogue",
        steps_taken=1,
        before_observation_id=None,
        after_observation_id=None,
    )
    skill = logger.append("skill_result", payload={"success": True})

    assert logger.read_all() == [observation, verifier, skill]


def test_action_result_append_order_remains_append_only_with_existing_event_types(
    tmp_path: Path,
) -> None:
    logger = EventLogger(tmp_path / "run.jsonl", run_id="run-1")
    observation = logger.append("observation")
    action = logger.append_action_result(
        ActionResult(action="wait", executed=True),
        skill_name="fake_skill",
        step_index=0,
        before_observation_id=None,
        after_observation_id=None,
    )
    verifier = logger.append_verifier_result(
        VerifierResult(status=VerifierStatus.ABSTAIN),
        skill_name="fake_skill",
        steps_taken=1,
        before_observation_id=None,
        after_observation_id=None,
    )

    assert logger.read_all() == [observation, action, verifier]


def test_append_verified_reward_persists_exact_breakdown_and_provenance(tmp_path: Path) -> None:
    logger = EventLogger(
        tmp_path / "run.jsonl",
        run_id="run-1",
        clock=ManualClock(),
        id_factory=SequenceFactory("event"),
    )
    verifier_result = VerifierResult(
        status=VerifierStatus.SUCCESS,
        evidence_ids=["first-evidence", "second-evidence"],
    )
    reward = VerifiedRewardBreakdown(
        profile_name="test_profile",
        verifier_result=verifier_result,
        contributions=(
            VerifiedRewardContribution(name="skill_success", value=1.0),
            VerifiedRewardContribution(name="avoid_death", value=-0.25),
        ),
        total=0.75,
    )

    record = logger.append_verified_reward(
        reward,
        skill_name="continue_dialogue",
        verifier_event_id="verifier-event-1",
    )

    assert record.event_type == "verified_reward"
    assert record.payload["skill_name"] == "continue_dialogue"
    assert record.payload["verifier_event_id"] == "verifier-event-1"
    assert record.evidence_ids == ["first-evidence", "second-evidence"]
    assert VerifiedRewardBreakdown.model_validate(record.payload["verified_reward"]) == reward
    assert logger.read_all() == [record]


def test_append_verified_reward_rejects_empty_verifier_event_id(tmp_path: Path) -> None:
    logger = EventLogger(tmp_path / "run.jsonl", run_id="run-1")
    reward = VerifiedRewardBreakdown(
        profile_name="test_profile",
        verifier_result=VerifierResult(status=VerifierStatus.ABSTAIN),
        total=0.0,
    )

    with pytest.raises(ValueError, match="verifier_event_id must be non-empty"):
        logger.append_verified_reward(
            reward,
            skill_name="continue_dialogue",
            verifier_event_id="",
        )


def test_verified_reward_append_order_remains_deterministic(tmp_path: Path) -> None:
    logger = EventLogger(
        tmp_path / "run.jsonl",
        run_id="run-1",
        clock=ManualClock(),
        id_factory=SequenceFactory("event"),
    )
    verifier = logger.append_verifier_result(
        VerifierResult(status=VerifierStatus.SUCCESS, evidence_ids=["evidence"]),
        skill_name="continue_dialogue",
        steps_taken=1,
        before_observation_id=None,
        after_observation_id=None,
    )
    reward = logger.append_verified_reward(
        VerifiedRewardBreakdown(
            profile_name="test_profile",
            verifier_result=VerifierResult(
                status=VerifierStatus.SUCCESS, evidence_ids=["evidence"]
            ),
            contributions=(VerifiedRewardContribution(name="skill_success", value=1.0),),
            total=1.0,
        ),
        skill_name="continue_dialogue",
        verifier_event_id=verifier.event_id,
    )
    skill = logger.append("skill_result", payload={"success": True})

    assert logger.read_all() == [verifier, reward, skill]
