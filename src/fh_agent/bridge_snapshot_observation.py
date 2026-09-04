"""Bounded host composition from a visible capture to one bridge Observation."""

import math
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.jsonl_payload_source import JsonlBridgePayloadSource
from fh_agent.bridge.observation_source import BridgeObservationSource
from fh_agent.bridge.snapshot_relay import relay_bridge_snapshot_response
from fh_agent.bridge_snapshot_host import capture_and_publish_bridge_snapshot_request
from fh_agent.memory.event_log import EventLogger
from fh_agent.memory.evidence import EvidenceStore
from fh_agent.observation.schemas import Observation
from fh_agent.perception.screen_capture import ScreenCapture

_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")


class BridgeSnapshotResponseWaiter(Protocol):
    """Wait for one response artifact to become available."""

    def wait_for_response(self, path: Path) -> None:
        """Return only after the response target exists."""


class BridgeSnapshotResponseWaitTimeoutError(TimeoutError):
    """Raised when a response does not arrive within the configured bound."""


class BridgeSnapshotObservationPreflightError(ValueError):
    """Raised when an observation cycle cannot safely begin."""


class BoundedBridgeSnapshotResponseWaiter:
    """Poll one response path with an explicit monotonic-clock time bound."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._require_positive_finite("timeout_seconds", timeout_seconds)
        self._require_positive_finite("poll_interval_seconds", poll_interval_seconds)
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep

    def wait_for_response(self, path: Path) -> None:
        """Wait until ``path`` exists, failing closed at the monotonic deadline."""

        deadline = self._clock() + self._timeout_seconds
        while True:
            remaining_seconds = deadline - self._clock()
            if path.exists() and remaining_seconds >= 0:
                return
            if remaining_seconds <= 0:
                msg = f"bridge snapshot response did not arrive before timeout: {path}"
                raise BridgeSnapshotResponseWaitTimeoutError(msg)
            self._sleep(min(self._poll_interval_seconds, remaining_seconds))

    @staticmethod
    def _require_positive_finite(name: str, value: float) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            msg = f"{name} must be a positive finite number"
            raise ValueError(msg)
        if value <= 0:
            msg = f"{name} must be a positive finite number"
            raise ValueError(msg)


class BridgeSnapshotObservationSource:
    """Compose one request-correlated visible bridge cycle per observation."""

    def __init__(
        self,
        capture: ScreenCapture,
        evidence_store: EvidenceStore,
        event_logger: EventLogger,
        response_waiter: BridgeSnapshotResponseWaiter,
        *,
        run_id: str,
        exchange_directory: Path,
        feed_path: Path,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._capture = capture
        self._evidence_store = evidence_store
        self._event_logger = event_logger
        self._response_waiter = response_waiter
        self._run_id = run_id
        self._exchange_directory = exchange_directory
        self._feed_path = feed_path
        self._request_id_factory = request_id_factory or (lambda: uuid4().hex)
        self._has_started_cycle = False
        self._payload_source = JsonlBridgePayloadSource(feed_path)
        self._observation_source = BridgeObservationSource(
            self._payload_source,
            run_id=run_id,
            expected_run_mode="bridge-assisted",
            screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_logger.path),
        )

    def observe(self) -> Observation:
        """Capture, request, await, relay, and return one canonical Observation."""

        request_id = self._request_id_factory()
        request_path, response_path = self._preflight(request_id)
        self._has_started_cycle = True
        host_result = capture_and_publish_bridge_snapshot_request(
            self._capture,
            self._evidence_store,
            self._event_logger,
            run_id=self._run_id,
            request_id=request_id,
            request_path=request_path,
        )
        self._response_waiter.wait_for_response(response_path)
        relay_bridge_snapshot_response(
            host_result.request,
            response_path=response_path,
            feed_path=self._feed_path,
        )
        return self._observation_source.observe()

    def _preflight(self, request_id: str) -> tuple[Path, Path]:
        if self._run_id != self._evidence_store.run_id or self._run_id != self._event_logger.run_id:
            msg = "bridge snapshot observation run IDs must match before capture"
            raise BridgeSnapshotObservationPreflightError(msg)
        if not self._exchange_directory.is_dir():
            msg = (
                f"bridge snapshot exchange directory is not a directory: {self._exchange_directory}"
            )
            raise BridgeSnapshotObservationPreflightError(msg)
        if not self._feed_path.parent.is_dir():
            msg = f"bridge snapshot feed parent is not a directory: {self._feed_path.parent}"
            raise BridgeSnapshotObservationPreflightError(msg)
        if not isinstance(request_id, str) or _REQUEST_ID_PATTERN.fullmatch(request_id) is None:
            msg = "bridge snapshot request ID is not a safe filesystem token"
            raise BridgeSnapshotObservationPreflightError(msg)

        request_path = self._exchange_directory / f"{request_id}.request.json"
        response_path = self._exchange_directory / f"{request_id}.response.json"
        if request_path.exists():
            msg = f"bridge snapshot request target already exists: {request_path}"
            raise BridgeSnapshotObservationPreflightError(msg)
        if response_path.exists():
            msg = f"bridge snapshot response target already exists: {response_path}"
            raise BridgeSnapshotObservationPreflightError(msg)
        if (
            not self._has_started_cycle
            and self._feed_path.exists()
            and self._feed_path.stat().st_size
        ):
            msg = "dedicated bridge snapshot feed must be empty before first observation"
            raise BridgeSnapshotObservationPreflightError(msg)

        return request_path, response_path
