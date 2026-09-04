import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.snapshot_request import (
    BridgeSnapshotRequest,
    BridgeSnapshotRequestError,
    create_bridge_snapshot_request,
    write_bridge_snapshot_request,
)
from fh_agent.memory.event_log import EventLogger


class StaticScreenshotEvidenceLookup:
    def __init__(self, latest_by_run: dict[str, str | None]) -> None:
        self._latest_by_run = latest_by_run
        self.run_ids: list[str] = []

    def latest_screenshot_evidence_id(self, *, run_id: str) -> str | None:
        self.run_ids.append(run_id)
        return self._latest_by_run.get(run_id)


def screenshot_event(logger: EventLogger, evidence_id: str) -> None:
    logger.append(
        "evidence",
        payload={"kind": "screenshot"},
        evidence_ids=[evidence_id],
    )


def request(*, screenshot_id: str = "shot-2") -> BridgeSnapshotRequest:
    return BridgeSnapshotRequest(
        request_id="request-1",
        run_id="run-1",
        screenshot_id=screenshot_id,
    )


def test_latest_durable_event_log_evidence_creates_request(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    logger = EventLogger(event_log_path, run_id="run-1")
    screenshot_event(logger, "shot-1")
    screenshot_event(logger, "shot-2")

    result = create_bridge_snapshot_request(
        request_id="request-1",
        run_id="run-1",
        screenshot_id="shot-2",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    )

    assert result == request()
    assert result.run_mode == "bridge-assisted"


def test_missing_or_stale_durable_evidence_rejects() -> None:
    with pytest.raises(BridgeSnapshotRequestError, match="no durable"):
        create_bridge_snapshot_request(
            request_id="request-1",
            run_id="run-1",
            screenshot_id="shot-1",
            screenshot_evidence_lookup=StaticScreenshotEvidenceLookup({"run-1": None}),
        )

    with pytest.raises(BridgeSnapshotRequestError, match="does not match"):
        create_bridge_snapshot_request(
            request_id="request-1",
            run_id="run-1",
            screenshot_id="shot-stale",
            screenshot_evidence_lookup=StaticScreenshotEvidenceLookup({"run-1": "shot-current"}),
        )


def test_evidence_from_another_run_rejects(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    screenshot_event(EventLogger(event_log_path, run_id="other-run"), "shot-1")

    with pytest.raises(BridgeSnapshotRequestError, match="no durable"):
        create_bridge_snapshot_request(
            request_id="request-1",
            run_id="run-1",
            screenshot_id="shot-1",
            screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
        )


@pytest.mark.parametrize("field_name", ["request_id", "run_id", "screenshot_id"])
@pytest.mark.parametrize("value", ["", "   "])
def test_blank_ids_reject(field_name: str, value: str) -> None:
    values = {
        "request_id": "request-1",
        "run_id": "run-1",
        "screenshot_id": "shot-1",
    }
    values[field_name] = value

    with pytest.raises(ValidationError):
        BridgeSnapshotRequest(**values)


def test_run_mode_is_fixed_to_bridge_assisted() -> None:
    assert request().run_mode == "bridge-assisted"

    with pytest.raises(ValidationError):
        BridgeSnapshotRequest(
            request_id="request-1",
            run_id="run-1",
            run_mode="debug",  # type: ignore[arg-type]
            screenshot_id="shot-1",
        )


def test_atomic_request_json_round_trips_exactly(tmp_path: Path) -> None:
    expected = request()
    target = tmp_path / "snapshot-request.json"

    returned_path = write_bridge_snapshot_request(expected, target)

    assert returned_path == target
    assert json.loads(target.read_text(encoding="utf-8")) == expected.model_dump(mode="json")
    assert BridgeSnapshotRequest.model_validate_json(target.read_text(encoding="utf-8")) == expected


def test_existing_request_target_is_not_overwritten(tmp_path: Path) -> None:
    target = tmp_path / "snapshot-request.json"
    target.write_text("original", encoding="utf-8")

    with pytest.raises(BridgeSnapshotRequestError, match="already exists"):
        write_bridge_snapshot_request(request(), target)

    assert target.read_text(encoding="utf-8") == "original"


def test_failed_publication_leaves_no_partial_target(tmp_path: Path) -> None:
    target = tmp_path / "snapshot-request.json"

    with patch("fh_agent.bridge.snapshot_request.os.link", side_effect=OSError("link failed")):
        with pytest.raises(BridgeSnapshotRequestError, match="could not publish"):
            write_bridge_snapshot_request(request(), target)

    assert not target.exists()
    assert list(tmp_path.glob(".snapshot-request.json.*.tmp")) == []


def test_request_creation_and_publication_leave_event_log_unchanged(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    logger = EventLogger(event_log_path, run_id="run-1")
    screenshot_event(logger, "shot-1")
    before = event_log_path.read_bytes()

    created = create_bridge_snapshot_request(
        request_id="request-1",
        run_id="run-1",
        screenshot_id="shot-1",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    )
    write_bridge_snapshot_request(created, tmp_path / "snapshot-request.json")

    assert event_log_path.read_bytes() == before


def test_request_schema_has_no_visible_or_hidden_state_fields() -> None:
    assert set(BridgeSnapshotRequest.model_fields) == {
        "request_id",
        "run_id",
        "run_mode",
        "screenshot_id",
    }
