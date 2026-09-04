"""Append-only local JSONL source for raw bridge payload objects."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fh_agent.bridge.observation_source import BridgePayloadSourceExhausted


class JsonlBridgePayloadError(ValueError):
    """Base error for local JSONL feed records that cannot be accepted."""


class InvalidJsonlBridgePayloadError(JsonlBridgePayloadError):
    """Raised when one complete JSONL record is not a UTF-8 JSON object."""


class JsonlBridgeFeedConsistencyError(JsonlBridgePayloadError):
    """Raised when an already-consumed append-only feed disappears or truncates."""


class JsonlBridgePayloadSource:
    """Read one complete raw JSON object at a time from an append-only local feed."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._offset = 0
        self._has_consumed_payload = False

    def next_payload(self) -> Mapping[str, Any]:
        """Return the next complete JSON object without reading ahead."""

        try:
            file_size = self._path.stat().st_size
        except FileNotFoundError as exc:
            if self._has_consumed_payload:
                msg = "append-only JSONL bridge feed disappeared after consumption"
                raise JsonlBridgeFeedConsistencyError(msg) from exc
            raise BridgePayloadSourceExhausted from exc

        if self._offset and file_size < self._offset:
            msg = "append-only JSONL bridge feed was truncated after consumption"
            raise JsonlBridgeFeedConsistencyError(msg)

        with self._path.open("rb") as file:
            file.seek(self._offset)
            raw_line = file.readline()
            next_offset = file.tell()

        if not raw_line or not raw_line.endswith(b"\n"):
            raise BridgePayloadSourceExhausted

        try:
            decoded_line = raw_line.decode("utf-8")
        except UnicodeDecodeError as exc:
            msg = "JSONL bridge payload is not valid UTF-8"
            raise InvalidJsonlBridgePayloadError(msg) from exc

        try:
            payload = json.loads(decoded_line)
        except json.JSONDecodeError as exc:
            msg = "JSONL bridge payload is not valid JSON"
            raise InvalidJsonlBridgePayloadError(msg) from exc

        if not isinstance(payload, dict):
            msg = "JSONL bridge payload root must be an object"
            raise InvalidJsonlBridgePayloadError(msg)

        self._offset = next_offset
        self._has_consumed_payload = True
        return payload
