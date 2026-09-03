import inspect
from pathlib import Path

from fh_agent.bridge import evidence_sync as evidence_sync_module
from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.memory.event_log import EventLogger


def screenshot_event(logger: EventLogger, evidence_id: str) -> None:
    logger.append(
        "evidence",
        payload={"kind": "screenshot"},
        evidence_ids=[evidence_id],
    )


def test_empty_or_nonexistent_event_log_returns_none(tmp_path: Path) -> None:
    lookup = EventLogBridgeScreenshotEvidenceLookup(tmp_path / "missing.jsonl")

    assert lookup.latest_screenshot_evidence_id(run_id="run-1") is None


def test_latest_screenshot_evidence_id_is_returned(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    logger = EventLogger(event_log_path, run_id="run-1")
    screenshot_event(logger, "shot-1")

    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_log_path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == "shot-1"
    )


def test_later_screenshot_evidence_supersedes_earlier_screenshot(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    logger = EventLogger(event_log_path, run_id="run-1")
    screenshot_event(logger, "shot-1")
    screenshot_event(logger, "shot-2")

    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_log_path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == "shot-2"
    )


def test_non_evidence_and_non_screenshot_events_are_ignored(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    logger = EventLogger(event_log_path, run_id="run-1")
    logger.append("observation", payload={"kind": "screenshot"}, evidence_ids=["ignored-action"])
    logger.append("evidence", payload={"kind": "annotation"}, evidence_ids=["ignored-kind"])
    screenshot_event(logger, "shot-1")

    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_log_path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == "shot-1"
    )


def test_screenshot_evidence_from_another_run_is_ignored(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    screenshot_event(EventLogger(event_log_path, run_id="other-run"), "other-shot")
    screenshot_event(EventLogger(event_log_path, run_id="run-1"), "run-shot")

    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_log_path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == "run-shot"
    )


def test_ambiguous_screenshot_evidence_records_are_ignored(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    logger = EventLogger(event_log_path, run_id="run-1")
    logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=[])
    logger.append(
        "evidence",
        payload={"kind": "screenshot"},
        evidence_ids=["shot-1", "shot-2"],
    )

    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_log_path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        is None
    )


def test_lookup_is_read_only(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    logger = EventLogger(event_log_path, run_id="run-1")
    screenshot_event(logger, "shot-1")
    before = event_log_path.read_bytes()

    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_log_path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == "shot-1"
    )

    assert event_log_path.read_bytes() == before


def test_evidence_sync_module_has_no_forbidden_runtime_dependencies() -> None:
    source = inspect.getsource(evidence_sync_module)

    for forbidden in (
        "fh_agent.body",
        "fh_agent.manager",
        "Verifier",
        "reward",
        "InputExecutor",
        "fh_agent.game",
        "socket",
        "http",
        "websocket",
        "subprocess",
    ):
        assert forbidden not in source
