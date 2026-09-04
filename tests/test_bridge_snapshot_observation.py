import inspect
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

import fh_agent.bridge_snapshot_observation as bridge_snapshot_observation_module
from fh_agent.bridge.observation_source import BridgePayloadSourceExhausted
from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError
from fh_agent.bridge.snapshot_relay import BridgeSnapshotRelayError
from fh_agent.bridge_snapshot_observation import (
    BoundedBridgeSnapshotResponseWaiter,
    BridgeSnapshotObservationPreflightError,
    BridgeSnapshotObservationSource,
    BridgeSnapshotResponseWaitTimeoutError,
)
from fh_agent.memory.event_log import EventLogger
from fh_agent.memory.evidence import EvidenceStore
from fh_agent.perception.screen_capture import DummyScreenCapture

BRIDGE_DIR = Path(__file__).parents[1] / "bridge"
CORE_BRIDGE_PATH = BRIDGE_DIR / "rmmv_visible_bridge.js"
TRANSPORT_PATH = BRIDGE_DIR / "rmmv_snapshot_file_transport.js"
WATCHER_PATH = BRIDGE_DIR / "rmmv_snapshot_request_watcher.js"
NODE = shutil.which("node")
requires_node = pytest.mark.skipif(NODE is None, reason="node is not available")


class SequenceFactory:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._count = 0

    def __call__(self) -> str:
        value = f"{self._prefix}-{self._count}"
        self._count += 1
        return value


class WritingWaiter:
    def __init__(self, response_factory: Callable[[str], dict[str, object]]) -> None:
        self._response_factory = response_factory
        self.paths: list[Path] = []

    def wait_for_response(self, path: Path) -> None:
        self.paths.append(path)
        request_id = path.name.removesuffix(".response.json")
        path.write_text(
            json.dumps(self._response_factory(request_id), separators=(",", ":")) + "\n",
            encoding="utf-8",
        )


class AdvancingClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


def response_for(
    request_id: str,
    *,
    run_id: str = "run-1",
    screenshot_id: str = "shot-0",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "run_id": run_id,
        "payload": payload
        or {
            "run_mode": "bridge-assisted",
            "screenshot_id": screenshot_id,
            "ui_state": "dialogue",
        },
    }


def components(tmp_path: Path, *, run_id: str = "run-1") -> tuple[EvidenceStore, EventLogger]:
    return (
        EvidenceStore(tmp_path / "screenshots", run_id=run_id, id_factory=SequenceFactory("shot")),
        EventLogger(tmp_path / "events.jsonl", run_id=run_id, id_factory=SequenceFactory("event")),
    )


def source(
    tmp_path: Path,
    waiter: object,
    *,
    request_ids: Callable[[], str] | None = None,
    evidence_store: EvidenceStore | None = None,
    event_logger: EventLogger | None = None,
    capture: DummyScreenCapture | None = None,
) -> BridgeSnapshotObservationSource:
    exchange = tmp_path / "exchange"
    exchange.mkdir(exist_ok=True)
    store, logger = (
        (evidence_store, event_logger) if evidence_store and event_logger else components(tmp_path)
    )
    return BridgeSnapshotObservationSource(
        capture or DummyScreenCapture(),
        store,
        logger,
        waiter,  # type: ignore[arg-type]
        run_id="run-1",
        exchange_directory=exchange,
        feed_path=tmp_path / "feed.jsonl",
        request_id_factory=request_ids or SequenceFactory("request"),
    )


def test_one_observe_creates_one_capture_evidence_request_response_feed_and_observation(
    tmp_path: Path,
) -> None:
    capture = DummyScreenCapture()
    waiter = WritingWaiter(lambda request_id: response_for(request_id))
    observation_source = source(tmp_path, waiter, capture=capture)

    observation = observation_source.observe()

    assert capture.capture_count == 1
    assert len(EventLogger(tmp_path / "events.jsonl", run_id="run-1").read_all()) == 1
    assert (tmp_path / "exchange" / "request-0.request.json").is_file()
    assert (tmp_path / "exchange" / "request-0.response.json").is_file()
    assert len((tmp_path / "feed.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert observation.run_id == "run-1"


def test_observation_screenshot_id_is_the_exact_captured_evidence_id(tmp_path: Path) -> None:
    observation = source(
        tmp_path, WritingWaiter(lambda request_id: response_for(request_id))
    ).observe()

    assert observation.screenshot_id == "shot-0"
    assert observation.evidence_ids == ["shot-0"]


def test_two_sequential_observes_consume_two_appended_records_once(tmp_path: Path) -> None:
    def write_response(request_id: str) -> dict[str, object]:
        screenshot_id = "shot-0" if request_id == "request-0" else "shot-1"
        return response_for(request_id, screenshot_id=screenshot_id)

    observation_source = source(tmp_path, WritingWaiter(write_response))

    first = observation_source.observe()
    second = observation_source.observe()

    assert [first.screenshot_id, second.screenshot_id] == ["shot-0", "shot-1"]
    assert len((tmp_path / "feed.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    with pytest.raises(BridgePayloadSourceExhausted):
        observation_source._payload_source.next_payload()


def test_bounded_waiter_times_out_deterministically_with_injected_clock_and_sleep(
    tmp_path: Path,
) -> None:
    clock = AdvancingClock()
    waiter = BoundedBridgeSnapshotResponseWaiter(
        timeout_seconds=1.0,
        poll_interval_seconds=0.4,
        clock=clock,
        sleep=clock.sleep,
    )

    with pytest.raises(BridgeSnapshotResponseWaitTimeoutError, match="did not arrive"):
        waiter.wait_for_response(tmp_path / "missing.response.json")

    assert clock.sleeps == [0.4, 0.4, 0.19999999999999996]


def test_timeout_preserves_durable_evidence_and_request_without_feed_payload(
    tmp_path: Path,
) -> None:
    clock = AdvancingClock()
    observation_source = source(
        tmp_path,
        BoundedBridgeSnapshotResponseWaiter(
            timeout_seconds=1.0,
            poll_interval_seconds=1.0,
            clock=clock,
            sleep=clock.sleep,
        ),
    )

    with pytest.raises(BridgeSnapshotResponseWaitTimeoutError):
        observation_source.observe()

    assert (tmp_path / "screenshots" / "run-1" / "shot-0.ppm").is_file()
    assert (tmp_path / "exchange" / "request-0.request.json").is_file()
    assert not (tmp_path / "feed.jsonl").exists()


def test_malformed_response_leaves_feed_unchanged(tmp_path: Path) -> None:
    waiter = WritingWaiter(lambda _request_id: {"not": "a response"})
    observation_source = source(tmp_path, waiter)

    with pytest.raises(BridgeSnapshotRelayError, match="envelope"):
        observation_source.observe()

    assert not (tmp_path / "feed.jsonl").exists()


@pytest.mark.parametrize(
    "response_factory",
    [
        lambda _request_id: response_for("other-request"),
        lambda request_id: response_for(request_id, run_id="other-run"),
        lambda request_id: response_for(request_id, screenshot_id="other-shot"),
    ],
)
def test_request_run_or_screenshot_mismatch_leaves_feed_unchanged(
    tmp_path: Path, response_factory: Callable[[str], dict[str, object]]
) -> None:
    observation_source = source(tmp_path, WritingWaiter(response_factory))

    with pytest.raises(BridgeSnapshotRelayError, match="does not match"):
        observation_source.observe()

    assert not (tmp_path / "feed.jsonl").exists()


def test_unsafe_request_token_rejects_before_capture(tmp_path: Path) -> None:
    capture = DummyScreenCapture()
    observation_source = source(
        tmp_path,
        WritingWaiter(lambda request_id: response_for(request_id)),
        request_ids=lambda: "../unsafe",
        capture=capture,
    )

    with pytest.raises(BridgeSnapshotObservationPreflightError, match="safe filesystem"):
        observation_source.observe()

    assert capture.capture_count == 0


def test_existing_response_rejects_before_capture(tmp_path: Path) -> None:
    capture = DummyScreenCapture()
    exchange = tmp_path / "exchange"
    exchange.mkdir()
    (exchange / "request-0.response.json").write_text("existing\n", encoding="utf-8")
    store, logger = components(tmp_path)
    observation_source = BridgeSnapshotObservationSource(
        capture,
        store,
        logger,
        WritingWaiter(lambda request_id: response_for(request_id)),
        run_id="run-1",
        exchange_directory=exchange,
        feed_path=tmp_path / "feed.jsonl",
        request_id_factory=lambda: "request-0",
    )

    with pytest.raises(BridgeSnapshotObservationPreflightError, match="response target"):
        observation_source.observe()

    assert capture.capture_count == 0


def test_non_empty_initial_feed_rejects_before_capture(tmp_path: Path) -> None:
    capture = DummyScreenCapture()
    (tmp_path / "feed.jsonl").write_text('{"existing":true}\n', encoding="utf-8")
    observation_source = source(
        tmp_path,
        WritingWaiter(lambda request_id: response_for(request_id)),
        capture=capture,
    )

    with pytest.raises(BridgeSnapshotObservationPreflightError, match="must be empty"):
        observation_source.observe()

    assert capture.capture_count == 0


def test_forbidden_raw_map_id_is_relayed_unchanged_then_rejected_downstream(tmp_path: Path) -> None:
    payload = {
        "run_mode": "bridge-assisted",
        "screenshot_id": "shot-0",
        "ui_state": "dialogue",
        "map_id": 3,
    }
    observation_source = source(
        tmp_path,
        WritingWaiter(lambda request_id: response_for(request_id, payload=payload)),
    )

    with pytest.raises(ForbiddenBridgeFieldError, match="map_id"):
        observation_source.observe()

    assert json.loads((tmp_path / "feed.jsonl").read_text(encoding="utf-8")) == payload


def test_valid_cycle_can_follow_a_downstream_forbidden_field_rejection(tmp_path: Path) -> None:
    responses = iter(
        [
            response_for(
                "request-0",
                payload={
                    "run_mode": "bridge-assisted",
                    "screenshot_id": "shot-0",
                    "map_id": 3,
                },
            ),
            response_for("request-1", screenshot_id="shot-1"),
        ]
    )
    observation_source = source(tmp_path, WritingWaiter(lambda _request_id: next(responses)))

    with pytest.raises(ForbiddenBridgeFieldError):
        observation_source.observe()

    observation = observation_source.observe()

    assert observation.screenshot_id == "shot-1"


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
  maxRequests: 1,
}});
if (control === null) {{
  process.exit(2);
}}
process.stdout.write("ready\\n");
"""


@requires_node
def test_node_watcher_composes_with_real_bounded_waiter_and_fake_visible_window(
    tmp_path: Path,
) -> None:
    assert NODE is not None
    exchange = tmp_path / "exchange"
    exchange.mkdir()
    watcher = subprocess.Popen(
        [NODE, "-e", watcher_harness(), str(exchange)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert watcher.stdout is not None
    assert watcher.stdout.readline() == "ready\n"
    store, logger = components(tmp_path)
    observation_source = BridgeSnapshotObservationSource(
        DummyScreenCapture(),
        store,
        logger,
        BoundedBridgeSnapshotResponseWaiter(timeout_seconds=3.0, poll_interval_seconds=0.01),
        run_id="run-1",
        exchange_directory=exchange,
        feed_path=tmp_path / "feed.jsonl",
        request_id_factory=lambda: "capture-1",
    )

    observation = observation_source.observe()
    stdout, stderr = watcher.communicate(timeout=5)

    assert watcher.returncode == 0, stderr
    assert stdout == ""
    assert observation.ui_state == "dialogue"
    assert observation.screenshot_id == "shot-0"


def test_module_has_no_manager_cortex_input_game_state_network_or_threading_authority() -> None:
    source_code = inspect.getsource(bridge_snapshot_observation_module)

    for forbidden in (
        "fh_agent.manager",
        "Cortex",
        "InputExecutor",
        "game-state",
        "socket",
        "http",
        "asyncio",
        "threading",
        "subprocess",
    ):
        assert forbidden not in source_code
