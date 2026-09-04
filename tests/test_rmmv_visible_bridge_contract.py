import re
from pathlib import Path

import pytest

from fh_agent.bridge.sanitizer import (
    FORBIDDEN_BRIDGE_FIELDS,
    VISIBLE_BRIDGE_FIELDS,
    ForbiddenBridgeFieldError,
    UnknownBridgeFieldError,
    sanitize_bridge_payload,
)

BRIDGE_SOURCE_PATH = Path(__file__).parents[1] / "bridge" / "rmmv_visible_bridge.js"


@pytest.fixture(scope="module")
def bridge_source() -> str:
    return BRIDGE_SOURCE_PATH.read_text(encoding="utf-8")


def test_existing_allowlist_and_forbidden_list_remain_intact(bridge_source: str) -> None:
    allowed_match = re.search(
        r"const ALLOWED_FIELDS = Object\.freeze\(\[(.*?)\]\);",
        bridge_source,
        flags=re.DOTALL,
    )
    forbidden_match = re.search(
        r"const FORBIDDEN_FIELDS = Object\.freeze\(\[(.*?)\]\);",
        bridge_source,
        flags=re.DOTALL,
    )

    assert allowed_match is not None
    assert forbidden_match is not None
    assert set(re.findall(r'"([^\"]+)"', allowed_match.group(1))) == VISIBLE_BRIDGE_FIELDS
    assert set(re.findall(r'"([^\"]+)"', forbidden_match.group(1))) == FORBIDDEN_BRIDGE_FIELDS


def test_builder_is_exported_through_visible_bridge_namespace(bridge_source: str) -> None:
    assert "function buildSnapshotPayload(request, visibleSurface)" in bridge_source
    assert "buildSnapshotPayload: buildSnapshotPayload" in bridge_source
    assert "window.FHVisibleBridge" in bridge_source


def test_request_screenshot_id_is_the_only_payload_screenshot_source(bridge_source: str) -> None:
    assert "screenshot_id: request.screenshot_id" in bridge_source
    assert 'field === "screenshot_id"' in bridge_source
    assert "visible surface must not provide screenshot_id" in bridge_source


def test_request_and_visible_surface_contract_reject_metadata_override_and_unknown_fields(
    bridge_source: str,
) -> None:
    assert 'request.run_mode !== "bridge-assisted"' in bridge_source
    assert "SNAPSHOT_REQUEST_FIELDS.indexOf(field) === -1" in bridge_source
    assert "FORBIDDEN_FIELDS.indexOf(field) !== -1" in bridge_source
    assert "ALLOWED_FIELDS.indexOf(field) === -1" in bridge_source


def test_builder_output_is_limited_to_existing_raw_bridge_fields(bridge_source: str) -> None:
    assert "run_mode: request.run_mode" in bridge_source
    assert "screenshot_id: request.screenshot_id" in bridge_source
    assert "payload[field] = visibleSurface[field]" in bridge_source
    assert "request_id:" not in bridge_source
    assert "run_id:" not in bridge_source


def test_builder_source_has_no_hidden_state_or_io_access(bridge_source: str) -> None:
    forbidden_identifiers = (
        "$gameMap",
        "$gameSwitches",
        "$gameVariables",
        "$dataMap",
        "$dataEnemies",
        "$dataItems",
        "require(",
        "fs.",
        "setInterval(",
        "setTimeout(",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "child_process",
    )

    assert not any(identifier in bridge_source for identifier in forbidden_identifiers)


def test_representative_valid_builder_payload_passes_existing_sanitizer() -> None:
    payload = {
        "run_mode": "bridge-assisted",
        "ui_state": "dialogue",
        "visible_message_text": "Visible line.",
        "screenshot_id": "shot-1",
    }

    assert sanitize_bridge_payload(payload) == {
        "ui_state": "dialogue",
        "visible_message_text": "Visible line.",
        "screenshot_id": "shot-1",
    }


@pytest.mark.parametrize(
    ("field", "error_type"),
    [
        ("map_id", ForbiddenBridgeFieldError),
        ("unexpected_visible_state", UnknownBridgeFieldError),
    ],
)
def test_forbidden_or_unknown_raw_payload_still_fails_existing_sanitizer(
    field: str,
    error_type: type[ValueError],
) -> None:
    with pytest.raises(error_type):
        sanitize_bridge_payload(
            {
                "run_mode": "bridge-assisted",
                "screenshot_id": "shot-1",
                field: "must remain downstream-visible",
            }
        )
