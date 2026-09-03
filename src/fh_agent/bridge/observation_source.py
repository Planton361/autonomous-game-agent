"""Bridge-local adapter from raw visible payloads to canonical observations."""

from collections.abc import Mapping
from typing import Any, Protocol, cast

from fh_agent.bridge.bridge_server import VisibleBridgeAdapter
from fh_agent.bridge.evidence_sync import (
    BridgeEvidenceSynchronizationError,
    BridgeScreenshotEvidenceLookup,
)
from fh_agent.bridge.sanitizer import BridgeRunMode
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSourceExhausted


class BridgePayloadSource(Protocol):
    """Provides one raw visible bridge payload at a time."""

    def next_payload(self) -> Mapping[str, Any]:
        """Return the next raw bridge payload."""


class BridgePayloadSourceExhausted(RuntimeError):
    """Raised when a raw bridge payload source has no payload remaining."""


class BridgeRunModeMismatchError(ValueError):
    """Raised when a valid payload changes the source's declared bridge mode."""


class BridgeObservationSource:
    """Adapt one visible bridge payload per observation request."""

    def __init__(
        self,
        payload_source: BridgePayloadSource,
        *,
        run_id: str,
        expected_run_mode: BridgeRunMode,
        screenshot_evidence_lookup: BridgeScreenshotEvidenceLookup | None = None,
    ) -> None:
        if expected_run_mode == "bridge-assisted" and screenshot_evidence_lookup is None:
            msg = "bridge-assisted observation sources require screenshot evidence lookup"
            raise BridgeEvidenceSynchronizationError(msg)

        self._payload_source = payload_source
        self._run_id = run_id
        self._expected_run_mode = expected_run_mode
        self._screenshot_evidence_lookup = screenshot_evidence_lookup
        self._adapter = VisibleBridgeAdapter()

    def observe(self) -> Observation:
        """Return the next canonical observation from exactly one raw payload."""

        try:
            raw_payload = self._payload_source.next_payload()
        except BridgePayloadSourceExhausted as exc:
            raise ObservationSourceExhausted from exc

        receipt = self._adapter.accept_observation_payload(raw_payload, run_id=self._run_id)
        if receipt.run_mode != self._expected_run_mode:
            raise BridgeRunModeMismatchError(
                f"expected bridge run mode {self._expected_run_mode!r}, "
                f"received {receipt.run_mode!r}"
            )

        observation = cast(Observation, receipt.observation)
        if self._expected_run_mode == "bridge-assisted":
            self._require_current_screenshot_evidence(observation)

        return observation

    def _require_current_screenshot_evidence(self, observation: Observation) -> None:
        screenshot_id = observation.screenshot_id
        if not screenshot_id:
            msg = "bridge-assisted payload is missing screenshot_id"
            raise BridgeEvidenceSynchronizationError(msg)

        lookup = self._screenshot_evidence_lookup
        if lookup is None:
            msg = "bridge-assisted observation source has no screenshot evidence lookup"
            raise BridgeEvidenceSynchronizationError(msg)

        latest_screenshot_evidence_id = lookup.latest_screenshot_evidence_id(run_id=self._run_id)
        if latest_screenshot_evidence_id is None:
            msg = "no durable screenshot evidence exists for bridge-assisted run"
            raise BridgeEvidenceSynchronizationError(msg)
        if screenshot_id != latest_screenshot_evidence_id:
            msg = (
                "bridge-assisted payload screenshot_id does not match latest durable "
                "screenshot evidence"
            )
            raise BridgeEvidenceSynchronizationError(msg)
