"""Bridge-local adapter from raw visible payloads to canonical observations."""

from collections.abc import Mapping
from typing import Any, Protocol, cast

from fh_agent.bridge.bridge_server import VisibleBridgeAdapter
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
    ) -> None:
        self._payload_source = payload_source
        self._run_id = run_id
        self._expected_run_mode = expected_run_mode
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

        return cast(Observation, receipt.observation)
