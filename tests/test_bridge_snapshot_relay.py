import inspect
import json
from pathlib import Path

import pytest

import fh_agent.bridge.snapshot_relay as snapshot_relay_module
from fh_agent.bridge.jsonl_payload_source import JsonlBridgePayloadSource
from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError, sanitize_bridge_payload
from fh_agent.bridge.snapshot_relay import (
    BridgeSnapshotRelayError,
    BridgeSnapshotRelayResult,
    relay_bridge_snapshot_response,
)
from fh_agent.bridge.snapshot_request import BridgeSnapshotRequest
from fh_agent.bridge.snapshot_response import BridgeSnapshotResponse


def request() -> BridgeSnapshotRequest:
    return BridgeSnapshotRequest(
        request_id="request-1",
        run_id="run-1",
        screenshot_id="shot-1",
    )


def response_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "run_mode": "bridge-assisted",
        "screenshot_id": "shot-1",
        "ui_state": "dialogue",
    }
    payload.update(overrides)
    return payload


def write_response(
    path: Path,
    *,
    request_id: str = "request-1",
    run_id: str = "run-1",
    payload: dict[str, object] | None = None,
    trailing_newline: bool = True,
) -> None:
    response = BridgeSnapshotResponse(
        request_id=request_id,
        run_id=run_id,
        payload=response_payload() if payload is None else payload,
    )
    text = json.dumps(response.model_dump(mode="json"), separators=(",", ":"))
    path.write_text(text + ("\n" if trailing_newline else ""), encoding="utf-8")


def test_valid_response_appends_one_jsonl_record_and_preserves_response(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    feed_path = tmp_path / "feed.jsonl"
    write_response(response_path)
    response_before = response_path.read_bytes()

    result = relay_bridge_snapshot_response(
        request(), response_path=response_path, feed_path=feed_path
    )

    assert result == BridgeSnapshotRelayResult(
        request_id="request-1",
        run_id="run-1",
        screenshot_id="shot-1",
        response_path=response_path,
        feed_path=feed_path,
    )
    expected_record = (
        json.dumps(response_payload(), separators=(",", ":"), sort_keys=True).encode("utf-8")
        + b"\n"
    )
    assert feed_path.read_bytes() == expected_record
    assert response_path.read_bytes() == response_before


def test_existing_feed_content_is_preserved_and_jsonl_source_reads_relayed_payload(
    tmp_path: Path,
) -> None:
    response_path = tmp_path / "response.json"
    feed_path = tmp_path / "feed.jsonl"
    feed_path.write_bytes(b'{"existing":true}\n')
    write_response(response_path)

    relay_bridge_snapshot_response(request(), response_path=response_path, feed_path=feed_path)

    source = JsonlBridgePayloadSource(feed_path)
    assert source.next_payload() == {"existing": True}
    assert source.next_payload() == response_payload()


def test_unknown_and_forbidden_fields_survive_for_existing_sanitizer(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    feed_path = tmp_path / "feed.jsonl"
    payload = response_payload(unknown_visible_state="raw", map_id=17)
    write_response(response_path, payload=payload)

    relay_bridge_snapshot_response(request(), response_path=response_path, feed_path=feed_path)

    relayed_payload = JsonlBridgePayloadSource(feed_path).next_payload()
    assert relayed_payload["unknown_visible_state"] == "raw"
    assert relayed_payload["map_id"] == 17
    with pytest.raises(ForbiddenBridgeFieldError):
        sanitize_bridge_payload(relayed_payload)


@pytest.mark.parametrize(
    ("request_id", "run_id", "payload"),
    [
        ("wrong-request", "run-1", response_payload()),
        ("request-1", "wrong-run", response_payload()),
        ("request-1", "run-1", response_payload(run_mode="debug")),
        ("request-1", "run-1", response_payload(screenshot_id="wrong-shot")),
    ],
)
def test_mismatched_provenance_leaves_feed_unchanged(
    tmp_path: Path,
    request_id: str,
    run_id: str,
    payload: dict[str, object],
) -> None:
    response_path = tmp_path / "response.json"
    feed_path = tmp_path / "feed.jsonl"
    feed_path.write_bytes(b"existing\n")
    before = feed_path.read_bytes()
    write_response(response_path, request_id=request_id, run_id=run_id, payload=payload)

    with pytest.raises(BridgeSnapshotRelayError, match="does not match"):
        relay_bridge_snapshot_response(request(), response_path=response_path, feed_path=feed_path)

    assert feed_path.read_bytes() == before


@pytest.mark.parametrize(
    "response_bytes",
    [
        b"\xff\n",
        b"{malformed}\n",
        b'{"request_id":"request-1"}\n',
        b'{"request_id":"request-1","run_id":"run-1","payload":{}}',
        b'{"request_id":"request-1","run_id":"run-1","payload":{"run_mode":"bridge-assisted","screenshot_id":"shot-1","value":NaN}}\n',
        b'{"request_id":"request-1","run_id":"run-1","payload":{"run_mode":"bridge-assisted","screenshot_id":"shot-1","value":Infinity}}\n',
        b'{"request_id":"request-1","run_id":"run-1","payload":{"run_mode":"bridge-assisted","screenshot_id":"shot-1","value":-Infinity}}\n',
    ],
)
def test_invalid_or_incomplete_response_leaves_feed_unchanged(
    tmp_path: Path,
    response_bytes: bytes,
) -> None:
    response_path = tmp_path / "response.json"
    feed_path = tmp_path / "feed.jsonl"
    feed_path.write_bytes(b"existing\n")
    before = feed_path.read_bytes()
    response_path.write_bytes(response_bytes)

    with pytest.raises(BridgeSnapshotRelayError):
        relay_bridge_snapshot_response(request(), response_path=response_path, feed_path=feed_path)

    assert feed_path.read_bytes() == before


def test_missing_response_and_missing_feed_parent_fail_closed(tmp_path: Path) -> None:
    response_path = tmp_path / "missing-response.json"
    with pytest.raises(BridgeSnapshotRelayError, match="could not read"):
        relay_bridge_snapshot_response(
            request(), response_path=response_path, feed_path=tmp_path / "feed.jsonl"
        )

    response_path = tmp_path / "response.json"
    write_response(response_path)
    with pytest.raises(BridgeSnapshotRelayError, match="could not append"):
        relay_bridge_snapshot_response(
            request(),
            response_path=response_path,
            feed_path=tmp_path / "missing-parent" / "feed.jsonl",
        )


def test_relay_has_no_sanitizer_or_runtime_authority() -> None:
    source = inspect.getsource(snapshot_relay_module)

    for forbidden in (
        "sanitize_bridge_payload",
        "fh_agent.bridge.sanitizer",
        "Observation",
        "fh_agent.manager",
        "Cortex",
        "EventLogger",
        "EvidenceStore",
        "poll",
        "socket",
        "http",
        "asyncio",
        "threading",
        "Input",
    ):
        assert forbidden not in source
