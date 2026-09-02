from datetime import UTC, datetime, timedelta
from pathlib import Path

from fh_agent.memory.event_log import EventLogger
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
