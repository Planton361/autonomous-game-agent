from datetime import UTC, datetime, timedelta
from pathlib import Path

from fh_agent.memory.event_log import EventLogger


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
