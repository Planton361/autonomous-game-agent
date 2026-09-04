from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError, sanitize_bridge_payload
from fh_agent.bridge.snapshot_request import BridgeSnapshotRequest
from fh_agent.bridge.snapshot_response import (
    BridgeSnapshotResponse,
    BridgeSnapshotResponseError,
    unwrap_bridge_snapshot_response,
)

BRIDGE_SOURCE_PATH = Path(__file__).parents[1] / "bridge" / "rmmv_visible_bridge.js"


def request() -> BridgeSnapshotRequest:
    return BridgeSnapshotRequest(
        request_id="request-1",
        run_id="run-1",
        screenshot_id="shot-1",
    )


def response(
    *,
    request_id: str = "request-1",
    run_id: str = "run-1",
    payload: dict[str, object] | None = None,
) -> BridgeSnapshotResponse:
    return BridgeSnapshotResponse(
        request_id=request_id,
        run_id=run_id,
        payload=(
            {"run_mode": "bridge-assisted", "screenshot_id": "shot-1"}
            if payload is None
            else payload
        ),
    )


def test_valid_response_unwraps_the_exact_raw_payload() -> None:
    raw_payload = {
        "run_mode": "bridge-assisted",
        "screenshot_id": "shot-1",
        "ui_state": "dialogue",
    }
    snapshot_response = response(payload=raw_payload)

    unwrapped = unwrap_bridge_snapshot_response(snapshot_response, request())

    assert unwrapped is snapshot_response.payload
    assert unwrapped == raw_payload


@pytest.mark.parametrize(
    ("snapshot_response", "message"),
    [
        (response(request_id="wrong-request"), "request_id"),
        (response(run_id="wrong-run"), "run_id"),
        (
            response(payload={"run_mode": "bridge-assisted", "screenshot_id": "wrong-shot"}),
            "screenshot_id",
        ),
        (
            response(payload={"run_mode": "debug", "screenshot_id": "shot-1"}),
            "run_mode",
        ),
        (response(payload={"screenshot_id": "shot-1"}), "run_mode"),
        (response(payload={"run_mode": "bridge-assisted"}), "screenshot_id"),
    ],
)
def test_mismatched_or_missing_provenance_rejects(
    snapshot_response: BridgeSnapshotResponse,
    message: str,
) -> None:
    with pytest.raises(BridgeSnapshotResponseError, match=message):
        unwrap_bridge_snapshot_response(snapshot_response, request())


@pytest.mark.parametrize("field_name", ["request_id", "run_id"])
@pytest.mark.parametrize("value", ["", "   "])
def test_blank_envelope_ids_reject(field_name: str, value: str) -> None:
    values: dict[str, object] = {
        "request_id": "request-1",
        "run_id": "run-1",
        "payload": {"run_mode": "bridge-assisted", "screenshot_id": "shot-1"},
    }
    values[field_name] = value

    with pytest.raises(ValidationError):
        BridgeSnapshotResponse(**values)


def test_unknown_and_forbidden_payload_fields_remain_unchanged_until_sanitization() -> None:
    raw_payload = {
        "run_mode": "bridge-assisted",
        "screenshot_id": "shot-1",
        "unknown_visible_state": "must remain raw",
        "map_id": 17,
    }
    snapshot_response = response(payload=raw_payload)

    unwrapped = unwrap_bridge_snapshot_response(snapshot_response, request())

    assert unwrapped["unknown_visible_state"] == "must remain raw"
    assert unwrapped["map_id"] == 17
    with pytest.raises(ForbiddenBridgeFieldError):
        sanitize_bridge_payload(unwrapped)


def test_response_model_is_frozen_and_forbids_extra_envelope_fields() -> None:
    snapshot_response = response()

    with pytest.raises(ValidationError):
        snapshot_response.request_id = "other-request"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        BridgeSnapshotResponse(
            request_id="request-1",
            run_id="run-1",
            payload={"run_mode": "bridge-assisted", "screenshot_id": "shot-1"},
            extra="not-permitted",
        )


def test_javascript_response_builder_is_exported_and_reuses_scene_payload_builder() -> None:
    source = BRIDGE_SOURCE_PATH.read_text(encoding="utf-8")

    assert "function buildSnapshotResponse(request, sceneRoot)" in source
    assert "const payload = buildSnapshotFromScene(request, sceneRoot);" in source
    assert "request_id: request.request_id" in source
    assert "run_id: request.run_id" in source
    assert "payload: payload" in source
    assert "buildSnapshotResponse: buildSnapshotResponse" in source


def test_javascript_response_builder_has_no_hidden_state_or_runtime_access() -> None:
    source = BRIDGE_SOURCE_PATH.read_text(encoding="utf-8")
    forbidden_identifiers = (
        "$gameMessage",
        "$gameMap",
        "$gamePlayer",
        "$gameSwitches",
        "$gameVariables",
        "$data",
        "_textState",
        "require(",
        "fs.",
        "setInterval(",
        "setTimeout(",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "child_process",
        "Input",
    )

    assert not any(identifier in source for identifier in forbidden_identifiers)
