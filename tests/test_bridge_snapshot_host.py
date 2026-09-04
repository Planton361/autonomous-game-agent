import inspect
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import fh_agent.bridge_snapshot_host as bridge_snapshot_host_module
from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.snapshot_request import BridgeSnapshotRequest, BridgeSnapshotRequestError
from fh_agent.bridge_snapshot_host import (
    BridgeSnapshotHostError,
    capture_and_publish_bridge_snapshot_request,
)
from fh_agent.memory.event_log import EventLogger
from fh_agent.memory.evidence import EvidenceStore
from fh_agent.perception.screen_capture import DummyScreenCapture, ScreenFrame


class SequenceFactory:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._count = 0

    def __call__(self) -> str:
        value = f"{self._prefix}-{self._count}"
        self._count += 1
        return value


class RaisingCapture:
    def capture(self) -> ScreenFrame:
        msg = "capture failed"
        raise RuntimeError(msg)


def components(tmp_path: Path, *, run_id: str = "run-1") -> tuple[EvidenceStore, EventLogger]:
    return (
        EvidenceStore(
            tmp_path / "screenshots",
            run_id=run_id,
            id_factory=SequenceFactory("shot"),
        ),
        EventLogger(
            tmp_path / "events.jsonl",
            run_id=run_id,
            id_factory=SequenceFactory("event"),
        ),
    )


def test_one_capture_creates_exact_evidence_event_and_screenshot_bound_request(
    tmp_path: Path,
) -> None:
    evidence_store, event_logger = components(tmp_path)
    capture = DummyScreenCapture(width=2, height=2)
    request_path = tmp_path / "request.json"

    result = capture_and_publish_bridge_snapshot_request(
        capture,
        evidence_store,
        event_logger,
        run_id="run-1",
        request_id="request-1",
        request_path=request_path,
    )

    assert capture.capture_count == 1
    assert result.evidence_record.evidence_id == "shot-0"
    assert Path(result.evidence_record.path).is_file()
    assert result.evidence_event.event_type == "evidence"
    assert result.evidence_event.evidence_ids == [result.evidence_record.evidence_id]
    assert result.evidence_event.payload == result.evidence_record.model_dump(mode="json")
    assert result.request.screenshot_id == result.evidence_record.evidence_id
    assert result.request_path == request_path
    assert BridgeSnapshotRequest.model_validate_json(request_path.read_text(encoding="utf-8")) == (
        result.request
    )
    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_logger.path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == result.evidence_record.evidence_id
    )


@pytest.mark.parametrize(
    ("store_run_id", "logger_run_id"),
    [("other-run", "run-1"), ("run-1", "other-run")],
)
def test_mismatched_run_ids_reject_before_capture(
    tmp_path: Path,
    store_run_id: str,
    logger_run_id: str,
) -> None:
    evidence_store, _ = components(tmp_path, run_id=store_run_id)
    _, event_logger = components(tmp_path, run_id=logger_run_id)
    capture = DummyScreenCapture()

    with pytest.raises(BridgeSnapshotHostError, match="run IDs"):
        capture_and_publish_bridge_snapshot_request(
            capture,
            evidence_store,
            event_logger,
            run_id="run-1",
            request_id="request-1",
            request_path=tmp_path / "request.json",
        )

    assert capture.capture_count == 0


def test_existing_request_target_rejects_before_capture_without_overwrite(tmp_path: Path) -> None:
    evidence_store, event_logger = components(tmp_path)
    capture = DummyScreenCapture()
    request_path = tmp_path / "request.json"
    request_path.write_bytes(b"existing request\n")

    with pytest.raises(BridgeSnapshotHostError, match="already exists"):
        capture_and_publish_bridge_snapshot_request(
            capture,
            evidence_store,
            event_logger,
            run_id="run-1",
            request_id="request-1",
            request_path=request_path,
        )

    assert capture.capture_count == 0
    assert request_path.read_bytes() == b"existing request\n"


def test_capture_failure_produces_no_request(tmp_path: Path) -> None:
    evidence_store, event_logger = components(tmp_path)
    request_path = tmp_path / "request.json"

    with pytest.raises(RuntimeError, match="capture failed"):
        capture_and_publish_bridge_snapshot_request(
            RaisingCapture(),
            evidence_store,
            event_logger,
            run_id="run-1",
            request_id="request-1",
            request_path=request_path,
        )

    assert not request_path.exists()
    assert event_logger.read_all() == []


def test_publication_failure_leaves_durable_evidence_and_event_intact(tmp_path: Path) -> None:
    evidence_store, event_logger = components(tmp_path)
    capture = DummyScreenCapture()
    request_path = tmp_path / "request.json"

    with patch(
        "fh_agent.bridge_snapshot_host.write_bridge_snapshot_request",
        side_effect=BridgeSnapshotRequestError("publication failed"),
    ):
        with pytest.raises(BridgeSnapshotRequestError, match="publication failed"):
            capture_and_publish_bridge_snapshot_request(
                capture,
                evidence_store,
                event_logger,
                run_id="run-1",
                request_id="request-1",
                request_path=request_path,
            )

    records = event_logger.read_all()
    assert capture.capture_count == 1
    assert len(records) == 1
    evidence_id = records[0].evidence_ids[0]
    assert (tmp_path / "screenshots" / "run-1" / f"{evidence_id}.ppm").is_file()
    assert not request_path.exists()
    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_logger.path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == evidence_id
    )


def test_sequential_captures_bind_each_request_to_its_own_latest_screenshot(tmp_path: Path) -> None:
    evidence_store, event_logger = components(tmp_path)
    capture = DummyScreenCapture(clock=lambda: datetime(2026, 9, 4, tzinfo=UTC))

    first = capture_and_publish_bridge_snapshot_request(
        capture,
        evidence_store,
        event_logger,
        run_id="run-1",
        request_id="request-1",
        request_path=tmp_path / "request-1.json",
    )
    second = capture_and_publish_bridge_snapshot_request(
        capture,
        evidence_store,
        event_logger,
        run_id="run-1",
        request_id="request-2",
        request_path=tmp_path / "request-2.json",
    )

    assert capture.capture_count == 2
    assert first.request.screenshot_id == first.evidence_record.evidence_id == "shot-0"
    assert second.request.screenshot_id == second.evidence_record.evidence_id == "shot-1"
    assert (
        EventLogBridgeScreenshotEvidenceLookup(event_logger.path).latest_screenshot_evidence_id(
            run_id="run-1"
        )
        == second.evidence_record.evidence_id
    )


def test_host_module_has_no_relay_runtime_or_control_authority() -> None:
    source = inspect.getsource(bridge_snapshot_host_module)

    for forbidden in (
        "snapshot_relay",
        "JsonlBridgePayloadSource",
        "fh_agent.manager",
        "Cortex",
        "poll",
        "socket",
        "http",
        "asyncio",
        "threading",
        "InputExecutor",
    ):
        assert forbidden not in source
