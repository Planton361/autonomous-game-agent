import json
import shutil
import subprocess
from pathlib import Path

import pytest

from fh_agent.bridge.jsonl_payload_source import JsonlBridgePayloadSource
from fh_agent.bridge.snapshot_relay import relay_bridge_snapshot_response
from fh_agent.bridge.snapshot_request import BridgeSnapshotRequest, write_bridge_snapshot_request
from fh_agent.bridge.snapshot_response import (
    BridgeSnapshotResponse,
    unwrap_bridge_snapshot_response,
)

BRIDGE_DIR = Path(__file__).parents[1] / "bridge"
CORE_BRIDGE_PATH = BRIDGE_DIR / "rmmv_visible_bridge.js"
TRANSPORT_PATH = BRIDGE_DIR / "rmmv_snapshot_file_transport.js"

NODE = shutil.which("node")
requires_node = pytest.mark.skipif(NODE is None, reason="node is not available")


def request() -> BridgeSnapshotRequest:
    return BridgeSnapshotRequest(
        request_id="request-1",
        run_id="run-1",
        screenshot_id="shot-1",
    )


def node_harness() -> str:
    return f"""
global.window = {{}};
window.Window_Message = function Window_Message() {{}};
require({json.dumps(str(CORE_BRIDGE_PATH))});
require({json.dumps(str(TRANSPORT_PATH))});
const root = {{ visible: true, renderable: true, children: [] }};
const message = new window.Window_Message();
message.visible = true;
message.renderable = true;
message.openness = 255;
message.parent = root;
root.children.push(message);
const result = window.FHVisibleBridgeFileTransport.processSnapshotFiles(
  process.argv[1],
  process.argv[2],
  root,
);
process.exit(result ? 0 : 1);
"""


def run_transport(request_path: Path, response_path: Path) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    return subprocess.run(
        [NODE, "-e", node_harness(), str(request_path), str(response_path)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_transport_is_separate_from_the_existing_pure_visible_bridge() -> None:
    core_source = CORE_BRIDGE_PATH.read_text(encoding="utf-8")
    transport_source = TRANSPORT_PATH.read_text(encoding="utf-8")

    assert "FHVisibleBridgeFileTransport" not in core_source
    assert "window.FHVisibleBridgeFileTransport" in transport_source
    assert "buildSnapshotResponse(request, sceneRoot)" in transport_source
    assert 'require("fs")' not in core_source
    assert "fs." not in core_source


def test_transport_delegates_to_the_existing_snapshot_response_builder() -> None:
    source = TRANSPORT_PATH.read_text(encoding="utf-8")

    assert "window.FHVisibleBridge.buildSnapshotResponse(request, sceneRoot)" in source
    assert "const request = readCompleteRequest(" in source


def test_transport_has_no_hidden_state_or_runtime_control_access() -> None:
    source = TRANSPORT_PATH.read_text(encoding="utf-8")
    forbidden = (
        "$game",
        "$data",
        "Game_Event",
        "_textState",
        "SceneManager",
        "Input",
        "save",
        "setInterval(",
        "setTimeout(",
        "watch(",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "socket",
        "http",
        "child_process",
        "feed",
    )

    assert not any(identifier in source for identifier in forbidden)


def test_transport_uses_exclusive_temp_and_non_overwriting_publication() -> None:
    source = TRANSPORT_PATH.read_text(encoding="utf-8")

    assert 'fs.openSync(temporaryPath, "wx", 0o600)' in source
    assert "fs.fsyncSync(descriptor)" in source
    assert "fs.linkSync(temporaryPath, responsePath)" in source
    assert "fs.unlinkSync(temporaryPath)" in source
    assert "unlinkSync(requestPath)" not in source


@requires_node
def test_one_shot_transport_composes_request_response_relay_and_jsonl_feed(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    feed_path = tmp_path / "feed.jsonl"
    snapshot_request = request()
    write_bridge_snapshot_request(snapshot_request, request_path)
    request_before = request_path.read_bytes()

    completed = run_transport(request_path, response_path)

    assert completed.returncode == 0, completed.stderr
    assert request_path.read_bytes() == request_before
    snapshot_response = BridgeSnapshotResponse.model_validate_json(
        response_path.read_text(encoding="utf-8")
    )
    assert unwrap_bridge_snapshot_response(snapshot_response, snapshot_request) == {
        "run_mode": "bridge-assisted",
        "screenshot_id": "shot-1",
        "ui_state": "dialogue",
    }
    assert not (tmp_path / "response.json.tmp").exists()

    relay_bridge_snapshot_response(
        snapshot_request,
        response_path=response_path,
        feed_path=feed_path,
    )

    assert JsonlBridgePayloadSource(feed_path).next_payload() == {
        "run_mode": "bridge-assisted",
        "screenshot_id": "shot-1",
        "ui_state": "dialogue",
    }


@requires_node
def test_incomplete_or_wrong_mode_request_produces_no_response(tmp_path: Path) -> None:
    incomplete_request_path = tmp_path / "incomplete-request.json"
    incomplete_response_path = tmp_path / "incomplete-response.json"
    incomplete_request_path.write_bytes(b'{"request_id":"request-1"}')

    assert run_transport(incomplete_request_path, incomplete_response_path).returncode == 1
    assert not incomplete_response_path.exists()

    wrong_mode_request_path = tmp_path / "wrong-mode-request.json"
    wrong_mode_response_path = tmp_path / "wrong-mode-response.json"
    wrong_mode_request_path.write_text(
        json.dumps(
            {
                "request_id": "request-1",
                "run_id": "run-1",
                "run_mode": "debug",
                "screenshot_id": "shot-1",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert run_transport(wrong_mode_request_path, wrong_mode_response_path).returncode == 1
    assert not wrong_mode_response_path.exists()


@requires_node
def test_existing_response_target_is_unchanged_and_request_is_not_deleted(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    write_bridge_snapshot_request(request(), request_path)
    request_before = request_path.read_bytes()
    response_path.write_bytes(b"existing response\n")

    assert run_transport(request_path, response_path).returncode == 1
    assert response_path.read_bytes() == b"existing response\n"
    assert request_path.read_bytes() == request_before
