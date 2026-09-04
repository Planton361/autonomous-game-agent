import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import fh_agent.bridge.jsonl_payload_source as jsonl_payload_source_module
from fh_agent.bridge.evidence_sync import (
    BridgeEvidenceSynchronizationError,
    EventLogBridgeScreenshotEvidenceLookup,
)
from fh_agent.bridge.jsonl_payload_source import (
    InvalidJsonlBridgePayloadError,
    JsonlBridgeFeedConsistencyError,
    JsonlBridgePayloadSource,
)
from fh_agent.bridge.observation_source import (
    BridgeObservationSource,
    BridgePayloadSourceExhausted,
)
from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError, UnknownBridgeFieldError
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.source import ObservationSourceExhausted


def append_payload(path: Path, payload: dict[str, Any]) -> None:
    with path.open("ab") as file:
        file.write(json.dumps(payload).encode("utf-8"))
        file.write(b"\n")


def bridge_payload(screenshot_id: str) -> dict[str, Any]:
    return {
        "run_mode": "bridge-assisted",
        "ui_state": "dialogue",
        "visible_message_text": "Visible line.",
        "screenshot_id": screenshot_id,
    }


def test_construction_performs_no_io_for_missing_path(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"

    source = JsonlBridgePayloadSource(path)

    assert not path.exists()
    with pytest.raises(BridgePayloadSourceExhausted):
        source.next_payload()
    assert not path.exists()


def test_one_complete_line_per_call_preserves_order_and_does_not_look_ahead(tmp_path: Path) -> None:
    path = tmp_path / "feed.jsonl"
    append_payload(path, {"sequence": 1})
    with path.open("ab") as file:
        file.write(b"{malformed}\n")
    source = JsonlBridgePayloadSource(path)

    assert source.next_payload() == {"sequence": 1}
    with pytest.raises(InvalidJsonlBridgePayloadError, match="not valid JSON"):
        source.next_payload()


def test_empty_eof_and_partial_line_recover_after_append_without_recreating_source(
    tmp_path: Path,
) -> None:
    path = tmp_path / "feed.jsonl"
    path.touch()
    source = JsonlBridgePayloadSource(path)

    with pytest.raises(BridgePayloadSourceExhausted):
        source.next_payload()

    with path.open("ab") as file:
        file.write(b'{"run_mode":"bridge-assisted","ui_state":"dial')
    with pytest.raises(BridgePayloadSourceExhausted):
        source.next_payload()

    with path.open("ab") as file:
        file.write(b'ogue","screenshot_id":"shot-1"}\n')
    assert source.next_payload() == {
        "run_mode": "bridge-assisted",
        "ui_state": "dialogue",
        "screenshot_id": "shot-1",
    }


def test_invalid_utf8_json_and_root_shape_fail_closed_without_advancing(tmp_path: Path) -> None:
    invalid_utf8 = tmp_path / "invalid-utf8.jsonl"
    invalid_utf8.write_bytes(b"\xff\n")
    source = JsonlBridgePayloadSource(invalid_utf8)
    with pytest.raises(InvalidJsonlBridgePayloadError, match="UTF-8"):
        source.next_payload()
    with pytest.raises(InvalidJsonlBridgePayloadError, match="UTF-8"):
        source.next_payload()

    malformed = tmp_path / "malformed.jsonl"
    malformed.write_text("{malformed}\n", encoding="utf-8")
    source = JsonlBridgePayloadSource(malformed)
    with pytest.raises(InvalidJsonlBridgePayloadError, match="not valid JSON"):
        source.next_payload()
    with pytest.raises(InvalidJsonlBridgePayloadError, match="not valid JSON"):
        source.next_payload()

    for index, root in enumerate(([], "hello", 42, None)):
        root_path = tmp_path / f"root-{index}.jsonl"
        root_path.write_text(json.dumps(root) + "\n", encoding="utf-8")
        with pytest.raises(InvalidJsonlBridgePayloadError, match="root must be an object"):
            JsonlBridgePayloadSource(root_path).next_payload()


def test_disappearance_and_truncation_after_consumption_fail_closed(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-after-consumption.jsonl"
    append_payload(missing_path, {"sequence": 1})
    source = JsonlBridgePayloadSource(missing_path)
    assert source.next_payload() == {"sequence": 1}
    missing_path.unlink()
    with pytest.raises(JsonlBridgeFeedConsistencyError, match="disappeared"):
        source.next_payload()

    truncated_path = tmp_path / "truncated-after-consumption.jsonl"
    append_payload(truncated_path, {"sequence": 1})
    source = JsonlBridgePayloadSource(truncated_path)
    assert source.next_payload() == {"sequence": 1}
    truncated_path.write_bytes(b"")
    with pytest.raises(JsonlBridgeFeedConsistencyError, match="truncated"):
        source.next_payload()


@pytest.mark.parametrize(
    ("field", "error_type"),
    [("map_id", ForbiddenBridgeFieldError), ("unknown_visible_field", UnknownBridgeFieldError)],
)
def test_raw_fields_reach_existing_sanitizer_unchanged(
    tmp_path: Path,
    field: str,
    error_type: type[ValueError],
) -> None:
    feed_path = tmp_path / "feed.jsonl"
    payload = bridge_payload("shot-1")
    payload[field] = 17
    append_payload(feed_path, payload)
    source = JsonlBridgePayloadSource(feed_path)

    assert source.next_payload()[field] == 17

    append_payload(feed_path, payload)
    observation_source = BridgeObservationSource(
        source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(
            tmp_path / "events.jsonl"
        ),
    )
    with pytest.raises(error_type):
        observation_source.observe()


def test_bridge_observation_source_composes_and_resumes_after_append(tmp_path: Path) -> None:
    feed_path = tmp_path / "feed.jsonl"
    event_path = tmp_path / "events.jsonl"
    event_logger = EventLogger(event_path, run_id="run-1")
    event_logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-1"])
    append_payload(feed_path, bridge_payload("shot-1"))
    payload_source = JsonlBridgePayloadSource(feed_path)
    observation_source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_path),
    )

    first = observation_source.observe()
    assert first.run_id == "run-1"
    assert first.ui_state == "dialogue"
    assert first.visible_message_text == "Visible line."
    assert first.screenshot_id == "shot-1"
    assert first.evidence_ids == ["shot-1"]
    with pytest.raises(ObservationSourceExhausted):
        observation_source.observe()

    event_logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-2"])
    append_payload(feed_path, bridge_payload("shot-2"))
    second = observation_source.observe()
    assert second.screenshot_id == "shot-2"
    assert second.evidence_ids == ["shot-2"]


def test_screenshot_mismatch_is_rejected_by_existing_downstream_gate(tmp_path: Path) -> None:
    feed_path = tmp_path / "feed.jsonl"
    event_path = tmp_path / "events.jsonl"
    EventLogger(event_path, run_id="run-1").append(
        "evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-2"]
    )
    append_payload(feed_path, bridge_payload("shot-1"))
    payload_source = JsonlBridgePayloadSource(feed_path)

    assert payload_source.next_payload()["screenshot_id"] == "shot-1"
    append_payload(feed_path, bridge_payload("shot-1"))
    observation_source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_path),
    )
    with pytest.raises(BridgeEvidenceSynchronizationError, match="does not match"):
        observation_source.observe()


def test_module_has_only_local_feed_dependencies() -> None:
    source = inspect.getsource(jsonl_payload_source_module)

    for forbidden in (
        "fh_agent.manager",
        "fh_agent.planner",
        "fh_agent.body",
        "fh_agent.game",
        "fh_agent.verifier",
        "fh_agent.memory",
        "EventLogger",
        "MemoryDB",
        "InputExecutor",
        "Cortex",
        "sanitize_bridge_payload",
        "VisibleBridgeAdapter",
        "BridgeScreenshotEvidenceLookup",
        "socket",
        "http",
        "asyncio",
        "threading",
        "subprocess",
    ):
        assert forbidden not in source
