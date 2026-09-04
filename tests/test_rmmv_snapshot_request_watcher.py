import json
import shutil
import subprocess
from pathlib import Path

import pytest

from fh_agent.bridge.jsonl_payload_source import JsonlBridgePayloadSource
from fh_agent.bridge.snapshot_relay import relay_bridge_snapshot_response
from fh_agent.bridge.snapshot_response import (
    BridgeSnapshotResponse,
    unwrap_bridge_snapshot_response,
)
from fh_agent.bridge_snapshot_host import capture_and_publish_bridge_snapshot_request
from fh_agent.memory.event_log import EventLogger
from fh_agent.memory.evidence import EvidenceStore
from fh_agent.perception.screen_capture import DummyScreenCapture

BRIDGE_DIR = Path(__file__).parents[1] / "bridge"
CORE_BRIDGE_PATH = BRIDGE_DIR / "rmmv_visible_bridge.js"
TRANSPORT_PATH = BRIDGE_DIR / "rmmv_snapshot_file_transport.js"
WATCHER_PATH = BRIDGE_DIR / "rmmv_snapshot_request_watcher.js"
NODE = shutil.which("node")
requires_node = pytest.mark.skipif(NODE is None, reason="node is not available")


def watcher_harness() -> str:
    return f"""
global.window = {{}};
window.Window_Message = function Window_Message() {{}};
const root = {{ visible: true, renderable: true, children: [] }};
const message = new window.Window_Message();
message.visible = true;
message.renderable = true;
message.openness = 255;
message.parent = root;
root.children.push(message);
window.SceneManager = {{ _scene: root }};
require({json.dumps(str(CORE_BRIDGE_PATH))});
require({json.dumps(str(TRANSPORT_PATH))});
require({json.dumps(str(WATCHER_PATH))});
const control = window.FHVisibleBridgeSnapshotWatcher.start({{
  exchangeDirectory: process.argv[1],
  maxRequests: Number(process.argv[2]),
}});
if (control === null) {{
  process.exit(2);
}}
process.stdout.write("ready\\n");
"""


def start_real_watcher(exchange_directory: Path, max_requests: int) -> subprocess.Popen[str]:
    assert NODE is not None
    watcher = subprocess.Popen(
        [NODE, "-e", watcher_harness(), str(exchange_directory), str(max_requests)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert watcher.stdout is not None
    assert watcher.stdout.readline() == "ready\n"
    return watcher


def complete_watcher(watcher: subprocess.Popen[str]) -> tuple[str, str]:
    try:
        stdout, stderr = watcher.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        watcher.kill()
        stdout, stderr = watcher.communicate()
        pytest.fail(f"watcher did not close; stdout={stdout!r}, stderr={stderr!r}")
    assert watcher.returncode == 0, stderr
    return stdout, stderr


def fake_watch_harness(*, filename: str, max_requests: int, duplicate: bool = False) -> str:
    return f"""
const Module = require("module");
const originalRequire = Module.prototype.require;
let callback = null;
let closeCount = 0;
let calls = [];
const fakeFs = {{
  statSync: function () {{ return {{ isDirectory: function () {{ return true; }} }}; }},
  watch: function (_directory, watcherCallback) {{
    callback = watcherCallback;
    return {{ close: function () {{ closeCount += 1; }} }};
  }},
}};
Module.prototype.require = function (name) {{
  if (name === "fs") {{ return fakeFs; }}
  return originalRequire.apply(this, arguments);
}};
global.window = {{
  SceneManager: {{ _scene: {{ rendered: true }} }},
  FHVisibleBridgeFileTransport: {{
    processSnapshotFiles: function (requestPath, responsePath, sceneRoot) {{
      calls.push({{ requestPath: requestPath, responsePath: responsePath, sceneRoot: sceneRoot }});
      return false;
    }},
  }},
}};
require({json.dumps(str(WATCHER_PATH))});
const control = window.FHVisibleBridgeSnapshotWatcher.start({{
  exchangeDirectory: "/exchange",
  maxRequests: {max_requests},
}});
callback("rename", {json.dumps(filename)});
{f'callback("change", {json.dumps(filename)});' if duplicate else ""}
control.close();
control.close();
process.stdout.write(JSON.stringify({{ calls: calls, closeCount: closeCount }}));
"""


def run_fake_watch(
    *, filename: str, max_requests: int, duplicate: bool = False
) -> dict[str, object]:
    assert NODE is not None
    completed = subprocess.run(
        [
            NODE,
            "-e",
            fake_watch_harness(filename=filename, max_requests=max_requests, duplicate=duplicate),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def components(tmp_path: Path) -> tuple[EvidenceStore, EventLogger]:
    return (
        EvidenceStore(tmp_path / "screenshots", run_id="run-1", id_factory=lambda: "shot-1"),
        EventLogger(tmp_path / "events.jsonl", run_id="run-1", id_factory=lambda: "event-1"),
    )


def test_watcher_is_separate_and_existing_visible_transport_files_remain_watcher_free() -> None:
    watcher_source = WATCHER_PATH.read_text(encoding="utf-8")

    assert "window.FHVisibleBridgeSnapshotWatcher" in watcher_source
    for existing_path in (CORE_BRIDGE_PATH, TRANSPORT_PATH):
        assert "FHVisibleBridgeSnapshotWatcher" not in existing_path.read_text(encoding="utf-8")


def test_watcher_source_has_bounded_watch_only_filename_and_scene_contracts() -> None:
    source = WATCHER_PATH.read_text(encoding="utf-8")

    assert "isPositiveFiniteInteger(options.maxRequests)" in source
    assert "dependencies.fs.watch(options.exchangeDirectory, processRequestEvent)" in source
    assert "REQUEST_FILENAME.test(filename)" in source
    assert "attemptedFilenames[filename] === true" in source
    assert "attempts += 1" in source
    assert "if (attempts >= options.maxRequests)" in source
    assert "watcher.close()" in source
    assert source.count("window.SceneManager._scene") == 3
    assert "processSnapshotFiles(" in source


def test_watcher_source_has_no_hidden_state_polling_network_input_or_feed_authority() -> None:
    source = WATCHER_PATH.read_text(encoding="utf-8")
    forbidden = (
        "$game",
        "$data",
        "Game_Event",
        "_textState",
        "game_switch",
        "game_variable",
        "map_id",
        "event_id",
        "save",
        "setInterval(",
        "setTimeout(",
        "while (",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "socket",
        "http",
        "Input",
        "sanitize",
        "JSONL",
        "unlink",
    )

    assert not any(identifier in source for identifier in forbidden)


@requires_node
def test_duplicate_events_are_deduplicated_and_close_is_idempotent() -> None:
    result = run_fake_watch(filename="request-1.request.json", max_requests=2, duplicate=True)

    assert len(result["calls"]) == 1
    assert result["closeCount"] == 1


@requires_node
def test_unrelated_and_unsafe_filenames_are_ignored() -> None:
    for filename in ("other.txt", "../escape.request.json", "request.request.json.tmp"):
        result = run_fake_watch(filename=filename, max_requests=2)

        assert result["calls"] == []
        assert result["closeCount"] == 1


@requires_node
def test_matching_attempt_consumes_budget_before_transport_rejection() -> None:
    result = run_fake_watch(filename="malformed.request.json", max_requests=1)

    assert len(result["calls"]) == 1
    assert result["closeCount"] == 1


@requires_node
def test_watcher_processes_m024_request_then_response_relay_and_jsonl_readback(
    tmp_path: Path,
) -> None:
    exchange_directory = tmp_path / "exchange"
    exchange_directory.mkdir()
    evidence_store, event_logger = components(tmp_path)
    watcher = start_real_watcher(exchange_directory, max_requests=1)
    request_path = exchange_directory / "capture-1.request.json"
    response_path = exchange_directory / "capture-1.response.json"

    host_result = capture_and_publish_bridge_snapshot_request(
        DummyScreenCapture(),
        evidence_store,
        event_logger,
        run_id="run-1",
        request_id="request-1",
        request_path=request_path,
    )
    request_before = request_path.read_bytes()
    complete_watcher(watcher)

    response = BridgeSnapshotResponse.model_validate_json(response_path.read_text(encoding="utf-8"))
    assert unwrap_bridge_snapshot_response(response, host_result.request) == {
        "run_mode": "bridge-assisted",
        "screenshot_id": host_result.evidence_record.evidence_id,
        "ui_state": "dialogue",
    }
    assert request_path.read_bytes() == request_before

    feed_path = tmp_path / "feed.jsonl"
    relay_bridge_snapshot_response(
        host_result.request,
        response_path=response_path,
        feed_path=feed_path,
    )
    assert JsonlBridgePayloadSource(feed_path).next_payload() == {
        "run_mode": "bridge-assisted",
        "screenshot_id": host_result.evidence_record.evidence_id,
        "ui_state": "dialogue",
    }


@requires_node
def test_malformed_request_and_existing_response_are_bounded_without_mutation(
    tmp_path: Path,
) -> None:
    malformed_exchange = tmp_path / "malformed"
    malformed_exchange.mkdir()
    malformed_request = malformed_exchange / "bad.request.json"
    malformed_response = malformed_exchange / "bad.response.json"
    malformed_watcher = start_real_watcher(malformed_exchange, max_requests=1)
    malformed_request.write_bytes(b"not valid JSON\n")
    malformed_before = malformed_request.read_bytes()
    complete_watcher(malformed_watcher)

    assert malformed_request.read_bytes() == malformed_before
    assert not malformed_response.exists()

    existing_exchange = tmp_path / "existing"
    existing_exchange.mkdir()
    evidence_store, event_logger = components(tmp_path)
    existing_response = existing_exchange / "capture.response.json"
    existing_response.write_bytes(b"existing response\n")
    existing_watcher = start_real_watcher(existing_exchange, max_requests=1)
    host_result = capture_and_publish_bridge_snapshot_request(
        DummyScreenCapture(),
        evidence_store,
        event_logger,
        run_id="run-1",
        request_id="request-1",
        request_path=existing_exchange / "capture.request.json",
    )
    request_before = host_result.request_path.read_bytes()
    complete_watcher(existing_watcher)

    assert existing_response.read_bytes() == b"existing response\n"
    assert host_result.request_path.read_bytes() == request_before
